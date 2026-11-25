"""Daily USD budget shared across workers, stored in Redis with expiry."""
from datetime import datetime, timezone
import redis
from fastapi import HTTPException
from app.config import settings
from app.redis_client import r

PRICE_INPUT_PER_1K = 0.00015
PRICE_OUTPUT_PER_1K = 0.0006

def _budget_key() -> str:
    return "day14:cost:" + datetime.now(timezone.utc).strftime("%Y-%m-%d")

def check_budget() -> None:
    try:
        spent = float(r.get(_budget_key()) or 0)
    except redis.RedisError:
        raise HTTPException(status_code=503, detail="Budget storage unavailable") from None
    if spent >= settings.daily_budget_usd:
        raise HTTPException(status_code=402, detail="Daily budget exhausted")

def record_cost(input_tokens: int, output_tokens: int) -> float:
    cost = input_tokens / 1000 * PRICE_INPUT_PER_1K + output_tokens / 1000 * PRICE_OUTPUT_PER_1K
    key = _budget_key()
    try:
        with r.pipeline(transaction=True) as pipe:
            pipe.incrbyfloat(key, cost)
            pipe.expire(key, 2 * 24 * 3600)
            pipe.execute()
    except redis.RedisError:
        raise HTTPException(status_code=503, detail="Budget storage unavailable") from None
    return cost
