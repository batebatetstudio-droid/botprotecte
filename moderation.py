import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import time
from datetime import timedelta

# ============================
# PERMISSIONS : 2 rôles sous le bot
# ============================

def has_moderation_permission(interaction: discord.Interaction) -> bool:
    guild = interaction.guild
    if guild is None:
        return False

    bot_member = guild.me
    bot_role = bot_member.top_role
    bot_index = guild.roles.index(bot_role)

    if bot_index < 2:
        return False

    allowed_roles = [
        guild.roles[bot_index - 1],
        guild.roles[bot_index - 2]
    ]

    member = guild.get_member(interaction.user.id)
    if member is None:
        return False

    return any(r in member.roles for r in allowed_roles)


# ============================
# ANTI-RAID / ANTI-SPAM CACHE
# ============================

join_cache: dict[int, list[float]] = {}
message_cache: dict[int, list[tuple[float, str]]] = {}


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.log_channel_id: int | None = None

    # ============================================================
    # COMMANDES SLASH
    # ============================================================

    @app_commands.command(name="ban", description="Bannir un utilisateur")
    async def ban(self, interaction: discord.Interaction, user: discord.Member, reason: str = "Aucune raison"):
        if not has_moderation_permission(interaction):
            await interaction.response.send_message("❌ Tu n'as pas la permission.", ephemeral=True)
            return

        await user.ban(reason=reason)
        await interaction.response.send_message(f"🔨 {user} banni.\nRaison : {reason}", ephemeral=True)
        self.log(interaction.guild, f"🔨 {user} banni par {interaction.user} — {reason}")

    @app_commands.command(name="kick", description="Expulser un utilisateur")
    async def kick(self, interaction: discord.Interaction, user: discord.Member, reason: str = "Aucune raison"):
        if not has_moderation_permission(interaction):
            await interaction.response.send_message("❌ Tu n'as pas la permission.", ephemeral=True)
            return

        await user.kick(reason=reason)
        await interaction.response.send_message(f"👢 {user} expulsé.\nRaison : {reason}", ephemeral=True)
        self.log(interaction.guild, f"👢 {user} expulsé par {interaction.user} — {reason}")

    @app_commands.command(name="timeout", description="Timeout un utilisateur")
    async def timeout(self, interaction: discord.Interaction, user: discord.Member, minutes: int):
        if not has_moderation_permission(interaction):
            await interaction.response.send_message("❌ Tu n'as pas la permission.", ephemeral=True)
            return

        until = discord.utils.utcnow() + timedelta(minutes=minutes)
        await user.timeout(until, reason=f"Timeout {minutes} minutes")
        await interaction.response.send_message(f"⛔ {user} timeout {minutes} minutes.", ephemeral=True)
        self.log(interaction.guild, f"⛔ {user} timeout par {interaction.user} — {minutes} min")

    @app_commands.command(name="clear", description="Supprimer des messages")
    async def clear(self, interaction: discord.Interaction, amount: int):
        if not has_moderation_permission(interaction):
            await interaction.response.send_message("❌ Tu n'as pas la permission.", ephemeral=True)
            return

        channel = interaction.channel

        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("❌ Impossible de supprimer des messages ici.", ephemeral=True)
            return

        await channel.purge(limit=amount)
        await interaction.response.send_message(f"🧹 {amount} messages supprimés.", ephemeral=True)
        self.log(interaction.guild, f"🧹 {amount} messages supprimés par {interaction.user}")

    @app_commands.command(name="setlogs", description="Définir le salon de logs")
    async def setlogs(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not has_moderation_permission(interaction):
            await interaction.response.send_message("❌ Tu n'as pas la permission.", ephemeral=True)
            return

        self.log_channel_id = channel.id
        await interaction.response.send_message(f"📘 Salon de logs défini : {channel.mention}", ephemeral=True)

    # ============================================================
    # LOGS
    # ============================================================

    def log(self, guild: discord.Guild | None, message: str):
        if guild is None or self.log_channel_id is None:
            return

        channel = guild.get_channel(self.log_channel_id)
        if isinstance(channel, discord.TextChannel):
            asyncio.create_task(channel.send(message))

    # ============================================================
    # ANTI-RAID
    # ============================================================

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        now = time.time()

        join_cache.setdefault(guild.id, [])
        join_cache[guild.id].append(now)

        join_cache[guild.id] = [t for t in join_cache[guild.id] if now - t <= 10]

        if len(join_cache[guild.id]) >= 5:
            try:
                await member.ban(reason="Anti-raid : arrivée massive")
                self.log(guild, f"⚠️ RAID détecté — {member} auto-banni")
            except Exception:
                pass

    # ============================================================
    # ANTI-SPAM
    # ============================================================

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return

        guild = message.guild
        author = message.author
        now = time.time()

        message_cache.setdefault(author.id, [])
        message_cache[author.id].append((now, message.content))

        message_cache[author.id] = [
            (t, msg) for (t, msg) in message_cache[author.id] if now - t <= 5
        ]

        if len(message_cache[author.id]) >= 6:
            await self._timeout_member(author, guild, "Anti-spam : flood")
            return

        contents = [msg for (_, msg) in message_cache[author.id]]
        if len(contents) >= 4 and len(set(contents)) == 1:
            await self._timeout_member(author, guild, "Anti-spam : répétition")
            return

        emoji_count = sum(c in "😀😁😂🤣😅😆😉😊😍😘😜🤪🤬🤯😎😈👿💀👻👽🤖💩🔥✨💥" for c in message.content)
        if emoji_count >= 15:
            await self._timeout_member(author, guild, "Anti-spam : emoji")
            return

        if message.mentions and len(message.mentions) >= 5:
            await self._timeout_member(author, guild, "Anti-spam : mentions")
            return

    async def _timeout_member(self, user: discord.User | discord.Member, guild: discord.Guild, reason: str):
        member = guild.get_member(user.id)
        if member is None:
            self.log(guild, f"⛔ {reason} — impossible de timeout {user}")
            return

        try:
            until = discord.utils.utcnow() + timedelta(minutes=10)
            await member.timeout(until, reason=reason)
            self.log(guild, f"⛔ {reason} — {member} timeout 10 min")
        except Exception:
            self.log(guild, f"❌ Timeout impossible sur {member}")

    # ============================================================
    # AUTO-BAN SUR ACTIONS DANGEREUSES
    # ============================================================

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        guild = channel.guild
        async for entry in guild.audit_logs(limit=1):
            user = entry.user
            if user and not user.bot:
                try:
                    await guild.ban(user, reason="Suppression de salon")
                    self.log(guild, f"🔨 Auto-ban : {user} a supprimé un salon")
                except Exception:
                    self.log(guild, f"❌ Auto-ban impossible sur {user}")

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        guild = role.guild
        async for entry in guild.audit_logs(limit=1):
            user = entry.user
            if user and not user.bot:
                try:
                    await guild.ban(user, reason="Suppression de rôle")
                    self.log(guild, f"🔨 Auto-ban : {user} a supprimé un rôle")
                except Exception:
                    self.log(guild, f"❌ Auto-ban impossible sur {user}")


# ============================================================
# SETUP — OBLIGATOIRE
# ============================================================

async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
