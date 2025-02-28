import requests
from bs4 import BeautifulSoup
import difflib
import json
import discord
from discord.ext import commands, tasks
import os

# === Configuration ===
TOKEN = os.getenv("DISCORD_BOT_TOKEN")  # Use Railway environment variable
CHANNEL_ID = "1218551925163819022" # Channel ID from Railway
CHECK_INTERVAL = 60  # Check every 1 minute
DATA_FILE = "tracked_docs.json"  # File to store previous versions

# === Setup Intents ===
intents = discord.Intents.default()
intents.message_content = True

# Initialize Bot
bot = commands.Bot(command_prefix="!", intents=intents)

# Load previously tracked URLs (if exists)
try:
    with open(DATA_FILE, "r") as file:
        tracked_urls = json.load(file)
except FileNotFoundError:
    tracked_urls = {}

# === Functions ===
def fetch_page_content(url):
    """Fetches the text content of a webpage."""
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        return soup.get_text()
    return None

def compare_content(new_content, old_content):
    """Compares two versions of content and returns differences."""
    diff = list(difflib.unified_diff(old_content.splitlines(), new_content.splitlines(), lineterm=""))
    return "\n".join(diff)

def save_tracked_data():
    """Saves the tracked URLs and their content to a file."""
    with open(DATA_FILE, "w") as file:
        json.dump(tracked_urls, file)

# === Background Task: Monitor Docs ===
@tasks.loop(seconds=CHECK_INTERVAL)
async def monitor_docs():
    """Checks for changes in tracked documentation pages."""
    for url, old_content in tracked_urls.items():
        new_content = fetch_page_content(url)
        if new_content and new_content != old_content:
            diff_text = compare_content(new_content, old_content)
            channel = bot.get_channel(CHANNEL_ID)
            
            if channel:
                message = f"🚨 **Documentation Updated for {url}!** 🚨\n```{diff_text[:1900]}```"
                await channel.send(message)
            else:
                print("⚠️ Error: Channel not found! Check your CHANNEL_ID.")

            tracked_urls[url] = new_content  # Update with new content
            save_tracked_data()
        
        print(f"Checked: {url} - No changes detected.")  # Debugging log

# === Bot Commands ===
@bot.command()
async def add(ctx, url: str):
    """Adds a new documentation URL to track."""
    if url in tracked_urls:
        await ctx.send("This URL is already being monitored!")
    else:
        content = fetch_page_content(url)
        if content:
            tracked_urls[url] = content
            save_tracked_data()
            await ctx.send(f"✅ Added {url} to the monitoring list!")
        else:
            await ctx.send("❌ Failed to fetch the page content.")

@bot.command()
async def remove(ctx, url: str):
    """Removes a URL from monitoring."""
    if url in tracked_urls:
        del tracked_urls[url]
        save_tracked_data()
        await ctx.send(f"❌ Removed {url} from the monitoring list!")
    else:
        await ctx.send("This URL is not being monitored.")

@bot.command()
async def list_assets(ctx):
    """Lists all monitored websites."""
    if tracked_urls:
        message = "**📌 Currently Monitored Websites:**\n" + "\n".join(tracked_urls.keys())
    else:
        message = "No websites are being monitored."
    await ctx.send(message)

@bot.event
async def on_ready():
    """Starts the bot and monitoring task."""
    print(f"✅ Logged in as {bot.user}")
    print(f"🔍 Monitoring {len(tracked_urls)} websites...")
    
    # Debugging: Check if bot can find the channel
    channel = bot.get_channel(CHANNEL_ID)
    print(f"📝 Bot Channel: {channel}")

    if channel:
        await channel.send("✅ Bot is online and monitoring documentation changes!")

    monitor_docs.start()

# Run the Bot
bot.run(TOKEN)
