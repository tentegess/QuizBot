import logging
import sys
from discord.ext import commands
import discord
import os
from dotenv import load_dotenv
from config.config import db
from bot_utils.utils import set_logger, calc_shards
from redis import asyncio as aioredis
from logging import ERROR, INFO

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True


class BotClass(commands.AutoShardedBot):
    def __init__(self, shards, total_shards):
        super().__init__(command_prefix="!", intents=intents, shard_ids=shards, shard_count=total_shards)
        self.db = db
        self.redis = aioredis.from_url(os.environ.get("REDIS_CONNECTION"), decode_responses=True)
        self.total_shards = total_shards

    def log(self, message, name, level, **kwargs):
        self.logger.name = name
        self.logger.log(level=level, msg=message, **kwargs)

    async def on_ready(self):
        self.logger.log(level=INFO,msg=f'Zalogowano jako {self.user.name}')
        self.logger.log(level=INFO, msg=f'Połączono z shardami: {list(self.shards.keys())}')
        try:
            await self.redis.ping()
            self.logger.log(level=INFO,msg="Połączono z bazą redis")
        except Exception as e:
            self.logger.log(level=ERROR,msg=e)

        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    self.logger.log(level=INFO,msg=f"Załadowano: {filename}")
                except Exception as e:
                    self.logger.log(level=ERROR,msg=f"Błąd przy ładowaniu {filename}: {e}")
        try:
            synced = await self.tree.sync()
            self.logger.log(level=INFO,msg=f"Zsynchronizowano {len(synced)} komend.")
        except Exception as e:
            self.logger.log(level=ERROR,msg=f"Błąd podczas synchronizacji komend: {e}")



if __name__ == "__main__":
    load_dotenv()
    inst_index = int(os.environ.get("INSTANCE_INDEX",0))
    total_shards = int(os.environ.get("TOTAL_SHARDS",1))
    total_instances = int(os.environ.get("TOTAL_INSTANCES",1))
    try:
        inst_shards = calc_shards(inst_index, total_instances, total_shards)
    except Exception as e:
        print(e)
        sys.exit(1)
    bot = BotClass(inst_shards, total_shards)
    bot.logger, console_handler = set_logger()
    bot.run(os.environ.get('DC_TOKEN'), log_handler=console_handler, log_level=logging.DEBUG)
