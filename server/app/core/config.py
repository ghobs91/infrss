from functools import cache

from pydantic import AnyUrl, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Environment
    ENVIRONMENT: str = Field(default="development", pattern="^(development|staging|production|test)$")
    LOG_LEVEL: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")

    # Supabase Configuration (validated URLs)
    SUPABASE_URL: AnyUrl
    SUPABASE_JWT_SECRET: SecretStr
    SUPABASE_SERVICE_ROLE_KEY: SecretStr
    SUPABASE_ANON_KEY: str = ""

    # Database Configuration
    # API uses Session Mode (port 5432) with QueuePool for persistent connections
    # Workers use Transaction Mode (port 6543) with NullPool for surgical transactions
    DATABASE_URL_API: str
    DATABASE_URL_WORKER: str

    # CORS Configuration
    CORS_ORIGIN: str = "*"

    # Redis Configuration (validated URL)
    REDIS_URL: str = "redis://localhost:6379/0"

    # AI Configuration
    ENABLE_AI: bool = True  # Master switch for all AI functionality

    # Gemini Configuration (LLM: summaries, translations, enrichment, similarity reasoning)
    GEMINI_API_KEY: str = ""
    GEMINI_SMART_MODEL: str = "gemini-3.6-flash"  # For complex reasoning (e.g. enrichment)
    GEMINI_FAST_MODEL: str = "gemini-3.5-flash-lite"  # For high-volume continuous parsing (summaries, translation)

    # OpenAI Configuration (Embeddings only, e.g. Meilisearch's REST embedder for feed search)
    OPENAI_API_KEY: str = ""
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_EMBEDDING_DIMENSIONS: int = 768

    # RSShub Configuration (validated URL)
    RSSHUB_URL: str = "http://localhost:1200"  # Default RSShub instance URL

    # SSRF protection: set true only if self-hosters need feeds from private/intranet hosts
    ALLOW_PRIVATE_FEED_URLS: bool = False

    # Primary-source catalog
    # SEC EDGAR requires a descriptive User-Agent with contact info (fair-access policy).
    SEC_USER_AGENT: str = "infrss-primary-catalog admin@example.com"
    SEC_RATE_LIMIT_RPS: float = 10.0  # SEC fair-access limit: 10 requests/second
    # Base URL the backend serves synthetic feeds from; used to build promoted feeds.url values.
    SYNTHETIC_FEED_BASE_URL: str = "http://localhost:8008"
    # Render JS-only newsrooms with Playwright. Off by default: Playwright is an optional extra.
    SYNTHETIC_USE_BROWSER: bool = False

    # Meilisearch Configuration
    MEILISEARCH_URL: str = "http://localhost:7700"
    MEILISEARCH_MASTER_KEY: SecretStr
    MEILISEARCH_INDEX_NAME: str = "feeds"

    # Inbound Webhook Config
    INBOUND_WEBHOOK_SECRET: SecretStr = Field(default_factory=lambda: SecretStr("dev_inbound_secret"))

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("GEMINI_API_KEY")
    @classmethod
    def validate_gemini_api_key(cls, v: str, info) -> str:
        """Validate GEMINI_API_KEY is provided when AI is enabled."""
        return v

    @field_validator("DATABASE_URL_API")
    @classmethod
    def validate_api_db_connection(cls, v: str) -> str:
        """Validate API database connection string format."""
        if not v:
            raise ValueError("DATABASE_URL_API is required")
        if not v.startswith("postgresql"):
            raise ValueError("DATABASE_URL_API must be a valid PostgreSQL connection string")
        return v

    @field_validator("DATABASE_URL_WORKER")
    @classmethod
    def validate_worker_db_connection(cls, v: str) -> str:
        """Validate Worker database connection string format."""
        if not v:
            raise ValueError("DATABASE_URL_WORKER is required")
        if not v.startswith("postgresql"):
            raise ValueError("DATABASE_URL_WORKER must be a valid PostgreSQL connection string")
        return v

    @field_validator("REDIS_URL")
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        """Validate Redis URL format."""
        if not v.startswith("redis://"):
            raise ValueError(f"Redis URL must start with 'redis://': {v}")
        return v

    @field_validator("RSSHUB_URL")
    @classmethod
    def validate_rsshub_url(cls, v: str) -> str:
        """Validate RSShub URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError(f"RSSHUB_URL must be a valid HTTP URL: {v}")
        return v

    @field_validator("SYNTHETIC_FEED_BASE_URL")
    @classmethod
    def validate_synthetic_feed_base_url(cls, v: str) -> str:
        """Validate the base URL synthetic feeds are served from."""
        if not v.startswith(("http://", "https://")):
            raise ValueError(f"SYNTHETIC_FEED_BASE_URL must be a valid HTTP URL: {v}")
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT == "development"

    @property
    def is_supabase_cloud(self) -> bool:
        """Detect if using Supabase Cloud by URL pattern."""
        return ".pooler.supabase.com" in self.DATABASE_URL_API or ".supabase.co" in self.DATABASE_URL_API


@cache
def get_settings() -> Settings:
    return Settings()
