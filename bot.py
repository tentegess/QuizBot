import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from flask import Flask, render_template
from threading import Thread
from routes import init_routes

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

app = Flask(__name__)
init_routes(app)


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

    def run_flask():
        app.run(host='0.0.0.0', port=5000)


    flask_thread = Thread(target=run_flask)
    flask_thread.start()

    bot.run(os.environ.get('DC_TOKEN'))
