import discord
from discord.ext import commands
import asyncio

class Aegis(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.whitelist = set()
        self.snapshots = {}
        self.threat = {}

    # ============================================================
    # SNAPSHOT
    # ============================================================
    async def create_snapshot(self, guild):
        snap = {
            "channels": {ch.id: ch.name for ch in guild.channels},
            "roles": {r.id: r.name for r in guild.roles}
        }
        self.snapshots[guild.id] = snap

    # ============================================================
    # THREAT SCORE
    # ============================================================
    def add_threat(self, guild, user, value):
        key = f"{guild.id}-{user.id}"
        current = self.threat.get(key, 0)
        new = min(current + value, 100)
        self.threat[key] = new
        return new

    # ============================================================
    # AUDIT LOGS
    # ============================================================
    async def get_executor(self, guild, action):
        logs = await guild.audit_logs(limit=1, action=action).flatten()
        return logs[0].user if logs else None

    # ============================================================
    # RESTAURATION
    # ============================================================
    async def restore_channel(self, guild, channel_id):
        snap = self.snapshots.get(guild.id)
        if not snap: return
        if channel_id not in snap["channels"]: return

        name = snap["channels"][channel_id]
        await guild.create_text_channel(name)

    async def restore_role(self, guild, role_id):
        snap = self.snapshots.get(guild.id)
        if not snap: return
        if role_id not in snap["roles"]: return

        name = snap["roles"][role_id]
        await guild.create_role(name=name)

    # ============================================================
    # LOCKDOWN
    # ============================================================
    async def lockdown(self, guild):
        for ch in guild.channels:
            try:
                await ch.set_permissions(guild.default_role, send_messages=False)
            except:
                pass

    # ============================================================
    # SANCTION
    # ============================================================
    async def sanction(self, guild, user):
        if user.id in self.whitelist: return
        if user == guild.owner: return

        member = guild.get_member(user.id)
        if not member: return

        try:
            await member.ban(reason="Aegis Shield: CRITICAL RAID")
        except:
            print("Impossible de bannir l'utilisateur")

    # ============================================================
    # EVENTS
    # ============================================================
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        guild = channel.guild
        author = await self.get_executor(guild, discord.AuditLogAction.channel_delete)
        if not author: return

        score = self.add_threat(guild, author, 15)

        if author.id not in self.whitelist:
            await self.restore_channel(guild, channel.id)

        if score >= 90:
            await self.lockdown(guild)
            await self.sanction(guild, author)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        guild = role.guild
        author = await self.get_executor(guild, discord.AuditLogAction.role_delete)
        if not author: return

        score = self.add_threat(guild, author, 20)

        if author.id not in self.whitelist:
            await self.restore_role(guild, role.id)

        if score >= 90:
            await self.lockdown(guild)
            await self.sanction(guild, author)

    # ============================================================
    # SLASH COMMANDS
    # ============================================================
    @discord.app_commands.command(name="aegis_snapshot", description="Créer un snapshot du serveur")
    async def snapshot_cmd(self, interaction: discord.Interaction):
        await self.create_snapshot(interaction.guild)
        await interaction.response.send_message("📸 Snapshot créé !")

    @discord.app_commands.command(name="aegis_whitelist", description="Ajouter un utilisateur à la whitelist")
    async def whitelist_cmd(self, interaction: discord.Interaction, user: discord.User):
        self.whitelist.add(user.id)
        await interaction.response.send_message(f"🟢 {user} ajouté à la whitelist")

# ============================================================
# SETUP OBLIGATOIRE POUR LES EXTENSIONS
# ============================================================
async def setup(bot):
    await bot.add_cog(Aegis(bot))
