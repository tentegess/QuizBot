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
        self.active_join_views = {}


    @commands.Cog.listener()
    async def on_ready(self):
        print("QuizCog załadowany.")

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        game_key = (message.guild.id, message.channel.id)

        if game_key in self.active_games:
            game = self.active_games[game_key]
            if game.message.id == message.id:
                await game.game_del()
        elif game_key in self.active_join_views:
            join_view = self.active_join_views[game_key]
            if join_view.message.id == message.id:
                del self.active_join_views[game_key]
                join_view.stop()
                join_view.message = None

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.embeds and not after.embeds:
            game_key = (after.guild.id, after.channel.id)

            if game_key in self.active_games:
                game = self.active_games[game_key]
                if game.message.id == after.id and len(after.embeds) == 0:
                    await game.message.delete()

            if game_key in self.active_join_views:
                join_view = self.active_join_views[game_key]
                if join_view.message.id == after.id and len(after.embeds) == 0:
                    await join_view.message.delete()



    @app_commands.command(name="startquiz", description="Rozpocznij quiz")
    async def start_quiz(self, ctx: discord.Interaction):
        guild_id = ctx.guild.id
        channel_id = ctx.channel.id
        game_key = (guild_id, channel_id)

        if game_key in self.active_games or game_key in self.active_join_views:
            await ctx.response.send_message("Gra już trwa w tym kanale.", ephemeral=True)
            return

        quiz = get_quiz_for_guild(guild_id)
        if not quiz:
            await ctx.response.send_message("Brak skonfigurowanego quizu dla tego serwera.", ephemeral=True)
            return

        join_view = JoinQuizView(timeout=10, cog=self, game_key=game_key)
        self.active_join_views[game_key] = join_view
        end_time = datetime.now(timezone.utc) + timedelta(seconds=join_view.timeout)

        embed = discord.Embed(
            title="Dołącz do Quizu!",
            description=f"Kliknij przycisk poniżej, aby dołączyć do quizu!\n\nPozostały czas: <t:{int(end_time.timestamp())}:R>"
        )
        embed.add_field(name="Uczestnicy:", value="Brak", inline=False)
        await ctx.response.send_message(embed=embed, view=join_view)
        message = await ctx.original_response()
        join_view.message = message
        await join_view.wait()

        if game_key in self.active_join_views:
            del self.active_join_views[game_key]

        if not join_view.message:
            view = discord.ui.View()
            embed = discord.Embed(
                title=f"Gra przerwana",
                description="Quiz został zakończony, ponieważ wiadomość z quizem została usunięta."
            )

            await ctx.channel.send(embed=embed, view=view)
            return

        if not join_view.players:
            await ctx.followup.send("Nikt nie dołączył do quizu.", ephemeral=True)
            return

        game = QuizSession(quiz, ctx.channel, self, players=join_view.players, message=message,
                           correct_answer_display_time=5,
                           scoreboard_display_time=5)
        self.active_games[game_key] = game
        await game.start()
async def setup(bot):
    await bot.add_cog(QuizCog(bot))