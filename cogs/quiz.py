import re

import discord
from discord.ext import commands
from discord import app_commands
from bot_utils.utils import get_quiz
from bot_modules.quiz_session import QuizSession
from model.settings_model import SettingsModel
import asyncio
from bot_modules.join_view import JoinQuizView
from datetime import datetime, timedelta, timezone
from typing import Optional, List
import motor.motor_asyncio
from bot_utils.RedisHelper import RedisHelper
from bot import BotClass
from logging import ERROR

class MembersListTransformer(app_commands.Transformer):
    async def transform(self, interaction: discord.Interaction, value: str) -> List[discord.Member]:
        parts = value.split()
        members = []

        mention_pattern = re.compile(r"<@!?(\d+)>")

        for chunk in parts:
            user_id = None

            match = mention_pattern.match(chunk)
            if match:
                user_id = int(match.group(1))
            else:
                if chunk.isdigit():
                    user_id = int(chunk)

            if user_id is not None:
                member = interaction.guild.get_member(user_id)
                if member:
                    members.append(member)

        return members

class QuizCog(commands.Cog):
    def __init__(self, bot:BotClass):
        self.bot = bot
        self.active_games = {}
        self.active_join_views = {}
        self.db = self.bot.db
        self.fs = motor.motor_asyncio.AsyncIOMotorGridFSBucket(self.db)
        self.redis = RedisHelper(self.bot.redis, self.bot.logger)
        self.bot.loop.create_task(self.on_ready())


    async def on_ready(self):
        await self.bot.wait_until_ready()
        await self.restore_sessions()

    async def restore_sessions(self):
        pattern = "quiz_session:*"
        keys = await self.redis.safe_keys(pattern)
        if keys is None:
            return
        for key in keys:
            parts = key.split(":")
            if len(parts) != 3:
                continue

            guild_id = int(parts[1])
            channel_id = int(parts[2])

            inst_shards = list(self.bot.shards.keys())
            total_shards = self.bot.total_shards
            guild_shard = (guild_id >> 22) % total_shards
            if guild_shard not in inst_shards:
                continue

            data = await self.redis.safe_get(key)
            if data is None:
                continue
            session = await QuizSession.from_state(data,self,self.bot)

            game_key = (guild_id, channel_id)
            self.active_games[game_key] = session
            await session.send_question()

    async def ensure_guild_settings(self, guild_id: int) -> dict:
        doc = await self.db['Settings'].find_one({"guild_id": guild_id})
        if doc is None:
            default_model = SettingsModel(guild_id=guild_id)
            await self.db['Settings'].insert_one(default_model.dict())
            return default_model.dict()
        return doc




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
                    description="Quiz został zakończony, ponieważ wiadomość z quizem została usunięta.",
                    color=discord.Color.red()
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
    @app_commands.describe(access_code="Kod quizu", allowed_users="Użytkownicy, którzy mogą dołączyć (opcjonalne, rozdzieleni spacją)",
                           join_window="Czas dołączenia (5-30), jeśli nie podasz to z bazy",
                           answer_time="Czas wyświetlenia odpowiedzi (5-30), jeśli nie podasz to z bazy",
                           results_time="Czas wyświetlania wyników (5-30), jeśli nie podasz to z bazy",
                           show_results="Czy pokazywać wyniki po każdym pytaniu (tak/nie)?"
                           )
    @app_commands.guild_only()
    async def start_quiz(self, ctx: discord.Interaction,
                        access_code: str,
                        allowed_users:Optional[app_commands.Transform[List[discord.Member], MembersListTransformer]],
                         join_window: Optional[int] = None,
                         answer_time: Optional[int] = None,
                         results_time: Optional[int] = None,
                         show_results: Optional[bool] = None
                         ):
        guild_id = ctx.guild.id
        channel_id = ctx.channel.id
        game_key = (guild_id, channel_id)

        if game_key in self.active_games or game_key in self.active_join_views:
            await ctx.response.send_message("Gra już trwa w tym kanale.", ephemeral=True)
            return

        if join_window is not None and not (5 <= join_window <=30):
            await ctx.response.send_message("czas dołączenia musi być w zakresie 5-30s", ephemeral=True)
            return

        if answer_time is not None and not (5 <= answer_time <=30):
            await ctx.response.send_message("czas wyświetlenia odpowiedzi być w zakresie 5-30s", ephemeral=True)
            return

        if results_time is not None and not (5 <= results_time <=30):
            await ctx.response.send_message("czas pokazania wyników musi być w zakresie 5-30s", ephemeral=True)
            return

        try:
            await ctx.response.defer()
            quiz = await get_quiz(self.db,access_code)

            settings = await self.ensure_guild_settings(guild_id)
            if join_window is not None:
                settings["join_window_display_time"] = join_window
            if answer_time is not None:
                settings["answer_display_time"] = answer_time
            if results_time is not None:
                settings["results_display_time"] = results_time
            if show_results is not None:
                settings["show_results_per_question"] = show_results

        except Exception as e:
            self.bot.log(message=e, name="MongoDB error", level=ERROR)
            await ctx.followup.send("Wystąpił problem z pobraniem quizu spróbuj ponownie później")
            return

        if quiz is None:
            await ctx.followup.send("Ten quiz nie istnieje")
            return

        join_view = JoinQuizView(timeout=settings["join_window_display_time"], cog=self, game_key=game_key, gamestarter=ctx.user, allowed_users=allowed_users)
        self.active_join_views[game_key] = join_view
        end_time = datetime.now(timezone.utc) + timedelta(seconds=join_view.timeout)

        embed = discord.Embed(
            title="Dołącz do Quizu "+ quiz.title,
            description=f"Kliknij przycisk poniżej, aby dołączyć do quizu!\n\nPozostały czas: <t:{int(end_time.timestamp())}:R>",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Uczestnicy:", value="Brak", inline=False)
        await ctx.followup.send(embed=embed, view=join_view)
        message = await ctx.original_response()
        join_view.message = message
        await asyncio.sleep(join_view.timeout)

        if game_key not in self.active_join_views:
            return


        if game_key in self.active_join_views:
            del self.active_join_views[game_key]

        if not join_view.players:
            embed = discord.Embed(
                title="Nikt nie dołączył do quizu",
                color=discord.Color.red()
            )
            await message.edit(embed=embed, view=None)
            return

        game = QuizSession(quiz, ctx.channel, self, players=join_view.players, message=message,
                           game_starter=ctx.user,
                           correct_answer_display_time=settings["answer_display_time"],
                           scoreboard_display_time=settings["results_display_time"],
                           send_private_messages=settings["show_results_per_question"])
        self.active_games[game_key] = game
        await game.start()

    @app_commands.command(name="endquiz", description="Zakończ aktualną grę")
    @app_commands.guild_only()
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
                    description="Gra została anulowana",
                    color=discord.Color.red()
                )
                await join_view.message.edit(embed=embed, view=None)
            join_view.stop()

            await ctx.response.send_message("Proces dołączania do gry został anulowany.", ephemeral=True)

        else:
            await ctx.response.send_message("Aktualnie nie ma żadnej aktywnej gry na tym kanale.",
                                            ephemeral=True)

    @app_commands.command(name="skipquestion", description="Pomiń aktualne pytanie")
    @app_commands.guild_only()
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

    @app_commands.command(name="kickplayer", description="Wyrzuć gracza z aktualnego quizu.")
    @app_commands.describe(member="Kogo wyrzucić z quizu?")
    @app_commands.guild_only()
    async def kick_player(self, interaction: discord.Interaction, member: discord.Member):
        guild_id = interaction.guild.id
        channel_id = interaction.channel.id
        game_key = (guild_id, channel_id)

        if game_key not in self.active_games:
            await interaction.response.send_message("Aktualnie nie ma żadnej aktywnej gry w tym kanale.",
                                                    ephemeral=True)
            return

        game = self.active_games[game_key]

        if interaction.user != game.game_starter and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Nie masz uprawnień do wyrzucania graczy z quizu.", ephemeral=True)
            return

        if member not in game.players:
            await interaction.response.send_message(f"{member.mention} i tak nie jest w tym quizie.", ephemeral=True)
            return

        game.kicked_players.add(member.id)
        if member in game.scores:
            del game.scores[member]
        if member in game.streaks:
            del game.streaks[member]

        await interaction.response.send_message(f"{member.mention} został wyrzucony z quizu.", ephemeral=True)



async def setup(bot):
    await bot.add_cog(QuizCog(bot))