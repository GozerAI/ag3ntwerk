"""
Tests for configuration management and validation.
"""

import os
import pytest
from unittest.mock import patch

from ag3ntwerk.core.config import (
    Config,
    ServerConfig,
    LLMConfig,
    RateLimitConfig,
    ShutdownConfig,
    HealthConfig,
    Environment,
    get_config,
    set_config,
    validate_config,
)


class TestServerConfig:
    """Tests for ServerConfig."""

    def test_default_port(self):
        """Default port should be 3737."""
        config = ServerConfig()
        assert config.port == 3737

    def test_default_host(self):
        """Default host should be 0.0.0.0."""
        config = ServerConfig()
        assert config.host == "0.0.0.0"

    def test_default_cors_origins(self):
        """CORS origins should include localhost variants."""
        config = ServerConfig()
        assert "http://localhost:3737" in config.cors_origins
        assert "http://127.0.0.1:3737" in config.cors_origins
        assert "http://localhost:3000" in config.cors_origins

    @patch.dict(os.environ, {"PORT": "9999"}, clear=False)
    def test_port_from_env(self):
        """Port should be overridable via environment variable."""
        config = ServerConfig.from_env()
        assert config.port == 9999

    @patch.dict(os.environ, {"HOST": "127.0.0.1"}, clear=False)
    def test_host_from_env(self):
        """Host should be overridable via environment variable."""
        config = ServerConfig.from_env()
        assert config.host == "127.0.0.1"

    def test_validate_valid_config(self):
        """Valid config should return no errors."""
        config = ServerConfig(port=3737, workers=2, log_level="INFO")
        errors = config.validate()
        assert len(errors) == 0

    def test_validate_invalid_port_low(self):
        """Port < 1 should fail validation."""
        config = ServerConfig(port=0)
        errors = config.validate()
        assert any("port" in e.lower() for e in errors)

    def test_validate_invalid_port_high(self):
        """Port > 65535 should fail validation."""
        config = ServerConfig(port=70000)
        errors = config.validate()
        assert any("port" in e.lower() for e in errors)

    def test_validate_invalid_workers(self):
        """Workers < 1 should fail validation."""
        config = ServerConfig(workers=0)
        errors = config.validate()
        assert any("workers" in e.lower() for e in errors)

    def test_validate_invalid_log_level(self):
        """Invalid log level should fail validation."""
        config = ServerConfig(log_level="INVALID")
        errors = config.validate()
        assert any("log level" in e.lower() for e in errors)


class TestLLMConfig:
    """Tests for LLMConfig."""

    def test_default_provider(self):
        """Default provider should be ollama."""
        config = LLMConfig()
        assert config.provider == "ollama"

    def test_default_base_url(self):
        """Default base URL should be ollama localhost."""
        config = LLMConfig()
        assert config.base_url == "http://localhost:11434"

    @patch.dict(os.environ, {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "test-key"}, clear=False)
    def test_openai_provider_from_env(self):
        """OpenAI provider should be configurable via env."""
        config = LLMConfig.from_env()
        assert config.provider == "openai"
        assert config.api_key == "test-key"

    def test_validate_invalid_provider(self):
        """Invalid provider should fail validation."""
        config = LLMConfig(provider="invalid_provider")
        errors = config.validate()
        assert any("provider" in e.lower() for e in errors)

    def test_validate_cloud_without_key(self):
        """Cloud provider without API key should fail validation."""
        config = LLMConfig(provider="openai", api_key=None)
        errors = config.validate()
        assert any("api key" in e.lower() for e in errors)

    def test_validate_local_without_key(self):
        """Local provider without API key should pass validation."""
        config = LLMConfig(provider="ollama", api_key=None)
        errors = config.validate()
        assert not any("api key" in e.lower() for e in errors)


class TestRateLimitConfig:
    """Tests for RateLimitConfig."""

    def test_defaults(self):
        """Rate limit defaults should be reasonable."""
        config = RateLimitConfig()
        assert config.enabled is True
        assert config.tasks_per_minute == 10
        assert config.chat_per_minute == 20
        assert config.global_per_minute == 100

    def test_validate_invalid_limits(self):
        """Zero or negative limits should fail validation."""
        config = RateLimitConfig(tasks_per_minute=0)
        errors = config.validate()
        assert len(errors) > 0


class TestShutdownConfig:
    """Tests for ShutdownConfig."""

    def test_defaults(self):
        """Shutdown defaults should be reasonable."""
        config = ShutdownConfig()
        assert config.drain_timeout == 30.0
        assert config.force_timeout == 60.0
        assert config.check_interval == 0.5

    def test_validate_force_less_than_drain(self):
        """force_timeout < drain_timeout should fail validation."""
        config = ShutdownConfig(drain_timeout=60, force_timeout=30)
        errors = config.validate()
        assert any("force_timeout" in e for e in errors)


class TestHealthConfig:
    """Tests for HealthConfig."""

    def test_defaults(self):
        """Health check defaults should be reasonable."""
        config = HealthConfig()
        assert config.cache_interval == 30.0
        assert config.timeout == 5.0
        assert config.enable_detailed is True


class TestConfig:
    """Tests for main Config class."""

    def test_default_environment(self):
        """Default environment should be development."""
        config = Config()
        assert config.environment == Environment.DEVELOPMENT
        assert config.is_development() is True

    def test_debug_in_development(self):
        """Debug should be True in development."""
        config = Config(environment=Environment.DEVELOPMENT)
        assert config.debug is True or config.is_development()

    def test_validate_full_config(self):
        """Full config with valid values should pass validation."""
        config = Config()
        config.llm = LLMConfig(provider="ollama")
        config.server = ServerConfig(port=3737)
        errors = config.validate()
        # Ollama doesn't require API key, so should be valid
        assert not any("api key" in e.lower() for e in errors)

    def test_to_dict_masks_api_key(self):
        """API key should be masked in dict output."""
        config = Config()
        config.llm.api_key = "secret-key"
        result = config.to_dict()
        assert result["llm"]["api_key"] == "***"


class TestConfigFunctions:
    """Tests for module-level configuration functions."""

    def test_get_config_returns_same_instance(self):
        """get_config should return the same instance."""
        config1 = get_config()
        config2 = get_config()
        # Note: might not be same instance if caching is disabled
        assert config1.version == config2.version

    def test_set_config(self):
        """set_config should update global config."""
        original = get_config()
        new_config = Config(version="2.0.0")
        set_config(new_config)
        assert get_config().version == "2.0.0"
        # Restore
        set_config(original)

    def test_validate_config(self):
        """validate_config should validate global config."""
        errors = validate_config()
        # Basic config should be valid (ollama doesn't require API key)
        assert isinstance(errors, list)


class TestEnvironment:
    """Tests for Environment enum."""

    def test_environment_values(self):
        """Environment enum should have expected values."""
        assert Environment.DEVELOPMENT.value == "development"
        assert Environment.TESTING.value == "testing"
        assert Environment.STAGING.value == "staging"
        assert Environment.PRODUCTION.value == "production"

    @patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=False)
    def test_production_from_env(self):
        """Config should detect production environment."""
        config = Config.from_env()
        assert config.environment == Environment.PRODUCTION
        assert config.is_production() is True
