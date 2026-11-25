"""Atomic Redis sliding window shared by every worker and instance."""
import hashlib
import uuid
import redis
from fastapi import HTTPException
from app.config import settings
from app.redis_client import r

# Redis TIME avoids clock differences between clients. Lua makes prune/count/add
# one operation, so simultaneous workers cannot exceed the same window limit.
SLIDING_WINDOW = """
local clock = redis.call('TIME')
local now = tonumber(clock[1]) + tonumber(clock[2]) / 1000000
local window = tonumber(ARGV[1])
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now - window)
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[2]) then
    local oldest = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
    return math.max(1, math.ceil(tonumber(oldest[2]) + window - now))
end
redis.call('ZADD', KEYS[1], now, ARGV[3])
redis.call('EXPIRE', KEYS[1], window)
return 0
"""

def check_rate_limit(key: str) -> None:
    storage_key = "day14:rate:" + hashlib.sha256(key.encode()).hexdigest()
    try:
        retry_after = int(r.eval(SLIDING_WINDOW, 1, storage_key, 60,
                                 settings.rate_limit_per_minute, uuid.uuid4().hex))
    except redis.RedisError:
        raise HTTPException(status_code=503, detail="Rate limit storage unavailable") from None
    if retry_after:
        raise HTTPException(status_code=429, detail="Rate limit exceeded",
                            headers={"Retry-After": str(retry_after)})
