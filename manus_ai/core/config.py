"""
Centralized Configuration Management
Handles all environment variables and application settings
"""

import os
from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings
from functools import lru_cache


class RedisConfig(BaseSettings):
    """Redis configuration"""
    url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    host: str = Field(default="localhost", env="REDIS_HOST")
    port: int = Field(default=6379, env="REDIS_PORT")
    db: int = Field(default=0, env="REDIS_DB")
    password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    max_connections: int = Field(default=50, env="REDIS_MAX_CONNECTIONS")

    class Config:
        env_file = ".env"
        case_sensitive = False


class CeleryConfig(BaseSettings):
    """Celery task queue configuration"""
    broker_url: str = Field(default="redis://localhost:6379/0", env="CELERY_BROKER_URL")
    result_backend: str = Field(default="redis://localhost:6379/1", env="CELERY_RESULT_BACKEND")
    worker_concurrency: int = Field(default=4, env="CELERY_WORKER_CONCURRENCY")
    worker_prefetch_multiplier: int = Field(default=1, env="CELERY_WORKER_PREFETCH_MULTIPLIER")
    max_tasks_per_child: int = Field(default=1000, env="CELERY_MAX_TASKS_PER_CHILD")
    task_time_limit: int = Field(default=3600, env="CELERY_TASK_TIME_LIMIT")  # 1 hour
    task_soft_time_limit: int = Field(default=3000, env="CELERY_TASK_SOFT_TIME_LIMIT")  # 50 min
    task_track_started: bool = Field(default=True, env="CELERY_TASK_TRACK_STARTED")
    result_expires: int = Field(default=86400, env="CELERY_RESULT_EXPIRES")  # 24 hours

    class Config:
        env_file = ".env"
        case_sensitive = False


class CacheConfig(BaseSettings):
    """Cache configuration"""
    default_ttl: int = Field(default=3600, env="CACHE_DEFAULT_TTL")  # 1 hour
    llm_response_ttl: int = Field(default=86400, env="CACHE_LLM_RESPONSE_TTL")  # 24 hours
    embedding_ttl: int = Field(default=604800, env="CACHE_EMBEDDING_TTL")  # 7 days
    api_response_ttl: int = Field(default=300, env="CACHE_API_RESPONSE_TTL")  # 5 minutes
    user_session_ttl: int = Field(default=3600, env="CACHE_USER_SESSION_TTL")  # 1 hour
    query_result_ttl: int = Field(default=60, env="CACHE_QUERY_RESULT_TTL")  # 1 minute
    max_size_mb: int = Field(default=1000, env="CACHE_MAX_SIZE_MB")
    strategy: str = Field(default="lru", env="CACHE_STRATEGY")  # lru, lfu, fifo, ttl

    class Config:
        env_file = ".env"
        case_sensitive = False


class DatabaseConfig(BaseSettings):
    """Database configuration"""
    mongodb_uri: str = Field(default="mongodb://localhost:27017", env="MONGODB_URI")
    mongodb_db_name: str = Field(default="manus_ai", env="MONGODB_DB_NAME")
    mongodb_max_pool_size: int = Field(default=100, env="MONGODB_MAX_POOL_SIZE")
    mongodb_min_pool_size: int = Field(default=10, env="MONGODB_MIN_POOL_SIZE")

    class Config:
        env_file = ".env"
        case_sensitive = False


class VectorDBConfig(BaseSettings):
    """Vector database configuration"""
    qdrant_host: str = Field(default="localhost", env="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, env="QDRANT_PORT")
    qdrant_grpc_port: int = Field(default=6334, env="QDRANT_GRPC_PORT")
    qdrant_api_key: Optional[str] = Field(default=None, env="QDRANT_API_KEY")
    embedding_model: str = Field(default="all-MiniLM-L6-v2", env="EMBEDDING_MODEL")
    embedding_dimension: int = Field(default=384, env="EMBEDDING_DIMENSION")

    class Config:
        env_file = ".env"
        case_sensitive = False


class LLMConfig(BaseSettings):
    """LLM provider configuration"""
    # OpenAI
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4-turbo-preview", env="OPENAI_MODEL")
    openai_max_tokens: int = Field(default=4000, env="OPENAI_MAX_TOKENS")

    # Anthropic
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-3-opus-20240229", env="ANTHROPIC_MODEL")
    anthropic_max_tokens: int = Field(default=4000, env="ANTHROPIC_MAX_TOKENS")

    # Google (Gemini)
    google_api_key: Optional[str] = Field(default=None, env="GOOGLE_API_KEY")
    gemini_model: str = Field(default="gemini-pro", env="GEMINI_MODEL")

    # Perplexity
    perplexity_api_key: Optional[str] = Field(default=None, env="PERPLEXITY_API_KEY")
    perplexity_model: str = Field(default="pplx-70b-online", env="PERPLEXITY_MODEL")

    # Default provider
    default_provider: str = Field(default="gemini", env="DEFAULT_LLM_PROVIDER")
    temperature: float = Field(default=0.7, env="LLM_TEMPERATURE")
    timeout_seconds: int = Field(default=120, env="LLM_TIMEOUT_SECONDS")

    class Config:
        env_file = ".env"
        case_sensitive = False


class ImageGenConfig(BaseSettings):
    """Image generation configuration"""
    dalle_enabled: bool = Field(default=False, env="DALLE_ENABLED")
    dalle_model: str = Field(default="dall-e-3", env="DALLE_MODEL")
    stable_diffusion_enabled: bool = Field(default=False, env="STABLE_DIFFUSION_ENABLED")

    class Config:
        env_file = ".env"
        case_sensitive = False


class AuthConfig(BaseSettings):
    """Authentication configuration"""
    jwt_secret_key: str = Field(default="your-secret-key-change-in-production", env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_minutes: int = Field(default=43200, env="JWT_EXPIRATION_MINUTES")  # 30 days
    api_key_expiration_days: int = Field(default=365, env="API_KEY_EXPIRATION_DAYS")
    password_min_length: int = Field(default=8, env="PASSWORD_MIN_LENGTH")
    bcrypt_rounds: int = Field(default=12, env="BCRYPT_ROUNDS")

    class Config:
        env_file = ".env"
        case_sensitive = False


class SecurityConfig(BaseSettings):
    """Security configuration"""
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: int = Field(default=60, env="RATE_LIMIT_WINDOW_SECONDS")
    cors_allowed_origins: List[str] = Field(default=["*"], env="CORS_ALLOWED_ORIGINS")
    max_upload_size_mb: int = Field(default=100, env="MAX_UPLOAD_SIZE_MB")
    allowed_file_extensions: List[str] = Field(
        default=[".pdf", ".docx", ".txt", ".csv", ".xlsx", ".png", ".jpg", ".jpeg"],
        env="ALLOWED_FILE_EXTENSIONS"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False


class MonitoringConfig(BaseSettings):
    """Monitoring and observability configuration"""
    prometheus_enabled: bool = Field(default=True, env="PROMETHEUS_ENABLED")
    prometheus_port: int = Field(default=9090, env="PROMETHEUS_PORT")
    flower_enabled: bool = Field(default=True, env="FLOWER_ENABLED")
    flower_port: int = Field(default=5555, env="FLOWER_PORT")
    flower_basic_auth: str = Field(default="admin:admin", env="FLOWER_BASIC_AUTH")
    grafana_enabled: bool = Field(default=True, env="GRAFANA_ENABLED")
    grafana_port: int = Field(default=3001, env="GRAFANA_PORT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    structured_logging: bool = Field(default=True, env="STRUCTURED_LOGGING")

    class Config:
        env_file = ".env"
        case_sensitive = False


class WebhookConfig(BaseSettings):
    """Webhook configuration"""
    max_retries: int = Field(default=3, env="WEBHOOK_MAX_RETRIES")
    retry_delay_seconds: int = Field(default=60, env="WEBHOOK_RETRY_DELAY_SECONDS")
    timeout_seconds: int = Field(default=30, env="WEBHOOK_TIMEOUT_SECONDS")
    max_webhooks_per_user: int = Field(default=100, env="WEBHOOK_MAX_PER_USER")
    signature_algorithm: str = Field(default="sha256", env="WEBHOOK_SIGNATURE_ALGORITHM")

    class Config:
        env_file = ".env"
        case_sensitive = False


class UsageConfig(BaseSettings):
    """Usage tracking and budget configuration"""
    tracking_enabled: bool = Field(default=True, env="USAGE_TRACKING_ENABLED")
    default_daily_budget_usd: float = Field(default=100.0, env="DEFAULT_DAILY_BUDGET_USD")
    default_monthly_budget_usd: float = Field(default=1000.0, env="DEFAULT_MONTHLY_BUDGET_USD")
    budget_warning_threshold: float = Field(default=0.8, env="BUDGET_WARNING_THRESHOLD")  # 80%
    cost_per_1k_tokens_gpt4: float = Field(default=0.03, env="COST_PER_1K_TOKENS_GPT4")
    cost_per_1k_tokens_gpt35: float = Field(default=0.002, env="COST_PER_1K_TOKENS_GPT35")
    cost_per_1k_tokens_claude: float = Field(default=0.024, env="COST_PER_1K_TOKENS_CLAUDE")
    cost_per_1k_tokens_gemini: float = Field(default=0.00025, env="COST_PER_1K_TOKENS_GEMINI")

    class Config:
        env_file = ".env"
        case_sensitive = False


class AppConfig(BaseSettings):
    """Main application configuration"""
    app_name: str = Field(default="Manus AI", env="APP_NAME")
    app_version: str = Field(default="2.0.0", env="APP_VERSION")
    environment: str = Field(default="development", env="ENVIRONMENT")  # development, staging, production
    debug: bool = Field(default=False, env="DEBUG")
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    workers: int = Field(default=4, env="WORKERS")
    reload: bool = Field(default=False, env="RELOAD")

    class Config:
        env_file = ".env"
        case_sensitive = False


class Config:
    """
    Master configuration class
    Provides access to all configuration sections
    """

    def __init__(self):
        self.app = AppConfig()
        self.redis = RedisConfig()
        self.celery = CeleryConfig()
        self.cache = CacheConfig()
        self.database = DatabaseConfig()
        self.vector_db = VectorDBConfig()
        self.llm = LLMConfig()
        self.image_gen = ImageGenConfig()
        self.auth = AuthConfig()
        self.security = SecurityConfig()
        self.monitoring = MonitoringConfig()
        self.webhook = WebhookConfig()
        self.usage = UsageConfig()

    def is_production(self) -> bool:
        """Check if running in production"""
        return self.app.environment.lower() == "production"

    def is_development(self) -> bool:
        """Check if running in development"""
        return self.app.environment.lower() == "development"

    def validate(self) -> List[str]:
        """
        Validate configuration and return list of warnings
        """
        warnings = []

        # Production checks
        if self.is_production():
            if self.app.debug:
                warnings.append("DEBUG mode enabled in production")

            if self.auth.jwt_secret_key == "your-secret-key-change-in-production":
                warnings.append("JWT secret key not changed from default")

            if "*" in self.security.cors_allowed_origins:
                warnings.append("CORS allows all origins in production")

            if self.monitoring.flower_basic_auth == "admin:admin":
                warnings.append("Flower using default credentials")

        # API key checks
        if not self.llm.openai_api_key and not self.llm.anthropic_api_key and not self.llm.google_api_key:
            warnings.append("No LLM API keys configured")

        # Cache checks
        if self.cache.max_size_mb < 100:
            warnings.append(f"Cache size very low: {self.cache.max_size_mb}MB")

        # Celery checks
        if self.celery.worker_concurrency < 2:
            warnings.append(f"Low worker concurrency: {self.celery.worker_concurrency}")

        return warnings

    def to_dict(self) -> dict:
        """Convert configuration to dictionary (for logging/debugging)"""
        return {
            "app": self.app.model_dump(),
            "redis": {**self.redis.model_dump(), "password": "***" if self.redis.password else None},
            "celery": self.celery.model_dump(),
            "cache": self.cache.model_dump(),
            "database": {**self.database.model_dump(), "mongodb_uri": "***"},
            "vector_db": self.vector_db.model_dump(),
            "llm": {
                **self.llm.model_dump(),
                "openai_api_key": "***" if self.llm.openai_api_key else None,
                "anthropic_api_key": "***" if self.llm.anthropic_api_key else None,
                "google_api_key": "***" if self.llm.google_api_key else None,
                "perplexity_api_key": "***" if self.llm.perplexity_api_key else None,
            },
            "auth": {**self.auth.model_dump(), "jwt_secret_key": "***"},
            "security": self.security.model_dump(),
            "monitoring": {
                **self.monitoring.model_dump(),
                "flower_basic_auth": "***" if self.monitoring.flower_basic_auth else None
            },
            "webhook": self.webhook.model_dump(),
            "usage": self.usage.model_dump(),
        }


@lru_cache()
def get_config() -> Config:
    """
    Get cached configuration instance
    Uses LRU cache to ensure single instance
    """
    return Config()


# Convenience function for quick access
def get_settings() -> Config:
    """Alias for get_config()"""
    return get_config()


if __name__ == "__main__":
    # Test configuration loading
    config = get_config()

    print("="*70)
    print("Manus AI Configuration")
    print("="*70)
    print(f"Environment: {config.app.environment}")
    print(f"Version: {config.app.version}")
    print(f"Debug: {config.app.debug}")
    print()

    # Validate
    warnings = config.validate()
    if warnings:
        print("⚠️  Configuration Warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("✓ Configuration validated successfully")

    print()
    print("Component Status:")
    print(f"  Redis: {config.redis.host}:{config.redis.port}")
    print(f"  Celery: {config.celery.worker_concurrency} workers")
    print(f"  Cache: {config.cache.max_size_mb}MB max, {config.cache.strategy} strategy")
    print(f"  MongoDB: {config.database.mongodb_db_name}")
    print(f"  Default LLM: {config.llm.default_provider}")
    print("="*70)
