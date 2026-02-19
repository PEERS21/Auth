from typing import Optional
from os import getenv
from dotenv import dotenv_values

async def store_state(redis_client, state: str, next_url: str, ttl: int = config.get("STATE_TTL", "")):
    key = f"{getenv("STATE_PREFIX")}{state}"
    await redis_client.setex(key, ttl, next_url)


async def pop_state(redis_client, state: str) -> Optional[str]:
    key = f"{getenv("STATE_PREFIX")}{state}"
    return await redis_client.getdel(key)
