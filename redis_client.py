import redis.asyncio as redis

async def init_redis(app):
    app['redis'] = redis.Redis(
        host='localhost',
        port=6379,
        db=0,
        decode_responses=True,
        encoding='utf-8'
    )

async def close_redis(app):
    if 'redis' in app:
        await app['redis'].close()