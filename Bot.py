import discord
from discord.ext import commands
import requests

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

TOKEN = "YOUR_DISCORD_TOKEN_HERE"  # Replace the real token
ROBUX_GROUP_ID = '11592051'  # Replace with your Roblox Group ID

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

@bot.command()
async def search(ctx, *, keyword):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    url = f'https://robloxsocial.com/groups/{ROBUX_GROUP_ID}/members'
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        await ctx.send('Failed to retrieve members.')
        return

    members = response.json().get('members', [])
    matching_users = [member for member in members if keyword.lower() in member['username'].lower() or keyword.lower() in member['displayName'].lower()]

    if not matching_users:
        await ctx.send('No users found.')
        return

    message = 'Users found:\n'
    for user in matching_users:
        message += f'{user["username"]} ({user["displayName"]})\n'

    await ctx.send(message)

bot.run(TOKEN)
