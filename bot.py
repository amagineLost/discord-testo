import discord
from discord.ext import commands
import os
import requests

# Set up Discord intents
intents = discord.Intents.default()
intents.message_content = True  # Correct the intent to enable reading message content
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Your Roblox group ID and Roblox cookie from environment variables for security
ROBLOX_GROUP_ID = 'YOUR_GROUP_ID'  # Replace with your group ID
ROBLOX_COOKIE = os.getenv('ROBLOX_COOKIE')  # Ensure your .ROBLOSECURITY cookie is in your environment variables

# Function to fetch group members from Roblox API
def fetch_group_members(group_id):
    url = f"https://groups.roblox.com/v1/groups/{group_id}/users?limit=100"

    headers = {
        'Cookie': f'.ROBLOSECURITY={ROBLOX_COOKIE}',
        'Content-Type': 'application/json',
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an error for non-200 responses
        return response.json().get('data', [])
    except requests.RequestException as e:
        print(f"Error fetching group members: {e}")
        return []

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

# Command to search for members by keyword
@bot.command()
async def search(ctx, *, keyword):
    members = fetch_group_members(ROBLOX_GROUP_ID)

    if not members:
        await ctx.send("No members found or failed to retrieve data.")
        return

    # Filter members based on the keyword
    matching_users = [member['user']['username'] for member in members if keyword.lower() in member['user']['username'].lower()]

    if not matching_users:
        await ctx.send("No matching users found.")
        return

    # Send matching users as a Discord message
    message = "\n".join(matching_users)
    await ctx.send(f"Matching users:\n{message}")

# Run the bot using the token from environment variables
bot.run(os.getenv('DISCORD_TOKEN'))
