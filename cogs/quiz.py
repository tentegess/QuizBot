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
                view = discord.ui.View()
                embed = discord.Embed(
                    title=f"Gra przerwana",
                    description="Quiz został zakończony, ponieważ wiadomość z quizem została usunięta."
                )
                await message.channel.send(embed=embed, view=view)
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

        join_view = JoinQuizView(timeout=10, cog=self, game_key=game_key, gamestarter=ctx.user)
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
        await asyncio.sleep(join_view.timeout)

        if game_key not in self.active_join_views:
            return

        if not join_view.players:
            await ctx.followup.send("Nikt nie dołączył do quizu.", ephemeral=True)
            return

        if game_key in self.active_join_views:
            del self.active_join_views[game_key]

        game = QuizSession(quiz, ctx.channel, self, players=join_view.players, message=message,
                           game_starter=ctx.user,
                           correct_answer_display_time=5,
                           scoreboard_display_time=5)
        self.active_games[game_key] = game
        await game.start()

    @app_commands.command(name="endquiz", description="Zakończ aktualną grę")
    async def end_quiz(self, ctx: discord.Interaction):
        guild_id = ctx.guild.id
        channel_id = ctx.channel.id
        game_key = (guild_id, channel_id)

        if game_key in self.active_games:
            game = self.active_games[game_key]

            if ctx.user != game.game_starter and not ctx.user.guild_permissions.administrator:
                await ctx.response.send_message("Nie masz uprawnień do zakończenia tej gry.", ephemeral=True)
                return

            await game.end_game()
            await ctx.response.send_message("Gra została zakończona.")
            return

        elif game_key in self.active_join_views:
            join_view = self.active_join_views[game_key]

            if ctx.user != join_view.game_starter and not ctx.user.guild_permissions.administrator:
                await ctx.response.send_message("Nie masz uprawnień do zakończenia tej gry.", ephemeral=True)
                return

            del self.active_join_views[game_key]

            if join_view.message:
                embed = discord.Embed(
                    title="Koniec gry!",
                    description="Gra została anulowana"
                )
                await join_view.message.edit(embed=embed)
            join_view.stop()

            await ctx.response.send_message("Proces dołączania do gry został anulowany.", ephemeral=True)

        else:
            await ctx.response.send_message("Aktualnie nie ma żadnej aktywnej gry na tym kanale.",
                                            ephemeral=True)

    @app_commands.command(name="skipquestion", description="Pomiń aktualne pytanie")
    async def skip_question(self, ctx: discord.Interaction):
        guild_id = ctx.guild.id
        channel_id = ctx.channel.id
        game_key = (guild_id, channel_id)

        if game_key not in self.active_games:
            await ctx.response.send_message("Aktualnie nie ma żadnej aktywnej gry w tym kanale.", ephemeral=True)
            return

        game = self.active_games[game_key]

        if ctx.user != game.game_starter and not ctx.user.guild_permissions.administrator:
            await ctx.response.send_message("Nie masz uprawnień do pominięcia pytania.", ephemeral=True)
            return

        if game.is_processing_question:
            await ctx.response.send_message("Pytanie jest obecnie przetwarzane.",
                                    ephemeral=True)
            return

        await ctx.response.send_message("Aktualne pytanie zostało pominięte.", ephemeral=True)

        if hasattr(game, 'question_task') and not game.question_task.done():
            game.question_task.cancel()

        await game.question_summary()


async def setup(bot):
    await bot.add_cog(QuizCog(bot))