from logging import ERROR

import discord
from discord.ext import commands
from discord import app_commands

from model.session_model import SessionModel
from model.settings_model import SettingsModel

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = self.bot.db

    async def ensure_guild_settings(self, guild_id: int):
        doc = await self.db['Settings'].find_one({"guild_id": guild_id})
        if doc is None:
            default_model = SettingsModel(guild_id=guild_id)
            await self.db['Settings'].insert_one(default_model.dict())
            return default_model.dict()
        return doc

    @app_commands.command(name="set_join_time", description="Ustaw czas dołączenia do quizu")
    @app_commands.describe(value="Czas w sekundach (5-30)")
    @app_commands.checks.cooldown(1, 5)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def set_join_quiz(self, interaction: discord.Interaction, value: int):
        if value < 5 or value > 30:
            await interaction.response.send_message("Wartość musi być w przedziale od 5 do 30.", ephemeral=True)
            return

        guild_id = interaction.guild_id

        try:
            await interaction.response.send_message("Ustawiam czas.", ephemeral=True)

            await self.ensure_guild_settings(guild_id)

            await self.db['Settings'].update_one(
                {"guild_id": guild_id},
                {"$set": {"join_window_display_time": value}},
                upsert=True
            )

            await interaction.edit_original_response(
                content=f"Czas dołączenia do quizu ustawiono na {value}s.",
            )
        except Exception as e:
            self.bot.log(message=e, name="MongoDB error", level=ERROR)
            await interaction.edit_original_response(content="Wystąpił błąd, spróbuj ponownie później")


    @app_commands.command(name="set_answer_time", description="Ustaw czas wyświetlenia odpowiedzi")
    @app_commands.describe(value="Czas w sekundach (5-30)")
    @app_commands.checks.cooldown(1, 5)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def set_answer_quiz(self, interaction: discord.Interaction, value: int):
        if value < 5 or value > 30:
            await interaction.response.send_message("Wartość musi być w przedziale od 5 do 30.", ephemeral=True)
            return

        guild_id = interaction.guild_id

        try:
            await interaction.response.send_message("Ustawiam czas.", ephemeral=True)

            await self.ensure_guild_settings(guild_id)

            await self.db['Settings'].update_one(
                {"guild_id": guild_id},
                {"$set": {"answer_display_time": value}},
                upsert=True
            )

            await interaction.edit_original_response(
                content=f"Czas wyświetlenia odpowiedzi ustawiono na {value}s.",
            )
        except Exception as e:
            self.bot.log(message=e, name="MongoDB error", level=ERROR)
            await interaction.edit_original_response(content="Wystąpił błąd, spróbuj ponownie później")

    @app_commands.command(name="set_leaderboard_time", description="Ustaw czas wyświetlenia wyników po pytaniu.")
    @app_commands.describe(value="Czas w sekundach (5-30)")
    @app_commands.checks.cooldown(1, 5)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def set_leaderboard_quiz(self, interaction: discord.Interaction, value: int):
        if value < 5 or value > 30:
            await interaction.response.send_message("Wartość musi być w przedziale od 5 do 30.", ephemeral=True)
            return

        guild_id = interaction.guild_id

        try:
            await interaction.response.send_message("Ustawiam czas.", ephemeral=True)

            await self.ensure_guild_settings(guild_id)

            await self.db['Settings'].update_one(
                {"guild_id": guild_id},
                {"$set": {"results_display_time": value}},
                upsert=True
            )

            await interaction.edit_original_response(
                content=f"Czas wyświetlenia wyników ustawiono na {value}s.",
            )
        except Exception as e:
            self.bot.log(message=e, name="MongoDB error", level=ERROR)
            await interaction.edit_original_response(content="Wystąpił błąd, spróbuj ponownie później")

    @app_commands.command(name="set_response_display", description="Ustaw wyświetlanie reakcji na odpowiedź użytkownika.")
    @app_commands.checks.cooldown(1, 5)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def set_response_quiz(self, interaction: discord.Interaction, value: bool):

        guild_id = interaction.guild_id

        try:
            await interaction.response.send_message("Ustawiam wartość.", ephemeral=True)

            await self.ensure_guild_settings(guild_id)

            await self.db['Settings'].update_one(
                {"guild_id": guild_id},
                {"$set": {"show_results_per_question": value}},
                upsert=True
            )
            status = "włączona" if value else "wyłączona"
            await interaction.edit_original_response(
                content=f"Reakcja na odpowiedź użytkownika {status}.",
            )
        except Exception as e:
            self.bot.log(message=e, name="MongoDB error", level=ERROR)
            await interaction.edit_original_response(content="Wystąpił błąd, spróbuj ponownie później")

    @app_commands.command(name="check_settings", description="Sprawdź aktualne ustawienia dla serwera")
    @app_commands.guild_only()
    async def check_settings(self, interaction: discord.Interaction):
        try:
            guild_id = interaction.guild.id
            await interaction.response.send_message("Pobieram ustawienia.", ephemeral=True)
            settings_doc = await self.ensure_guild_settings(guild_id)
            embed = discord.Embed(
                title=f"Ustawienia serwera: {interaction.guild.name}",
                description="Oto aktualnie skonfigurowane wartości:",
                color=discord.Color.blurple()
            )
            embed.add_field(
                name="Czas okna dołączenia (join_window_display_time)",
                value=f"{settings_doc.get('join_window_display_time', None)} sek.",
                inline=False
            )
            embed.add_field(
                name="Czas wyświetlania odpowiedzi (answer_display_time)",
                value=f"{settings_doc.get('answer_display_time', None)} sek.",
                inline=False
            )
            embed.add_field(
                name="Czas wyświetlania wyników (results_display_time)",
                value=f"{settings_doc.get('results_display_time', 10)} sek.",
                inline=False
            )
            show_results = settings_doc.get('show_results_per_question', False)
            show_str = "Włączone" if show_results else "Wyłączone"
            embed.add_field(
                name="Reakcje na odpowiedź użytkownika (show_results_per_question)",
                value=show_str,
                inline=False
            )

            embed.set_footer(text="Aby zmienić wartości, użyj odpowiednich komend.")
            await interaction.edit_original_response(embed=embed)
        except Exception as e:
            self.bot.log(message=e, name="MongoDB error", level=ERROR)
            await interaction.edit_original_response(content="Wystąpił błąd, spróbuj ponownie później")




async def setup(bot):
    await bot.add_cog(AdminCog(bot))