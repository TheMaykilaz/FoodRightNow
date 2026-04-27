import os
import json
import functools
import redis
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

try:
    redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2)
    redis_client.ping()
    print(f"[Cache] Connected to Redis at {REDIS_URL}")
except Exception:
    redis_client = None
    print(f"[Cache] Redis unavailable at {REDIS_URL} — caching disabled")


def cacheable(prefix: str, ttl: int = 60):
    """
    Caching decorator analogous to Spring @Cacheable.
    Stores JSON response in Redis. Returns X-Cache: HIT/MISS header.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if redis_client is None:
                return func(*args, **kwargs)

            # Build cache key from kwargs, skipping db session and request objects
            key_parts = []
            for k, v in sorted(kwargs.items()):
                if k in ('db', 'request'):
                    continue
                if v is not None:
                    key_parts.append(f"{k}={v}")

            cache_key = f"cache:{prefix}:{':'.join(key_parts)}" if key_parts else f"cache:{prefix}"

            # Check cache
            try:
                cached = redis_client.get(cache_key)
                if cached is not None:
                    return JSONResponse(
                        content=json.loads(cached),
                        headers={"X-Cache": "HIT"}
                    )
            except Exception:
                pass

            # Cache MISS — call original function
            result = func(*args, **kwargs)
            encoded = jsonable_encoder(result)

            # Store result in Redis
            try:
                serialized = json.dumps(encoded, default=str)
                redis_client.setex(cache_key, ttl, serialized)
            except Exception:
                pass

            return JSONResponse(
                content=encoded,
                headers={"X-Cache": "MISS"}
            )
        return wrapper
    return decorator


def cache_evict(prefix: str):
    """Evict all cache entries matching the given prefix. Analogous to Spring @CacheEvict."""
    if redis_client is None:
        return
    try:
        keys = list(redis_client.scan_iter(f"cache:{prefix}*"))
        if keys:
            redis_client.delete(*keys)
    except Exception:
        pass


def cache_flush_all():
    """Flush entire cache. For testing purposes."""
    if redis_client is None:
        return 0
    try:
        keys = list(redis_client.scan_iter("cache:*"))
        if keys:
            redis_client.delete(*keys)
        return len(keys)
    except Exception:
        return 0
