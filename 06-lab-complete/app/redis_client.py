"""Lazy Redis connection: liveness never depends on Redis availability."""
import redis
from app.config import settings

r = redis.from_url(settings.redis_url, decode_responses=True,
                   socket_connect_timeout=settings.redis_connect_timeout,
                   socket_timeout=settings.redis_socket_timeout,
                   health_check_interval=30)

def redis_healthy() -> bool:
    try:
        return bool(r.ping())
    except redis.RedisError:
        return False
