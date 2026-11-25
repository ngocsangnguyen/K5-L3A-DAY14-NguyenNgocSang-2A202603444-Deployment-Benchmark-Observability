"""Production agent: auth, shared quotas, JSON logs and graceful lifecycle."""
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import check_budget, record_cost
from app.rate_limiter import check_rate_limit
from app.redis_client import r, redis_healthy
from utils.mock_llm import ask as llm_ask

class JsonFormatter(logging.Formatter):
    def format(self, record):
        data = {"ts": datetime.now(timezone.utc).isoformat(), "level": record.levelname,
                "event": record.getMessage(), **getattr(record, "fields", {})}
        if record.exc_info:
            data["exception"] = self.formatException(record.exc_info)
        return json.dumps(data, ensure_ascii=False)

handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger = logging.getLogger("day14.agent")
logger.handlers = [handler]
logger.propagate = False
logger.setLevel(settings.log_level)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", extra={"fields": {"environment": settings.environment}})
    yield
    # Uvicorn drains active requests before running lifespan cleanup.
    logger.info("shutdown")
    r.close()

app = FastAPI(title="Production AI Agent", lifespan=lifespan)

@app.middleware("http")
async def request_log(request: Request, call_next):
    started = time.perf_counter()
    request_id = uuid.uuid4().hex[:12]
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        logger.info("http_request", extra={"fields": {"request_id": request_id,
                    "method": request.method, "path": request.url.path,
                    "status": status, "ms": round((time.perf_counter()-started)*1000, 2)}})

class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    user_id: str | None = Field(default=None, max_length=128)

    @field_validator("question")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("question must contain non-whitespace characters")
        return value

@app.get("/health")
def health():
    return {"status": "ok", "environment": settings.environment}

@app.get("/ready")
def ready():
    if not redis_healthy():
        raise HTTPException(status_code=503, detail="Redis unavailable")
    return {"ready": True}

@app.post("/ask")
def ask(body: AskRequest, key: str = Depends(verify_api_key)):
    check_rate_limit(key)
    check_budget()
    try:
        answer = llm_ask(body.question)
    except Exception:
        logger.exception("llm_error")
        raise HTTPException(status_code=503, detail="LLM unavailable") from None
    # This mock returns a string, so token usage is an explicit approximation.
    input_tokens = max(1, len(body.question) // 4)
    output_tokens = max(1, len(answer) // 4)
    cost = record_cost(input_tokens, output_tokens)
    return {"question": body.question, "answer": answer,
            "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens,
                      "cost_usd": cost, "token_count_method": "characters_divided_by_4"}}
