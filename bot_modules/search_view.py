import discord
from discord.ui import Button, View
import asyncio
from typing import Optional, List

from pymongo import DESCENDING

from bot_utils.utils import fetch_quizzes_page, SortEnum


class SearchView(discord.ui.View):
    def __init__(self, db,
        user_id: int,
        search: str,
        total_count: int,
        page: int,
        page_size: int,
        sort: SortEnum,):
        super().__init__(timeout=180)
        self.db = db
        self.user_id = user_id
        self.search = search
        self.total_count = total_count
        self.page = page
        self.page_size = page_size
        self.sort= sort

        self.max_page = (self.total_count - 1) // self.page_size

        self.update_buttons()

    def update_buttons(self):
        self.prev_button.disabled = (self.page <= 0)
        self.next_button.disabled = (self.page >= self.max_page)

    def build_embed(self, results: list, page: int) -> discord.Embed:
        embed = discord.Embed(
            title=f"Wyniki wyszukiwaniadla {self.search} | Strona {page + 1}/{self.max_page + 1}",
            color=discord.Color.blurple()
        )
        embed.description = f"Znaleziono {self.total_count} quizów pasujących do frazy."

        for r in results:
            t = r["title"]
            acode = r["access_code"]
            qcount = r["questions_count"]
            user = r["user_id"]
            embed.add_field(
                name=f"{t} | Kod quizu: {acode}",
                value=f"Liczba pytań: {qcount}\nAutor: {user}",
                inline=False
            )
        return embed

    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.primary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page -= 1
        self.update_buttons()

        results = await fetch_quizzes_page(
            db=self.db,
            user_id=self.user_id,
            search=self.search,
            page=self.page,
            page_size=self.page_size,
            sort=self.sort,
        )
        embed = self.build_embed(results, self.page)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        self.update_buttons()

        results = await fetch_quizzes_page(
            db=self.db,
            user_id=self.user_id,
            search=self.search,
            page=self.page,
            page_size=self.page_size,
            sort=self.sort,
        )
        embed = self.build_embed(results, self.page)
        await interaction.response.edit_message(embed=embed, view=self)
