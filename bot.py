import discord
from discord.ext import commands
import os
import requests

# Create intents object and enable all required intents
intents = discord.Intents.all()

# Initialize bot with the specified intents
bot = commands.Bot(command_prefix='!', intents=intents)

ROBLOX_GROUP_ID = '11592051'  # Replace with your group ID
ROBLOX_COOKIE = os.getenv('ROBLOX_COOKIE')  # Ensure this is correctly set in your environment

# Function to get user ID from username
def get_user_id(username):
    url = "https://users.roblox.com/v1/usernames/users"
    headers = {
        'Cookie': f'.ROBLOSECURITY={ROBLOX_COOKIE}',
        'Content-Type': 'application/json',
    }
    data = {
        "usernames": [username]
    }

    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()

        users = response.json().get('data', [])
        if not users:
            return None, "User not found"

        return users[0]['id'], None
    except requests.RequestException as e:
        return None, f"Error fetching user ID: {e}"

# Function to get the rank of the user in the group
def get_user_rank_in_group(user_id, group_id):
    url = f"https://groups.roblox.com/v1/users/{user_id}/groups/roles"
    headers = {
        'Cookie': f'.ROBLOSECURITY={ROBLOX_COOKIE}',
        'Content-Type': 'application/json',
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        groups = response.json().get('data', [])
        for group in groups:
            if group['group']['id'] == int(group_id):
                return group['role']['rank'], None

        return None, "User is not in the group"
    except requests.RequestException as e:
        return None, f"Error fetching user rank: {e}"

# Function to get the user rank by username
def get_user_rank(username):
    user_id, error = get_user_id(username)
    if error:
        return f"Error: {error}"

    rank, error = get_user_rank_in_group(user_id, ROBLOX_GROUP_ID)
    if error:
        return f"Error: {error}"

    return f"{username}'s rank in the group: {rank}"

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

# Command to check the rank of a user in the Roblox group
@bot.command()
async def rank(ctx, *, username: str):
    await ctx.send(f"Fetching rank for {username}...")
    
    # Call the function to get the rank
    rank_info = get_user_rank(username)
    
    # Send the result to the Discord channel
    await ctx.send(rank_info)

bot.run(os.getenv('DISCORD_TOKEN'))
