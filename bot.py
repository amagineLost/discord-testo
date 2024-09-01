import discord
from discord.ext import commands
import os
import aiohttp
import logging
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create intents object and enable all required intents
intents = discord.Intents.default()
intents.members = True
intents.presences = True
intents.message_content = True

# Initialize bot with the specified intents
bot = commands.Bot(command_prefix='!', intents=intents)

ROBLOX_GROUP_ID = '11592051'
ROBLOX_COOKIE = os.getenv('ROBLOX_COOKIE')
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
RANK_NAME_MAPPING_JSON = os.getenv('RANK_NAME_MAPPING')
GAME_ID = 15673118894  # Replace with your actual game ID

# Check if necessary environment variables are set
if not ROBLOX_COOKIE or not DISCORD_TOKEN or not RANK_NAME_MAPPING_JSON:
    raise ValueError("Environment variables ROBLOX_COOKIE, DISCORD_TOKEN, and RANK_NAME_MAPPING must be set.")

# Load rank name mapping from environment variable
try:
    RANK_NAME_MAPPING = json.loads(RANK_NAME_MAPPING_JSON)
except json.JSONDecodeError as e:
    raise ValueError("Invalid JSON format in RANK_NAME_MAPPING environment variable.") from e

# Create a dictionary to track ongoing commands
command_locks = {}
command_rate_limit = 60  # Rate limit in seconds

def days_to_years_days(days):
    years = days // 365
    remaining_days = days % 365
    return years, remaining_days

async def fetch_json(session, url, method='GET', headers=None, json=None):
    try:
        async with session.request(method, url, headers=headers, json=json) as response:
            response.raise_for_status()
            return await response.json()
    except aiohttp.ClientResponseError as e:
        logging.error(f"HTTP Error {e.status}: {e.message} for URL {url}")
        raise Exception(f"HTTP Error {e.status}: {e.message}")
    except aiohttp.ClientError as e:
        logging.error(f"Request Error: {e} for URL {url}")
        raise Exception(f"Request Error: {e}")
    except json.JSONDecodeError as e:
        logging.error(f"JSON Decode Error: {e} for URL {url}")
        raise Exception(f"JSON Decode Error: {e}")

async def get_user_info(username):
    url = "https://users.roblox.com/v1/usernames/users"
    headers = {
        'Cookie': f'.ROBLOSECURITY={ROBLOX_COOKIE}',
        'Content-Type': 'application/json',
    }
    data = {"usernames": [username]}

    async with aiohttp.ClientSession() as session:
        users_data = await fetch_json(session, url, method='POST', headers=headers, json=data)
        users = users_data.get('data', [])
        if not users:
            return None, "User not found"
        user = users[0]
        user_id = user['id']
        display_name = user['displayName']
        
        # Get account creation date
        user_info_url = f"https://users.roblox.com/v1/users/{user_id}"
        user_info_data = await fetch_json(session, user_info_url, headers=headers)
        created_date_str = user_info_data['created']
        created_date = datetime.strptime(created_date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        current_date = datetime.utcnow()
        account_age_days = (current_date - created_date).days
        account_age_years, remaining_days = days_to_years_days(account_age_days)
        
        # Get user avatar URL
        avatar_url = await get_roblox_avatar(session, user_id)
        
        return {
            'id': user_id,
            'display_name': display_name,
            'account_age_years': account_age_years,
            'account_age_days': remaining_days,
            'avatar_url': avatar_url
        }, None

async def get_user_rank_in_group(user_id, group_id):
    url = f"https://groups.roblox.com/v1/users/{user_id}/groups/roles"
    headers = {
        'Cookie': f'.ROBLOSECURITY={ROBLOX_COOKIE}',
        'Content-Type': 'application/json',
    }

    async with aiohttp.ClientSession() as session:
        groups_data = await fetch_json(session, url, headers=headers)
        groups = groups_data.get('data', [])
        for group in groups:
            if group['group']['id'] == int(group_id):
                rank_number = group['role']['rank']
                return RANK_NAME_MAPPING.get(str(rank_number), "Unknown Rank"), None
        return None, "User is not in the group"

async def get_roblox_avatar(session, user_id):
    url = f"https://thumbnails.roblox.com/v1/users/avatar?userIds={user_id}&size=420x420&format=Png&isCircular=false"
    headers = {
        'Cookie': f'.ROBLOSECURITY={ROBLOX_COOKIE}'
    }
    try:
        data = await fetch_json(session, url, headers=headers)
        if data['data']:
            return data['data'][0]['imageUrl']
    except Exception as e:
        logging.error(f"Failed to fetch avatar for user ID {user_id}: {e}")
    return None

async def get_owned_game_passes(user_id):
    url = f"https://api.roblox.com/users/{user_id}/game-pass"
    headers = {
        'Cookie': f'.ROBLOSECURITY={ROBLOX_COOKIE}'
    }
    async with aiohttp.ClientSession() as session:
        try:
            data = await fetch_json(session, url, headers=headers)
            owned_game_passes = [gp for gp in data if gp.get("gameId") == GAME_ID]
            return owned_game_passes
        except Exception as e:
            logging.error(f"Failed to fetch game passes for user ID {user_id}: {e}")
            return []

@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user.name}')

@bot.command()
async def rank(ctx, *, username: str):
    lock_key = f"{ctx.guild.id}-{ctx.channel.id}-{username}"
    logging.debug(f"Received rank command for {username} in channel {ctx.channel.id}.")

    if lock_key in command_locks:
        time_left = command_rate_limit - (discord.utils.utcnow() - command_locks[lock_key]).total_seconds()
        if time_left > 0:
            await ctx.send(f"Please wait {int(time_left)} seconds before reusing the command for `{username}`.")
            logging.debug(f"Rate-limited response for {username}.")
            return
        else:
            command_locks[lock_key] = discord.utils.utcnow()
    else:
        command_locks[lock_key] = discord.utils.utcnow()

    try:
        ongoing_message = None
        async for message in ctx.channel.history(limit=10):
            if message.author == bot.user and message.content.startswith(f"Fetching rank for {username}"):
                ongoing_message = message
                break

        if ongoing_message:
            await ongoing_message.edit(content=f"Fetching rank for {username}...")
        else:
            ongoing_message = await ctx.send(f"Fetching rank for {username}...")
            logging.debug(f"Sent initial fetching message for {username}.")

        user_info, error = await get_user_info(username)
        if error:
            await ongoing_message.edit(content=f"Error: {error}")
            logging.error(f"Error occurred for {username}: {error}")
            return

        user_id = user_info['id']
        display_name = user_info['display_name']
        account_age_years = user_info['account_age_years']
        account_age_days = user_info['account_age_days']
        avatar_url = user_info['avatar_url']
        rank, error = await get_user_rank_in_group(user_id, ROBLOX_GROUP_ID)
        if error:
            await ongoing_message.edit(content=f"Error: {error}")
            logging.error(f"Error occurred for {username}: {error}")
            return

        game_passes = await get_owned_game_passes(user_id)

        # Create embed
        embed = discord.Embed(
            title=f"Rank Information for {display_name}",
            description=f"**Username:** {username}\n**Display Name:** {display_name}\n**Rank:** {rank}\n**Account Age:** {account_age_years} years and {account_age_days} days",
            color=0x1E90FF
        )
        if avatar_url:
            embed.set_thumbnail(url=avatar_url)
        embed.add_field(name="Roblox Profile", value=f"[{display_name}'s Profile](https://www.roblox.com/users/{user_id}/profile)", inline=False)
        
        # Add game passes information
        if game_passes:
            game_passes_list = "\n".join([f"Game Pass ID: {gp['id']}" for gp in game_passes])
            embed.add_field(name="Owned Game Passes", value=game_passes_list, inline=False)
        else:
            embed.add_field(name="Owned Game Passes", value="No game passes found", inline=False)

        # Add footer
        embed.set_footer(text=f"Information retrieved from Roblox | Requested at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")

        # Edit message with embed
        await ongoing_message.edit(content=None, embed=embed)
        logging.debug(f"Edited message with rank info for {username}.")
    except Exception as e:
        await ongoing_message.edit(content=f"An error occurred: {e}")
        logging.error(f"An unexpected error occurred for {username}: {e}")

bot.run(DISCORD_TOKEN)
