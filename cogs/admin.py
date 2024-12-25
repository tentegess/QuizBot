import discord
from discord.ext import commands
from discord import app_commands

from model.session_model import SessionModel

from bot_utils.utils import guild_only

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = self.bot.db

    @app_commands.command(name="gettoken", description="Testowa komenda czy coś")
    @app_commands.checks.has_permissions(administrator=True)
    @guild_only()
    async def set_quiz(self, interaction: discord.Interaction, user_id: str):
        try:
            user_id = int(user_id) 
        except ValueError:
            await interaction.response.send_message("Podano nieprawidłowy user_id!", ephemeral=True)
            return
        sessions_collection = self.db["Sessions"]

        doc = await sessions_collection.find_one({"user_id": user_id})

        if not doc:
            await interaction.response.send_message("Brak sesji dla tego user_id!", ephemeral=True)
            return

        session_model = SessionModel(**doc)

        msg = f"Token: {session_model.token}\nRefresh: {session_model.refresh_token}\nExpires: {session_model.token_expires_at}"
        await interaction.response.send_message(msg, ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCog(bot))