"""
Whisper/Buzz Integration for ag3ntwerk.

Provides speech-to-text transcription capabilities.
Uses OpenAI Whisper models locally via Buzz or directly.

Requirements:
    - pip install openai-whisper
    - Or install Buzz: https://github.com/chidiwilliams/buzz

Whisper is ideal for:
    - Transcribing voice commands for agents
    - Meeting transcription and summarization
    - Multi-language speech recognition
    - Real-time voice input
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from pathlib import Path
import json
import subprocess

logger = logging.getLogger(__name__)


class WhisperModel(str, Enum):
    """Available Whisper model sizes."""

    TINY = "tiny"
    BASE = "base"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    LARGE_V2 = "large-v2"
    LARGE_V3 = "large-v3"


class TaskType(str, Enum):
    """Whisper task types."""

    TRANSCRIBE = "transcribe"
    TRANSLATE = "translate"  # Translate to English


@dataclass
class TranscriptionConfig:
    """Configuration for transcription."""

    model: WhisperModel = WhisperModel.BASE
    language: Optional[str] = None  # Auto-detect if None
    task: TaskType = TaskType.TRANSCRIBE
    temperature: float = 0.0
    beam_size: int = 5
    word_timestamps: bool = False
    initial_prompt: Optional[str] = None
    condition_on_previous_text: bool = True
    fp16: bool = True  # Use FP16 for GPU
    verbose: bool = False


@dataclass
class TranscriptionSegment:
    """A segment of transcribed text."""

    id: int
    start: float
    end: float
    text: str
    words: Optional[List[Dict[str, Any]]] = None
    confidence: float = 1.0


@dataclass
class TranscriptionResult:
    """Result of transcription."""

    text: str
    segments: List[TranscriptionSegment] = field(default_factory=list)
    language: str = "en"
    duration: float = 0.0
    audio_path: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "text": self.text,
            "segments": [
                {
                    "id": s.id,
                    "start": s.start,
                    "end": s.end,
                    "text": s.text,
                    "words": s.words,
                    "confidence": s.confidence,
                }
                for s in self.segments
            ],
            "language": self.language,
            "duration": self.duration,
            "audio_path": self.audio_path,
            "metadata": self.metadata,
        }

    def to_srt(self) -> str:
        """Convert to SRT subtitle format."""
        lines = []
        for segment in self.segments:
            lines.append(str(segment.id + 1))
            start = self._format_timestamp(segment.start)
            end = self._format_timestamp(segment.end)
            lines.append(f"{start} --> {end}")
            lines.append(segment.text.strip())
            lines.append("")
        return "\n".join(lines)

    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds to SRT timestamp."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


class WhisperIntegration:
    """
    Integration with Whisper for speech-to-text.

    Provides transcription capabilities using OpenAI Whisper models.

    Example:
        integration = WhisperIntegration()

        # Transcribe audio file
        result = await integration.transcribe("meeting.wav")
        print(result.text)

        # Transcribe with specific model
        result = await integration.transcribe(
            "speech.mp3",
            config=TranscriptionConfig(model=WhisperModel.MEDIUM),
        )

        # Get segments with timestamps
        for segment in result.segments:
            print(f"[{segment.start:.2f}s] {segment.text}")
    """

    def __init__(
        self,
        models_dir: Optional[str] = None,
        device: str = "auto",
        default_model: WhisperModel = WhisperModel.BASE,
    ):
        """
        Initialize Whisper integration.

        Args:
            models_dir: Directory for model weights
            device: Device to use (auto, cuda, cpu)
            default_model: Default model size
        """
        self.models_dir = Path(models_dir) if models_dir else Path("./models/whisper")
        self.device = device
        self.default_model = default_model

        self.models_dir.mkdir(parents=True, exist_ok=True)

        self._model = None
        self._loaded_model_name: Optional[str] = None

    def _get_device(self) -> str:
        """Get the device to use for inference."""
        if self.device == "auto":
            try:
                import torch

                return "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                return "cpu"
        return self.device

    def _load_model(self, model_name: str) -> Any:
        """Load a Whisper model."""
        if self._loaded_model_name == model_name and self._model is not None:
            return self._model

        try:
            import whisper

            logger.info(f"Loading Whisper model: {model_name}")
            self._model = whisper.load_model(
                model_name,
                device=self._get_device(),
                download_root=str(self.models_dir),
            )
            self._loaded_model_name = model_name
            logger.info(f"Whisper model {model_name} loaded successfully")
            return self._model

        except ImportError:
            raise ImportError("Whisper not installed. Install with: pip install openai-whisper")

    async def transcribe(
        self,
        audio_path: str,
        config: Optional[TranscriptionConfig] = None,
    ) -> TranscriptionResult:
        """
        Transcribe an audio file.

        Args:
            audio_path: Path to audio file
            config: Transcription configuration

        Returns:
            TranscriptionResult with transcribed text
        """
        config = config or TranscriptionConfig(model=self.default_model)

        # Try whisper library first
        try:
            return await self._transcribe_whisper(audio_path, config)
        except ImportError:
            pass

        # Try faster-whisper
        try:
            return await self._transcribe_faster_whisper(audio_path, config)
        except ImportError:
            pass

        # Try Buzz CLI
        try:
            return await self._transcribe_buzz(audio_path, config)
        except Exception as e:
            logger.debug("Buzz transcription backend unavailable: %s", e)

        raise RuntimeError(
            "No transcription backend available. Install one of: "
            "openai-whisper, faster-whisper, or Buzz"
        )

    async def _transcribe_whisper(
        self,
        audio_path: str,
        config: TranscriptionConfig,
    ) -> TranscriptionResult:
        """Transcribe using openai-whisper."""
        import whisper

        loop = asyncio.get_running_loop()

        def _transcribe():
            model = self._load_model(config.model.value)

            result = model.transcribe(
                audio_path,
                language=config.language,
                task=config.task.value,
                temperature=config.temperature,
                beam_size=config.beam_size,
                word_timestamps=config.word_timestamps,
                initial_prompt=config.initial_prompt,
                condition_on_previous_text=config.condition_on_previous_text,
                fp16=config.fp16 and self._get_device() == "cuda",
                verbose=config.verbose,
            )

            return result

        result = await loop.run_in_executor(None, _transcribe)

        segments = [
            TranscriptionSegment(
                id=seg["id"],
                start=seg["start"],
                end=seg["end"],
                text=seg["text"],
                words=seg.get("words"),
            )
            for seg in result.get("segments", [])
        ]

        duration = segments[-1].end if segments else 0.0

        return TranscriptionResult(
            text=result["text"],
            segments=segments,
            language=result.get("language", "en"),
            duration=duration,
            audio_path=audio_path,
            metadata={"backend": "whisper", "model": config.model.value},
        )

    async def _transcribe_faster_whisper(
        self,
        audio_path: str,
        config: TranscriptionConfig,
    ) -> TranscriptionResult:
        """Transcribe using faster-whisper."""
        from faster_whisper import WhisperModel

        loop = asyncio.get_running_loop()

        def _transcribe():
            model = WhisperModel(
                config.model.value,
                device=self._get_device(),
                compute_type="float16" if config.fp16 else "float32",
                download_root=str(self.models_dir),
            )

            segments, info = model.transcribe(
                audio_path,
                language=config.language,
                task=config.task.value,
                beam_size=config.beam_size,
                word_timestamps=config.word_timestamps,
                initial_prompt=config.initial_prompt,
                condition_on_previous_text=config.condition_on_previous_text,
            )

            return list(segments), info

        segments_raw, info = await loop.run_in_executor(None, _transcribe)

        segments = [
            TranscriptionSegment(
                id=i,
                start=seg.start,
                end=seg.end,
                text=seg.text,
                words=[{"word": w.word, "start": w.start, "end": w.end} for w in (seg.words or [])],
            )
            for i, seg in enumerate(segments_raw)
        ]

        text = " ".join(seg.text.strip() for seg in segments)
        duration = segments[-1].end if segments else 0.0

        return TranscriptionResult(
            text=text,
            segments=segments,
            language=info.language,
            duration=duration,
            audio_path=audio_path,
            metadata={
                "backend": "faster-whisper",
                "model": config.model.value,
                "language_probability": info.language_probability,
            },
        )

    async def _transcribe_buzz(
        self,
        audio_path: str,
        config: TranscriptionConfig,
    ) -> TranscriptionResult:
        """Transcribe using Buzz CLI."""
        # Try to find buzz executable
        buzz_path = self._find_buzz()
        if not buzz_path:
            raise RuntimeError("Buzz not found")

        output_path = audio_path + ".txt"

        cmd = [
            buzz_path,
            "--model",
            config.model.value,
            "--task",
            config.task.value,
            "--output",
            output_path,
            audio_path,
        ]

        if config.language:
            cmd.extend(["--language", config.language])

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"Buzz failed: {stderr.decode()}")

        with open(output_path, "r") as f:
            text = f.read()

        os.remove(output_path)

        return TranscriptionResult(
            text=text,
            segments=[],
            language=config.language or "en",
            audio_path=audio_path,
            metadata={"backend": "buzz", "model": config.model.value},
        )

    def _find_buzz(self) -> Optional[str]:
        """Find Buzz executable."""
        # Check common locations
        locations = [
            "buzz",
            "buzz.exe",
            os.path.expanduser("~/.local/bin/buzz"),
            "/usr/local/bin/buzz",
        ]

        for loc in locations:
            if (
                os.path.isfile(loc)
                or subprocess.run(
                    ["which", loc] if os.name != "nt" else ["where", loc],
                    capture_output=True,
                ).returncode
                == 0
            ):
                return loc

        return None

    async def transcribe_stream(
        self,
        audio_stream: Any,
        config: Optional[TranscriptionConfig] = None,
        chunk_duration: float = 5.0,
    ):
        """
        Transcribe an audio stream in chunks.

        Args:
            audio_stream: Audio stream or generator
            config: Transcription configuration
            chunk_duration: Duration of each chunk in seconds

        Yields:
            TranscriptionSegment for each chunk
        """
        config = config or TranscriptionConfig(model=self.default_model)

        import tempfile

        chunk_id = 0
        async for chunk in audio_stream:
            # Write chunk to temp file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_path = f.name
                f.write(chunk)

            try:
                result = await self.transcribe(temp_path, config)
                for segment in result.segments:
                    segment.id = chunk_id
                    yield segment
                    chunk_id += 1
            finally:
                os.remove(temp_path)

    async def detect_language(
        self,
        audio_path: str,
    ) -> Dict[str, float]:
        """
        Detect the language of an audio file.

        Args:
            audio_path: Path to audio file

        Returns:
            Dictionary mapping language codes to probabilities
        """
        try:
            import whisper

            model = self._load_model(WhisperModel.BASE.value)

            # Load audio and pad/trim
            audio = whisper.load_audio(audio_path)
            audio = whisper.pad_or_trim(audio)

            # Make log-Mel spectrogram
            mel = whisper.log_mel_spectrogram(audio).to(model.device)

            # Detect language
            _, probs = model.detect_language(mel)

            return dict(probs)

        except ImportError:
            # Fallback: just return detected language from transcription
            result = await self.transcribe(
                audio_path,
                TranscriptionConfig(model=WhisperModel.TINY),
            )
            return {result.language: 1.0}

    def list_available_models(self) -> List[str]:
        """List available Whisper models."""
        return [m.value for m in WhisperModel]

    def get_model_info(self, model: WhisperModel) -> Dict[str, Any]:
        """Get information about a model."""
        model_info = {
            WhisperModel.TINY: {
                "parameters": "39M",
                "vram": "~1GB",
                "speed": "~32x",
                "quality": "Basic",
            },
            WhisperModel.BASE: {
                "parameters": "74M",
                "vram": "~1GB",
                "speed": "~16x",
                "quality": "Good",
            },
            WhisperModel.SMALL: {
                "parameters": "244M",
                "vram": "~2GB",
                "speed": "~6x",
                "quality": "Better",
            },
            WhisperModel.MEDIUM: {
                "parameters": "769M",
                "vram": "~5GB",
                "speed": "~2x",
                "quality": "Great",
            },
            WhisperModel.LARGE: {
                "parameters": "1550M",
                "vram": "~10GB",
                "speed": "~1x",
                "quality": "Excellent",
            },
            WhisperModel.LARGE_V2: {
                "parameters": "1550M",
                "vram": "~10GB",
                "speed": "~1x",
                "quality": "Excellent (improved)",
            },
            WhisperModel.LARGE_V3: {
                "parameters": "1550M",
                "vram": "~10GB",
                "speed": "~1x",
                "quality": "Best",
            },
        }
        return model_info.get(model, {})

    async def batch_transcribe(
        self,
        audio_paths: List[str],
        config: Optional[TranscriptionConfig] = None,
        max_concurrent: int = 3,
    ) -> List[TranscriptionResult]:
        """
        Transcribe multiple audio files.

        Args:
            audio_paths: List of audio file paths
            config: Transcription configuration
            max_concurrent: Maximum concurrent transcriptions

        Returns:
            List of TranscriptionResults
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _transcribe_one(path: str) -> TranscriptionResult:
            async with semaphore:
                return await self.transcribe(path, config)

        tasks = [_transcribe_one(path) for path in audio_paths]
        return await asyncio.gather(*tasks)

    def supported_formats(self) -> List[str]:
        """List supported audio formats."""
        return ["wav", "mp3", "m4a", "ogg", "flac", "webm", "aac", "wma", "aiff", "opus"]
