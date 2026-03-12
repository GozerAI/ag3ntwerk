"""
Configuration Management and Validation for ag3ntwerk.

Provides:
- Centralized configuration management
- Type-safe configuration with validation
- Environment variable loading
- Default values and constraints
- Startup validation

Usage:
    from ag3ntwerk.core.config import Config, get_config, validate_config

    # Get configuration
    config = get_config()
    print(config.llm.provider)  # "ollama"

    # Validate at startup
    errors = validate_config()
    if errors:
        raise ConfigurationError(f"Invalid configuration: {errors}")
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from ag3ntwerk.core.logging import get_logger

logger = get_logger(__name__)


class Environment(Enum):
    """Application environment."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class LLMConfig:
    """LLM provider configuration."""

    provider: str = "ollama"
    base_url: str = "http://localhost:11434"
    api_key: Optional[str] = None
    default_model: Optional[str] = None
    timeout: float = 300.0
    max_retries: int = 3
    retry_delay: float = 1.0

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Create configuration from environment variables."""
        provider = os.getenv("LLM_PROVIDER", "ollama").lower()

        # Provider-specific defaults
        base_urls = {
            "ollama": "http://localhost:11434",
            "gpt4all": "http://localhost:4891/v1",
            "openai": "https://api.openai.com/v1",
            "anthropic": "https://api.anthropic.com",
            "google": "https://generativelanguage.googleapis.com/v1beta",
            "openrouter": "https://openrouter.ai/api/v1",
            "huggingface": "https://api-inference.huggingface.co",
            "github": "https://models.inference.ai.azure.com",
            "perplexity": "https://api.perplexity.ai",
        }

        api_key_vars = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            "huggingface": "HUGGINGFACE_API_KEY",
            "github": "GITHUB_TOKEN",
            "perplexity": "PERPLEXITY_API_KEY",
        }

        # For Ollama, also check OLLAMA_HOST env var
        if provider == "ollama":
            base_url = os.getenv(
                "LLM_BASE_URL", os.getenv("OLLAMA_HOST", base_urls.get(provider, ""))
            )
        else:
            base_url = os.getenv("LLM_BASE_URL", base_urls.get(provider, ""))

        api_key = None
        if provider in api_key_vars:
            api_key = os.getenv(api_key_vars[provider])

        # For Ollama, also check OLLAMA_MODEL
        default_model = os.getenv("LLM_DEFAULT_MODEL") or os.getenv("OLLAMA_MODEL")

        return cls(
            provider=provider,
            base_url=base_url,
            api_key=api_key,
            default_model=default_model,
            timeout=float(os.getenv("LLM_TIMEOUT", "300")),
            max_retries=int(os.getenv("LLM_MAX_RETRIES", "3")),
            retry_delay=float(os.getenv("LLM_RETRY_DELAY", "1.0")),
        )

    def validate(self) -> List[str]:
        """Validate configuration."""
        errors = []

        valid_providers = {
            "ollama",
            "gpt4all",
            "openai",
            "anthropic",
            "google",
            "gemini",
            "openrouter",
            "huggingface",
            "hf",
            "github",
            "perplexity",
        }
        if self.provider not in valid_providers:
            errors.append(f"Invalid LLM provider: {self.provider}")

        if not self.base_url:
            errors.append("LLM base URL is required")

        # Cloud providers require API key
        cloud_providers = {
            "openai",
            "anthropic",
            "google",
            "openrouter",
            "huggingface",
            "github",
            "perplexity",
        }
        if self.provider in cloud_providers and not self.api_key:
            errors.append(f"{self.provider} requires an API key")

        if self.timeout <= 0:
            errors.append("LLM timeout must be positive")

        if self.max_retries < 0:
            errors.append("LLM max_retries cannot be negative")

        return errors


@dataclass
class ServerConfig:
    """Server configuration."""

    host: str = "0.0.0.0"
    port: int = 3737
    workers: int = 1
    reload: bool = False
    log_level: str = "INFO"
    log_format: str = "console"
    cors_origins: List[str] = field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:3737",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3737",
            "http://127.0.0.1:5173",
        ]
    )

    @classmethod
    def from_env(cls) -> "ServerConfig":
        """Create configuration from environment variables."""
        cors_origins = os.getenv("CORS_ORIGINS", "")
        if cors_origins:
            origins = [o.strip() for o in cors_origins.split(",")]
        else:
            origins = [
                "http://localhost:3000",
                "http://localhost:3737",
                "http://localhost:5173",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:3737",
                "http://127.0.0.1:5173",
            ]

        return cls(
            host=os.getenv("AGENTWERK_HOST", os.getenv("HOST", "0.0.0.0")),
            port=int(os.getenv("AGENTWERK_PORT", os.getenv("PORT", "3737"))),
            workers=int(os.getenv("WORKERS", "1")),
            reload=os.getenv("RELOAD", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            log_format=os.getenv("LOG_FORMAT", "console").lower(),
            cors_origins=origins,
        )

    def validate(self) -> List[str]:
        """Validate configuration."""
        errors = []

        if self.port < 1 or self.port > 65535:
            errors.append(f"Invalid port: {self.port}")

        if self.workers < 1:
            errors.append(f"Workers must be at least 1: {self.workers}")

        valid_log_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.log_level not in valid_log_levels:
            errors.append(f"Invalid log level: {self.log_level}")

        valid_log_formats = {"console", "json"}
        if self.log_format not in valid_log_formats:
            errors.append(f"Invalid log format: {self.log_format}")

        return errors


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""

    enabled: bool = True
    tasks_per_minute: int = 10
    chat_per_minute: int = 20
    workflows_per_minute: int = 5
    global_per_minute: int = 100

    @classmethod
    def from_env(cls) -> "RateLimitConfig":
        """Create configuration from environment variables."""
        return cls(
            enabled=os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true",
            tasks_per_minute=int(os.getenv("RATE_LIMIT_TASKS", "10")),
            chat_per_minute=int(os.getenv("RATE_LIMIT_CHAT", "20")),
            workflows_per_minute=int(os.getenv("RATE_LIMIT_WORKFLOWS", "5")),
            global_per_minute=int(os.getenv("RATE_LIMIT_GLOBAL", "100")),
        )

    def validate(self) -> List[str]:
        """Validate configuration."""
        errors = []

        if self.tasks_per_minute < 1:
            errors.append("tasks_per_minute must be at least 1")
        if self.chat_per_minute < 1:
            errors.append("chat_per_minute must be at least 1")
        if self.workflows_per_minute < 1:
            errors.append("workflows_per_minute must be at least 1")
        if self.global_per_minute < 1:
            errors.append("global_per_minute must be at least 1")

        return errors


@dataclass
class ShutdownConfig:
    """Graceful shutdown configuration."""

    drain_timeout: float = 30.0
    force_timeout: float = 60.0
    check_interval: float = 0.5

    @classmethod
    def from_env(cls) -> "ShutdownConfig":
        """Create configuration from environment variables."""
        return cls(
            drain_timeout=float(os.getenv("SHUTDOWN_DRAIN_TIMEOUT", "30")),
            force_timeout=float(os.getenv("SHUTDOWN_FORCE_TIMEOUT", "60")),
            check_interval=float(os.getenv("SHUTDOWN_CHECK_INTERVAL", "0.5")),
        )

    def validate(self) -> List[str]:
        """Validate configuration."""
        errors = []

        if self.drain_timeout <= 0:
            errors.append("drain_timeout must be positive")
        if self.force_timeout <= 0:
            errors.append("force_timeout must be positive")
        if self.force_timeout < self.drain_timeout:
            errors.append("force_timeout must be >= drain_timeout")
        if self.check_interval <= 0:
            errors.append("check_interval must be positive")

        return errors


@dataclass
class HealthConfig:
    """Health check configuration."""

    cache_interval: float = 30.0
    timeout: float = 5.0
    enable_detailed: bool = True

    @classmethod
    def from_env(cls) -> "HealthConfig":
        """Create configuration from environment variables."""
        return cls(
            cache_interval=float(os.getenv("HEALTH_CACHE_INTERVAL", "30")),
            timeout=float(os.getenv("HEALTH_TIMEOUT", "5")),
            enable_detailed=os.getenv("HEALTH_DETAILED", "true").lower() == "true",
        )

    def validate(self) -> List[str]:
        """Validate configuration."""
        errors = []

        if self.cache_interval < 0:
            errors.append("cache_interval cannot be negative")
        if self.timeout <= 0:
            errors.append("timeout must be positive")

        return errors


@dataclass
class IntegrationsConfig:
    """Revenue Stack integration credentials configuration."""

    # Social — LinkedIn
    linkedin_access_token: Optional[str] = None
    linkedin_person_urn: Optional[str] = None

    # Social — Twitter / X
    twitter_bearer_token: Optional[str] = None
    twitter_api_key: Optional[str] = None
    twitter_api_secret: Optional[str] = None
    twitter_access_token: Optional[str] = None
    twitter_access_secret: Optional[str] = None

    # Payments — Gumroad
    gumroad_access_token: Optional[str] = None

    # Voice — Whisper backend preference
    whisper_backend: str = "auto"

    @classmethod
    def from_env(cls) -> "IntegrationsConfig":
        """Create configuration from environment variables."""
        return cls(
            linkedin_access_token=os.getenv("LINKEDIN_ACCESS_TOKEN"),
            linkedin_person_urn=os.getenv("LINKEDIN_PERSON_URN"),
            twitter_bearer_token=os.getenv("TWITTER_BEARER_TOKEN"),
            twitter_api_key=os.getenv("TWITTER_API_KEY"),
            twitter_api_secret=os.getenv("TWITTER_API_SECRET"),
            twitter_access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
            twitter_access_secret=os.getenv("TWITTER_ACCESS_SECRET"),
            gumroad_access_token=os.getenv("GUMROAD_ACCESS_TOKEN"),
            whisper_backend=os.getenv("WHISPER_BACKEND", "auto"),
        )

    def validate(self) -> List[str]:
        """Validate configuration (warnings only — integrations are optional)."""
        errors = []
        valid_backends = {"auto", "openai-whisper", "faster-whisper", "buzz"}
        if self.whisper_backend not in valid_backends:
            errors.append(
                f"Invalid WHISPER_BACKEND: {self.whisper_backend} "
                f"(expected one of {valid_backends})"
            )
        return errors

    @property
    def linkedin_configured(self) -> bool:
        """Check if LinkedIn credentials are present."""
        return bool(self.linkedin_access_token and self.linkedin_person_urn)

    @property
    def twitter_configured(self) -> bool:
        """Check if Twitter credentials are present."""
        return bool(self.twitter_bearer_token)

    @property
    def gumroad_configured(self) -> bool:
        """Check if Gumroad credentials are present."""
        return bool(self.gumroad_access_token)

    def summary(self) -> Dict[str, bool]:
        """Return which integrations are configured."""
        return {
            "linkedin": self.linkedin_configured,
            "twitter": self.twitter_configured,
            "gumroad": self.gumroad_configured,
            "whisper": self.whisper_backend != "",
        }


@dataclass
class Config:
    """Main application configuration."""

    environment: Environment = Environment.DEVELOPMENT
    app_name: str = "ag3ntwerk Command Center"
    version: str = "1.0.0"
    debug: bool = False

    llm: LLMConfig = field(default_factory=LLMConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    shutdown: ShutdownConfig = field(default_factory=ShutdownConfig)
    health: HealthConfig = field(default_factory=HealthConfig)
    integrations: IntegrationsConfig = field(default_factory=IntegrationsConfig)

    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables."""
        env_str = os.getenv("AGENTWERK_ENV", os.getenv("ENVIRONMENT", "development")).lower()
        try:
            environment = Environment(env_str)
        except ValueError:
            environment = Environment.DEVELOPMENT

        debug = os.getenv("DEBUG", "false").lower() == "true"
        if environment == Environment.DEVELOPMENT:
            debug = True

        return cls(
            environment=environment,
            app_name=os.getenv("APP_NAME", "ag3ntwerk Command Center"),
            version=os.getenv("APP_VERSION", "1.0.0"),
            debug=debug,
            llm=LLMConfig.from_env(),
            server=ServerConfig.from_env(),
            rate_limit=RateLimitConfig.from_env(),
            shutdown=ShutdownConfig.from_env(),
            health=HealthConfig.from_env(),
            integrations=IntegrationsConfig.from_env(),
        )

    def validate(self) -> List[str]:
        """Validate all configuration."""
        errors = []

        errors.extend(self.llm.validate())
        errors.extend(self.server.validate())
        errors.extend(self.rate_limit.validate())
        errors.extend(self.shutdown.validate())
        errors.extend(self.health.validate())
        errors.extend(self.integrations.validate())

        return errors

    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == Environment.PRODUCTION

    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == Environment.DEVELOPMENT

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (masks sensitive values)."""
        return {
            "environment": self.environment.value,
            "app_name": self.app_name,
            "version": self.version,
            "debug": self.debug,
            "llm": {
                "provider": self.llm.provider,
                "base_url": self.llm.base_url,
                "api_key": "***" if self.llm.api_key else None,
                "default_model": self.llm.default_model,
                "timeout": self.llm.timeout,
            },
            "server": {
                "host": self.server.host,
                "port": self.server.port,
                "workers": self.server.workers,
                "log_level": self.server.log_level,
            },
            "rate_limit": {
                "enabled": self.rate_limit.enabled,
                "tasks_per_minute": self.rate_limit.tasks_per_minute,
                "chat_per_minute": self.rate_limit.chat_per_minute,
            },
            "integrations": self.integrations.summary(),
        }


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def set_config(config: Config) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config


def validate_config() -> List[str]:
    """
    Validate the current configuration.

    Returns:
        List of validation error messages (empty if valid)
    """
    config = get_config()
    return config.validate()


def validate_config_or_raise(strict: bool = True) -> None:
    """
    Validate configuration and raise exception if invalid.

    In production mode with strict=True, also validates:
    - Required secrets are present
    - Database is accessible
    - External services are reachable

    Args:
        strict: If True, enforce strict production requirements

    Raises:
        ConfigurationError: If configuration is invalid
    """
    from ag3ntwerk.core.exceptions import ConfigurationError

    config = get_config()
    errors = config.validate()

    # Production-specific validations
    if config.is_production() and strict:
        prod_errors = _validate_production_requirements(config)
        errors.extend(prod_errors)

    if errors:
        error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        logger.error(error_msg)
        raise ConfigurationError(error_msg)

    logger.info("Configuration validated successfully")


def _validate_production_requirements(config: Config) -> List[str]:
    """
    Validate production-specific requirements.

    These checks only run in production to ensure the application
    is properly configured before accepting traffic.
    """
    errors = []

    # Check for required environment variables in production
    required_env_vars = [
        ("DATABASE_BACKEND", "Database backend must be configured"),
    ]

    # If using PostgreSQL, require connection details
    if os.getenv("DATABASE_BACKEND", "").lower() == "postgresql":
        required_env_vars.extend(
            [
                ("PG_HOST", "PostgreSQL host is required"),
                ("PG_PASSWORD", "PostgreSQL password is required"),
            ]
        )

    # Check for secrets encryption key if using file backend
    if os.getenv("SECRET_BACKEND", "").lower() == "file":
        required_env_vars.append(
            ("AGENTWERK_SECRETS_KEY", "Secrets encryption key is required for file backend")
        )

    for env_var, message in required_env_vars:
        if not os.getenv(env_var):
            errors.append(f"[PRODUCTION] {message} ({env_var} not set)")

    # Warn about debug mode in production
    if config.debug:
        errors.append("[PRODUCTION] Debug mode should be disabled in production")

    # Warn about default CORS origins in production
    default_origins = {"http://localhost:3000", "http://localhost:3737", "http://127.0.0.1:3000"}
    if any(origin in config.server.cors_origins for origin in default_origins):
        logger.warning(
            "Production environment has localhost CORS origins configured. "
            "Consider restricting to production domains only."
        )

    # Log integration credential status (warnings, not errors — integrations are optional)
    integ = config.integrations
    if not integ.linkedin_configured:
        logger.warning(
            "[PRODUCTION] LinkedIn credentials not configured — social distribution to LinkedIn disabled"
        )
    if not integ.twitter_configured:
        logger.warning(
            "[PRODUCTION] Twitter credentials not configured — social distribution to Twitter disabled"
        )
    if not integ.gumroad_configured:
        logger.warning(
            "[PRODUCTION] Gumroad credentials not configured — revenue tracking disabled"
        )

    return errors


def validate_startup(fail_fast: bool = True) -> bool:
    """
    Complete startup validation for production deployments.

    This function should be called at application startup to ensure
    all required services and configurations are available.

    Args:
        fail_fast: If True (default), raise exception on first error.
                   If False, log all errors and return False.

    Returns:
        True if all validations pass, False otherwise

    Raises:
        ConfigurationError: If fail_fast=True and validation fails
    """
    from ag3ntwerk.core.exceptions import ConfigurationError

    config = get_config()
    all_errors = []

    # Step 1: Validate configuration
    logger.info("Validating configuration...")
    try:
        validate_config_or_raise(strict=config.is_production())
    except ConfigurationError as e:
        if fail_fast:
            raise
        all_errors.append(str(e))

    # Step 2: Check database connectivity (if configured)
    if os.getenv("DATABASE_BACKEND"):
        logger.info("Checking database connectivity...")
        db_error = _check_database_connectivity()
        if db_error:
            if fail_fast and config.is_production():
                raise ConfigurationError(f"Database check failed: {db_error}")
            all_errors.append(f"Database: {db_error}")

    # Step 3: Check LLM provider connectivity (non-blocking)
    logger.info("Checking LLM provider connectivity...")
    llm_error = _check_llm_connectivity(config)
    if llm_error:
        # LLM errors are warnings, not fatal
        logger.warning(f"LLM provider check: {llm_error}")

    if all_errors:
        logger.error(f"Startup validation failed with {len(all_errors)} error(s)")
        for error in all_errors:
            logger.error(f"  - {error}")
        return False

    logger.info("Startup validation completed successfully")
    return True


def _check_database_connectivity() -> Optional[str]:
    """Check if database is accessible."""
    try:
        from ag3ntwerk.persistence.database import DatabaseConfig

        db_config = DatabaseConfig.from_env()

        if db_config.backend.value == "sqlite":
            # SQLite just needs directory to exist
            from pathlib import Path

            db_path = Path(db_config.sqlite_path).expanduser().resolve()
            if not db_path.parent.exists():
                return f"SQLite directory does not exist: {db_path.parent}"
            return None

        elif db_config.backend.value == "postgresql":
            # Test PostgreSQL connection
            import socket

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            try:
                result = sock.connect_ex((db_config.pg_host, db_config.pg_port))
                if result != 0:
                    return (
                        f"Cannot connect to PostgreSQL at {db_config.pg_host}:{db_config.pg_port}"
                    )
            finally:
                sock.close()
            return None

    except (OSError, ImportError) as e:
        return f"Database check error: {e}"

    return None


def _check_llm_connectivity(config: Config) -> Optional[str]:
    """Check if LLM provider is accessible (non-blocking check)."""
    try:
        import socket
        from urllib.parse import urlparse

        parsed = urlparse(config.llm.base_url)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "https" else 80)

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        try:
            result = sock.connect_ex((host, port))
            if result != 0:
                return f"Cannot reach LLM provider at {host}:{port}"
        finally:
            sock.close()

    except (OSError, ImportError, ValueError) as e:
        return f"LLM connectivity check error: {e}"

    return None


def log_config_summary() -> None:
    """Log a summary of the current configuration."""
    config = get_config()

    logger.info(
        "Configuration loaded",
        environment=config.environment.value,
        llm_provider=config.llm.provider,
        server_port=config.server.port,
        log_level=config.server.log_level,
        debug=config.debug,
    )

    # Log integration status
    integ_summary = config.integrations.summary()
    active = [k for k, v in integ_summary.items() if v]
    inactive = [k for k, v in integ_summary.items() if not v]
    if active:
        logger.info(f"Integrations active: {', '.join(active)}")
    if inactive:
        logger.info(f"Integrations not configured: {', '.join(inactive)}")


__all__ = [
    # Enums
    "Environment",
    # Config classes
    "Config",
    "LLMConfig",
    "ServerConfig",
    "RateLimitConfig",
    "ShutdownConfig",
    "HealthConfig",
    "IntegrationsConfig",
    # Functions
    "get_config",
    "set_config",
    "validate_config",
    "validate_config_or_raise",
    "validate_startup",
    "log_config_summary",
]
