import discord
from discord.ext import commands
from discord import app_commands

TICKET_CATEGORY_NAME = "Tickets"
TICKET_LOGS_NAME = "ticket-logs"

# ==========================
# Récupération / création du salon de logs
# ==========================

async def get_logs_channel(guild: discord.Guild) -> discord.TextChannel:
    logs = discord.utils.get(guild.channels, name=TICKET_LOGS_NAME)

    if logs is None or not isinstance(logs, discord.TextChannel):
        logs = await guild.create_text_channel(TICKET_LOGS_NAME)

    return logs

# ==========================
# Bouton : fermer le ticket
# ==========================

class CloseTicket(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Fermer le ticket", style=discord.ButtonStyle.red)
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):

        guild = interaction.guild
        if guild is None:
            return

        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("❌ Ce salon ne peut pas être fermé.", ephemeral=True)
            return

        logs = await get_logs_channel(guild)

        transcript_name = f"transcript-{channel.name}.txt"
        transcript_content = ""

        async for msg in channel.history(limit=None):
            transcript_content += f"[{msg.created_at}] {msg.author}: {msg.content}\n"

        with open(transcript_name, "w", encoding="utf-8") as f:
            f.write(transcript_content)

        await logs.send(
            f"📤 Ticket fermé : {channel.name}",
            file=discord.File(transcript_name)
        )

        await interaction.response.send_message("🔒 Ticket fermé.", ephemeral=True)
        await channel.delete()

# ==========================
# Bouton : ouvrir un ticket
# ==========================

class TicketButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📩 Ouvrir un ticket", style=discord.ButtonStyle.blurple)
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):

        guild = interaction.guild
        if guild is None:
            return

        member = guild.get_member(interaction.user.id)
        if member is None:
            await interaction.response.send_message("❌ Impossible de récupérer ton profil.", ephemeral=True)
            return

        category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
        if category is None:
            category = await guild.create_category(TICKET_CATEGORY_NAME)

        logs = await get_logs_channel(guild)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        ticket_channel = await guild.create_text_channel(
            f"ticket-{interaction.user.name}",
            category=category,
            overwrites=overwrites
        )

        await ticket_channel.send(
            f"🎫 Ticket ouvert par {interaction.user.mention}",
            view=CloseTicket()
        )

        await interaction.response.send_message(
            f"📩 Ton ticket a été ouvert : {ticket_channel.mention}",
            ephemeral=True
        )

        await logs.send(f"📥 Ticket ouvert par {interaction.user} → {ticket_channel.mention}")

# ==========================
# Commande : /ticket_panel
# ==========================

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ticket_panel", description="Créer le panel de tickets")
    async def ticket_panel(self, interaction: discord.Interaction):

        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("❌ Utilisable uniquement dans un serveur.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🎫 Support",
            description="Clique sur le bouton ci-dessous pour ouvrir un ticket.",
            color=discord.Color.blurple()
        )

        await interaction.response.send_message(embed=embed, view=TicketButtons())

async def setup(bot):
    await bot.add_cog(Tickets(bot))
