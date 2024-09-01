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
        return user, None

async def get_username_history(user_id):
    url = f"https://users.roblox.com/v1/users/{user_id}/username-history"
    headers = {
        'Cookie': f'.ROBLOSECURITY={ROBLOX_COOKIE}',
    }
    async with aiohttp.ClientSession() as session:
        history_data = await fetch_json(session, url, headers=headers)
        return history_data.get('data', [])

async def get_online_status(user_id):
    url = f"https://users.roblox.com/v1/users/{user_id}/presence"
    headers = {
        'Cookie': f'.ROBLOSECURITY={ROBLOX_COOKIE}',
    }
    async with aiohttp.ClientSession() as session:
        presence_data = await fetch_json(session, url, headers=headers)
        return presence_data.get('status', 'Unknown')

async def get_user_description(user_id):
    url = f"https://users.roblox.com/v1/users/{user_id}"
    headers = {
        'Cookie': f'.ROBLOSECURITY={ROBLOX_COOKIE}',
    }
    async with aiohttp.ClientSession() as session:
        user_data = await fetch_json(session, url, headers=headers)
        return user_data.get('description', 'No description available')

async def get_account_age(user_id):
    url = f"https://users.roblox.com/v1/users/{user_id}"
    headers = {
        'Cookie': f'.ROBLOSECURITY={ROBLOX_COOKIE}',
    }
    async with aiohttp.ClientSession() as session:
        user_data = await fetch_json(session, url, headers=headers)
        created_date = user_data.get('created')
        if created_date:
            created_date = datetime.strptime(created_date, "%Y-%m-%dT%H:%M:%S.%fZ")
            current_date = datetime.utcnow()
            account_age_days = (current_date - created_date).days
            years, days = divmod(account_age_days, 365)
            return years, days
        return None, "Failed to retrieve account age"

async def get_rap(user_id):
    url = f"https://api.robloxscripts.com/rap?userId={user_id}"
    async with aiohttp.ClientSession() as session:
        rap_data = await fetch_json(session, url)
        return rap_data.get('rap', 'No RAP data available')

async def get_limited_items(user_id):
    url = f"https://api.robloxscripts.com/ltditems?userId={user_id}"
    async with aiohttp.ClientSession() as session:
        limited_items_data = await fetch_json(session, url)
        return limited_items_data.get('items', [])

async def get_avatar_images(user_id):
    url = f"https://thumbnails.roblox.com/v1/users/avatar?userIds={user_id}&size=420x420&format=Png&isCircular=false"
    async with aiohttp.ClientSession() as session:
        response = await fetch_json(session, url)
        if response['data']:
            return response['data'][0]['imageUrl']
    return None

async def get_status_message(user_id):
    url = f"https://users.roblox.com/v1/users/{user_id}"
    headers = {
        'Cookie': f'.ROBLOSECURITY={ROBLOX_COOKIE}',
    }
    async with aiohttp.ClientSession() as session:
        user_data = await fetch_json(session, url, headers=headers)
        return user_data.get('status', 'No status message available')

async def get_friends_list(user_id):
    url = f"https://friends.roblox.com/v1/users/{user_id}/friends"
    headers = {
        'Cookie': f'.ROBLOSECURITY={ROBLOX_COOKIE}',
    }
    async with aiohttp.ClientSession() as session:
        friends_data = await fetch_json(session, url, headers=headers)
        return [friend['name'] for friend in friends_data.get('data', [])]

async def get_user_groups(user_id):
    url = f"https://groups.roblox.com/v1/users/{user_id}/groups/roles"
    headers = {
        'Cookie': f'.ROBLOSECURITY={ROBLOX_COOKIE}',
    }
    async with aiohttp.ClientSession() as session:
        groups_data = await fetch_json(session, url, headers=headers)
        return [group['group']['name'] for group in groups_data.get('data', [])]

@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user.name}')

@bot.command()
async def info(ctx, *, username: str):
    try:
        user, error = await get_user_info(username)
        if error:
            await ctx.send(f"Error: {error}")
            logging.error(f"Error occurred for {username}: {error}")
            return

        user_id = user['id']
        display_name = user.get('displayName', 'Unknown')
        username_history = await get_username_history(user_id)
        online_status = await get_online_status(user_id)
        description = await get_user_description(user_id)
        account_age_years, account_age_days = await get_account_age(user_id)
        rap = await get_rap(user_id)
        limited_items = await get_limited_items(user_id)
        avatar_url = await get_avatar_images(user_id)
        status_message = await get_status_message(user_id)
        friends_list = await get_friends_list(user_id)
        groups = await get_user_groups(user_id)

        embed = discord.Embed(
            title=f"Info for {display_name}",
            description=f"**Username:** {username}\n**Display Name:** {display_name}\n**Online Status:** {online_status}\n**Description:** {description}\n**Account Age:** {account_age_years} years and {account_age_days} days\n**Creation Date:** {user.get('created', 'Unknown')}\n**RAP:** {rap}\n**Status Message:** {status_message}",
            color=0x1E90FF
        )

        if avatar_url:
            embed.set_thumbnail(url=avatar_url)
        embed.add_field(name="Username History", value=", ".join(username_history) if username_history else "No history available", inline=False)
        embed.add_field(name="Limited Items", value=", ".join(limited_items) if limited_items else "No limited items available", inline=False)
        embed.add_field(name="Friends List", value=", ".join(friends_list) if friends_list else "No friends available", inline=False)
        embed.add_field(name="Groups", value=", ".join(groups) if groups else "No groups available", inline=False)
        embed.add_field(name="Roblox Profile", value=f"[{display_name}'s Profile](https://www.roblox.com/users/{user_id}/profile)", inline=False)

        await ctx.send(embed=embed)
        logging.debug(f"Sent info message for {username}")
    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)}")
        logging.error(f"Exception occurred in info command: {str(e)}")

bot.run(DISCORD_TOKEN)
