import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Ładowanie cogs
@bot.event
async def on_ready():
    print(f'Zalogowano jako {bot.user.name}')
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            await bot.load_extension(f'cogs.{filename[:-3]}')
    try:
        synced = await bot.tree.sync()
        print(f"Zsynchronizowano {len(synced)} komend.")
    except Exception as e:
        print(f"Błąd podczas synchronizacji komend: {e}")
    print('Wszystkie cogs zostały załadowane.')

if __name__ == "__main__":
    load_dotenv()
    bot.run(os.environ.get('DC_TOKEN'))