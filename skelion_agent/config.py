from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Skelion Unified Autonomous Platform"
    VERSION: str = "1.0.0-unified"
    API_V1_STR: str = "/api/v1"

    # Core security keys – safe defaults so the server boots with zero env vars
    SECRET_KEY: str = "dev-secret-key"
    ENCRYPTION_KEY: str = "dev-encryption-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Database & Redis broker
    DATABASE_URL: str = "sqlite:///helios.db"
    DATABASE_URI: str = "sqlite:///helios.db"  # Alias for backward compatibility
    REDIS_URL: str = "redis://localhost:6379/0"

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
