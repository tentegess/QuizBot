import discord
from discord.ui import Button, View
import asyncio
from utils.get_quiz import get_quiz_for_guild
from classes.quiz_session import QuizSession

class JoinQuizView(View):
    def __init__(self, timeout=10):
        super().__init__()
        self.players = set()
        self.timeout = timeout

    @discord.ui.button(label="Dołącz do quizu", style=discord.ButtonStyle.primary)
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        if user in self.players:
            await interaction.response.send_message("Już dołączyłeś do quizu!", ephemeral=True)
            return

        self.players.add(user)
        await interaction.response.send_message("Dołączyłeś do quizu!", ephemeral=True)

        message = interaction.message
        embed = message.embeds[0]
        player_names = ', '.join([player.name for player in self.players])
        fields = [field for field in embed.fields if field.name != "Uczestnicy:"]
        embed.clear_fields()
        for field in fields:
            embed.add_field(name=field.name, value=field.value, inline=field.inline)
        embed.add_field(name="Uczestnicy:", value=player_names or "Brak", inline=False)
        await message.edit(embed=embed)

