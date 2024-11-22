import discord
from discord.ext import commands
from discord import app_commands

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setquiz", description="Ustaw quiz dla serwera")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_quiz(self, interaction: discord.Interaction, quiz_id: int):
        guild_id = interaction.guild.id
        await interaction.response.send_message(f"Quiz został ustawiony na ID: {quiz_id}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCog(bot))