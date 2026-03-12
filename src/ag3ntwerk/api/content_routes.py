"""
Content Pipeline API routes for ag3ntwerk.

Provides endpoints for monitoring and managing the content pipeline:
- Content pieces (articles, social posts, etc.)
- Pipeline executions
- Distribution status
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ag3ntwerk.models.content import ContentFormat, ContentPiece

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/content", tags=["content"])


# ============================================================
# Pydantic Models
# ============================================================


class ContentCreate(BaseModel):
    """Request model for creating content."""

    title: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1)
    format: ContentFormat = ContentFormat.ARTICLE
    summary: str = Field(default="", max_length=500)
    tags: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)


class PipelineExecutionCreate(BaseModel):
    """Request model for starting a content pipeline."""

    campaign: str = Field(..., min_length=1, max_length=200)
    audience: str = Field(default="")
    channels: List[str] = Field(default_factory=list)
    content_types: List[str] = Field(default_factory=list)


class DistributionUpdate(BaseModel):
    """Request model for updating distribution status."""

    platform: str = Field(..., min_length=1)
    status: str = Field(..., pattern="^(pending|in_progress|completed|failed)$")


# ============================================================
# In-Memory Storage
# ============================================================

_content_pieces: Dict[str, ContentPiece] = {}
_pipeline_executions: Dict[str, Dict[str, Any]] = {}
_distribution_history: List[Dict[str, Any]] = []


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ============================================================
# Content Endpoints
# ============================================================


@router.get("/pieces")
async def list_content_pieces(
    format: Optional[ContentFormat] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """List all content pieces, optionally filtered by format."""
    pieces = list(_content_pieces.values())

    if format:
        pieces = [p for p in pieces if p.format == format]

    # Sort by created_at descending
    pieces.sort(key=lambda p: p.created_at, reverse=True)

    return {
        "content": [p.model_dump() for p in pieces[:limit]],
        "count": len(pieces[:limit]),
        "total": len(_content_pieces),
    }


@router.post("/pieces")
async def create_content_piece(content_data: ContentCreate) -> Dict[str, Any]:
    """Create a new content piece."""
    piece_id = f"content_{uuid4().hex[:8]}"

    piece = ContentPiece(
        id=piece_id,
        title=content_data.title,
        body=content_data.body,
        format=content_data.format,
        summary=content_data.summary,
        tags=content_data.tags,
        keywords=content_data.keywords,
    )

    _content_pieces[piece_id] = piece

    logger.info(f"Created content piece: {piece_id}")

    return piece.model_dump()


@router.get("/pieces/{piece_id}")
async def get_content_piece(piece_id: str) -> Dict[str, Any]:
    """Get a specific content piece."""
    piece = _content_pieces.get(piece_id)
    if not piece:
        raise HTTPException(status_code=404, detail="Content piece not found")
    return piece.model_dump()


@router.delete("/pieces/{piece_id}")
async def delete_content_piece(piece_id: str) -> Dict[str, Any]:
    """Delete a content piece."""
    if piece_id not in _content_pieces:
        raise HTTPException(status_code=404, detail="Content piece not found")

    del _content_pieces[piece_id]
    return {"success": True, "deleted": piece_id}


@router.post("/pieces/{piece_id}/distribute")
async def distribute_content(
    piece_id: str,
    platform: str,
) -> Dict[str, Any]:
    """Mark content as distributed to a platform."""
    piece = _content_pieces.get(piece_id)
    if not piece:
        raise HTTPException(status_code=404, detail="Content piece not found")

    if platform not in piece.published_platforms:
        piece.published_platforms.append(platform)

    _distribution_history.append(
        {
            "content_id": piece_id,
            "platform": platform,
            "timestamp": _utcnow().isoformat(),
            "status": "completed",
        }
    )

    return {
        "success": True,
        "content_id": piece_id,
        "platform": platform,
        "published_platforms": piece.published_platforms,
    }


# ============================================================
# Pipeline Endpoints
# ============================================================


@router.get("/pipeline/executions")
async def list_pipeline_executions() -> Dict[str, Any]:
    """List all pipeline executions."""
    executions = list(_pipeline_executions.values())
    executions.sort(key=lambda e: e.get("started_at", ""), reverse=True)
    return {"executions": executions, "count": len(executions)}


@router.post("/pipeline/start")
async def start_pipeline(params: PipelineExecutionCreate) -> Dict[str, Any]:
    """Start a content distribution pipeline."""
    execution_id = f"pipeline_{uuid4().hex[:8]}"

    execution = {
        "id": execution_id,
        "campaign": params.campaign,
        "audience": params.audience,
        "channels": params.channels,
        "content_types": params.content_types,
        "status": "in_progress",
        "current_step": "content_planning",
        "steps": [
            {"name": "content_planning", "status": "in_progress", "agent": "Echo"},
            {"name": "content_creation", "status": "pending", "agent": "Echo"},
            {"name": "product_alignment_check", "status": "pending", "agent": "Blueprint"},
            {"name": "distribution", "status": "pending", "agent": "Echo"},
        ],
        "started_at": _utcnow().isoformat(),
        "completed_at": None,
        "content_created": 0,
        "content_distributed": 0,
    }

    _pipeline_executions[execution_id] = execution

    logger.info(f"Started content pipeline: {execution_id}")

    return execution


@router.get("/pipeline/executions/{execution_id}")
async def get_pipeline_execution(execution_id: str) -> Dict[str, Any]:
    """Get pipeline execution details."""
    execution = _pipeline_executions.get(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Pipeline execution not found")
    return execution


@router.post("/pipeline/executions/{execution_id}/advance")
async def advance_pipeline(execution_id: str) -> Dict[str, Any]:
    """Advance the pipeline to the next step (for testing/demo)."""
    execution = _pipeline_executions.get(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Pipeline execution not found")

    if execution["status"] != "in_progress":
        raise HTTPException(status_code=400, detail="Pipeline is not in progress")

    steps = execution["steps"]
    current_step_idx = next(
        (i for i, s in enumerate(steps) if s["status"] == "in_progress"),
        -1,
    )

    if current_step_idx >= 0:
        # Complete current step
        steps[current_step_idx]["status"] = "completed"

        # Start next step or complete pipeline
        if current_step_idx + 1 < len(steps):
            steps[current_step_idx + 1]["status"] = "in_progress"
            execution["current_step"] = steps[current_step_idx + 1]["name"]
        else:
            execution["status"] = "completed"
            execution["current_step"] = None
            execution["completed_at"] = _utcnow().isoformat()

    return execution


@router.post("/pipeline/executions/{execution_id}/cancel")
async def cancel_pipeline(execution_id: str) -> Dict[str, Any]:
    """Cancel a pipeline execution."""
    execution = _pipeline_executions.get(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Pipeline execution not found")

    execution["status"] = "cancelled"
    execution["completed_at"] = _utcnow().isoformat()

    return execution


# ============================================================
# Distribution History
# ============================================================


@router.get("/distribution/history")
async def get_distribution_history(limit: int = 50) -> Dict[str, Any]:
    """Get content distribution history."""
    history = _distribution_history[-limit:][::-1]  # Most recent first
    return {"history": history, "count": len(history)}


# ============================================================
# Stats Endpoint
# ============================================================


@router.get("/stats")
async def get_content_stats() -> Dict[str, Any]:
    """Get content pipeline statistics."""
    pieces = list(_content_pieces.values())

    # Count by format
    format_counts = {}
    for piece in pieces:
        format_name = piece.format.value
        format_counts[format_name] = format_counts.get(format_name, 0) + 1

    # Distribution stats
    total_distributed = sum(len(p.published_platforms) for p in pieces)
    platforms_used = set()
    for piece in pieces:
        platforms_used.update(piece.published_platforms)

    # Pipeline stats
    executions = list(_pipeline_executions.values())
    active_pipelines = len([e for e in executions if e["status"] == "in_progress"])
    completed_pipelines = len([e for e in executions if e["status"] == "completed"])

    return {
        "content": {
            "total_pieces": len(pieces),
            "by_format": format_counts,
        },
        "distribution": {
            "total_distributions": total_distributed,
            "platforms_used": list(platforms_used),
            "recent_count": len(_distribution_history[-24:]),
        },
        "pipeline": {
            "total_executions": len(executions),
            "active": active_pipelines,
            "completed": completed_pipelines,
        },
    }
