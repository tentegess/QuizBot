import json
import logging
from redis import asyncio as aioredis

logger = logging.getLogger(__name__)

class RedisHelper:
    def __init__(self, client: aioredis):
        self.client = client

    async def safe_set(self, key: str, data: dict, ex=3600):
        try:
            serialized = json.dumps(data)
            await self.client.set(key, serialized, ex=ex)
        except (aioredis.RedisError, ConnectionError) as e:
            logger.warning(f"[REDIS] Nie udało się zapisać {key}: {e}")


    async def safe_get(self, key: str):
        try:
            raw = await self.client.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except (aioredis.RedisError, ConnectionError) as e:
            logger.warning(f"[REDIS] Nie udało się odczytać {key}: {e}")
            return None

    async def safe_keys(self, key: str):
        try:
            raw = await self.client.keys(key)
            if raw is None:
                return []
            return raw
        except (aioredis.RedisError, ConnectionError) as e:
            logger.warning(f"[REDIS] Nie udało się odczytać {key}: {e}")
            return None

    async def safe_delete(self, key: str):
        try:
            await self.client.delete(key)
        except (aioredis.RedisError, ConnectionError) as e:
            logger.warning(f"[REDIS] Nie udało się usunąć klucza {key}: {e}")