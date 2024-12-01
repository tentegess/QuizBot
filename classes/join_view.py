import discord
from discord.ui import Button, View
import asyncio
from utils.get_quiz import get_quiz_for_guild
from classes.quiz_session import QuizSession

class JoinQuizView(View):
    def __init__(self, cog, game_key, timeout=10, send_private_messages=True):
        super().__init__()
        self.players = set()
        self.timeout = timeout
        self.send_private_messages = send_private_messages

        self.cog = cog
        self.game_key = game_key
        self.message = None

    @discord.ui.button(label="Dołącz do quizu", style=discord.ButtonStyle.primary)
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        await interaction.response.defer()
        if user in self.players:
            if self.send_private_messages:
                try:
                    await user.send("Już dołączyłeś do quizu.")
                except discord.Forbidden:
                    pass
            return

        self.players.add(user)
        if self.send_private_messages:
            try:
                await user.send("Dołączyłeś do quizu.")
            except discord.Forbidden:
                pass

        message = interaction.message
        embed = message.embeds[0]
        player_names = ', '.join([player.name for player in self.players])
        fields = [field for field in embed.fields if field.name != "Uczestnicy:"]
        embed.clear_fields()
        for field in fields:
            embed.add_field(name=field.name, value=field.value, inline=field.inline)
        embed.add_field(name="Uczestnicy:", value=player_names or "Brak", inline=False)
        await message.edit(embed=embed)