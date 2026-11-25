"""12-Factor settings; environment overrides the optional local .env file."""
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv(override=False)

@dataclass(frozen=True)
class Settings:
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    agent_api_key: str = field(default_factory=lambda: os.getenv("AGENT_API_KEY", ""))
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    rate_limit_per_minute: int = field(default_factory=lambda: int(os.getenv("RATE_LIMIT_PER_MINUTE", "10")))
    daily_budget_usd: float = field(default_factory=lambda: float(os.getenv("DAILY_BUDGET_USD", "1.0")))
    redis_connect_timeout: float = field(default_factory=lambda: float(os.getenv("REDIS_CONNECT_TIMEOUT_SECONDS", "2")))
    redis_socket_timeout: float = field(default_factory=lambda: float(os.getenv("REDIS_SOCKET_TIMEOUT_SECONDS", "3")))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper())

    def __post_init__(self):
        if not 1 <= self.port <= 65535:
            raise ValueError("PORT must be between 1 and 65535")
        if self.redis_connect_timeout <= 0 or self.redis_socket_timeout <= 0:
            raise ValueError("Redis timeouts must be positive")
        if self.rate_limit_per_minute < 1 or self.daily_budget_usd < 0:
            raise ValueError("Rate limit must be positive and budget must be nonnegative")

settings = Settings()
