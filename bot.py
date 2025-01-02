import logging
from discord.ext.ipc import Server, ClientPayload
from discord.ext import commands
import discord
import os
from dotenv import load_dotenv
from config.config import db
import asyncio
from bot_utils.utils import set_logger

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True


class BotClass(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.ipc2 = Server(self, secret_key='test')
        self.db = db

    def log(self, message, name, level, **kwargs):
        self.logger.name = name
        self.logger.log(level=level, msg=message, **kwargs)

    async def on_ready(self):
        print(f'Zalogowano jako {self.user.name}')

        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f"Załadowano: {filename}")
                except Exception as e:
                    print(f"Błąd przy ładowaniu {filename}: {e}")
        try:
            synced = await self.tree.sync()
            print(f"Zsynchronizowano {len(synced)} komend.")
        except Exception as e:
            print(f"Błąd podczas synchronizacji komend: {e}")

        asyncio.create_task(self.ipc2.start())

    @Server.route()
    async def guild_count(self, _):
        return str(len(self.guilds))

    @Server.route()
    async def bot_guilds(self, _):
        guild_ids = [str(guild.id) for guild in self.guilds]
        return {"data": guild_ids}

    @Server.route()
    async def guild_stats(self, data: ClientPayload):
        guild = self.get_guild(data.guild_id)
        if not guild:
            return {
                "member_count": 0,
                "name": "Unknown"
            }
        return {
            "name": guild.name,
            "member_count": guild.member_count
        }

    async def on_ipc_ready(self):
        print("Ipc server is ready.")

    async def on_ipc_error(self, endpoint: str, exc: Exception):
        raise exc


if __name__ == "__main__":
    load_dotenv()
    bot = BotClass()
    bot.logger, console_handler = set_logger()
    bot.run(os.environ.get('DC_TOKEN'), log_handler=console_handler, log_level=logging.DEBUG)
