import discord
from discord.ext import commands
from discord import app_commands
import json
import os

WELCOME_FILE = "welcome.json"

# ============================================================
# CHARGEMENT / SAUVEGARDE
# ============================================================

def load_welcome():
    if not os.path.exists(WELCOME_FILE):
        with open(WELCOME_FILE, "w") as f:
            json.dump({}, f)
    with open(WELCOME_FILE, "r") as f:
        return json.load(f)

def save_welcome(data):
    with open(WELCOME_FILE, "w") as f:
        json.dump(data, f, indent=4)

welcome_settings = load_welcome()

# Cache des invitations
invite_cache = {}

# ============================================================
# COG
# ============================================================

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ------------------------------------------------------------
    # /welcome_config
    # ------------------------------------------------------------

    @app_commands.command(
        name="welcome_config",
        description="Configurer le système de bienvenue"
    )
    async def welcome_config(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        message: str
    ):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "❌ Utilisable uniquement dans un serveur.",
                ephemeral=True
            )
            return

        gid = str(guild.id)

        welcome_settings.setdefault(gid, {})
        welcome_settings[gid]["channel"] = channel.id
        welcome_settings[gid]["message"] = message
        save_welcome(welcome_settings)

        await interaction.response.send_message(
            f"✅ Salon configuré : {channel.mention}\n📝 Message : `{message}`",
            ephemeral=True
        )

    # ------------------------------------------------------------
    # Cache des invitations
    # ------------------------------------------------------------

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            try:
                invite_cache[guild.id] = await guild.invites()
            except:
                invite_cache[guild.id] = []

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        guild = invite.guild
        invite_cache[guild.id] = await guild.invites()

    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        guild = invite.guild
        invite_cache[guild.id] = await guild.invites()

    # ------------------------------------------------------------
    # Message de bienvenue
    # ------------------------------------------------------------

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        gid = str(guild.id)

        if gid not in welcome_settings:
            return

        data = welcome_settings[gid]
        channel_id = data.get("channel")
        msg = data.get("message", "Bienvenue {user} !")

        channel = guild.get_channel(channel_id)

        # 🔥 Sécurité : uniquement les salons textuels
        if not isinstance(channel, discord.TextChannel):
            return

        # ------------------------------------------------------------
        # Trouver l’inviteur
        # ------------------------------------------------------------

        inviter = None
        try:
            old_invites = invite_cache.get(guild.id, [])
            new_invites = await guild.invites()

            for new in new_invites:
                for old in old_invites:
                    if new.code == old.code and new.uses > old.uses:
                        inviter = new.inviter
                        break

            invite_cache[guild.id] = new_invites
        except:
            inviter = None

        # ------------------------------------------------------------
        # Construire l’embed
        # ------------------------------------------------------------

        text = msg.replace("{user}", member.mention).replace("{server}", guild.name)

        embed = discord.Embed(
            title="🎉 Nouveau membre !",
            description=text,
            color=discord.Color.green()
        )

        # Image de profil
        embed.set_thumbnail(
            url=member.avatar.url if member.avatar else member.default_avatar.url
        )

        # Inviteur
        if inviter:
            embed.add_field(name="Invité par", value=inviter.mention, inline=False)
        else:
            embed.add_field(name="Invité par", value="Impossible à déterminer", inline=False)

        await channel.send(embed=embed)


# ============================================================
# SETUP
# ============================================================

async def setup(bot):
    await bot.add_cog(Welcome(bot))
