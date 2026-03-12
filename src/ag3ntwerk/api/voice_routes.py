"""
Voice Recording API routes for ag3ntwerk.

Provides endpoints for:
- Audio file upload and transcription
- Real-time recording status
- Whisper configuration
"""

import asyncio
import logging
import os
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel, Field

from ag3ntwerk.integrations.voice.whisper import (
    WhisperIntegration,
    TranscriptionConfig,
    TranscriptionResult,
    WhisperModel,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/voice", tags=["voice"])


# ============================================================
# Pydantic Models
# ============================================================


class TranscriptionRequest(BaseModel):
    """Request model for transcription settings."""

    model: str = Field(default="base", description="Whisper model size")
    language: Optional[str] = Field(default=None, description="Language code or auto-detect")


class TranscriptionResponse(BaseModel):
    """Response model for transcription result."""

    id: str
    text: str
    language: str
    duration: float
    segments_count: int
    status: str
    created_at: str


class WhisperStatusResponse(BaseModel):
    """Response model for Whisper status."""

    available: bool
    backend: Optional[str]
    models_available: list
    default_model: str


# ============================================================
# In-Memory Storage
# ============================================================

_transcriptions: Dict[str, Dict[str, Any]] = {}
_transcription_counter = 0

# Whisper integration instance
_whisper: Optional[WhisperIntegration] = None
_whisper_init_lock = asyncio.Lock()


def _get_whisper() -> WhisperIntegration:
    """Get or create Whisper integration instance (sync fast-path)."""
    global _whisper
    if _whisper is None:
        _whisper = WhisperIntegration()
    return _whisper


async def _get_whisper_async() -> WhisperIntegration:
    """Get or create Whisper integration instance with async lock."""
    global _whisper
    if _whisper is None:
        async with _whisper_init_lock:
            if _whisper is None:
                _whisper = WhisperIntegration()
    return _whisper


def _get_transcription_id() -> str:
    """Generate a unique transcription ID."""
    global _transcription_counter
    _transcription_counter += 1
    return f"trans_{_transcription_counter:06d}"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ============================================================
# Status Endpoints
# ============================================================


@router.get("/status")
async def get_voice_status() -> Dict[str, Any]:
    """Get the status of voice/transcription services."""
    whisper = await _get_whisper_async()

    try:
        is_available = whisper.is_available()
        backend = whisper.backend if hasattr(whisper, "backend") else "unknown"
    except Exception as e:
        logger.warning(f"Failed to check Whisper availability: {e}")
        is_available = False
        backend = None

    return {
        "whisper": {
            "available": is_available,
            "backend": backend,
            "default_model": "base",
        },
        "supported_formats": ["wav", "mp3", "ogg", "webm", "m4a", "flac"],
        "max_file_size_mb": 25,
    }


# ============================================================
# Transcription Endpoints
# ============================================================


@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    model: str = Form(default="base"),
    language: Optional[str] = Form(default=None),
) -> Dict[str, Any]:
    """
    Transcribe an uploaded audio file.

    Accepts audio in various formats (wav, mp3, ogg, webm, m4a, flac).
    Returns the transcription result immediately.
    """
    whisper = await _get_whisper_async()

    # Validate file type
    allowed_types = [
        "audio/wav",
        "audio/mpeg",
        "audio/mp3",
        "audio/ogg",
        "audio/webm",
        "audio/x-m4a",
        "audio/flac",
        "audio/x-wav",
    ]

    # Be flexible with content types (browsers may send different types)
    content_type = audio.content_type or ""
    filename = audio.filename or "audio.wav"
    ext = Path(filename).suffix.lower()

    if ext not in [".wav", ".mp3", ".ogg", ".webm", ".m4a", ".flac"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {ext}. Supported: wav, mp3, ogg, webm, m4a, flac",
        )

    # Create temp file with proper extension
    temp_dir = tempfile.gettempdir()
    temp_path = Path(temp_dir) / f"audio_{_get_transcription_id()}{ext}"

    try:
        # Save uploaded file
        content = await audio.read()

        # Check file size (25MB limit)
        if len(content) > 25 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="Audio file too large. Maximum size is 25MB.",
            )

        with open(temp_path, "wb") as f:
            f.write(content)

        # Configure transcription
        try:
            model_enum = WhisperModel(model)
        except ValueError:
            model_enum = WhisperModel.BASE

        config = TranscriptionConfig(
            model=model_enum,
            language=language,
        )

        # Check if Whisper is available
        if not whisper.is_available():
            raise HTTPException(
                status_code=503,
                detail="Whisper transcription service is not available. Please install openai-whisper or configure Buzz.",
            )

        # Perform transcription
        result = await whisper.transcribe(str(temp_path), config)

        # Store result
        trans_id = _get_transcription_id()
        _transcriptions[trans_id] = {
            "id": trans_id,
            "result": result,
            "created_at": _utcnow().isoformat(),
            "status": "completed",
        }

        return {
            "id": trans_id,
            "text": result.text,
            "language": result.language,
            "duration": result.duration,
            "segments_count": len(result.segments),
            "segments": [
                {
                    "start": s.start,
                    "end": s.end,
                    "text": s.text,
                }
                for s in result.segments
            ],
            "status": "completed",
            "created_at": _transcriptions[trans_id]["created_at"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}",
        )
    finally:
        # Clean up temp file
        if temp_path.exists():
            try:
                os.remove(temp_path)
            except Exception as e:
                logger.warning(f"Failed to clean up temp file: {e}")


@router.get("/transcriptions")
async def list_transcriptions() -> Dict[str, Any]:
    """List recent transcriptions."""
    transcriptions = [
        {
            "id": t["id"],
            "text_preview": (
                t["result"].text[:100] + "..." if len(t["result"].text) > 100 else t["result"].text
            ),
            "language": t["result"].language,
            "duration": t["result"].duration,
            "status": t["status"],
            "created_at": t["created_at"],
        }
        for t in _transcriptions.values()
    ]
    return {"transcriptions": transcriptions, "count": len(transcriptions)}


@router.get("/transcriptions/{trans_id}")
async def get_transcription(trans_id: str) -> Dict[str, Any]:
    """Get a specific transcription result."""
    trans = _transcriptions.get(trans_id)
    if not trans:
        raise HTTPException(status_code=404, detail="Transcription not found")

    result = trans["result"]
    return {
        "id": trans_id,
        "text": result.text,
        "language": result.language,
        "duration": result.duration,
        "segments": [
            {
                "id": s.id,
                "start": s.start,
                "end": s.end,
                "text": s.text,
            }
            for s in result.segments
        ],
        "status": trans["status"],
        "created_at": trans["created_at"],
    }


# ============================================================
# Interview Audio Integration
# ============================================================


@router.post("/transcribe-for-interview")
async def transcribe_for_interview(
    audio: UploadFile = File(...),
    session_id: str = Form(...),
) -> Dict[str, Any]:
    """
    Transcribe audio specifically for an interview session.

    This endpoint transcribes the audio and returns the text
    ready to be submitted as an interview answer.
    """
    # First transcribe the audio
    result = await transcribe_audio(audio=audio, model="base")

    return {
        "session_id": session_id,
        "transcription_id": result["id"],
        "text": result["text"],
        "duration": result["duration"],
        "ready_for_submission": True,
    }
