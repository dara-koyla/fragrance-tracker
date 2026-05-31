import os
import aiohttp
import aiosqlite
import discord
from bs4 import BeautifulSoup
from discord.ext import commands, tasks

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "900"))

URL = "https://www.fragrantica.com/whats-new/"

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# -------------------------
# DATABASE
# -------------------------

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
        cursor = await db.execute(
            "SELECT url FROM fragrances WHERE url=?",
            (url,)
        )
        row = await cursor.fetchone()
        return row is not None


async def save(url):
    async with aiosqlite.connect("fragrances.db") as db:
        await db.execute(
            "INSERT OR IGNORE INTO fragrances(url) VALUES(?)",
            (url,)
        )
        await db.commit()


# -------------------------
# SCRAPER
# -------------------------

async def fetch_launches():

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(
            URL,
            headers=headers,
            timeout=30
        ) as response:

            html = await response.text()

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

    unique = {}

    for item in launches:
        unique[item["url"]] = item

    return list(unique.values())


# -------------------------
# DISCORD NOTIFICATION
# -------------------------

async def notify(channel, item):

    embed = discord.Embed(
        title="🆕 New Fragrance Added",
        description=item["title"],
        url=item["url"],
        color=0x5865F2
    )

    embed.add_field(
        name="Fragrantica Link",
        value=item["url"],
        inline=False
    )

    await channel.send(embed=embed)


# -------------------------
# CHECK LOOP
# -------------------------

@tasks.loop(seconds=CHECK_INTERVAL)
async def check_fragrantica():

    print("Checking Fragrantica...")

    channel = bot.get_channel(CHANNEL_ID)

    if channel is None:
        print("Channel not found")
        return

    launches = await fetch_launches()

    print(f"Found {len(launches)} perfume links")

    for item in launches:

        if await exists(item["url"]):
            continue

        await save(item["url"])

        print("New perfume:", item["title"])

        await notify(channel, item)


# -------------------------
# COMMANDS
# -------------------------

@bot.command()
async def test(ctx):
    await ctx.send("Bot is working.")


@bot.command()
async def status(ctx):
    await ctx.send("Fragrantica tracker is online.")


# ______new update section______________--
@bot.command()
async def check(ctx):

    launches = await fetch_launches()

    await ctx.send(f"Found {len(launches)} perfume links")

    if launches:
        await ctx.send(
            f"First result:\n{launches[0]['title']}\n{launches[0]['url']}"
        )
# -------------------------
# EVENTS
# -------------------------

@bot.event
async def on_ready():

    print(f"Logged in as {bot.user}")

    channel = bot.get_channel(CHANNEL_ID)

    if channel:
        await channel.send("✅ Fragrantica Tracker Started")

    await init_db()

    if not check_fragrantica.is_running():
        check_fragrantica.start()


# -------------------------
# START BOT
# -------------------------

bot.run(TOKEN)

