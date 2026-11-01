import os
import sys
import logging
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool
from sqlmodel import create_engine
import redis
import redis.asyncio as aioredis

logger = logging.getLogger("skelion.config")


class Settings(BaseSettings):
    PROJECT_NAME: str = "Skelion Unified Autonomous Platform"
    VERSION: str = "1.0.0-unified"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # Core security keys – safe defaults so the server boots with zero env vars
    SECRET_KEY: str = "dev-secret-key"
    ENCRYPTION_KEY: str = "dev-encryption-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Database & Redis broker
    DATABASE_URL: str = "sqlite:///helios.db"
    DATABASE_URI: str = "sqlite:///helios.db"  # Alias for backward compatibility
    REDIS_URL: str = "redis://localhost:6379/0"

    # SQLAlchemy Connection Pool Settings
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    DB_POOL_PRE_PING: bool = True

    # Redis Connection Pool Settings
    REDIS_MAX_CONNECTIONS: int = 50
    REDIS_SOCKET_TIMEOUT: float = 5.0
    REDIS_SOCKET_CONNECT_TIMEOUT: float = 5.0
    REDIS_RETRY_ON_TIMEOUT: bool = True

    # Third-Party Integrations
    RAZORPAY_KEY_ID: str = "rzp_test_placeholder_key"
    RAZORPAY_KEY_SECRET: str = "rzp_test_dummy_secret"
    STRIPE_API_KEY: str = "sk_test_mock"
    STRIPE_WEBHOOK_SECRET: str = "whsec_testmock"
    GITHUB_APP_ID: str = "0"
    GITHUB_WEBHOOK_SECRET: str = "mock_gh_secret"
    GITHUB_PRIVATE_KEY: Optional[str] = None

    # Server Ports & Host standardization
    CONTROL_PLANE_HOST: str = "127.0.0.1"
    CONTROL_PLANE_PORT: int = 8002
    EDGE_PROXY_HOST: str = "127.0.0.1"
    EDGE_PROXY_PORT: int = 8080
    UPSTREAM_URL: str = "http://127.0.0.1:8000"

    # Quotas & Defaults
    DEFAULT_MONTHLY_QUOTA: int = 1000
    ERROR_RATE_THRESHOLD: float = 0.25

    # LLM Key Pool
    PROVIDER_KEYS_JSON: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env.skelion",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()


def create_database_engine(
    url: Optional[str] = None, settings_obj: Optional[Settings] = None
) -> Engine:
    """Create a configured SQLAlchemy engine with production connection pooling."""
    s = settings_obj or settings
    db_url = url or s.DATABASE_URL
    if "sqlite" in db_url:
        return create_engine(
            db_url,
            connect_args={"check_same_thread": False},
            pool_pre_ping=s.DB_POOL_PRE_PING,
            echo=False,
        )
    else:
        return create_engine(
            db_url,
            poolclass=QueuePool,
            pool_size=s.DB_POOL_SIZE,
            max_overflow=s.DB_MAX_OVERFLOW,
            pool_timeout=s.DB_POOL_TIMEOUT,
            pool_recycle=s.DB_POOL_RECYCLE,
            pool_pre_ping=s.DB_POOL_PRE_PING,
            echo=False,
        )


# Global SQLAlchemy Engine with connection pool
engine: Engine = create_database_engine()


def get_db_engine() -> Engine:
    """Return the configured SQLAlchemy engine."""
    return engine


# Redis Connection Pools (Async and Sync)
async_redis_pool = aioredis.ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=settings.REDIS_MAX_CONNECTIONS,
    socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
    socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
    retry_on_timeout=settings.REDIS_RETRY_ON_TIMEOUT,
    decode_responses=True,
)

sync_redis_pool = redis.ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=settings.REDIS_MAX_CONNECTIONS,
    socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
    socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
    retry_on_timeout=settings.REDIS_RETRY_ON_TIMEOUT,
    decode_responses=True,
)


def get_async_redis() -> aioredis.Redis:
    """Return an async Redis client backed by the connection pool."""
    return aioredis.Redis(connection_pool=async_redis_pool)


def get_sync_redis() -> redis.Redis:
    """Return a synchronous Redis client backed by the connection pool."""
    return redis.Redis(connection_pool=sync_redis_pool)


def validate_secrets(
    raise_on_error: bool = False,
    exit_on_failure: bool = True,
    strict: Optional[bool] = None,
) -> List[str]:
    """
    Validate required secrets at startup.
    In production mode (or when strict=True), exits with error (code 1) if required secrets are missing
    or set to insecure defaults.
    """
    missing: List[str] = []
    env = (os.getenv("ENVIRONMENT") or settings.ENVIRONMENT or "development").lower()
    is_prod = (
        strict
        if strict is not None
        else (
            env == "production"
            or os.getenv("STRICT_SECRETS_CHECK", "false").lower() in ("1", "true")
        )
    )

    if is_prod:
        required_keys = ["SECRET_KEY", "ENCRYPTION_KEY", "DATABASE_URL", "REDIS_URL"]
        insecure_placeholders = {
            "dev-secret-key",
            "dummy_secret",
            "change_me",
            "dev-encryption-key",
            "",
        }
        for key in required_keys:
            val = os.getenv(key) or getattr(settings, key, None)
            if not val or str(val).strip() in insecure_placeholders:
                missing.append(key)
    else:
        # In non-production, ensure keys are not explicitly set to empty strings
        sec_val = os.getenv("SECRET_KEY", settings.SECRET_KEY)
        enc_val = os.getenv("ENCRYPTION_KEY", settings.ENCRYPTION_KEY)
        if sec_val is not None and str(sec_val).strip() == "":
            missing.append("SECRET_KEY")
        if enc_val is not None and str(enc_val).strip() == "":
            missing.append("ENCRYPTION_KEY")

    if missing:
        msg = f"[CRITICAL] Startup aborted: Missing or insecure required secrets: {', '.join(missing)}"
        logger.critical(msg)
        print(msg, file=sys.stderr)
        if raise_on_error:
            raise ValueError(msg)
        if exit_on_failure:
            sys.exit(1)

    return missing
