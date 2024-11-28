import discord
from discord.ext import commands
from discord import app_commands
from utils.get_quiz import get_quiz_for_guild
import asyncio
import traceback
from datetime import datetime, timedelta, timezone

class QuizSession:
    def __init__(self, quiz, channel, cog, players, message, player_threads, correct_answer_display_time=5, scoreboard_display_time=5):
        self.quiz = quiz
        self.channel = channel
        self.cog = cog
        self.players = players
        self.current_question_index = 0
        self.scores = {}
        self.player_answers = {}
        self.message = message
        self.answered_users = set()
        self.current_view = None

        self.correct_answer_display_time = correct_answer_display_time
        self.scoreboard_display_time = scoreboard_display_time
        self.player_threads = player_threads

    async def start(self, ctx):
        await self.send_question(ctx)

    async def send_question(self, ctx):

        if self.current_view:
            self.current_view.stop()
            self.current_view = None

        if self.current_question_index >= len(self.quiz.questions):
            await self.end_game()
            return

        question = self.quiz.questions[self.current_question_index]
        end_time = datetime.now(timezone.utc) + timedelta(seconds=question.time_limit)

        embed = discord.Embed(
            title=f"Pytanie {self.current_question_index + 1}",
            description=question.text
        )
        embed.add_field(name="Pozostały czas", value=f"<t:{int(end_time.timestamp())}:R>")

        view = discord.ui.View(timeout=question.time_limit)
        for idx, answer in enumerate(question.answers):
            button = discord.ui.Button(label=answer, style=discord.ButtonStyle.primary)
            button.callback = self.create_answer_callback(idx)
            view.add_item(button)

        self.current_view = view

        if self.message:
            await self.message.edit(embed=embed, view=view)
        else:
            self.message = await self.channel.send(embed=embed, view=view)

        self.answered_users.clear()
        self.player_answers.clear()

        self.question_task = asyncio.create_task(self.question_timer(ctx, question.time_limit))

    async def question_timer(self, ctx, time_limit):
        try:
            await asyncio.sleep(time_limit)
            for item in self.current_view.children:
                item.disabled = True
            await self.message.edit(view=self.current_view)
            await self.question_summary()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Błąd w question_timer: {e}")


    def create_answer_callback(self, selected_index):
        async def callback(interaction):
            user = interaction.user
            thread = self.player_threads.get(user.id)

            if user not in self.players:
                await interaction.response.send_message("Nie jesteś uczestnikiem tego quizu.", ephemeral=True)
                return

            if user.id in self.answered_users:
                await thread.send("Już odpowiedziałeś na to pytanie.")
                return

            await interaction.response.defer()

            self.answered_users.add(user.id)
            self.player_answers[user.id] = selected_index
            correct_index = self.quiz.questions[self.current_question_index].correct_answer

            if user.id not in self.scores:
                self.scores[user.id] = 0

            if selected_index == correct_index:
                self.scores[user.id] += 1
                if thread:
                    await thread.send("Poprawna odpowiedź!")
            else:
                if thread:
                    await thread.send("Błędna odpowiedź.")

            if len(self.answered_users) >= len(self.players):
                self.question_task.cancel()
                if self.current_view:
                    self.current_view.stop()
                    self.current_view = None
                await self.question_summary()


        return callback

    async def question_summary(self):
        question = self.quiz.questions[self.current_question_index]
        correct_index = question.correct_answer
        correct_answer = question.answers[correct_index]

        correct_answer_embed = discord.Embed(
            title=f"Poprawna odpowiedź na pytanie {self.current_question_index + 1}",
            description=f"Poprawna odpowiedź: {correct_answer}"
        )
        await self.message.edit(embed=correct_answer_embed, view=None)
        if self.current_view:
            self.current_view.stop()
            self.current_view = None

        await asyncio.sleep(self.correct_answer_display_time)

        leaderboard = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)
        scores_text = ""
        for user_id, score in leaderboard:
            user = self.channel.guild.get_member(user_id)
            if user is None:
                try:
                    user = await self.cog.bot.fetch_user(user_id)
                except discord.NotFound:
                    user = None
            if user is not None:
                scores_text += f"{user.name}: {score} punktów\n"
            else:
                scores_text += f"Użytkownik ID {user_id}: {score} punktów\n"

        scoreboard_embed = discord.Embed(
            title="Aktualne wyniki",
            description=scores_text
        )
        await self.message.edit(embed=scoreboard_embed, view=None)

        await asyncio.sleep(self.scoreboard_display_time)

        self.current_question_index += 1
        await self.send_question(self.message)

    async def end_game(self):
        leaderboard = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)
        description = ""
        for user_id, score in leaderboard:
            user = self.channel.guild.get_member(user_id)
            if user is None:
                try:
                    user = await self.cog.bot.fetch_user(user_id)
                except discord.NotFound:
                    user = None
            if user is not None:
                description += f"{user.name}: {score} punktów\n"
            else:
                description += f"Użytkownik ID {user_id}: {score} punktów\n"

        embed = discord.Embed(title="Koniec gry!", description=description)
        await self.message.edit(embed=embed, view=None)

        for thread in self.player_threads.values():
            await thread.delete()
        self.player_threads.clear()

        game_key = (self.channel.guild.id, self.channel.id)
        del self.cog.active_games[game_key]
