from typing import Optional

from dotenv import dotenv_values
config = dotenv_values("/run/secrets/peers_auth")

async def store_state(redis_client, state: str, next_url: str, ttl: int = config.get("STATE_TTL", "")):
    key = f"{config.get("STATE_PREFIX", "")}{state}"
    await redis_client.setex(key, ttl, next_url)


async def pop_state(redis_client, state: str) -> Optional[str]:
    key = f"{config.get("STATE_PREFIX", "")}{state}"
    return await redis_client.getdel(key)
