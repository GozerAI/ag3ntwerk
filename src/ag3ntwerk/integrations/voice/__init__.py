"""
Voice Integrations for ag3ntwerk.

This package provides integrations with voice/speech technologies:
- OpenVoice: Advanced text-to-speech with voice cloning
- Whisper: Speech-to-text transcription via Buzz
- ExpertiseExtractor: LLM-based insight extraction from transcripts
- AIInterviewer: Voice-guided interview with follow-up generation
"""

from ag3ntwerk.integrations.voice.openvoice import (
    OpenVoiceIntegration,
    VoiceConfig,
    VoiceStyle,
)
from ag3ntwerk.integrations.voice.whisper import (
    WhisperIntegration,
    TranscriptionConfig,
    TranscriptionResult,
)
from ag3ntwerk.integrations.voice.expertise_extractor import (
    ExpertiseExtractor,
    ExtractionResult,
)
from ag3ntwerk.integrations.voice.ai_interviewer import (
    AIInterviewer,
    InterviewScript,
    InterviewQuestion,
    InterviewSession,
    InterviewResult,
    InterviewAnswer,
    InterviewStatus,
)

__all__ = [
    "OpenVoiceIntegration",
    "VoiceConfig",
    "VoiceStyle",
    "WhisperIntegration",
    "TranscriptionConfig",
    "TranscriptionResult",
    "ExpertiseExtractor",
    "ExtractionResult",
    "AIInterviewer",
    "InterviewScript",
    "InterviewQuestion",
    "InterviewSession",
    "InterviewResult",
    "InterviewAnswer",
    "InterviewStatus",
]
