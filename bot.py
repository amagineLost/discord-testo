import discord
from discord.ext import commands
import requests
import os

# Create an instance of Intents with all intents enabled
intents = discord.Intents.default()
intents.members = True  # Enable member intents

# Fetch environment variables
TOKEN = os.getenv("DISCORD_TOKEN")  # Get the Discord token from environment variables
ROBUX_GROUP_ID = os.getenv("ROBUX_GROUP_ID")  # Get the Roblox Group ID from environment variables

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

@bot.command()
async def search(ctx, *, keyword):
    # Fetch the list of Roblox users from the group
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    url = f'https://robloxsocial.com/groups/{ROBUX_GROUP_ID}/members'  # This URL is hypothetical
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        await ctx.send('Failed to retrieve members from Roblox.')
        return

    try:
        members = response.json().get('members', [])
    except ValueError:
        await ctx.send('Error parsing Roblox members data.')
        return

    # Search for members whose username or display name contains the keyword
    matching_users = [member for member in members if keyword.lower() in member['username'].lower() or keyword.lower() in member['displayName'].lower()]

    if not matching_users:
        await ctx.send('No users found.')
        return

    # Prepare the list of matching users
    message = 'Users found:\n'
    for user in matching_users:
        message += f'{user["username"]} ({user["displayName"]})\n'

    # Send the result to the Discord channel
    await ctx.send(message)

bot.run(TOKEN)
