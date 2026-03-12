"""
Interview Management API routes for ag3ntwerk.

Provides endpoints for managing AI-guided interviews:
- Create and manage interview scripts
- Start/stop interview sessions
- Process answers (text or audio)
- View session history and results
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field

from ag3ntwerk.integrations.voice.ai_interviewer import (
    AIInterviewer,
    InterviewScript,
    InterviewQuestion,
    InterviewSession,
    InterviewResult,
    InterviewStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/interviews", tags=["interviews"])


# ============================================================
# Pydantic Models
# ============================================================


class QuestionCreate(BaseModel):
    """Request model for creating a question."""

    text: str = Field(..., min_length=5, max_length=500)
    topic: str = Field(default="")


class ScriptCreate(BaseModel):
    """Request model for creating an interview script."""

    topic: str = Field(..., min_length=3, max_length=200)
    description: str = Field(default="")
    questions: List[QuestionCreate] = Field(..., min_length=1, max_length=20)
    max_followups_per_question: int = Field(default=2, ge=0, le=5)


class AnswerSubmit(BaseModel):
    """Request model for submitting a text answer."""

    text: str = Field(..., min_length=1, max_length=10000)


class SessionResponse(BaseModel):
    """Response model for interview session."""

    id: str
    topic: str
    status: str
    current_question_index: int
    total_questions: int
    current_question: Optional[str]
    progress: float
    answers_count: int
    started_at: Optional[str]
    completed_at: Optional[str]


class ResultResponse(BaseModel):
    """Response model for interview result."""

    session_id: str
    topic: str
    answers_count: int
    transcript_preview: str
    duration_seconds: float
    insights_summary: Optional[Dict[str, Any]]


# ============================================================
# In-Memory Storage (replace with database in production)
# ============================================================

_scripts: Dict[str, InterviewScript] = {}
_sessions: Dict[str, InterviewSession] = {}
_results: Dict[str, InterviewResult] = {}
_script_counter = 0

# Shared interviewer instance (initialized without Whisper/Extractor for now)
_interviewer = AIInterviewer()


def _get_script_id() -> str:
    """Generate a unique script ID."""
    global _script_counter
    _script_counter += 1
    return f"script_{_script_counter:04d}"


# ============================================================
# Script Endpoints
# ============================================================


@router.get("/scripts")
async def list_scripts() -> Dict[str, Any]:
    """List all interview scripts."""
    scripts = []
    for script_id, script in _scripts.items():
        scripts.append(
            {
                "id": script_id,
                "topic": script.topic,
                "description": script.description,
                "question_count": len(script.questions),
            }
        )
    return {"scripts": scripts, "count": len(scripts)}


@router.post("/scripts")
async def create_script(script_data: ScriptCreate) -> Dict[str, Any]:
    """Create a new interview script."""
    script_id = _get_script_id()

    questions = [InterviewQuestion(text=q.text, topic=q.topic) for q in script_data.questions]

    script = InterviewScript(
        topic=script_data.topic,
        description=script_data.description,
        questions=questions,
        max_followups_per_question=script_data.max_followups_per_question,
    )

    _scripts[script_id] = script

    logger.info(f"Created interview script: {script_id} - {script.topic}")

    return {
        "id": script_id,
        "topic": script.topic,
        "description": script.description,
        "question_count": len(questions),
    }


@router.get("/scripts/{script_id}")
async def get_script(script_id: str) -> Dict[str, Any]:
    """Get a specific interview script."""
    script = _scripts.get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    return {
        "id": script_id,
        "topic": script.topic,
        "description": script.description,
        "questions": [{"text": q.text, "topic": q.topic} for q in script.questions],
        "max_followups_per_question": script.max_followups_per_question,
    }


@router.delete("/scripts/{script_id}")
async def delete_script(script_id: str) -> Dict[str, Any]:
    """Delete an interview script."""
    if script_id not in _scripts:
        raise HTTPException(status_code=404, detail="Script not found")

    del _scripts[script_id]
    return {"success": True, "deleted": script_id}


# ============================================================
# Session Endpoints
# ============================================================


def _session_to_response(session: InterviewSession) -> Dict[str, Any]:
    """Convert session to response dict."""
    current_q = session.current_question
    return {
        "id": session.id,
        "topic": session.script.topic,
        "status": session.status.value,
        "current_question_index": session.current_question_index,
        "total_questions": len(session.all_questions),
        "current_question": current_q.text if current_q else None,
        "progress": session.progress,
        "answers_count": len(session.answers),
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
    }


@router.get("/sessions")
async def list_sessions() -> Dict[str, Any]:
    """List all interview sessions."""
    sessions = [_session_to_response(s) for s in _sessions.values()]
    return {"sessions": sessions, "count": len(sessions)}


@router.post("/sessions")
async def start_session(script_id: str = Form(...)) -> Dict[str, Any]:
    """Start a new interview session from a script."""
    script = _scripts.get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    session = await _interviewer.start_session(script)
    _sessions[session.id] = session

    logger.info(f"Started interview session: {session.id}")

    return _session_to_response(session)


@router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> Dict[str, Any]:
    """Get interview session details."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    response = _session_to_response(session)
    response["answers"] = [
        {
            "question_index": a.question_index,
            "question_text": a.question_text,
            "transcript_preview": (
                a.transcript_text[:200] + "..."
                if len(a.transcript_text) > 200
                else a.transcript_text
            ),
            "duration_seconds": a.duration_seconds,
        }
        for a in session.answers
    ]

    return response


@router.post("/sessions/{session_id}/answer")
async def submit_answer(session_id: str, answer: AnswerSubmit) -> Dict[str, Any]:
    """Submit a text answer to the current question."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != InterviewStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=400,
            detail=f"Session is {session.status.value}, not in_progress",
        )

    session = await _interviewer.process_answer(session, text=answer.text)
    _sessions[session_id] = session

    return _session_to_response(session)


@router.post("/sessions/{session_id}/answer/audio")
async def submit_audio_answer(
    session_id: str,
    audio: UploadFile = File(...),
) -> Dict[str, Any]:
    """Submit an audio answer to be transcribed."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != InterviewStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=400,
            detail=f"Session is {session.status.value}, not in_progress",
        )

    # For now, audio answers are not supported without Whisper
    # This endpoint is a placeholder for future integration
    raise HTTPException(
        status_code=501,
        detail="Audio transcription not yet configured. Please submit text answers.",
    )


@router.post("/sessions/{session_id}/finish")
async def finish_session(session_id: str) -> Dict[str, Any]:
    """Finish an interview session and extract insights."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    result = await _interviewer.finish_session(session)
    _results[session_id] = result

    # Update session status
    _sessions[session_id] = session

    return {
        "session_id": result.session_id,
        "topic": result.topic,
        "answers_count": len(result.answers),
        "transcript_preview": (
            result.full_transcript[:500] + "..."
            if len(result.full_transcript) > 500
            else result.full_transcript
        ),
        "duration_seconds": result.duration_seconds,
        "insights_summary": result.insights.to_dict() if result.insights else None,
        "metadata": result.metadata,
    }


@router.post("/sessions/{session_id}/cancel")
async def cancel_session(session_id: str) -> Dict[str, Any]:
    """Cancel an in-progress interview session."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session = await _interviewer.cancel_session(session)
    _sessions[session_id] = session

    return _session_to_response(session)


# ============================================================
# Results Endpoints
# ============================================================


@router.get("/results")
async def list_results() -> Dict[str, Any]:
    """List all interview results."""
    results = [
        {
            "session_id": r.session_id,
            "topic": r.topic,
            "answers_count": len(r.answers),
            "duration_seconds": r.duration_seconds,
        }
        for r in _results.values()
    ]
    return {"results": results, "count": len(results)}


@router.get("/results/{session_id}")
async def get_result(session_id: str) -> Dict[str, Any]:
    """Get the full result of a completed interview."""
    result = _results.get(session_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Result not found. The session may not be finished yet.",
        )

    return {
        "session_id": result.session_id,
        "topic": result.topic,
        "answers": [
            {
                "question_index": a.question_index,
                "question_text": a.question_text,
                "transcript_text": a.transcript_text,
                "duration_seconds": a.duration_seconds,
            }
            for a in result.answers
        ],
        "full_transcript": result.full_transcript,
        "duration_seconds": result.duration_seconds,
        "insights": result.insights.to_dict() if result.insights else None,
        "metadata": result.metadata,
    }


@router.get("/results/{session_id}/transcript")
async def get_transcript(session_id: str) -> Dict[str, Any]:
    """Get just the transcript from an interview."""
    result = _results.get(session_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")

    return {
        "session_id": result.session_id,
        "topic": result.topic,
        "transcript": result.full_transcript,
    }
