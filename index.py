import discord
import asyncio
from flask import Flask
from threading import Thread
from dotenv import load_dotenv
import os

# Charger le fichier .env
load_dotenv()

TOKEN = os.getenv("TOKEN")

# --- Serveur Flask pour Render ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot online"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- Bot Discord ---
intents = discord.Intents.all()
bot = discord.Bot(intents=intents)

@bot.event
async def on_ready():
    print(f"{bot.user} est connecté et prêt !")

# --- Lancer Flask puis le bot ---
keep_alive()
asyncio.run(bot.start(TOKEN))
