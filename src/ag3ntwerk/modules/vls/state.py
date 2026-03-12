"""
VLS State Management.

Manages persistence and retrieval of vertical launch states.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ag3ntwerk.modules.vls.core import LaunchStatus

logger = logging.getLogger(__name__)


# =============================================================================
# Launch State
# =============================================================================


@dataclass
class LaunchState:
    """Complete state of a vertical launch."""

    launch_id: str
    vertical_name: str
    status: LaunchStatus
    current_stage: int
    created_at: datetime
    updated_at: datetime

    # Stage execution results
    stage_results: Dict[str, Any] = field(default_factory=dict)

    # Gate validation results
    gate_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Evidence collected at each stage
    evidence: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)

    # Blueprint (populated after stage 3)
    blueprint: Optional[Dict[str, Any]] = None

    # Runtime metrics (ongoing)
    metrics: Dict[str, float] = field(default_factory=dict)

    # Stop-loss tracking
    stop_loss_violations: List[Dict[str, Any]] = field(default_factory=list)

    # Error tracking
    errors: List[Dict[str, Any]] = field(default_factory=list)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "launch_id": self.launch_id,
            "vertical_name": self.vertical_name,
            "status": self.status.value,
            "current_stage": self.current_stage,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "stage_results": self.stage_results,
            "gate_results": self.gate_results,
            "evidence": self.evidence,
            "blueprint": self.blueprint,
            "metrics": self.metrics,
            "stop_loss_violations": self.stop_loss_violations,
            "errors": self.errors,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LaunchState":
        """Deserialize from dictionary."""
        return cls(
            launch_id=data["launch_id"],
            vertical_name=data["vertical_name"],
            status=LaunchStatus(data["status"]),
            current_stage=data["current_stage"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            stage_results=data.get("stage_results", {}),
            gate_results=data.get("gate_results", {}),
            evidence=data.get("evidence", {}),
            blueprint=data.get("blueprint"),
            metrics=data.get("metrics", {}),
            stop_loss_violations=data.get("stop_loss_violations", []),
            errors=data.get("errors", []),
            metadata=data.get("metadata", {}),
        )

    def add_stage_result(self, stage_name: str, result: Any) -> None:
        """Add a stage execution result."""
        self.stage_results[stage_name] = result
        self.updated_at = datetime.now(timezone.utc)

    def add_gate_result(
        self,
        stage_name: str,
        status: str,
        score: float,
        evidence: List[Dict[str, Any]],
        failures: List[str],
    ) -> None:
        """Add a gate validation result."""
        self.gate_results[stage_name] = {
            "status": status,
            "score": score,
            "evidence": evidence,
            "failures": failures,
            "validated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.updated_at = datetime.now(timezone.utc)

    def add_evidence(self, stage_name: str, evidence_item: Dict[str, Any]) -> None:
        """Add evidence for a stage."""
        if stage_name not in self.evidence:
            self.evidence[stage_name] = []
        self.evidence[stage_name].append(evidence_item)
        self.updated_at = datetime.now(timezone.utc)

    def add_error(
        self, stage_name: str, error_message: str, error_details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add an error record."""
        error_record = {
            "stage": stage_name,
            "message": error_message,
            "details": error_details or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.errors.append(error_record)
        self.updated_at = datetime.now(timezone.utc)

    def record_stop_loss_violation(
        self,
        metric_name: str,
        current_value: float,
        threshold: float,
        severity: str = "warning",
    ) -> None:
        """Record a stop-loss threshold violation."""
        violation = {
            "metric": metric_name,
            "current_value": current_value,
            "threshold": threshold,
            "severity": severity,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.stop_loss_violations.append(violation)
        self.updated_at = datetime.now(timezone.utc)


# =============================================================================
# State Manager
# =============================================================================


class VLSStateManager:
    """Manages persistence and retrieval of VLS launch states."""

    def __init__(self, state_dir: Optional[Path] = None):
        """
        Initialize state manager.

        Args:
            state_dir: Directory for state files (default: ~/.ag3ntwerk/vls/launches)
        """
        if state_dir is None:
            state_dir = Path.home() / ".ag3ntwerk" / "vls" / "launches"

        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"VLS state directory: {self.state_dir}")

    def _get_state_file(self, launch_id: str) -> Path:
        """Get the path to a state file."""
        return self.state_dir / f"{launch_id}.json"

    def save_state(self, state: LaunchState) -> None:
        """
        Persist launch state to disk.

        Args:
            state: Launch state to save
        """
        state_file = self._get_state_file(state.launch_id)

        try:
            # Update timestamp
            state.updated_at = datetime.now(timezone.utc)

            # Write to file
            with open(state_file, "w") as f:
                json.dump(state.to_dict(), f, indent=2)

            logger.debug(f"Saved state for launch {state.launch_id}")

        except Exception as e:
            logger.error(f"Failed to save state for launch {state.launch_id}: {e}")
            raise

    def load_state(self, launch_id: str) -> Optional[LaunchState]:
        """
        Load launch state from disk.

        Args:
            launch_id: ID of the launch to load

        Returns:
            Launch state or None if not found
        """
        state_file = self._get_state_file(launch_id)

        if not state_file.exists():
            logger.warning(f"State file not found for launch {launch_id}")
            return None

        try:
            with open(state_file, "r") as f:
                data = json.load(f)

            state = LaunchState.from_dict(data)
            logger.debug(f"Loaded state for launch {launch_id}")
            return state

        except Exception as e:
            logger.error(f"Failed to load state for launch {launch_id}: {e}")
            raise

    def delete_state(self, launch_id: str) -> bool:
        """
        Delete a launch state.

        Args:
            launch_id: ID of the launch to delete

        Returns:
            True if deleted, False if not found
        """
        state_file = self._get_state_file(launch_id)

        if not state_file.exists():
            return False

        try:
            state_file.unlink()
            logger.info(f"Deleted state for launch {launch_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete state for launch {launch_id}: {e}")
            raise

    def list_launches(
        self,
        status: Optional[LaunchStatus] = None,
        vertical_name: Optional[str] = None,
    ) -> List[LaunchState]:
        """
        List all launches, optionally filtered.

        Args:
            status: Filter by launch status
            vertical_name: Filter by vertical name

        Returns:
            List of launch states
        """
        launches = []

        for state_file in self.state_dir.glob("*.json"):
            try:
                state = self.load_state(state_file.stem)

                if state is None:
                    continue

                # Apply filters
                if status and state.status != status:
                    continue

                if vertical_name and state.vertical_name != vertical_name:
                    continue

                launches.append(state)

            except Exception as e:
                logger.warning(f"Failed to load state file {state_file}: {e}")
                continue

        # Sort by creation date (newest first)
        launches.sort(key=lambda s: s.created_at, reverse=True)

        return launches

    def get_active_launches(self) -> List[LaunchState]:
        """Get all launches that are currently active (not stopped/failed/archived)."""
        active_statuses = [
            LaunchStatus.PENDING,
            LaunchStatus.STAGE_1_INTELLIGENCE,
            LaunchStatus.STAGE_2_VALIDATION,
            LaunchStatus.STAGE_3_BLUEPRINT,
            LaunchStatus.STAGE_4_BUILD,
            LaunchStatus.STAGE_5_INTAKE,
            LaunchStatus.STAGE_6_ACQUISITION,
            LaunchStatus.STAGE_7_ROUTING,
            LaunchStatus.STAGE_8_BILLING,
            LaunchStatus.STAGE_9_MONITORING,
            LaunchStatus.STAGE_10_KNOWLEDGE,
            LaunchStatus.LIVE,
            LaunchStatus.PAUSED,
        ]

        all_launches = self.list_launches()
        return [launch for launch in all_launches if launch.status in active_statuses]

    def create_new_launch(
        self, launch_id: str, vertical_name: str, metadata: Optional[Dict[str, Any]] = None
    ) -> LaunchState:
        """
        Create a new launch state.

        Args:
            launch_id: Unique identifier for the launch
            vertical_name: Name of the vertical
            metadata: Optional metadata

        Returns:
            New launch state
        """
        now = datetime.now(timezone.utc)

        state = LaunchState(
            launch_id=launch_id,
            vertical_name=vertical_name,
            status=LaunchStatus.PENDING,
            current_stage=0,
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
        )

        self.save_state(state)
        logger.info(f"Created new launch: {launch_id} ({vertical_name})")

        return state
