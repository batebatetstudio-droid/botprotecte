import discord
from discord.ext import commands

class ProtectRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.protected_roles: list[int] = []
        self.allowed_role_id: int | None = None

    # ============================================================
    # COMMANDE SLASH : /protect_roles
    # ============================================================
    @discord.app_commands.command(
        name="protect_roles",
        description="Active la protection des rôles du serveur"
    )
    async def protect_roles(self, interaction: discord.Interaction):
        guild: discord.Guild | None = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "⚠ Impossible de récupérer le serveur.",
                ephemeral=True
            )
            return

        # Trouver le rôle du bot
        bot_member: discord.Member | None = guild.get_member(self.bot.user.id)
        if bot_member is None:
            await interaction.response.send_message(
                "⚠ Impossible de récupérer le rôle du bot.",
                ephemeral=True
            )
            return

        bot_role: discord.Role = bot_member.top_role

        # Trouver le rôle juste en dessous du bot
        roles_sorted = sorted(guild.roles, key=lambda r: r.position, reverse=True)

        allowed_role: discord.Role | None = None
        for r in roles_sorted:
            if r.position < bot_role.position:
                allowed_role = r
                break

        if allowed_role is None:
            await interaction.response.send_message(
                "⚠ Aucun rôle trouvé juste en dessous du bot.",
                ephemeral=True
            )
            return

        # Enregistrer le rôle autorisé
        self.allowed_role_id = allowed_role.id

        # Protéger tous les rôles
        self.protected_roles = [r.id for r in guild.roles]

        await interaction.response.send_message(
            f"🛡 Protection des rôles activée !\n"
            f"🔒 Tous les rôles sont protégés.\n"
            f"🔓 Le rôle autorisé à supprimer des rôles est : **{allowed_role.name}**.\n"
            f"❌ Tous les autres seront bannis.",
            ephemeral=True
        )

    # ============================================================
    # EVENT : suppression d’un rôle
    # ============================================================
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        guild: discord.Guild | None = role.guild
        if guild is None:
            return

        # Audit logs
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
            executor: discord.abc.User | None = entry.user

            if executor is None:
                return

            # Si c'est le bot → ignorer
            if executor.id == self.bot.user.id:
                return

            member: discord.Member | None = guild.get_member(executor.id)
            if member is None:
                return

            # Si le membre a le rôle autorisé → ignorer
            if any(r.id == self.allowed_role_id for r in member.roles):
                print(f"⚠ {executor} a supprimé un rôle mais il est autorisé.")
                return

            # Sinon → BAN
            try:
                await guild.ban(executor, reason=f"Suppression d'un rôle protégé : {role.name}")
                print(f"🔨 {executor} banni pour suppression du rôle protégé {role.name}")
            except Exception as e:
                print("Erreur lors du ban :", e)

# ============================================================
# SETUP OBLIGATOIRE POUR LES EXTENSIONS
# ============================================================
async def setup(bot):
    await bot.add_cog(ProtectRoles(bot))
