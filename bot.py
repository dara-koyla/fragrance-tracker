
import os
import aiohttp
import aiosqlite
import aiohttp
import discord
from bs4 import BeautifulSoup
from discord.ext import tasks, commands

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "900"))

URL = "https://www.fragrantica.com/whats-new/"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


async def init_db():
    async with aiosqlite.connect("fragrances.db") as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS fragrances(
            url TEXT PRIMARY KEY
        )
        """)
        await db.commit()


async def exists(url):
    async with aiosqlite.connect("fragrances.db") as db:
        cur = await db.execute(
            "SELECT url FROM fragrances WHERE url=?",
            (url,)
        )
        row = await cur.fetchone()
        return row is not None


async def save(url):
    async with aiosqlite.connect("fragrances.db") as db:
        await db.execute(
            "INSERT OR IGNORE INTO fragrances(url) VALUES(?)",
            (url,)
        )
        await db.commit()


async def fetch_launches():

    headers = {
        "User-Agent":
        "Mozilla/5.0"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(URL, headers=headers) as r:
            html = await r.text()

    soup = BeautifulSoup(html, "html.parser")

    launches = []

    for link in soup.find_all("a", href=True):

        href = link["href"]

        if "/perfume/" not in href:
            continue

        title = link.get_text(strip=True)

        if not title:
            continue

        if href.startswith("/"):
            href = "https://www.fragrantica.com" + href

        launches.append({
            "title": title,
            "url": href
        })

    return launches


async def notify(channel, item):

    embed = discord.Embed(
        title="🆕 New Fragrance",
        description=item["title"],
        url=item["url"]
    )

    embed.add_field(
        name="Fragrantica",
        value=item["url"],
        inline=False
    )

    await channel.send(embed=embed)


@tasks.loop(seconds=CHECK_INTERVAL)
async def check_fragrantica():

    channel = bot.get_channel(CHANNEL_ID)

    if not channel:
        return

    launches = await fetch_launches()

    for item in launches:

        if await exists(item["url"]):
            continue

        await save(item["url"])
        await notify(channel, item)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    channel = bot.get_channel(1510348121576837301)

    if channel:
        await channel.send("Bot startup test")
