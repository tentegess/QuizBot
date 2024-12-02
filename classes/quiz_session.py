import discord
from discord.ext import commands
from discord import app_commands
from utils.get_quiz import get_quiz_for_guild
import asyncio
import traceback
from datetime import datetime, timedelta, timezone

class QuizSession:
    def __init__(self, quiz, channel, cog, players, message, correct_answer_display_time=5, scoreboard_display_time=5
                 , send_private_messages=True):
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
        self.game_ended = False

        self.correct_answer_display_time = correct_answer_display_time
        self.scoreboard_display_time = scoreboard_display_time
        self.send_private_messages = send_private_messages

    async def start(self):
        await self.send_question()

    async def send_question(self):
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
            success = await self.safe_message_edit(embed=embed, view=view)
            if not success:
                return
        else:
            self.message = await self.channel.send(embed=embed, view=view)

        self.answered_users.clear()

        self.question_task = asyncio.create_task(self.question_timer(question.time_limit))


    async def question_timer(self, time_limit):
        try:
            await asyncio.sleep(time_limit)
            for item in self.current_view.children:
                item.disabled = True
            #await self.message.edit(view=self.current_view)
            await self.question_summary()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Błąd w question_timer: {e}")

    async def question_summary(self):
        question = self.quiz.questions[self.current_question_index]
        correct_index = question.correct_answer
        correct_answer = question.answers[correct_index]

        answer_view = discord.ui.View()

        for idx, answer in enumerate(question.answers):
            if idx == correct_index:
                style = discord.ButtonStyle.green
            else:
                style = discord.ButtonStyle.danger

            button = discord.ui.Button(label=answer, style=style, disabled=True)
            answer_view.add_item(button)

        correct_answer_embed = discord.Embed(
            title=f"Poprawna odpowiedź na pytanie {self.current_question_index + 1}",
            description=f"Poprawna odpowiedź: {correct_answer}"
        )
        success = await self.safe_message_edit(embed=correct_answer_embed, view=answer_view)
        if not success:
            return

        await asyncio.sleep(self.correct_answer_display_time)

        if self.current_question_index + 1 >= len(self.quiz.questions):
            await self.end_game()
        else:
            await self.show_scoreboard(next_question_in=self.scoreboard_display_time)
            await asyncio.sleep(self.scoreboard_display_time)
            self.current_question_index += 1
            await self.send_question()

    def create_answer_callback(self, selected_index):
        async def callback(interaction):
            user = interaction.user

            if user not in self.players:
                await interaction.response.send_message("Nie jesteś uczestnikiem tego quizu.", ephemeral=True)
                return

            if user.id in self.answered_users:
                await interaction.response.defer()
                await self.send_mess(user, "Już odpowiedziałeś na to pytanie")
                return

            await interaction.response.defer()

            self.answered_users.add(user.id)

            correct_index = self.quiz.questions[self.current_question_index].correct_answer

            if user not in self.scores:
                self.scores[user] = 0

            if selected_index == correct_index:
                self.scores[user] += 1
                await self.send_mess(user, "Poprawna odpowiedź")
            else:
                await self.send_mess(user, "Błędna odpowiedź")

            if len(self.answered_users) >= len(self.players):
                self.question_task.cancel()
                await self.question_summary()

        return callback

    async def send_mess(self, user, desc):
        if self.send_private_messages:
            try:
                await user.send(desc)
            except discord.Forbidden:
                pass

    async def show_scoreboard(self, final=False, next_question_in=None):
        leaderboard = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)
        scores_text = "\n".join([f"{user.name}: {score} punktów" for user, score in leaderboard])

        title = "Aktualne wyniki" if not final else "Koniec gry! Ostateczne wyniki"

        scoreboard_embed = discord.Embed(
            title=title,
            description=scores_text
        )

        if next_question_in is not None:
            end_time = datetime.now(timezone.utc) + timedelta(seconds=next_question_in)
            scoreboard_embed.add_field(name="Następne pytanie ", value=f"<t:{int(end_time.timestamp())}:R>")

        success = await self.safe_message_edit(embed=scoreboard_embed, view=None)
        if not success:
            return

    async def safe_message_edit(self, embed=None, view=None):
        try:
            await self.message.edit(embed=embed, view=view)
        except discord.NotFound:
            await self.game_del()
            return False
        except discord.HTTPException as e:
            print(f"Błąd podczas edycji wiadomości: {e}")
            return False
        return True

    async def game_del(self):
        if self.game_ended:
            return
        self.game_ended = True
        if hasattr(self, 'question_task') and not self.question_task.done():
            self.question_task.cancel()

        view = discord.ui.View()
        embed = discord.Embed(
            title=f"Gra przerwana",
            description="Quiz został zakończony, ponieważ wiadomość z quizem została usunięta."
        )

        await self.channel.send(embed=embed, view=view)

        game_key = (self.channel.guild.id, self.channel.id)
        if game_key in self.cog.active_games:
            del self.cog.active_games[game_key]

    async def end_game(self):
        if self.game_ended:
            return
        self.game_ended = True
        await self.show_scoreboard(final=True)

        game_key = (self.channel.guild.id, self.channel.id)
        if game_key in self.cog.active_games:
            del self.cog.active_games[game_key]
