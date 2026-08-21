import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import random

DATA_FILE = "data.json"

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

class Casino(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==========================
    # /coinflip
    # ==========================
    @app_commands.command(name="coinflip", description="Parier sur pile ou face")
    @app_commands.describe(choice="pile ou face", amount="Montant à parier")
    async def coinflip(self, interaction: discord.Interaction, choice: str, amount: int):
        choice = choice.lower()
        if choice not in ["pile", "face"]:
            await interaction.response.send_message("❌ Choix invalide (pile/face).", ephemeral=True)
            return

        if amount <= 0:
            await interaction.response.send_message("❌ Montant invalide.", ephemeral=True)
            return

        user = get_user_data(interaction.user.id)
        if user["money"] < amount:
            await interaction.response.send_message("❌ Tu n'as pas assez d'argent.", ephemeral=True)
            return

        result = random.choice(["pile", "face"])

        if result == choice:
            user["money"] += amount
            msg = f"🎉 C'est **{result}** ! Tu gagnes **{amount}** pièces."
        else:
            user["money"] -= amount
            msg = f"💀 C'est **{result}**... Tu perds **{amount}** pièces."

        set_user_data(interaction.user.id, user)
        await interaction.response.send_message(msg, ephemeral=True)

    # ==========================
    # /roulette
    # ==========================
    @app_commands.command(name="roulette", description="Roulette (rouge/noir)")
    @app_commands.describe(color="rouge ou noir", amount="Montant à parier")
    async def roulette(self, interaction: discord.Interaction, color: str, amount: int):
        color = color.lower()
        if color not in ["rouge", "noir"]:
            await interaction.response.send_message("❌ Couleur invalide (rouge/noir).", ephemeral=True)
            return

        if amount <= 0:
            await interaction.response.send_message("❌ Montant invalide.", ephemeral=True)
            return

        user = get_user_data(interaction.user.id)
        if user["money"] < amount:
            await interaction.response.send_message("❌ Tu n'as pas assez d'argent.", ephemeral=True)
            return

        result = random.choice(["rouge", "noir"])

        if result == color:
            user["money"] += amount
            msg = f"🎉 La roulette tombe sur **{result}** ! Tu gagnes **{amount}** pièces."
        else:
            user["money"] -= amount
            msg = f"💀 La roulette tombe sur **{result}**... Tu perds **{amount}** pièces."

        set_user_data(interaction.user.id, user)
        await interaction.response.send_message(msg, ephemeral=True)

    # ==========================
    # /slots
    # ==========================
    @app_commands.command(name="slots", description="Machine à sous")
    @app_commands.describe(amount="Montant à parier")
    async def slots(self, interaction: discord.Interaction, amount: int):
        if amount <= 0:
            await interaction.response.send_message("❌ Montant invalide.", ephemeral=True)
            return

        user = get_user_data(interaction.user.id)
        if user["money"] < amount:
            await interaction.response.send_message("❌ Tu n'as pas assez d'argent.", ephemeral=True)
            return

        symbols = ["🍒", "🍋", "⭐", "💎"]
        roll = [random.choice(symbols) for _ in range(3)]

        msg = f"🎰 {' | '.join(roll)}\n"

        if roll[0] == roll[1] == roll[2]:
            gain = amount * 5
            user["money"] += gain
            msg += f"🎉 Jackpot ! Tu gagnes **{gain}** pièces."
        elif roll[0] == roll[1] or roll[1] == roll[2] or roll[0] == roll[2]:
            gain = amount * 2
            user["money"] += gain
            msg += f"✨ Deux symboles identiques ! Tu gagnes **{gain}** pièces."
        else:
            user["money"] -= amount
            msg += f"💀 Rien... Tu perds **{amount}** pièces."

        set_user_data(interaction.user.id, user)
        await interaction.response.send_message(msg, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Casino(bot))
