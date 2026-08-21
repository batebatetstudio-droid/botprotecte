import discord
from discord.ext import commands
from discord import app_commands

protected_channels = {}
protect_all_channels = {}

# ============================================================
# PERMISSION : rôle juste en dessous du bot
# ============================================================

def has_server_permission(interaction: discord.Interaction) -> bool:
    guild = interaction.guild
    if guild is None:
        return False

    if guild.me is None:
        return False

    bot_role = guild.me.top_role
    if bot_role is None:
        return False

    bot_index = guild.roles.index(bot_role)
    if bot_index <= 0:
        return False

    allowed_role = guild.roles[bot_index - 1]

    member = guild.get_member(interaction.user.id)
    if member is None:
        return False

    return allowed_role in member.roles


# ============================================================
# CONFIRMATION PROTECT ALL
# ============================================================

class ConfirmProtectAll(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=30)
        self.guild_id = guild_id

    @discord.ui.button(label="✅ Oui, activer", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not has_server_permission(interaction):
            await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
            return

        protect_all_channels[self.guild_id] = True
        await interaction.response.edit_message(
            content="🛡 Protection totale activée.",
            view=None
        )

    @discord.ui.button(label="❌ Non, annuler", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not has_server_permission(interaction):
            await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
            return

        await interaction.response.edit_message(
            content="❌ Protection totale annulée.",
            view=None
        )


# ============================================================
# COG PROTECT
# ============================================================

class Protect(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ------------------------------------------------------------
    # /protect_mode
    # ------------------------------------------------------------
    @app_commands.command(name="protect_mode", description="Activer ou désactiver la protection totale")
    async def protect_mode(self, interaction: discord.Interaction, mode: str):

        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("❌ Utilisable uniquement dans un serveur.", ephemeral=True)
            return

        if not has_server_permission(interaction):
            await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
            return

        if mode.lower() == "on":
            embed = discord.Embed(
                title="⚠️ Avertissement",
                description="Activer la protection totale bannira automatiquement toute personne supprimant un salon (texte, vocal, conférence, forum, thread).",
                color=discord.Color.red()
            )
            view = ConfirmProtectAll(guild.id)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            return

        elif mode.lower() == "off":
            protect_all_channels[guild.id] = False
            await interaction.response.send_message("🛡 Protection totale désactivée.", ephemeral=True)
            return

        else:
            await interaction.response.send_message("Utilise `on` ou `off`.", ephemeral=True)

    # ------------------------------------------------------------
    # /protect_setup
    # ------------------------------------------------------------
    @app_commands.command(name="protect_setup", description="Protège le premier et le dernier salon du serveur")
    async def protect_setup(self, interaction: discord.Interaction):

        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("❌ Utilisable uniquement dans un serveur.", ephemeral=True)
            return

        if not has_server_permission(interaction):
            await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
            return

        if guild.channels is None:
            await interaction.response.send_message("❌ Impossible de récupérer les salons.", ephemeral=True)
            return

        # On protège TOUS les types de salons
        all_channels = [
            c for c in guild.channels
            if isinstance(c, (discord.TextChannel, discord.VoiceChannel, discord.StageChannel, discord.ForumChannel, discord.CategoryChannel))
        ]

        if len(all_channels) < 2:
            await interaction.response.send_message("❌ Il faut au moins 2 salons.", ephemeral=True)
            return

        first_channel = all_channels[0]
        last_channel = all_channels[-1]

        protected_channels[guild.id] = [first_channel.id, last_channel.id]

        await interaction.response.send_message(
            f"🔒 Salons protégés :\n• {first_channel.name}\n• {last_channel.name}",
            ephemeral=True
        )

    # ------------------------------------------------------------
    # EVENT : suppression de salon (texte, vocal, conférence, forum, catégorie)
    # ------------------------------------------------------------
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):

        guild = channel.guild
        if guild is None:
            return

        if guild.me is None:
            return

        # Protection totale ?
        if protect_all_channels.get(guild.id) is True:
            is_protected = True
        else:
            is_protected = channel.id in protected_channels.get(guild.id, [])

        if not is_protected:
            return

        # Audit logs
        entry = None
        async for log in guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
            entry = log
            break

        if entry is None or entry.user is None:
            return

        user = entry.user

        # Ne pas auto-ban le bot
        if self.bot.user and user.id == self.bot.user.id:
            return

        try:
            await guild.ban(user, reason="Suppression d'un salon protégé")
        except Exception as e:
            print("Erreur ban :", e)


async def setup(bot):
    await bot.add_cog(Protect(bot))
