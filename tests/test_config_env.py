"""Tests for environment variable configuration."""

import os


def test_config_reads_agentwerk_vars(monkeypatch):
    monkeypatch.setenv("AGENTWERK_ENV", "development")
    monkeypatch.setenv("AGENTWERK_HOST", "127.0.0.1")
    monkeypatch.setenv("AGENTWERK_PORT", "3737")
    from ag3ntwerk.core.config import Config

    cfg = Config.from_env()
    assert cfg.server.host == "127.0.0.1"
    assert cfg.server.port == 3737
