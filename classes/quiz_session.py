import discord
from discord.ext import commands
from discord import app_commands
from utils.get_quiz import get_quiz_for_guild
import asyncio
import traceback
from datetime import datetime, timedelta, timezone

class QuizSession:
    def __init__(self, quiz, channel, cog, players, message):
        self.quiz = quiz
        self.channel = channel
        self.cog = cog
        self.players = players
        self.current_question_index = 0
        self.scores = {}
        self.message = message
        self.answered_users = set()
        self.current_view = None

    async def start(self, ctx):
        await self.send_question(ctx)

    async def send_question(self, ctx):
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

        self.question_task = asyncio.create_task(self.question_timer(ctx, question.time_limit))

    async def question_timer(self, ctx, time_limit):
        try:
            await asyncio.sleep(time_limit)
            for item in self.current_view.children:
                item.disabled = True
            embed = self.message.embeds[0]
            embed.add_field(name="Status", value="Czas na to pytanie minął!", inline=False)
            await self.message.edit(embed=embed, view=self.current_view)
            self.current_question_index += 1
            if hasattr(self, 'timer_task'):
                self.timer_task.cancel()
            await self.send_question(ctx)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Błąd w question_timer: {e}")


    def create_answer_callback(self, selected_index):
        async def callback(interaction):
            if not any(not item.disabled for item in self.current_view.children):
                await interaction.response.send_message("Czas na odpowiedź minął!", ephemeral=True)
                return

            user = interaction.user

            if user.id in self.answered_users:
                await interaction.response.send_message("Już odpowiedziałeś na to pytanie.", ephemeral=True)
                return

            if user not in self.players:
                await interaction.response.send_message("Nie jesteś uczestnikiem tego quizu.", ephemeral=True)
                return

            self.answered_users.add(user.id)

            correct_index = self.quiz.questions[self.current_question_index].correct_answer

            if user not in self.scores:
                self.scores[user] = 0

            if selected_index == correct_index:
                self.scores[user] += 1
                await interaction.response.send_message("Poprawna odpowiedź!", ephemeral=True)
                #await interaction.response.edit_message(content="Poprawna odpowiedź!")
            else:
                await interaction.response.send_message("Błędna odpowiedź.", ephemeral=True)
                #await interaction.response.edit_message("Blędna odpowiedź!")

            if len(self.answered_users) >= len(self.players):
                self.question_task.cancel()
                self.current_question_index += 1
                await self.send_question(interaction)

        return callback

    async def end_game(self):
        leaderboard = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)
        description = "\n".join([f"{user.name}: {score} punktów" for user, score in leaderboard])

        embed = discord.Embed(title="Koniec gry!", description=description)
        await self.message.edit(embed=embed, view=None)

        game_key = (self.channel.guild.id, self.channel.id)
        del self.cog.active_games[game_key]
