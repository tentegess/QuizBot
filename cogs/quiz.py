import traceback
import discord
from discord.ext import commands
from discord import app_commands
from utils.get_quiz import get_quiz_for_guild
from classes.quiz_session import QuizSession
import asyncio
from classes.join_view import JoinQuizView
from datetime import datetime, timedelta, timezone

class QuizCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}

    @commands.Cog.listener()
    async def on_ready(self):
        print("QuizCog załadowany.")

    @app_commands.command(name="startquiz", description="Rozpocznij quiz")
    async def start_quiz(self, ctx: discord.Interaction):
        guild_id = ctx.guild.id
        channel_id = ctx.channel.id
        game_key = (guild_id, channel_id)

        if game_key in self.active_games:
            await ctx.response.send_message("Gra już trwa w tym kanale.", ephemeral=True)
            return

        quiz = get_quiz_for_guild(guild_id)
        if not quiz:
            await ctx.response.send_message("Brak skonfigurowanego quizu dla tego serwera.", ephemeral=True)
            return

        join_view = JoinQuizView(timeout=10)
        end_time = datetime.now(timezone.utc) + timedelta(seconds=join_view.timeout)
        embed = discord.Embed(
            title="Dołącz do Quizu!",
            description=f"Kliknij przycisk poniżej, aby dołączyć do quizu!\n\nPozostały czas: <t:{int(end_time.timestamp())}:R>"
        )
        embed.add_field(name="Uczestnicy:", value="Brak", inline=False)
        await ctx.response.send_message(embed=embed, view=join_view)
        message = await ctx.original_response()

        await asyncio.sleep(join_view.timeout)

        # Dezaktywujemy przycisk dołączania
        for item in join_view.children:
            item.disabled = True
        try:
            await message.edit(view=join_view)
        except Exception as e:
            print(f"Błąd podczas dezaktywacji przycisku dołączania: {e}")

        if not join_view.players:
            await ctx.followup.send("Nikt nie dołączył do quizu.", ephemeral=True)
            return

        game = QuizSession(quiz, ctx.channel, self, players=join_view.players, message=message,
                           player_threads=join_view.player_threads,
                           correct_answer_display_time=5,
                           scoreboard_display_time=5)
        self.active_games[game_key] = game
        await game.start(ctx)

async def setup(bot):
    await bot.add_cog(QuizCog(bot))