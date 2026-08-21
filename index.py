import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

# ============================
# CHARGEMENT DU TOKEN
# ============================

load_dotenv()
TOKEN = os.getenv("TOKEN")

# ============================
# INTENTS
# ============================

intents = discord.Intents.all()

# ============================
# BOT
# ============================

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

# ============================
# FLASK (KEEP ALIVE)
# ============================

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot online"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    thread = Thread(target=run_flask)
    thread.start()

# ============================
# CHARGEMENT DES COMMANDES
# ============================

@bot.event
async def setup_hook():
    """
    setup_hook = appelé AVANT on_ready
    → parfait pour charger les extensions
    """
    for filename in os.listdir("./commands"):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"commands.{filename[:-3]}")
                print(f"✔ Module chargé : {filename}")
            except Exception as e:
                print(f"❌ Erreur chargement {filename} : {e}")

# ============================
# READY
# ============================

@bot.event
async def on_ready():
    print(f"🤖 Connecté en tant que {bot.user}")

    try:
        await bot.tree.sync()
        print("✔ Slash commands synchronisées.")
    except Exception as e:
        print(f"❌ Erreur sync : {e}")

# ============================
# LANCEMENT DU BOT
# ============================

keep_alive()

async def main():
    async with bot:
        await bot.start(TOKEN)

asyncio.run(main())
