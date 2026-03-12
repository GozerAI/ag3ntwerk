"""
Tests for production deployment hardening.

Phase 7: IntegrationsConfig, environment validation, and health checks.
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from ag3ntwerk.core.config import (
    IntegrationsConfig,
    Config,
    Environment,
    get_config,
    set_config,
    validate_config,
)


# =============================================================================
# IntegrationsConfig Tests
# =============================================================================


class TestIntegrationsConfig:
    """Tests for IntegrationsConfig dataclass."""

    def test_defaults(self):
        """Test default values — all credentials None, whisper auto."""
        cfg = IntegrationsConfig()
        assert cfg.linkedin_access_token is None
        assert cfg.linkedin_person_urn is None
        assert cfg.twitter_bearer_token is None
        assert cfg.twitter_api_key is None
        assert cfg.twitter_api_secret is None
        assert cfg.twitter_access_token is None
        assert cfg.twitter_access_secret is None
        assert cfg.gumroad_access_token is None
        assert cfg.whisper_backend == "auto"

    def test_linkedin_configured_both_required(self):
        """LinkedIn needs both token and person URN."""
        cfg = IntegrationsConfig(
            linkedin_access_token="tok", linkedin_person_urn="urn:li:person:123"
        )
        assert cfg.linkedin_configured is True

    def test_linkedin_not_configured_missing_urn(self):
        """LinkedIn not configured if person URN is missing."""
        cfg = IntegrationsConfig(linkedin_access_token="tok")
        assert cfg.linkedin_configured is False

    def test_linkedin_not_configured_missing_token(self):
        """LinkedIn not configured if token is missing."""
        cfg = IntegrationsConfig(linkedin_person_urn="urn:li:person:123")
        assert cfg.linkedin_configured is False

    def test_twitter_configured(self):
        """Twitter is configured with bearer token."""
        cfg = IntegrationsConfig(twitter_bearer_token="bearer123")
        assert cfg.twitter_configured is True

    def test_twitter_not_configured(self):
        """Twitter not configured without bearer token."""
        cfg = IntegrationsConfig()
        assert cfg.twitter_configured is False

    def test_gumroad_configured(self):
        """Gumroad configured with access token."""
        cfg = IntegrationsConfig(gumroad_access_token="gum123")
        assert cfg.gumroad_configured is True

    def test_gumroad_not_configured(self):
        """Gumroad not configured without token."""
        cfg = IntegrationsConfig()
        assert cfg.gumroad_configured is False

    def test_summary_all_configured(self):
        """Summary shows all integrations when fully configured."""
        cfg = IntegrationsConfig(
            linkedin_access_token="tok",
            linkedin_person_urn="urn",
            twitter_bearer_token="bearer",
            gumroad_access_token="gum",
            whisper_backend="auto",
        )
        summary = cfg.summary()
        assert summary["linkedin"] is True
        assert summary["twitter"] is True
        assert summary["gumroad"] is True
        assert summary["whisper"] is True

    def test_summary_none_configured(self):
        """Summary shows no integrations when none configured."""
        cfg = IntegrationsConfig()
        summary = cfg.summary()
        assert summary["linkedin"] is False
        assert summary["twitter"] is False
        assert summary["gumroad"] is False
        assert summary["whisper"] is True  # whisper defaults to "auto"

    def test_validate_valid_backend(self):
        """Valid whisper backends pass validation."""
        for backend in ("auto", "openai-whisper", "faster-whisper", "buzz"):
            cfg = IntegrationsConfig(whisper_backend=backend)
            assert cfg.validate() == []

    def test_validate_invalid_backend(self):
        """Invalid whisper backend fails validation."""
        cfg = IntegrationsConfig(whisper_backend="invalid-backend")
        errors = cfg.validate()
        assert len(errors) == 1
        assert "WHISPER_BACKEND" in errors[0]

    def test_from_env_all_set(self):
        """from_env reads all environment variables."""
        env = {
            "LINKEDIN_ACCESS_TOKEN": "li_tok",
            "LINKEDIN_PERSON_URN": "urn:li:person:abc",
            "TWITTER_BEARER_TOKEN": "tw_bearer",
            "TWITTER_API_KEY": "tw_key",
            "TWITTER_API_SECRET": "tw_secret",
            "TWITTER_ACCESS_TOKEN": "tw_tok",
            "TWITTER_ACCESS_SECRET": "tw_sec",
            "GUMROAD_ACCESS_TOKEN": "gum_tok",
            "WHISPER_BACKEND": "faster-whisper",
        }
        with patch.dict(os.environ, env, clear=False):
            cfg = IntegrationsConfig.from_env()
            assert cfg.linkedin_access_token == "li_tok"
            assert cfg.linkedin_person_urn == "urn:li:person:abc"
            assert cfg.twitter_bearer_token == "tw_bearer"
            assert cfg.twitter_api_key == "tw_key"
            assert cfg.twitter_api_secret == "tw_secret"
            assert cfg.twitter_access_token == "tw_tok"
            assert cfg.twitter_access_secret == "tw_sec"
            assert cfg.gumroad_access_token == "gum_tok"
            assert cfg.whisper_backend == "faster-whisper"

    def test_from_env_defaults(self):
        """from_env uses defaults when env vars not set."""
        env_keys = [
            "LINKEDIN_ACCESS_TOKEN",
            "LINKEDIN_PERSON_URN",
            "TWITTER_BEARER_TOKEN",
            "TWITTER_API_KEY",
            "TWITTER_API_SECRET",
            "TWITTER_ACCESS_TOKEN",
            "TWITTER_ACCESS_SECRET",
            "GUMROAD_ACCESS_TOKEN",
            "WHISPER_BACKEND",
        ]
        clean_env = {k: v for k, v in os.environ.items() if k not in env_keys}
        with patch.dict(os.environ, clean_env, clear=True):
            cfg = IntegrationsConfig.from_env()
            assert cfg.linkedin_access_token is None
            assert cfg.whisper_backend == "auto"


# =============================================================================
# Config Integration Tests
# =============================================================================


class TestConfigWithIntegrations:
    """Test that Config includes IntegrationsConfig."""

    def test_config_has_integrations(self):
        """Config dataclass includes integrations field."""
        cfg = Config()
        assert isinstance(cfg.integrations, IntegrationsConfig)

    def test_config_from_env_includes_integrations(self):
        """Config.from_env() loads integrations."""
        env = {
            "GUMROAD_ACCESS_TOKEN": "test_gum",
            "AGENTWERK_ENV": "development",
        }
        with patch.dict(os.environ, env, clear=False):
            cfg = Config.from_env()
            assert cfg.integrations.gumroad_access_token == "test_gum"

    def test_config_validate_includes_integrations(self):
        """Config.validate() includes IntegrationsConfig validation."""
        cfg = Config()
        cfg.integrations = IntegrationsConfig(whisper_backend="bad-backend")
        errors = cfg.validate()
        assert any("WHISPER_BACKEND" in e for e in errors)

    def test_config_to_dict_includes_integrations(self):
        """Config.to_dict() includes integration summary."""
        cfg = Config()
        cfg.integrations = IntegrationsConfig(
            linkedin_access_token="tok",
            linkedin_person_urn="urn",
        )
        d = cfg.to_dict()
        assert "integrations" in d
        assert d["integrations"]["linkedin"] is True
        assert d["integrations"]["gumroad"] is False


# =============================================================================
# Production Validation Tests
# =============================================================================


class TestProductionValidation:
    """Test production-specific validation behaviour."""

    def test_valid_config_passes(self):
        """Default config (development) passes validation."""
        cfg = Config()
        errors = cfg.validate()
        assert errors == []

    def test_invalid_whisper_backend_detected(self):
        """Invalid whisper backend is caught by validation."""
        cfg = Config()
        cfg.integrations = IntegrationsConfig(whisper_backend="nonexistent")
        errors = cfg.validate()
        assert len(errors) == 1


# =============================================================================
# Health Check Integration Tests
# =============================================================================


class TestIntegrationHealthCheck:
    """Test the integrations health check function."""

    async def test_health_check_no_integrations(self):
        """Health check warns when no integrations configured."""
        from ag3ntwerk.core.config import set_config

        cfg = Config()
        set_config(cfg)

        from ag3ntwerk.core.config import get_config

        integ = get_config().integrations
        summary = integ.summary()
        active = [k for k, v in summary.items() if v]
        # whisper defaults to "auto" which counts as configured
        assert "whisper" in active

    async def test_health_check_with_integrations(self):
        """Health check passes when integrations are configured."""
        cfg = Config()
        cfg.integrations = IntegrationsConfig(
            linkedin_access_token="tok",
            linkedin_person_urn="urn",
            gumroad_access_token="gum",
        )
        set_config(cfg)

        integ = get_config().integrations
        summary = integ.summary()
        active = [k for k, v in summary.items() if v]
        assert "linkedin" in active
        assert "gumroad" in active
        assert "whisper" in active


# =============================================================================
# Docker Compose Validation Tests
# =============================================================================


class TestDockerComposeEnvVars:
    """Test that Docker Compose files include Revenue Stack env vars."""

    def test_prod_compose_has_linkedin_vars(self):
        """Prod Docker Compose includes LinkedIn env vars."""
        compose_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "docker-compose.prod.yml"
        )
        with open(compose_path) as f:
            content = f.read()
        assert "LINKEDIN_ACCESS_TOKEN" in content
        assert "LINKEDIN_PERSON_URN" in content

    def test_prod_compose_has_twitter_vars(self):
        """Prod Docker Compose includes Twitter env vars."""
        compose_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "docker-compose.prod.yml"
        )
        with open(compose_path) as f:
            content = f.read()
        assert "TWITTER_BEARER_TOKEN" in content
        assert "TWITTER_API_KEY" in content

    def test_prod_compose_has_gumroad_var(self):
        """Prod Docker Compose includes Gumroad env var."""
        compose_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "docker-compose.prod.yml"
        )
        with open(compose_path) as f:
            content = f.read()
        assert "GUMROAD_ACCESS_TOKEN" in content

    def test_prod_compose_has_whisper_var(self):
        """Prod Docker Compose includes Whisper backend env var."""
        compose_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "docker-compose.prod.yml"
        )
        with open(compose_path) as f:
            content = f.read()
        assert "WHISPER_BACKEND" in content

    def test_dev_compose_has_revenue_stack_vars(self):
        """Dev Docker Compose also includes Revenue Stack env vars."""
        compose_path = os.path.join(os.path.dirname(__file__), "..", "..", "docker-compose.yml")
        with open(compose_path) as f:
            content = f.read()
        assert "LINKEDIN_ACCESS_TOKEN" in content
        assert "GUMROAD_ACCESS_TOKEN" in content
        assert "WHISPER_BACKEND" in content


# =============================================================================
# Package Import Tests
# =============================================================================


class TestConfigImports:
    """Test that IntegrationsConfig is properly exported."""

    def test_import_from_config(self):
        """Test importing IntegrationsConfig from config module."""
        from ag3ntwerk.core.config import IntegrationsConfig

        assert IntegrationsConfig is not None

    def test_in_all_list(self):
        """Test IntegrationsConfig is in __all__."""
        import ag3ntwerk.core.config as cfg_mod

        assert "IntegrationsConfig" in cfg_mod.__all__
