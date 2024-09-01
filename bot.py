import discord
from discord.ext import commands
import os
import aiohttp
import logging
import json

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create intents object and enable all required intents
intents = discord.Intents.default()
intents.members = True
intents.presences = True
intents.message_content = True  # This is required to read message content in newer API versions

# Initialize bot with the specified intents
bot = commands.Bot(command_prefix='!', intents=intents)

ROBLOX_GROUP_ID = '11592051'  # Replace with your group ID
ROBLOX_COOKIE = os.getenv('ROBLOX_COOKIE')  # Ensure this is correctly set in your environment
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
RANK_NAME_MAPPING_JSON = os.getenv('RANK_NAME_MAPPING')

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

async def fetch_json(session, url, method='GET', headers=None, json=None):
    try:
        async with session.request(method, url, headers=headers, json=json) as response:
            response.raise_for_status()
            return await response.json()
    except aiohttp.ClientResponseError as e:
        raise Exception(f"HTTP Error {e.status}: {e.message}")
    except aiohttp.ClientError as e:
        raise Exception(f"Request Error: {e}")

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
        return {
            'id': user['id'],
            'display_name': user['displayName']
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
        rank, error = await get_user_rank_in_group(user_id, ROBLOX_GROUP_ID)
        if error:
            await ongoing_message.edit(content=f"Error: {error}")
            logging.error(f"Error occurred for {username}: {error}")
            return

        embed = discord.Embed(
            title=f"Rank Information for {display_name}",
            description=f"**Username:** {username}\n**Display Name:** {display_name}\n**Rank:** {rank}",
            color=0x1E90FF
        )
        embed.set_thumbnail(url=f"https://www.roblox.com/avatar-thumbnail/{user_id}?width=150&height=150&format=png")
        embed.add_field(name="Roblox Profile", value=f"[{display_name}'s Profile](https://www.roblox.com/users/{user_id}/profile)", inline=False)

        await ongoing_message.edit(content=None, embed=embed)
        logging.debug(f"Edited message with rank info for {username}.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")
        logging.error(f"Error occurred for {username}: {e}")
    finally:
        if lock_key in command_locks:
            command_locks.pop(lock_key, None)
            logging.debug(f"Lock released for {username}.")

bot.run(DISCORD_TOKEN)
