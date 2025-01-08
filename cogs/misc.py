import logging
from datetime import timedelta, datetime, timezone
from logging import ERROR

import discord
from discord.ext import commands
from discord import app_commands

from typing import Optional
from bot_modules.search_view import SearchView
from model.settings_model import SettingsModel

from enum import Enum
from bot_utils.utils import fetch_quizzes_page, count_quizzes


class TimeRange(Enum):
    day = "day"
    week = "week"
    month = "month"




class MiscCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = self.bot.db

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        self.bot.log(message="bot dołącza", name="test", level=logging.INFO)
        try:
            default_settings = SettingsModel(guild_id=guild.id).dict()
            await self.db['Settings'].update_one(
                {"guild_id": guild.id},
                {"$set": default_settings},
                upsert=True
            )
            self.bot.log(message=f"Utworzono ustawienia dla gildii {guild.name}", name="Join", level=logging.INFO)
        except Exception as e:
            self.bot.log(message=f"Błąd w tworzeniu ustawień dla gildii {guild.name}", name="MongoDB Error", level=ERROR)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        try:
            await self.db['Settings'].delete_one({"guild_id": guild.id})
            self.bot.log(message=f"usunięto ustawienia dla gildii {guild.name}", name="Join", level=logging.INFO)
        except Exception as e:
            self.bot.log(message=f"Błąd w usunięciu ustawień dla gildii {guild.name}", name="MongoDB Error", level=ERROR)


    @app_commands.command(name="leaderboard", description="Wyświetla listę najlepszych graczy.")
    @app_commands.describe(
        time_range="Okres (day/week/month). Brak = wszystkie wyniki.",
        limit="Ilu użytkowników wyświetlić (domyślnie 10)",
    )
    @app_commands.guild_only()
    async def leaderboard(
            self,
            interaction: discord.Interaction,
            time_range: Optional[TimeRange] = None,  # day/week/month
            limit: Optional[int] = 10
    ):
        guild_id = interaction.guild.id

        query = {"guild_id": guild_id}

        now = datetime.now(timezone.utc)
        if time_range == TimeRange.day:
            cutoff = now - timedelta(days=1)
            query["finished_at"] = {"$gte": cutoff}
        elif time_range == TimeRange.week:
            cutoff = now - timedelta(weeks=1)
            query["finished_at"] = {"$gte": cutoff}
        elif time_range == TimeRange.month:
            cutoff = now - timedelta(days=30)
            query["finished_at"] = {"$gte": cutoff}

        pipeline = [
            {"$match": query},
            {"$group": {
                "_id": "$user_id",
                "total_score": {"$sum": "$score"}
            }},
            {"$sort": {"total_score": -1}},
            {"$limit": limit}
        ]

        try:
            await interaction.response.defer()
            results_coll = self.db["Results"]
            docs = await results_coll.aggregate(pipeline).to_list(None)
        except Exception as e:
            self.bot.log(message=e, name="MongoDB error", level=ERROR)
            await interaction.followup.send("Wystąpił problem z pobraniem wyników spróbuj ponownie później", ephemeral=True)
            return

        if not docs:
            await interaction.followup.send("Brak wyników w tym okresie.", ephemeral=True)
            return

        embed = discord.Embed(
            title="Ranking graczy",
            description=f"Wyniki serwera: {interaction.guild.name}",
            color=discord.Color.gold()
        )

        description = ""
        rank = 1
        for doc in docs:
            user_id = doc["_id"]
            total_score = doc["total_score"]
            member = interaction.guild.get_member(user_id)
            user_mention = member.mention if member else f"<@{user_id}>"
            description += f"**{rank}.** {user_mention} — {total_score} pkt\n"
            rank += 1

        embed.description = description
        await interaction.followup.send(embed=embed, ephemeral=False)

    @app_commands.command(name="searchquiz", description="Wyszukaj quizy po słowie kluczowym.")
    @app_commands.describe(keyword="Fraza do wyszukania",
                           page_size="Liczba quizów na stronę (domyślnie 5)",
                           sort="Sortowanie wyników (domyślnie od najnowszych)")
    @app_commands.choices(sort=[
        app_commands.Choice(name="Tytuł rosnąco", value="title_asc"),
        app_commands.Choice(name="Tytuł malejąco", value="title_desc"),
        app_commands.Choice(name="Liczba pytań rosnąco", value="question_asc"),
        app_commands.Choice(name="Liczba pytań malejąco", value="question_desc"),
        app_commands.Choice(name="Autor rosnąco", value="author_asc"),
        app_commands.Choice(name="Autor malejąco", value="author_desc"),
        app_commands.Choice(name="Data utworzenia rosnąco", value="created_asc"),
        app_commands.Choice(name="Data utworzenia malejąco", value="created_desc"),
        app_commands.Choice(name="Ostatnia modyfikacja rosnąco", value="updated_asc"),
        app_commands.Choice(name="Ostatnia modyfikacja malejąco", value="updated_desc"),
    ])
    @app_commands.guild_only()
    async def search_quiz(self, interaction: discord.Interaction, keyword: str, page_size: Optional[int] = 5,
                          sort:Optional[str] = "created_desc"):
        try:
            await interaction.response.send_message("Szukam quizów.", ephemeral=True)
            total = await count_quizzes(self.bot.db, interaction.user.id, keyword)
            if total == 0:
                await interaction.edit_original_response(content="Brak wyników dla tej frazy.")
                return

            page = 0
            print(sort)
            results = await fetch_quizzes_page(
                db=self.bot.db,
                user_id=interaction.user.id,
                search=keyword,
                page=page,
                page_size=page_size,
                sort=sort,
            )
        except Exception as e:
            self.bot.log(message=e, name="MongoDB error", level=ERROR)
            await interaction.edit_original_response(content="Wystąpił problem z wyszukaniem quizów spróbuj ponownie później")
            return

        view = SearchView(
            db=self.bot.db,
            user_id=interaction.user.id,
            search=keyword,
            total_count=total,
            page=page,
            page_size=page_size,
            sort=sort,
        )

        embed = view.build_embed(results, page)
        await interaction.edit_original_response(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(MiscCog(bot))