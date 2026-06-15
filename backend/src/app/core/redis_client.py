import os

from redis.asyncio import Redis

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")


class RedisClient:
    _instance: Redis | None = None
    _loop_id: int | None = None

    @classmethod
    def get_instance(cls) -> Redis:
        import asyncio

        try:
            loop = asyncio.get_running_loop()
            current_loop_id = id(loop)
        except RuntimeError:
            current_loop_id = None

        if cls._instance is not None and cls._loop_id == current_loop_id:
            return cls._instance

        cls._instance = Redis.from_url(REDIS_URL, decode_responses=True)
        cls._loop_id = current_loop_id
        return cls._instance

    @classmethod
    async def close(cls) -> None:
        if cls._instance is not None:
            await cls._instance.close()
            cls._instance = None
            cls._loop_id = None

    @classmethod
    async def get(cls, key: str) -> str | None:
        redis = cls.get_instance()
        return await redis.get(key)

    @classmethod
    async def set(cls, key: str, value: str, ttl: int) -> None:
        redis = cls.get_instance()
        if ttl > 0:
            await redis.setex(key, ttl, value)
        else:
            await redis.set(key, value)

    @classmethod
    async def delete(cls, key: str) -> None:
        redis = cls.get_instance()
        await redis.delete(key)

    @classmethod
    async def delete_pattern(cls, pattern: str) -> None:
        redis = cls.get_instance()
        keys = []
        async for key in redis.scan_iter(match=pattern):
            keys.append(key)
        if keys:
            await redis.delete(*keys)

    @classmethod
    async def flushdb(cls) -> None:
        redis = cls.get_instance()
        await redis.flushdb()


redis_client = RedisClient()
