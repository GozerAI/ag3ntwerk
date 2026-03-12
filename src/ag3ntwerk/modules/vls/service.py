"""
VLS Service Interface.

Provides the agent-facing API for the Vertical Launch System.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ag3ntwerk.modules.vls.core import (
    LaunchStatus,
    NicheCandidate,
    status_from_stage_number,
    stage_number_from_status,
)
from ag3ntwerk.modules.vls.state import LaunchState, VLSStateManager
from ag3ntwerk.modules.vls.gates import get_gate, GateStatus
from ag3ntwerk.modules.vls.evidence import EvidenceCollector

logger = logging.getLogger(__name__)


class VLSService:
    """
    Vertical Launch System Service.

    Provides high-level interface for launching and managing verticals.
    """

    def __init__(self, state_manager: Optional[VLSStateManager] = None):
        """
        Initialize VLS service.

        Args:
            state_manager: State manager (creates default if not provided)
        """
        self.state_manager = state_manager or VLSStateManager()
        logger.info("VLS Service initialized")

    async def launch_vertical(
        self,
        vertical_name: str,
        constraints: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Launch a new vertical through the VLS pipeline.

        Args:
            vertical_name: Name of the vertical to launch
            constraints: Optional constraints (budget, metros, etc.)
            metadata: Optional metadata

        Returns:
            Launch ID
        """
        # Generate unique launch ID
        launch_id = str(uuid.uuid4())

        # Create launch state
        state = self.state_manager.create_new_launch(
            launch_id=launch_id,
            vertical_name=vertical_name,
            metadata={
                **(metadata or {}),
                "constraints": constraints or {},
                "launched_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        logger.info(f"Launched vertical: {vertical_name} (ID: {launch_id})")

        return launch_id

    async def get_launch_status(self, launch_id: str) -> Dict[str, Any]:
        """
        Get current status of a launch.

        Args:
            launch_id: Launch identifier

        Returns:
            Status dictionary with current stage, metrics, and next actions
        """
        state = self.state_manager.load_state(launch_id)

        if not state:
            return {
                "error": "Launch not found",
                "launch_id": launch_id,
            }

        return {
            "launch_id": state.launch_id,
            "vertical_name": state.vertical_name,
            "status": state.status.value,
            "current_stage": state.current_stage,
            "stage_name": self._get_stage_name(state.current_stage),
            "created_at": state.created_at.isoformat(),
            "updated_at": state.updated_at.isoformat(),
            "metrics": state.metrics,
            "blueprint": state.blueprint,
            "stop_loss_violations": state.stop_loss_violations,
            "errors": state.errors,
            "metadata": state.metadata,
        }

    async def pause_launch(self, launch_id: str, reason: Optional[str] = None) -> bool:
        """
        Pause an active launch.

        Args:
            launch_id: Launch identifier
            reason: Optional reason for pausing

        Returns:
            True if paused, False if not found or already stopped
        """
        state = self.state_manager.load_state(launch_id)

        if not state:
            logger.warning(f"Cannot pause launch {launch_id}: not found")
            return False

        if state.status in [LaunchStatus.STOPPED, LaunchStatus.FAILED, LaunchStatus.ARCHIVED]:
            logger.warning(
                f"Cannot pause launch {launch_id}: already in terminal state {state.status}"
            )
            return False

        state.status = LaunchStatus.PAUSED
        state.metadata["paused_at"] = datetime.now(timezone.utc).isoformat()
        if reason:
            state.metadata["pause_reason"] = reason

        self.state_manager.save_state(state)
        logger.info(f"Paused launch {launch_id}: {reason}")

        return True

    async def resume_launch(self, launch_id: str) -> bool:
        """
        Resume a paused launch.

        Args:
            launch_id: Launch identifier

        Returns:
            True if resumed, False if not found or not paused
        """
        state = self.state_manager.load_state(launch_id)

        if not state:
            logger.warning(f"Cannot resume launch {launch_id}: not found")
            return False

        if state.status != LaunchStatus.PAUSED:
            logger.warning(
                f"Cannot resume launch {launch_id}: not in paused state (current: {state.status})"
            )
            return False

        # Restore to appropriate stage status
        state.status = status_from_stage_number(state.current_stage)
        state.metadata["resumed_at"] = datetime.now(timezone.utc).isoformat()

        self.state_manager.save_state(state)
        logger.info(f"Resumed launch {launch_id}")

        return True

    async def abort_launch(self, launch_id: str, reason: Optional[str] = None) -> bool:
        """
        Abort a launch (terminal action).

        Args:
            launch_id: Launch identifier
            reason: Optional reason for aborting

        Returns:
            True if aborted, False if not found
        """
        state = self.state_manager.load_state(launch_id)

        if not state:
            logger.warning(f"Cannot abort launch {launch_id}: not found")
            return False

        state.status = LaunchStatus.STOPPED
        state.metadata["aborted_at"] = datetime.now(timezone.utc).isoformat()
        if reason:
            state.metadata["abort_reason"] = reason

        state.add_error(
            stage_name=self._get_stage_name(state.current_stage),
            error_message=f"Launch aborted: {reason or 'manual abort'}",
        )

        self.state_manager.save_state(state)
        logger.warning(f"Aborted launch {launch_id}: {reason}")

        return True

    async def validate_stage_gate(
        self,
        launch_id: str,
        stage_name: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validate a stage gate.

        Args:
            launch_id: Launch identifier
            stage_name: Stage to validate
            context: Stage results and evidence

        Returns:
            Gate validation result
        """
        state = self.state_manager.load_state(launch_id)

        if not state:
            return {"error": "Launch not found"}

        # Get gate validator
        try:
            gate = get_gate(stage_name)
        except KeyError:
            return {"error": f"No gate defined for stage: {stage_name}"}

        # Validate gate
        result = gate.validate(context)

        # Save gate result to state
        state.add_gate_result(
            stage_name=stage_name,
            status=result.status.value,
            score=result.score,
            evidence=[
                {
                    "type": e.evidence_type,
                    "value": e.value,
                    "weight": e.weight,
                    "source": e.source,
                    "confidence": e.confidence,
                }
                for e in result.evidence
            ],
            failures=result.failures,
        )

        self.state_manager.save_state(state)

        return {
            "status": result.status.value,
            "score": result.score,
            "passed": result.status == GateStatus.PASS,
            "pass_threshold": result.pass_threshold,
            "failures": result.failures,
            "warnings": result.warnings,
            "recommendation": result.recommendation,
        }

    async def list_launches(
        self,
        status: Optional[LaunchStatus] = None,
        vertical_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List all launches with optional filtering.

        Args:
            status: Filter by status
            vertical_name: Filter by vertical name

        Returns:
            List of launch summaries
        """
        launches = self.state_manager.list_launches(status=status, vertical_name=vertical_name)

        return [
            {
                "launch_id": launch.launch_id,
                "vertical_name": launch.vertical_name,
                "status": launch.status.value,
                "current_stage": launch.current_stage,
                "stage_name": self._get_stage_name(launch.current_stage),
                "created_at": launch.created_at.isoformat(),
                "updated_at": launch.updated_at.isoformat(),
                "has_errors": len(launch.errors) > 0,
                "stop_loss_violations": len(launch.stop_loss_violations),
            }
            for launch in launches
        ]

    async def get_active_launches(self) -> List[Dict[str, Any]]:
        """Get all active launches."""
        active_launches = self.state_manager.get_active_launches()

        return [
            {
                "launch_id": launch.launch_id,
                "vertical_name": launch.vertical_name,
                "status": launch.status.value,
                "current_stage": launch.current_stage,
                "created_at": launch.created_at.isoformat(),
            }
            for launch in active_launches
        ]

    async def get_agent_report(self, agent_code: str) -> Dict[str, Any]:
        """
        Generate agent-tailored report.

        Args:
            agent_code: Agent requesting the report

        Returns:
            Agent-specific VLS report
        """
        active_launches = self.state_manager.get_active_launches()

        # Get all launches
        all_launches = self.state_manager.list_launches()

        # Agent-specific insights
        report = {
            "module": "vls",
            "agent": agent_code,
            "summary": {
                "total_launches": len(all_launches),
                "active_launches": len(active_launches),
                "live_verticals": len([l for l in all_launches if l.status == LaunchStatus.LIVE]),
                "failed_launches": len(
                    [l for l in all_launches if l.status == LaunchStatus.FAILED]
                ),
            },
            "active_launches": [
                {
                    "launch_id": launch.launch_id,
                    "vertical_name": launch.vertical_name,
                    "status": launch.status.value,
                    "current_stage": launch.current_stage,
                    "stage_name": self._get_stage_name(launch.current_stage),
                }
                for launch in active_launches[:5]  # Limit to 5 most recent
            ],
        }

        # Add agent-specific sections
        if agent_code in ["Echo", "Blueprint", "Compass"]:
            # Market intelligence focus
            report["market_intelligence"] = {
                "pending_validation": len(
                    [l for l in active_launches if l.status == LaunchStatus.STAGE_1_INTELLIGENCE]
                ),
            }

        elif agent_code in ["Keystone", "Vector"]:
            # Financial focus
            total_revenue = sum(
                launch.metrics.get("total_revenue", 0)
                for launch in all_launches
                if launch.status == LaunchStatus.LIVE
            )
            report["financial"] = {
                "total_revenue": total_revenue,
                "live_verticals": len([l for l in all_launches if l.status == LaunchStatus.LIVE]),
            }

        elif agent_code in ["Forge", "Foundry"]:
            # Infrastructure focus
            report["infrastructure"] = {
                "deployments_in_progress": len(
                    [l for l in active_launches if l.status == LaunchStatus.STAGE_4_BUILD]
                ),
            }

        elif agent_code in ["Aegis", "Citadel"]:
            # Risk focus
            all_violations = sum(len(launch.stop_loss_violations) for launch in all_launches)
            report["risk"] = {
                "total_stop_loss_violations": all_violations,
                "launches_with_violations": len(
                    [l for l in all_launches if l.stop_loss_violations]
                ),
            }

        return report

    def _get_stage_name(self, stage_number: int) -> str:
        """Get human-readable stage name."""
        stage_names = {
            0: "Pending",
            1: "Market Intelligence",
            2: "Validation & Economics",
            3: "Blueprint Definition",
            4: "Build & Deployment",
            5: "Lead Intake",
            6: "Buyer Acquisition",
            7: "Routing & Delivery",
            8: "Billing & Revenue",
            9: "Monitoring & Stop-Loss",
            10: "Knowledge Capture",
            11: "Live",
        }
        return stage_names.get(stage_number, f"Stage {stage_number}")
