import discord
from discord.ext import commands
import os
import aiohttp
import logging
import asyncio

# Configure logging
logging.basicConfig(level=logging.DEBUG)  # Set to DEBUG to capture detailed logs

# Create intents object and enable all required intents
intents = discord.Intents.all()

# Initialize bot with the specified intents
bot = commands.Bot(command_prefix='!', intents=intents)

ROBLOX_GROUP_ID = '11592051'  # Replace with your group ID
ROBLOX_COOKIE = os.getenv('ROBLOX_COOKIE')  # Ensure this is correctly set in your environment
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# Check if necessary environment variables are set
if not ROBLOX_COOKIE or not DISCORD_TOKEN:
    raise ValueError("Environment variables ROBLOX_COOKIE and DISCORD_TOKEN must be set.")

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

async def get_user_id(username):
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
        return users[0]['id'], None

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
                return group['role']['rank'], None
        return None, "User is not in the group"

async def get_user_rank(username):
    user_id, error = await get_user_id(username)
    if error:
        return f"Error: {error}"

    rank, error = await get_user_rank_in_group(user_id, ROBLOX_GROUP_ID)
    if error:
        return f"Error: {error}"

    return f"{username}'s rank in the group: {rank}"

@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user.name}')

@bot.command()
async def rank(ctx, *, username: str):
    # Use the username to create a unique lock key
    lock_key = f"{ctx.guild.id}-{ctx.channel.id}-{username}"
    logging.debug(f"Received rank command for {username} in channel {ctx.channel.id}.")

    # Check if the command is rate-limited
    if lock_key in command_locks:
        time_left = command_rate_limit - (discord.utils.utcnow() - command_locks[lock_key]).total_seconds()
        if time_left > 0:
            await ctx.send(f"Please wait {int(time_left)} seconds before reusing the command for `{username}`.")
            logging.debug(f"Rate-limited response for {username}.")
            return
        else:
            # Update the lock timestamp if the cooldown has expired
            command_locks[lock_key] = discord.utils.utcnow()

    # Set the lock with the current timestamp
    command_locks[lock_key] = discord.utils.utcnow()

    try:
        # Check if there's already an ongoing message for this command
        ongoing_message = None
        async for message in ctx.channel.history(limit=10):
            if message.author == bot.user and message.content.startswith(f"Fetching rank for {username}"):
                ongoing_message = message
                break

        if ongoing_message:
            # Edit the existing message
            await ongoing_message.edit(content=f"Fetching rank for {username}...")
        else:
            # Send an initial message to indicate that the process has started
            ongoing_message = await ctx.send(f"Fetching rank for {username}...")
            logging.debug(f"Sent initial fetching message for {username}.")

        # Call the function to get the rank
        rank_info = await get_user_rank(username)

        # Edit the existing message with the rank information
        await ongoing_message.edit(content=rank_info)
        logging.debug(f"Edited message with rank info for {username}.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")
        logging.error(f"Error occurred for {username}: {e}")
    finally:
        # Ensure lock is removed
        if lock_key in command_locks:
            command_locks.pop(lock_key, None)
            logging.debug(f"Lock released for {username}.")

bot.run(DISCORD_TOKEN)
