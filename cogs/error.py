import discord
from logging import ERROR
from discord.ext import commands
from discord import app_commands
from typing import Any, NoReturn
import traceback

class ErrorsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.tree.error(coro=self.__dispatch_to_app_command_handler)

        self.default_error = "Bot nie dziaua :("

    async def __dispatch_to_app_command_handler(self, interaction: discord.Interaction,
                                                error: discord.app_commands.AppCommandError):
        self.bot.dispatch("app_command_error", interaction, error)

    async def __respond_to_interaction(self, interaction: discord.Interaction) -> bool:
        try:
            await interaction.response.send_message(content=self.default_error, ephemeral=True)
            return True
        except discord.errors.InteractionResponded:
            return False

    def trace_error(self, level: str, error: Exception) -> NoReturn:
        self.bot.log(
            message=type(error).__name__,
            name=f"discord.{level}",
            level=ERROR,
            exc_info=error,
        )

    @commands.Cog.listener("on_app_command_error")
    async def get_app_command_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        try:
            await self.__respond_to_interaction(interaction)
            raise error
        except app_commands.errors.MissingPermissions as e:
            await interaction.edit_original_response(content="Nie masz uprawnień Administratora")
        except app_commands.errors.CheckFailure as e:
            await interaction.edit_original_response(content=e)
        self.trace_error("get_app_command_error", error)

async def setup(bot):
    await bot.add_cog(ErrorsCog(bot))