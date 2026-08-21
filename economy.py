import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import time

DATA_FILE = "data.json"

# ==========================
# LOAD / SAVE
# ==========================

def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({"users": {}, "shop": {}}, f)
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_user_data(user_id: int):
    data = load_data()
    uid = str(user_id)

    if uid not in data["users"]:
        data["users"][uid] = {
            "xp": 0,
            "level": 1,
            "money": 0,
            "last_daily": 0,
            "last_work": 0,
            "inventory": []
        }
        save_data(data)

    return data["users"][uid]

def set_user_data(user_id: int, user_data: dict):
    data = load_data()
    data["users"][str(user_id)] = user_data
    save_data(data)

# ==========================
# COG ECONOMY
# ==========================

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==========================
    # /balance
    # ==========================
    @app_commands.command(name="balance", description="Voir ton argent")
    async def balance(self, interaction: discord.Interaction):
        user = get_user_data(interaction.user.id)

        embed = discord.Embed(
            title=f"💰 Argent de {interaction.user.name}",
            description=f"Tu as **{user['money']}** pièces.",
            color=discord.Color.gold()
        )

        await interaction.response.send_message(embed=embed)

    # ==========================
    # /daily
    # ==========================
    @app_commands.command(name="daily", description="Récompense quotidienne")
    async def daily(self, interaction: discord.Interaction):
        user = get_user_data(interaction.user.id)
        now = int(time.time())

        if now - user["last_daily"] < 86400:
            remaining = 86400 - (now - user["last_daily"])
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            await interaction.response.send_message(
                f"⏳ Tu dois attendre encore **{hours}h {minutes}m**.",
                ephemeral=True
            )
            return

        reward = 250
        user["money"] += reward
        user["last_daily"] = now
        set_user_data(interaction.user.id, user)

        await interaction.response.send_message(
            f"🎁 Tu as reçu **{reward} pièces** !",
            ephemeral=True
        )

    # ==========================
    # /pay
    # ==========================
    @app_commands.command(name="pay", description="Envoyer de l'argent à un utilisateur")
    @app_commands.describe(user="Utilisateur à payer", amount="Montant à envoyer")
    async def pay(self, interaction: discord.Interaction, user: discord.User, amount: int):
        if amount <= 0:
            await interaction.response.send_message("❌ Montant invalide.", ephemeral=True)
            return

        sender = get_user_data(interaction.user.id)
        receiver = get_user_data(user.id)

        if sender["money"] < amount:
            await interaction.response.send_message("❌ Tu n'as pas assez d'argent.", ephemeral=True)
            return

        sender["money"] -= amount
        receiver["money"] += amount

        set_user_data(interaction.user.id, sender)
        set_user_data(user.id, receiver)

        await interaction.response.send_message(
            f"💸 Tu as envoyé **{amount}** pièces à {user.mention}.",
            ephemeral=True
        )

    # ==========================
    # /inventory
    # ==========================
    @app_commands.command(name="inventory", description="Voir ton inventaire")
    async def inventory(self, interaction: discord.Interaction):
        user = get_user_data(interaction.user.id)
        inv = user["inventory"]

        if not inv:
            await interaction.response.send_message("📭 Ton inventaire est vide.", ephemeral=True)
            return

        items = "\n".join([f"• {item}" for item in inv])
        embed = discord.Embed(
            title=f"🎒 Inventaire de {interaction.user.name}",
            description=items,
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    # ==========================
    # /shop
    # ==========================
    @app_commands.command(name="shop", description="Voir la boutique")
    async def shop(self, interaction: discord.Interaction):
        data = load_data()
        shop_data = data.get("shop", {})

        if not shop_data:
            await interaction.response.send_message("🛒 La boutique est vide.", ephemeral=True)
            return

        desc = ""
        for name, info in shop_data.items():
            desc += f"• **{name}** — {info['price']} pièces\n"

        embed = discord.Embed(
            title="🛒 Boutique",
            description=desc,
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed)

    # ==========================
    # /buy
    # ==========================
    @app_commands.command(name="buy", description="Acheter un objet dans la boutique")
    @app_commands.describe(item="Nom de l'objet à acheter")
    async def buy(self, interaction: discord.Interaction, item: str):
        data = load_data()
        shop_data = data.get("shop", {})

        if item not in shop_data:
            await interaction.response.send_message("❌ Cet objet n'existe pas.", ephemeral=True)
            return

        user = get_user_data(interaction.user.id)
        price = shop_data[item]["price"]

        if user["money"] < price:
            await interaction.response.send_message("❌ Tu n'as pas assez d'argent.", ephemeral=True)
            return

        user["money"] -= price
        user["inventory"].append(item)
        set_user_data(interaction.user.id, user)

        await interaction.response.send_message(
            f"✅ Tu as acheté **{item}** pour **{price}** pièces.",
            ephemeral=True
        )

    # ==========================
    # /work
    # ==========================
    @app_commands.command(name="work", description="Travailler pour gagner de l'argent")
    async def work(self, interaction: discord.Interaction):
        user = get_user_data(interaction.user.id)
        now = int(time.time())

        if now - user["last_work"] < 1800:
            remaining = 1800 - (now - user["last_work"])
            minutes = remaining // 60
            await interaction.response.send_message(
                f"⏳ Tu dois attendre encore **{minutes} minutes** avant de retravailler.",
                ephemeral=True
            )
            return

        gain = 150
        user["money"] += gain
        user["last_work"] = now
        set_user_data(interaction.user.id, user)

        await interaction.response.send_message(
            f"🛠 Tu as travaillé et gagné **{gain} pièces**.",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Economy(bot))
