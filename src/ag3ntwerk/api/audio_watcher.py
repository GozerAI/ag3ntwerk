"""
Audio file watcher for meeting intelligence auto-ingestion.

Monitors a configured directory for new audio files (from HiDock or any recorder)
and automatically queues them for the meeting processing pipeline.

Uses watchdog for filesystem monitoring with debounce and file stability checks.
"""

import asyncio
import fnmatch
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

DEFAULT_PATTERNS = ["*.wav", "*.mp3", "*.m4a", "*.aac", "*.ogg", "*.flac", "*.webm"]


@dataclass
class AudioWatcherConfig:
    """Configuration for the audio file watcher."""

    watch_dir: str = ""
    patterns: List[str] = field(default_factory=lambda: list(DEFAULT_PATTERNS))
    recursive: bool = False
    debounce_seconds: float = 5.0
    stability_check_interval: float = 2.0
    stability_checks: int = 2

    @classmethod
    def from_env(cls) -> "AudioWatcherConfig":
        return cls(
            watch_dir=os.getenv("AGENTWERK_MEETING_WATCH_DIR", ""),
            debounce_seconds=float(os.getenv("AGENTWERK_MEETING_DEBOUNCE", "5.0")),
        )


class AudioWatcher:
    """
    Watches a directory for new audio files and auto-processes them.

    Uses watchdog for filesystem events with debounce to avoid
    processing files still being written (common with HiDock recordings).

    Usage:
        watcher = AudioWatcher(config, meeting_service)
        watcher.start()
        # ... later ...
        watcher.stop()
    """

    def __init__(self, config: AudioWatcherConfig, meeting_service):
        self.config = config
        self._meeting_service = meeting_service
        self._observer = None
        self._running = False
        self._recent_files: dict = {}  # path -> timestamp for debounce
        self._lock = threading.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def is_running(self) -> bool:
        return self._running

    def start(self):
        """Start watching the configured directory."""
        if self._running:
            logger.warning("AudioWatcher already running")
            return

        if not self.config.watch_dir:
            logger.error("No watch directory configured")
            return

        watch_path = Path(self.config.watch_dir)
        if not watch_path.exists():
            logger.warning("Watch directory does not exist: %s, creating it", self.config.watch_dir)
            watch_path.mkdir(parents=True, exist_ok=True)

        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler, FileCreatedEvent

            handler = _AudioFileHandler(self)
            self._observer = Observer()
            self._observer.schedule(
                handler,
                str(watch_path),
                recursive=self.config.recursive,
            )
            self._observer.daemon = True
            self._observer.start()
            self._running = True

            # Capture event loop for async callback
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                self._loop = None

            logger.info(
                "AudioWatcher started: watching %s for %s",
                self.config.watch_dir,
                self.config.patterns,
            )

        except ImportError:
            logger.error(
                "watchdog not installed. Install with: pip install watchdog"
            )
            # Fallback: poll-based watcher
            self._start_polling()

    def stop(self):
        """Stop watching."""
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
        self._running = False
        logger.info("AudioWatcher stopped")

    def _matches_pattern(self, filename: str) -> bool:
        """Check if filename matches any configured pattern."""
        return any(fnmatch.fnmatch(filename.lower(), p.lower()) for p in self.config.patterns)

    def _should_process(self, file_path: str) -> bool:
        """Check debounce — skip if we've seen this file recently."""
        with self._lock:
            now = time.time()
            last_seen = self._recent_files.get(file_path, 0)
            if now - last_seen < self.config.debounce_seconds:
                return False
            self._recent_files[file_path] = now
            # Clean old entries
            cutoff = now - 60
            self._recent_files = {
                k: v for k, v in self._recent_files.items() if v > cutoff
            }
            return True

    def _is_file_stable(self, file_path: str) -> bool:
        """Check if file has stopped growing (not still being written)."""
        try:
            sizes = []
            for _ in range(self.config.stability_checks):
                sizes.append(os.path.getsize(file_path))
                time.sleep(self.config.stability_check_interval)
            return len(set(sizes)) == 1 and sizes[0] > 0
        except OSError:
            return False

    def on_file_detected(self, file_path: str):
        """Handle a new audio file detection."""
        filename = os.path.basename(file_path)

        if not self._matches_pattern(filename):
            return

        if not self._should_process(file_path):
            logger.debug("Debounced: %s", file_path)
            return

        logger.info("New audio file detected: %s", file_path)

        # Run stability check and processing in a thread
        thread = threading.Thread(
            target=self._process_in_background,
            args=(file_path,),
            daemon=True,
        )
        thread.start()

    def _process_in_background(self, file_path: str):
        """Wait for file stability then trigger processing."""
        if not self._is_file_stable(file_path):
            logger.warning("File not stable (still being written?): %s", file_path)
            return

        logger.info("Processing stable audio file: %s", file_path)

        # Schedule async processing
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._process_audio(file_path),
                self._loop,
            )
        else:
            # Create new event loop if needed
            try:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(self._process_audio(file_path))
                loop.close()
            except Exception as e:
                logger.error("Failed to process audio %s: %s", file_path, e)

    async def _process_audio(self, file_path: str):
        """Process the audio file through the meeting pipeline."""
        try:
            meeting = await self._meeting_service.process_audio(
                file_path, source="hidock"
            )
            logger.info(
                "Meeting processed: %s (status=%s, title=%s)",
                meeting.id,
                meeting.status.value,
                meeting.title,
            )
        except Exception as e:
            logger.error("Meeting processing failed for %s: %s", file_path, e)

    def _start_polling(self):
        """Fallback poll-based watcher when watchdog is not available."""
        self._running = True
        self._poll_thread = threading.Thread(
            target=self._poll_loop, daemon=True
        )
        self._poll_thread.start()
        logger.info("AudioWatcher started (polling mode): %s", self.config.watch_dir)

    def _poll_loop(self):
        """Poll directory for new files."""
        seen = set()
        watch_path = Path(self.config.watch_dir)

        # Initialize with existing files
        if watch_path.exists():
            for f in watch_path.iterdir():
                if f.is_file():
                    seen.add(str(f))

        while self._running:
            time.sleep(self.config.debounce_seconds)
            if not watch_path.exists():
                continue

            for f in watch_path.iterdir():
                fp = str(f)
                if f.is_file() and fp not in seen:
                    seen.add(fp)
                    self.on_file_detected(fp)


class _AudioFileHandler:
    """Watchdog event handler for audio files."""

    def __init__(self, watcher: AudioWatcher):
        self._watcher = watcher

    def dispatch(self, event):
        if hasattr(event, "is_directory") and event.is_directory:
            return
        if hasattr(event, "event_type") and event.event_type == "created":
            self._watcher.on_file_detected(event.src_path)

    # watchdog FileSystemEventHandler interface
    def on_created(self, event):
        if not event.is_directory:
            self._watcher.on_file_detected(event.src_path)

    def on_modified(self, event):
        pass

    def on_deleted(self, event):
        pass

    def on_moved(self, event):
        pass
