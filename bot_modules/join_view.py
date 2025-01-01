import discord
from discord.ui import Button, View
import asyncio
from typing import Optional, List


class JoinQuizView(View):
    def __init__(self, cog, game_key,gamestarter, timeout=10, send_private_messages=True,allowed_users: Optional[List[discord.Member]] = None):
        super().__init__()
        self.players = set()
        self.timeout = timeout

        self.send_private_messages = send_private_messages
        self.game_starter = gamestarter
        self.allowed_users = allowed_users

        self.cog = cog
        self.game_key = game_key
        self.message = None

    @discord.ui.button(label="Dołącz do quizu", style=discord.ButtonStyle.primary)
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user

        if self.allowed_users is not None and (user not in self.allowed_users and user.id is not self.game_starter.id):
            embed = discord.Embed(
                title="Nie możesz dołączyć do tego quizu.",
                description="Nie znajdujesz się na liście dozwolonych uczestników.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if user in self.players:
            if self.send_private_messages:
                embed = discord.Embed(
                    title="Już dołączyłeś do quizu",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.defer()
            return

        self.players.add(user)
        if self.send_private_messages:
            embed = discord.Embed(
                title="Dołączyłeś do quizu",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.defer()

        message = interaction.message
        embed = message.embeds[0]
        player_names = ', '.join([player.name for player in self.players])
        fields = [field for field in embed.fields if field.name != "Uczestnicy:"]
        embed.clear_fields()
        for field in fields:
            embed.add_field(name=field.name, value=field.value, inline=field.inline)
        embed.add_field(name="Uczestnicy:", value=player_names or "Brak", inline=False)
        await message.edit(embed=embed)

