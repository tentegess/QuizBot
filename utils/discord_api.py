import asyncio
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

    async def _make_request(self, url: str):
        async with self.session.get(url, headers=self.headers) as response:
            if response.status == 200:
                return await response.json()
            elif response.status == 429:
                retry_after = int(response.headers.get("Retry-After", 1))
                print(f"Rate limit reached. Retrying in {retry_after} seconds...")
                await asyncio.sleep(retry_after)
                return await self._make_request(url)
            else:
                raise Exception(f"Request failed with status {response.status}")

    async def fetch_guilds(self):
        url = f"{self.BASE_URL}/users/@me/guilds"
        guilds = await self._make_request(url)
        return [guild["id"] for guild in guilds]

    async def fetch_guild_name(self, guild_id: str):
        url = f"{self.BASE_URL}/guilds/{guild_id}"
        guild_data = await self._make_request(url)
        return {"name": guild_data.get("name")}

    async def close(self):
        await self.session.close()

discord_api = DiscordAPI()
