"""
OpenVoice Integration for ag3ntwerk.

Provides advanced text-to-speech capabilities with voice cloning.
Enables agents to have unique, consistent voice personas.

Requirements:
    - pip install openvoice-cli
    - Or: git clone https://github.com/myshell-ai/OpenVoice

OpenVoice is ideal for:
    - Giving each agent a unique voice
    - Voice cloning from reference audio
    - Multi-language speech synthesis
    - Emotional and stylistic voice control
"""

import asyncio
import logging
import os
import tempfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from pathlib import Path
import subprocess
import json

logger = logging.getLogger(__name__)


class VoiceStyle(str, Enum):
    """Voice styles/emotions for synthesis."""

    DEFAULT = "default"
    FRIENDLY = "friendly"
    PROFESSIONAL = "professional"
    CHEERFUL = "cheerful"
    SERIOUS = "serious"
    EXCITED = "excited"
    SAD = "sad"
    ANGRY = "angry"
    WHISPERING = "whispering"
    SHOUTING = "shouting"


@dataclass
class VoiceConfig:
    """Configuration for voice synthesis."""

    name: str = "default"
    language: str = "en"
    style: VoiceStyle = VoiceStyle.DEFAULT
    speed: float = 1.0  # 0.5 to 2.0
    pitch: float = 1.0  # 0.5 to 2.0
    volume: float = 1.0  # 0.0 to 1.0
    reference_audio: Optional[str] = None  # Path to reference audio for cloning
    output_format: str = "wav"  # wav, mp3, ogg
    sample_rate: int = 22050


@dataclass
class SynthesisResult:
    """Result of speech synthesis."""

    audio_path: str
    text: str
    duration: float
    voice_config: VoiceConfig
    metadata: Dict[str, Any] = field(default_factory=dict)


class OpenVoiceIntegration:
    """
    Integration with OpenVoice for text-to-speech synthesis.

    Provides voice synthesis with optional voice cloning capabilities.

    Example:
        integration = OpenVoiceIntegration()

        # Simple synthesis
        result = await integration.synthesize(
            "Hello, I am the CEO.",
            VoiceConfig(style=VoiceStyle.PROFESSIONAL),
        )

        # With voice cloning
        result = await integration.synthesize_with_clone(
            "Hello, this is my cloned voice.",
            reference_audio="path/to/reference.wav",
        )
    """

    def __init__(
        self,
        models_dir: Optional[str] = None,
        output_dir: Optional[str] = None,
        device: str = "auto",
    ):
        """
        Initialize OpenVoice integration.

        Args:
            models_dir: Directory for model weights
            output_dir: Directory for output audio files
            device: Device to use (auto, cuda, cpu)
        """
        self.models_dir = Path(models_dir) if models_dir else Path("./models/openvoice")
        self.output_dir = Path(output_dir) if output_dir else Path("./output/audio")
        self.device = device

        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._model = None
        self._tone_converter = None
        self._voice_configs: Dict[str, VoiceConfig] = {}

        # Pre-defined agent voices
        self._executive_voices = {
            "CEO": VoiceConfig(
                name="ceo",
                style=VoiceStyle.PROFESSIONAL,
                speed=0.95,
                pitch=0.95,
            ),
            "Keystone": VoiceConfig(
                name="cfo",
                style=VoiceStyle.SERIOUS,
                speed=0.9,
                pitch=1.0,
            ),
            "Forge": VoiceConfig(
                name="cto",
                style=VoiceStyle.FRIENDLY,
                speed=1.05,
                pitch=1.05,
            ),
            "Echo": VoiceConfig(
                name="cmo",
                style=VoiceStyle.CHEERFUL,
                speed=1.1,
                pitch=1.1,
            ),
            "Nexus": VoiceConfig(
                name="coo",
                style=VoiceStyle.PROFESSIONAL,
                speed=1.0,
                pitch=1.0,
            ),
        }

    def _load_model(self) -> None:
        """Load the OpenVoice model."""
        try:
            from openvoice import se_extractor
            from openvoice.api import ToneColorConverter
            from melo.api import TTS

            # Initialize TTS
            self._tts = TTS(language="EN", device=self._get_device())

            # Initialize tone converter for voice cloning
            ckpt_converter = self.models_dir / "converter"
            if ckpt_converter.exists():
                self._tone_converter = ToneColorConverter(
                    f"{ckpt_converter}/config.json",
                    device=self._get_device(),
                )
                self._tone_converter.load_ckpt(f"{ckpt_converter}/checkpoint.pth")

            self._se_extractor = se_extractor
            logger.info("OpenVoice model loaded successfully")

        except ImportError:
            logger.warning(
                "OpenVoice not installed. Using fallback TTS. "
                "Install with: pip install openvoice-cli"
            )
            self._model = None

    def _get_device(self) -> str:
        """Get the device to use for inference."""
        if self.device == "auto":
            try:
                import torch

                return "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                return "cpu"
        return self.device

    async def synthesize(
        self,
        text: str,
        config: Optional[VoiceConfig] = None,
        output_path: Optional[str] = None,
    ) -> SynthesisResult:
        """
        Synthesize speech from text.

        Args:
            text: Text to synthesize
            config: Voice configuration
            output_path: Optional output file path

        Returns:
            SynthesisResult with audio path
        """
        config = config or VoiceConfig()

        if output_path is None:
            output_path = str(
                self.output_dir / f"speech_{hash(text) % 10000}.{config.output_format}"
            )

        # Try OpenVoice first
        if self._model is not None or self._try_load_openvoice():
            return await self._synthesize_openvoice(text, config, output_path)

        # Fallback to pyttsx3 or other TTS
        return await self._synthesize_fallback(text, config, output_path)

    def _try_load_openvoice(self) -> bool:
        """Try to load OpenVoice model."""
        try:
            self._load_model()
            return self._model is not None or hasattr(self, "_tts")
        except Exception as e:
            logger.warning(f"Failed to load OpenVoice: {e}")
            return False

    async def _synthesize_openvoice(
        self,
        text: str,
        config: VoiceConfig,
        output_path: str,
    ) -> SynthesisResult:
        """Synthesize using OpenVoice."""
        loop = asyncio.get_running_loop()

        def _synthesize():
            # Map style to speaker
            speaker_ids = self._tts.hps.data.spk2id

            # Use default speaker or map style
            speaker = list(speaker_ids.keys())[0]

            # Generate base audio
            self._tts.tts_to_file(
                text,
                speaker_ids[speaker],
                output_path,
                speed=config.speed,
            )

            return output_path

        await loop.run_in_executor(None, _synthesize)

        # Get audio duration
        duration = await self._get_audio_duration(output_path)

        return SynthesisResult(
            audio_path=output_path,
            text=text,
            duration=duration,
            voice_config=config,
        )

    async def _synthesize_fallback(
        self,
        text: str,
        config: VoiceConfig,
        output_path: str,
    ) -> SynthesisResult:
        """Fallback synthesis using pyttsx3 or edge-tts."""
        loop = asyncio.get_running_loop()

        # Try edge-tts first (better quality)
        try:
            import edge_tts

            voice_map = {
                VoiceStyle.DEFAULT: "en-US-GuyNeural",
                VoiceStyle.FRIENDLY: "en-US-JennyNeural",
                VoiceStyle.PROFESSIONAL: "en-US-GuyNeural",
                VoiceStyle.CHEERFUL: "en-US-AriaNeural",
                VoiceStyle.SERIOUS: "en-US-DavisNeural",
            }

            voice = voice_map.get(config.style, "en-US-GuyNeural")

            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)

            duration = await self._get_audio_duration(output_path)

            return SynthesisResult(
                audio_path=output_path,
                text=text,
                duration=duration,
                voice_config=config,
                metadata={"engine": "edge-tts"},
            )

        except ImportError:
            pass

        # Fall back to pyttsx3
        try:
            import pyttsx3

            def _synthesize():
                engine = pyttsx3.init()
                engine.setProperty("rate", int(150 * config.speed))
                engine.setProperty("volume", config.volume)
                engine.save_to_file(text, output_path)
                engine.runAndWait()

            await loop.run_in_executor(None, _synthesize)

            duration = await self._get_audio_duration(output_path)

            return SynthesisResult(
                audio_path=output_path,
                text=text,
                duration=duration,
                voice_config=config,
                metadata={"engine": "pyttsx3"},
            )

        except ImportError:
            raise RuntimeError(
                "No TTS engine available. Install one of: " "openvoice, edge-tts, pyttsx3"
            )

    async def synthesize_with_clone(
        self,
        text: str,
        reference_audio: str,
        config: Optional[VoiceConfig] = None,
        output_path: Optional[str] = None,
    ) -> SynthesisResult:
        """
        Synthesize speech with voice cloning.

        Args:
            text: Text to synthesize
            reference_audio: Path to reference audio for cloning
            config: Voice configuration
            output_path: Optional output file path

        Returns:
            SynthesisResult with cloned voice audio
        """
        config = config or VoiceConfig()
        config.reference_audio = reference_audio

        if output_path is None:
            output_path = str(
                self.output_dir / f"cloned_{hash(text) % 10000}.{config.output_format}"
            )

        if not self._try_load_openvoice() or self._tone_converter is None:
            logger.warning("Voice cloning requires OpenVoice. Falling back to standard synthesis.")
            return await self.synthesize(text, config, output_path)

        loop = asyncio.get_running_loop()

        def _clone_and_synthesize():
            # Extract speaker embedding from reference
            target_se, _ = self._se_extractor.get_se(
                reference_audio,
                self._tone_converter,
                vad=True,
            )

            # Generate base audio
            temp_path = output_path + ".temp.wav"
            speaker_ids = self._tts.hps.data.spk2id
            speaker = list(speaker_ids.keys())[0]

            self._tts.tts_to_file(
                text,
                speaker_ids[speaker],
                temp_path,
                speed=config.speed,
            )

            # Get source speaker embedding
            source_se = self._se_extractor.get_se(
                temp_path,
                self._tone_converter,
                vad=True,
            )[0]

            # Apply voice conversion
            self._tone_converter.convert(
                audio_src_path=temp_path,
                src_se=source_se,
                tgt_se=target_se,
                output_path=output_path,
            )

            # Clean up temp file
            os.remove(temp_path)

            return output_path

        await loop.run_in_executor(None, _clone_and_synthesize)

        duration = await self._get_audio_duration(output_path)

        return SynthesisResult(
            audio_path=output_path,
            text=text,
            duration=duration,
            voice_config=config,
            metadata={"cloned": True, "reference": reference_audio},
        )

    async def _get_audio_duration(self, audio_path: str) -> float:
        """Get the duration of an audio file."""
        try:
            import wave

            with wave.open(audio_path, "rb") as f:
                frames = f.getnframes()
                rate = f.getframerate()
                return frames / float(rate)
        except (ImportError, OSError, ValueError) as e:
            logger.debug("wave module failed to read audio duration, trying pydub: %s", e)
            try:
                from pydub import AudioSegment

                audio = AudioSegment.from_file(audio_path)
                return len(audio) / 1000.0
            except Exception as e2:
                logger.debug("pydub also failed to read audio duration: %s", e2)
                return 0.0

    def get_agent_voice(self, agent_code: str) -> VoiceConfig:
        """
        Get the voice configuration for an agent.

        Args:
            agent_code: Agent code (CEO, Keystone, etc.)

        Returns:
            VoiceConfig for the agent
        """
        return self._executive_voices.get(
            agent_code.upper(),
            VoiceConfig(),
        )

    def set_executive_voice(
        self,
        agent_code: str,
        config: VoiceConfig,
    ) -> None:
        """
        Set a custom voice configuration for an agent.

        Args:
            agent_code: Agent code
            config: Voice configuration
        """
        self._executive_voices[agent_code.upper()] = config

    async def synthesize_for_executive(
        self,
        text: str,
        agent_code: str,
        output_path: Optional[str] = None,
    ) -> SynthesisResult:
        """
        Synthesize speech using an agent's voice.

        Args:
            text: Text to synthesize
            agent_code: Agent code (CEO, Keystone, etc.)
            output_path: Optional output file path

        Returns:
            SynthesisResult
        """
        config = self.get_agent_voice(agent_code)
        return await self.synthesize(text, config, output_path)

    def list_available_voices(self) -> List[str]:
        """List available pre-defined voices."""
        voices = list(self._executive_voices.keys())

        # Add OpenVoice voices if available
        if hasattr(self, "_tts") and self._tts is not None:
            try:
                speaker_ids = self._tts.hps.data.spk2id
                voices.extend(list(speaker_ids.keys()))
            except Exception as e:
                logger.debug("Failed to enumerate OpenVoice speaker IDs: %s", e)

        return voices

    def list_supported_languages(self) -> List[str]:
        """List supported languages."""
        return ["en", "es", "fr", "zh", "ja", "ko"]

    async def batch_synthesize(
        self,
        texts: List[str],
        config: Optional[VoiceConfig] = None,
    ) -> List[SynthesisResult]:
        """
        Synthesize multiple texts.

        Args:
            texts: List of texts to synthesize
            config: Voice configuration (applied to all)

        Returns:
            List of SynthesisResults
        """
        tasks = [self.synthesize(text, config) for text in texts]
        return await asyncio.gather(*tasks)
