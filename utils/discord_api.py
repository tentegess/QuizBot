import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

class DiscordAPI:
    BASE_URL = "https://discord.com/api/v10"

    def __init__(self):
        self.bot_token = os.getenv("DC_TOKEN")
        self.headers = {
            "Authorization": f"Bot {self.bot_token}",
            "Content-Type": "application/json"
        }
        self.session = None

    async def setup(self):
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def fetch_guilds(self):
        async with self.session.get(f"{self.BASE_URL}/users/@me/guilds", headers=self.headers) as response:
            if response.status == 200:
                guilds = await response.json()
                return [guild["id"] for guild in guilds]
            raise Exception(f"Failed to fetch guilds: {response.status}")

    async def fetch_guild_name(self, guild_id: str):
        async with self.session.get(f"{self.BASE_URL}/guilds/{guild_id}", headers=self.headers) as response:
            if response.status == 200:
                guild_data = await response.json()

                return {
                    "name": guild_data.get("name"),
                }
            raise Exception(f"Failed to fetch guild stats: {response.status}")

    async def close(self):
        await self.session.close()

discord_api = DiscordAPI()
