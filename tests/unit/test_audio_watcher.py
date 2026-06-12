"""Tests for AudioWatcher meeting auto-ingestion."""

import os
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ag3ntwerk.api.audio_watcher import (
    AudioWatcher,
    AudioWatcherConfig,
    DEFAULT_PATTERNS,
)


# ============================================================
# Config
# ============================================================


class TestAudioWatcherConfig:
    def test_defaults(self):
        cfg = AudioWatcherConfig()
        assert cfg.watch_dir == ""
        assert cfg.patterns == DEFAULT_PATTERNS
        assert cfg.recursive is False
        assert cfg.debounce_seconds == 5.0

    def test_custom(self):
        cfg = AudioWatcherConfig(
            watch_dir="/recordings",
            patterns=["*.wav"],
            debounce_seconds=10.0,
        )
        assert cfg.watch_dir == "/recordings"
        assert cfg.patterns == ["*.wav"]

    def test_from_env(self):
        with patch.dict(os.environ, {
            "AGENTWERK_MEETING_WATCH_DIR": "/test/dir",
            "AGENTWERK_MEETING_DEBOUNCE": "3.0",
        }):
            cfg = AudioWatcherConfig.from_env()
            assert cfg.watch_dir == "/test/dir"
            assert cfg.debounce_seconds == 3.0

    def test_from_env_defaults(self):
        with patch.dict(os.environ, {}, clear=True):
            cfg = AudioWatcherConfig.from_env()
            assert cfg.watch_dir == ""
            assert cfg.debounce_seconds == 5.0


# ============================================================
# Pattern Matching
# ============================================================


class TestPatternMatching:
    def _make_watcher(self, patterns=None):
        cfg = AudioWatcherConfig(
            watch_dir="/tmp",
            patterns=patterns or DEFAULT_PATTERNS,
        )
        return AudioWatcher(cfg, MagicMock())

    def test_wav_matches(self):
        w = self._make_watcher()
        assert w._matches_pattern("meeting.wav") is True

    def test_mp3_matches(self):
        w = self._make_watcher()
        assert w._matches_pattern("recording.mp3") is True

    def test_m4a_matches(self):
        w = self._make_watcher()
        assert w._matches_pattern("audio.m4a") is True

    def test_txt_does_not_match(self):
        w = self._make_watcher()
        assert w._matches_pattern("notes.txt") is False

    def test_py_does_not_match(self):
        w = self._make_watcher()
        assert w._matches_pattern("script.py") is False

    def test_case_insensitive(self):
        w = self._make_watcher()
        assert w._matches_pattern("MEETING.WAV") is True
        assert w._matches_pattern("Audio.M4A") is True

    def test_custom_patterns(self):
        w = self._make_watcher(patterns=["*.wav"])
        assert w._matches_pattern("test.wav") is True
        assert w._matches_pattern("test.mp3") is False


# ============================================================
# Debounce
# ============================================================


class TestDebounce:
    def test_first_file_passes(self):
        cfg = AudioWatcherConfig(watch_dir="/tmp", debounce_seconds=5.0)
        w = AudioWatcher(cfg, MagicMock())
        assert w._should_process("/audio/test.wav") is True

    def test_same_file_debounced(self):
        cfg = AudioWatcherConfig(watch_dir="/tmp", debounce_seconds=5.0)
        w = AudioWatcher(cfg, MagicMock())
        assert w._should_process("/audio/test.wav") is True
        assert w._should_process("/audio/test.wav") is False

    def test_different_files_not_debounced(self):
        cfg = AudioWatcherConfig(watch_dir="/tmp", debounce_seconds=5.0)
        w = AudioWatcher(cfg, MagicMock())
        assert w._should_process("/audio/a.wav") is True
        assert w._should_process("/audio/b.wav") is True


# ============================================================
# File Stability
# ============================================================


class TestFileStability:
    def test_stable_file(self):
        cfg = AudioWatcherConfig(
            watch_dir="/tmp",
            stability_check_interval=0.01,  # fast for testing
            stability_checks=2,
        )
        w = AudioWatcher(cfg, MagicMock())

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(b"\x00" * 100)
            f.flush()
            path = f.name

        try:
            assert w._is_file_stable(path) is True
        finally:
            os.unlink(path)

    def test_empty_file_not_stable(self):
        cfg = AudioWatcherConfig(
            watch_dir="/tmp",
            stability_check_interval=0.01,
            stability_checks=2,
        )
        w = AudioWatcher(cfg, MagicMock())

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = f.name
            # Don't write anything — 0 bytes

        try:
            assert w._is_file_stable(path) is False
        finally:
            os.unlink(path)

    def test_nonexistent_file(self):
        cfg = AudioWatcherConfig(
            watch_dir="/tmp",
            stability_check_interval=0.01,
            stability_checks=2,
        )
        w = AudioWatcher(cfg, MagicMock())
        assert w._is_file_stable("/nonexistent/file.wav") is False


# ============================================================
# Lifecycle
# ============================================================


class TestWatcherLifecycle:
    def test_not_running_initially(self):
        cfg = AudioWatcherConfig(watch_dir="/tmp")
        w = AudioWatcher(cfg, MagicMock())
        assert w.is_running() is False

    def test_start_without_watch_dir(self):
        cfg = AudioWatcherConfig(watch_dir="")
        w = AudioWatcher(cfg, MagicMock())
        w.start()
        assert w.is_running() is False  # Should fail gracefully

    def test_stop_when_not_running(self):
        cfg = AudioWatcherConfig(watch_dir="/tmp")
        w = AudioWatcher(cfg, MagicMock())
        w.stop()  # Should not raise
        assert w.is_running() is False

    def test_on_file_detected_non_audio(self):
        cfg = AudioWatcherConfig(watch_dir="/tmp")
        svc = MagicMock()
        w = AudioWatcher(cfg, svc)
        w.on_file_detected("/tmp/notes.txt")
        # Should not trigger processing for non-audio files
