"""Tests for the Ollama lifecycle manager."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import sys
import importlib.util

# Load ollama_manager module directly to avoid namespace collision with other nexus packages
_module_path = (
    Path(__file__).parent.parent.parent
    / "src"
    / "nexus"
    / "src"
    / "nexus"
    / "services"
    / "ollama_manager.py"
)
_spec = importlib.util.spec_from_file_location("ollama_manager", _module_path)
ollama_manager_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ollama_manager_module)

OllamaManager = ollama_manager_module.OllamaManager
OllamaStatus = ollama_manager_module.OllamaStatus
get_ollama_manager = ollama_manager_module.get_ollama_manager
ensure_ollama_running = ollama_manager_module.ensure_ollama_running


class TestOllamaStatus:
    """Tests for OllamaStatus enum."""

    def test_status_values(self):
        """Test that all expected status values exist."""
        assert OllamaStatus.STOPPED.value == "stopped"
        assert OllamaStatus.STARTING.value == "starting"
        assert OllamaStatus.RUNNING.value == "running"
        assert OllamaStatus.ERROR.value == "error"
        assert OllamaStatus.UNKNOWN.value == "unknown"


class TestOllamaManager:
    """Tests for OllamaManager class."""

    def test_init_default_values(self):
        """Test manager initialization with defaults."""
        manager = OllamaManager()

        assert manager.host == "http://localhost:11434"
        assert manager.auto_start is True
        assert manager.health_check_interval == 30.0
        assert manager.startup_timeout == 60.0
        assert manager.preload_models == []
        assert manager.status == OllamaStatus.UNKNOWN

    def test_init_custom_values(self):
        """Test manager initialization with custom values."""
        manager = OllamaManager(
            host="http://custom:8080",
            auto_start=False,
            health_check_interval=60.0,
            startup_timeout=120.0,
            preload_models=["model1", "model2"],
        )

        assert manager.host == "http://custom:8080"
        assert manager.auto_start is False
        assert manager.health_check_interval == 60.0
        assert manager.startup_timeout == 120.0
        assert manager.preload_models == ["model1", "model2"]

    def test_is_running_property(self):
        """Test is_running property."""
        manager = OllamaManager()

        assert manager.is_running is False

        manager._status = OllamaStatus.RUNNING
        assert manager.is_running is True

        manager._status = OllamaStatus.STOPPED
        assert manager.is_running is False

    def test_status_callback_registration(self):
        """Test status change callback registration."""
        manager = OllamaManager()
        callback = MagicMock()

        manager.on_status_change(callback)
        assert callback in manager._status_callbacks

    def test_status_change_notifies_callbacks(self):
        """Test that status changes notify registered callbacks."""
        manager = OllamaManager()
        callback = MagicMock()
        manager.on_status_change(callback)

        manager._set_status(OllamaStatus.RUNNING)

        callback.assert_called_once_with(OllamaStatus.RUNNING)

    def test_status_change_only_on_actual_change(self):
        """Test that callbacks only fire on actual status change."""
        manager = OllamaManager()
        manager._status = OllamaStatus.RUNNING
        callback = MagicMock()
        manager.on_status_change(callback)

        # Same status - should not call
        manager._set_status(OllamaStatus.RUNNING)
        callback.assert_not_called()

        # Different status - should call
        manager._set_status(OllamaStatus.STOPPED)
        callback.assert_called_once_with(OllamaStatus.STOPPED)

    def test_get_status_info(self):
        """Test get_status_info returns expected data."""
        manager = OllamaManager(host="http://test:1234", auto_start=False)

        info = manager.get_status_info()

        assert info["status"] == "unknown"
        assert info["is_running"] is False
        assert info["started_by_us"] is False
        assert info["host"] == "http://test:1234"
        assert info["auto_start"] is False
        assert info["consecutive_failures"] == 0

    @pytest.mark.asyncio
    async def test_check_health_success_live(self):
        """Test health check against live Ollama (if running)."""
        manager = OllamaManager()

        # This test checks against real Ollama if it's running
        # If Ollama isn't running, the test still passes (we verify behavior)
        result = await manager.check_health()

        # The result depends on whether Ollama is actually running
        # We just verify the method runs and updates status correctly
        if result:
            assert manager.status == OllamaStatus.RUNNING
            assert manager._consecutive_failures == 0
        else:
            # After single failure, status may not change yet
            assert manager._consecutive_failures >= 1

    @pytest.mark.asyncio
    async def test_check_health_failure(self):
        """Test health check when Ollama is not running."""
        manager = OllamaManager()

        with patch("aiohttp.ClientSession") as mock_session:
            mock_session.return_value.__aenter__.return_value.get.side_effect = Exception(
                "Connection refused"
            )

            # Need 3 failures to change status
            for _ in range(3):
                result = await manager.check_health()

            assert result is False
            assert manager._consecutive_failures == 3
            assert manager.status == OllamaStatus.STOPPED

    @pytest.mark.asyncio
    async def test_get_models_live(self):
        """Test getting models list (live test)."""
        manager = OllamaManager()

        # Test against live Ollama if running
        result = await manager.get_models()

        # Result is a list (may be empty if Ollama not running or no models)
        assert isinstance(result, list)

        # If we got models, verify structure
        if result:
            for model in result:
                assert "name" in model

    @pytest.mark.asyncio
    async def test_get_models_failure(self):
        """Test getting models when Ollama is unavailable."""
        manager = OllamaManager()

        with patch("aiohttp.ClientSession") as mock_session:
            mock_session.return_value.__aenter__.return_value.get.side_effect = Exception(
                "Connection refused"
            )

            result = await manager.get_models()

            assert result == []

    @pytest.mark.asyncio
    async def test_get_running_models_live(self):
        """Test getting currently loaded models (live test)."""
        manager = OllamaManager()

        # Test against live Ollama if running
        result = await manager.get_running_models()

        # Result is a list (may be empty if Ollama not running or no models loaded)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_start_when_already_running(self):
        """Test start when Ollama is already running."""
        manager = OllamaManager()

        with patch.object(manager, "check_health", return_value=True):
            result = await manager.start()

            assert result is True
            assert manager._started_by_us is False

    @pytest.mark.asyncio
    async def test_start_without_executable(self):
        """Test start when Ollama executable not found."""
        manager = OllamaManager()
        manager._ollama_path = None

        with patch.object(manager, "check_health", return_value=False):
            result = await manager.start()

            assert result is False
            assert manager.status == OllamaStatus.ERROR

    @pytest.mark.asyncio
    async def test_stop_when_not_started_by_us(self):
        """Test stop doesn't kill Ollama we didn't start."""
        manager = OllamaManager()
        manager._started_by_us = False
        manager._process = MagicMock()

        await manager.stop(force=False)

        manager._process.terminate.assert_not_called()

    @pytest.mark.asyncio
    async def test_stop_force(self):
        """Test force stop kills Ollama even if we didn't start it."""
        manager = OllamaManager()
        manager._started_by_us = False

        # Create proper mock process
        mock_process = MagicMock()
        mock_process.kill = MagicMock()
        mock_process.wait = MagicMock()
        manager._process = mock_process

        await manager.stop(force=True)

        mock_process.kill.assert_called_once()


class TestGetOllamaManager:
    """Tests for get_ollama_manager function."""

    def test_returns_singleton(self):
        """Test that get_ollama_manager returns singleton instance."""
        # Reset singleton for test
        ollama_manager_module._manager_instance = None

        manager1 = get_ollama_manager()
        manager2 = get_ollama_manager()

        assert manager1 is manager2

        # Reset for other tests
        ollama_manager_module._manager_instance = None

    def test_custom_params_on_first_call(self):
        """Test that custom params are used on first call."""
        ollama_manager_module._manager_instance = None

        manager = get_ollama_manager(
            host="http://custom:9999",
            auto_start=False,
        )

        assert manager.host == "http://custom:9999"
        assert manager.auto_start is False

        # Reset for other tests
        ollama_manager_module._manager_instance = None


class TestEnsureOllamaRunning:
    """Tests for ensure_ollama_running function."""

    @pytest.mark.asyncio
    async def test_ensure_ollama_running(self):
        """Test ensure_ollama_running starts Ollama and monitoring."""
        ollama_manager_module._manager_instance = None

        with patch.object(OllamaManager, "start", new_callable=AsyncMock) as mock_start:
            with patch.object(
                OllamaManager, "start_health_monitoring", new_callable=AsyncMock
            ) as mock_monitoring:
                mock_start.return_value = True

                manager = await ensure_ollama_running()

                mock_start.assert_called_once()
                mock_monitoring.assert_called_once()

        # Reset for other tests
        ollama_manager_module._manager_instance = None


class TestOllamaManagerIntegration:
    """Integration-style tests for OllamaManager."""

    def test_find_ollama_checks_path(self):
        """Test that _find_ollama checks system PATH."""
        manager = OllamaManager()

        # Should have checked for ollama in PATH
        # Result depends on system state, but should not raise
        assert manager._ollama_path is None or manager._ollama_path.name in [
            "ollama",
            "ollama.exe",
        ]

    def test_default_paths_by_platform(self):
        """Test that default paths are defined for major platforms."""
        assert "Windows" in OllamaManager.DEFAULT_PATHS
        assert "Darwin" in OllamaManager.DEFAULT_PATHS
        assert "Linux" in OllamaManager.DEFAULT_PATHS

        for platform_paths in OllamaManager.DEFAULT_PATHS.values():
            assert len(platform_paths) > 0
            for path in platform_paths:
                assert isinstance(path, Path)
