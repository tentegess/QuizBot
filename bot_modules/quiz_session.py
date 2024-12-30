import io

import discord
import asyncio
from datetime import datetime, timedelta, timezone
from model.game_model import GameModel
from model.resut_model import ResultModel
from model.quiz_model import QuizModel

class QuizSession:
    def __init__(self, quiz:QuizModel, channel, cog, players, message, game_starter, correct_answer_display_time=5, scoreboard_display_time=5
                 , send_private_messages=True):
        self.quiz = quiz
        self.questions = quiz.questions

        self.channel = channel
        self.cog = cog
        self.players = players
        self.current_question_index = 0
        self.scores = {}
        self.player_answers = {}
        self.message = message
        self.answered_users = set()
        self.current_view = None
        self.game_starter = game_starter

        self.streaks = {player: 0 for player in self.players}
        self.correct_count_for_question = 0

        self.correct_answer_display_time = correct_answer_display_time
        self.scoreboard_display_time = scoreboard_display_time
        self.send_private_messages = send_private_messages

        self.is_processing_question = False
        self.game_ended = False



    async def start(self):
        await self.send_question()

    async def send_question(self):
        if self.game_ended:
            return

        if self.current_question_index >= len(self.quiz.questions):
            await self.end_game()
            return

        question = self.questions[self.current_question_index]

        self.correct_count_for_question = 0

        view = discord.ui.View(timeout=question.time)
        for idx, option in enumerate(question.options):
            button = discord.ui.Button(label=option.option, style=discord.ButtonStyle.primary)
            button.callback = self.create_answer_callback(idx)
            view.add_item(button)

        self.current_view = view

        embed = discord.Embed(
            title=f"Pytanie {self.current_question_index + 1}",
            color=discord.Color.blurple()
        )

        file = []
        if question.image_url:
            try:
                out = io.BytesIO()
                await self.cog.fs.download_to_stream(question.image_url, out)
                out.seek(0)
                file.append(discord.File(out, filename="question_image.png"))
                embed.set_image(url="attachment://question_image.png")
            except Exception as e:
                print(f"Błąd pobierania obrazu z GridFS: {e}")

        end_time = datetime.now(timezone.utc) + timedelta(seconds=question.time)
        embed.description=f"**Koniec czasu <t:{int(end_time.timestamp())}:R>** \n\n {question.question}"

        if self.message:
            success = await self.safe_message_edit(embed=embed, view=view, file=file)
            if not success:
                return
        else:
            self.message = await self.channel.send(embed=embed, view=view)

        self.answered_users.clear()

        self.question_task = asyncio.create_task(self.question_timer(question.time))


    async def question_timer(self, time: int):
        try:
            await asyncio.sleep(time)
            for item in self.current_view.children:
                item.disabled = True
            await self.question_summary()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Błąd w question_timer: {e}")

    async def question_summary(self):
        if self.game_ended:
            return

        if self.is_processing_question:
            return
        self.is_processing_question = True
        try:
            question = self.questions[self.current_question_index]
            correct_index = next(
                (i for i, opt in enumerate(question.options) if opt.is_correct),
                None
            )

            if correct_index is None:
                correct_index = -1

            correct_answer = question.options[correct_index].option if correct_index >= 0 else "(brak poprawnej)"

            answer_view = discord.ui.View()

            for idx, option in enumerate(question.options):
                style = discord.ButtonStyle.green if idx == correct_index else discord.ButtonStyle.danger

                button = discord.ui.Button(label=option.option, style=style, disabled=True)
                answer_view.add_item(button)

            correct_answer_embed = discord.Embed(
                title=f"Poprawna odpowiedź na pytanie {self.current_question_index + 1}",
                description=f"Poprawna odpowiedź: {correct_answer}",
                color = discord.Color.blurple()
            )
            success = await self.safe_message_edit(embed=correct_answer_embed, view=answer_view)
            if not success:
                return

            await asyncio.sleep(self.correct_answer_display_time)
            if self.game_ended:
                return

            if self.current_question_index + 1 >= len(self.quiz.questions):
                await self.end_game()
            else:
                await self.show_scoreboard(next_question_in=self.scoreboard_display_time)
                await asyncio.sleep(self.scoreboard_display_time)
                self.current_question_index += 1
                await self.send_question()
        finally:
            self.is_processing_question = False

    def create_answer_callback(self, selected_index):
        async def callback(interaction):
            async def callback_mess(embed):
                if self.send_private_messages:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await interaction.response.defer()
            user = interaction.user

            if user not in self.players:
                embed = discord.Embed(
                    title="Nie jesteś uczestnikiem tego quizu."
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            if user.id in self.answered_users:
                embed = discord.Embed(
                    title="Już odpowiedziałeś na to pytanie"
                )
                await callback_mess(embed)
                return

            self.answered_users.add(user.id)

            question = self.questions[self.current_question_index]
            answer = question.options[selected_index]

            if user not in self.scores:
                self.scores[user] = 0

            if answer.is_correct:
                base_points = max(1000 - (self.correct_count_for_question * 100), 500)
                self.correct_count_for_question += 1
                streak = self.streaks[user]
                multiplier = 1.0 + (streak * 0.1)

                self.scores[user] += int(base_points*multiplier)
                self.streaks[user] += 1

                embed = discord.Embed(
                    title="Poprawna odpowiedź!",
                    description=f"Zdobywasz {int(base_points*multiplier)} punktów!",
                    color=discord.Color.green()
                )
                embed.add_field(name="Aktualny wynik", value=str(self.scores[user]), inline=True)
                embed.add_field(name="Streak", value=str(self.streaks[user]), inline=True)

                await callback_mess(embed)
            else:
                self.streaks[user] = 0
                streak = 0

                embed = discord.Embed(
                    title="Błędna odpowiedź!",
                    description="Niestety, nie zdobywasz punktów.",
                    color=discord.Color.red()
                )
                embed.add_field(name="Aktualny wynik", value=str(self.scores[user]), inline=True)
                embed.add_field(name="Streak", value=str(streak), inline=True)
                await callback_mess(embed)

            if len(self.answered_users) >= len(self.players):
                self.question_task.cancel()
                await self.question_summary()

        return callback

    async def send_mess(self, user, desc):
        pass
        # if self.send_private_messages:
        #     try:
        #         await user.send(desc)
        #     except discord.Forbidden:
        #         pass

    async def show_scoreboard(self, final=False, next_question_in=None):
        leaderboard = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)
        scores_text = ""
        rank = 1
        for user, score in leaderboard:
            member = self.channel.guild.get_member(user.id)
            user_mention = member.mention if member else f"<@{user.id}>"
            scores_text += f"**{rank}.** {user_mention} — {score} pkt\n"
            rank += 1

        title = "Aktualne wyniki" if not final else "Koniec gry! Ostateczne wyniki"

        scoreboard_embed = discord.Embed(
            title=title,
            description=scores_text,
            color = discord.Color.blurple() if not final else discord.Color.gold()
        )

        if next_question_in is not None:
            end_time = datetime.now(timezone.utc) + timedelta(seconds=next_question_in)
            scoreboard_embed.add_field(name="Następne pytanie ", value=f"<t:{int(end_time.timestamp())}:R>")

        success = await self.safe_message_edit(embed=scoreboard_embed, view=None)
        if not success:
            return

    async def safe_message_edit(self, embed=None, view=None, file=[]):
        try:
            await self.message.edit(embed=embed, view=view, attachments=file)
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
        self.question_task = None

        view = discord.ui.View()
        embed = discord.Embed(
            title=f"Gra przerwana",
            description="Quiz został zakończony, ponieważ wiadomość z quizem została usunięta.",
            color=discord.Color.red()
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

        if hasattr(self, 'question_task') and not self.question_task.done():
            self.question_task.cancel()
        self.question_task = None

        game_key = (self.channel.guild.id, self.channel.id)
        if game_key in self.cog.active_games:
            del self.cog.active_games[game_key]

        games_coll = self.cog.db["Games"]
        results_coll = self.cog.db["Results"]

        now = datetime.now(timezone.utc)
        game = GameModel(
            guild_id=self.channel.guild.id,
            quiz_code=self.quiz.access_code,
            finished_at=now
        )

        doc_game = game.model_dump(by_alias=True, exclude_unset=True)
        insert_res = await games_coll.insert_one(doc_game)
        game.id = insert_res.inserted_id

        bulk_docs = []
        for player, score in self.scores.items():
            user_id = player.id if hasattr(player, "id") else player
            result_obj = ResultModel(
                game_id=game.id,
                user_id=user_id,
                guild_id=self.channel.guild.id,
                score=score,
                finished_at=now
            )
            doc_res = result_obj.model_dump(by_alias=True, exclude_unset=True)
            bulk_docs.append(doc_res)

        if bulk_docs:
            await results_coll.insert_many(bulk_docs)
