import discord
from discord.ext import commands
import requests
import os

# Create an instance of Intents with all intents enabled
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.reactions = True
intents.typing = True
intents.presences = True
intents.voice_states = True
intents.message_content = True  # Add this line to handle message content

# Retrieve sensitive information from environment variables
TOKEN = os.getenv('DISCORD_TOKEN')
ROBUX_GROUP_ID = os.getenv('ROBUX_GROUP_ID')

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

@bot.command()
async def search(ctx, *, keyword):
    # Example using a hypothetical API endpoint
    url = f'https://example.com/api/groups/{ROBUX_GROUP_ID}/members'
    headers = {
        'User-Agent': 'YourUserAgent'
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.RequestException as e:
        await ctx.send(f'Error during request: {e}')
        return

    try:
        members = response.json().get('members', [])
    except ValueError:
        await ctx.send('Error parsing members data.')
        return

    matching_users = [member for member in members if keyword.lower() in member['username'].lower() or keyword.lower() in member['displayName'].lower()]

    if not matching_users:
        await ctx.send('No users found.')
        return

    message = 'Users found:\n'
    for user in matching_users:
        message += f'{user["username"]} ({user["displayName"]})\n'

    await ctx.send(message)

bot.run(TOKEN)
