import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import time

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

def update_user_data(user_id: int, xp_gain: int = 0, money_gain: int = 0):
    user = get_user_data(user_id)
    user["xp"] += xp_gain
    user["money"] += money_gain

    xp_needed = user["level"] * 100
    if user["xp"] >= xp_needed:
        user["level"] += 1
        user["xp"] = 0

    set_user_data(user_id, user)

class XP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        update_user_data(message.author.id, xp_gain=10, money_gain=5)

    @app_commands.command(name="rank", description="Voir ton niveau et ton XP")
    async def rank(self, interaction: discord.Interaction):
        user = get_user_data(interaction.user.id)

        embed = discord.Embed(
            title=f"📊 Rank de {interaction.user.name}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Niveau", value=user["level"], inline=True)
        embed.add_field(name="XP", value=f"{user['xp']} / {user['level'] * 100}", inline=True)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard", description="Voir le classement des niveaux")
    async def leaderboard(self, interaction: discord.Interaction):
        data = load_data()
        users = data["users"]

        if not users:
            await interaction.response.send_message("📭 Aucun joueur enregistré.", ephemeral=True)
            return

        sorted_users = sorted(
            users.items(),
            key=lambda x: (x[1]["level"], x[1]["xp"]),
            reverse=True
        )

        desc = ""
        for i, (uid, udata) in enumerate(sorted_users[:10], start=1):
            member = interaction.guild.get_member(int(uid)) if interaction.guild else None
            name = member.name if member else uid
            desc += f"**#{i}** {name} — Niveau {udata['level']} ({udata['xp']} XP)\n"

        embed = discord.Embed(
            title="🏆 Leaderboard",
            description=desc,
            color=discord.Color.purple()
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="give_xp", description="Donner de l'XP à un utilisateur (admin)")
    async def give_xp(self, interaction: discord.Interaction, user: discord.User, amount: int):

        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("❌ Cette commande doit être utilisée dans un serveur.", ephemeral=True)
            return

        member = guild.get_member(interaction.user.id)
        if member is None or not member.guild_permissions.administrator:
            await interaction.response.send_message("❌ Réservé aux admins.", ephemeral=True)
            return

        if amount <= 0:
            await interaction.response.send_message("❌ Montant invalide.", ephemeral=True)
            return

        update_user_data(user.id, xp_gain=amount, money_gain=0)
        await interaction.response.send_message(
            f"⭐ {user.mention} a reçu **{amount} XP**.",
            ephemeral=True
        )

    @app_commands.command(name="reset_xp", description="Réinitialiser l'XP d'un utilisateur (admin)")
    async def reset_xp(self, interaction: discord.Interaction, user: discord.User):

        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("❌ Cette commande doit être utilisée dans un serveur.", ephemeral=True)
            return

        member = guild.get_member(interaction.user.id)
        if member is None or not member.guild_permissions.administrator:
            await interaction.response.send_message("❌ Réservé aux admins.", ephemeral=True)
            return

        u = get_user_data(user.id)
        u["xp"] = 0
        u["level"] = 1
        set_user_data(user.id, u)

        await interaction.response.send_message(
            f"♻️ XP de {user.mention} réinitialisé.",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(XP(bot))
