import redis.asyncio as redis
from os import getenv

async def init_redis(app):
    app['pool'] = redis.ConnectionPool.from_url(getenv("REDIS_URL"))
    app['redis'] = redis.Redis(connection_pool=app['pool'])

async def close_redis(app):
    if 'redis' in app:
        await app['redis'].close()
    if 'pool' in app:
        await app['pool'].close()