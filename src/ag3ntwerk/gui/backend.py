"""
ag3ntwerk GUI Backend - Connects dashboard to Nexus.

Provides async bridge for Qt and real-time task management.
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from threading import Thread
from queue import Queue

from PySide6.QtCore import QObject, Signal, QTimer

logger = logging.getLogger(__name__)


@dataclass
class GUITask:
    """Task representation for the GUI."""

    id: str
    description: str
    task_type: str
    assigned_to: str
    status: str  # pending, in_progress, completed, failed
    created_at: datetime = field(default_factory=datetime.now)
    result: Optional[str] = None
    error: Optional[str] = None


class AsyncBridge(QObject):
    """
    Bridge between Qt's event loop and asyncio.

    Allows running async operations from Qt and emitting signals
    when operations complete.
    """

    # Signals for async operation results
    task_completed = Signal(str, object)  # task_id, result
    task_failed = Signal(str, str)  # task_id, error
    status_updated = Signal(dict)  # status dict
    message_received = Signal(str, str)  # sender, message
    connection_changed = Signal(bool, str)  # connected, provider_name

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[Thread] = None
        self._running = False
        self._pending_tasks: Queue = Queue()

    def start(self):
        """Start the async event loop in a background thread."""
        if self._running:
            return

        self._running = True
        self._thread = Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the async event loop."""
        self._running = False
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=2.0)

    def _run_loop(self):
        """Run the asyncio event loop in background thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        try:
            self._loop.run_forever()
        finally:
            self._loop.close()

    def run_async(self, coro, callback: Optional[Callable] = None):
        """
        Run an async coroutine from Qt.

        Args:
            coro: Coroutine to run
            callback: Optional callback when complete
        """
        if not self._loop or not self._running:
            logger.warning("Async bridge not running")
            return

        def done_callback(future):
            try:
                result = future.result()
                if callback:
                    # Schedule callback in Qt's thread
                    QTimer.singleShot(0, lambda: callback(result))
            except Exception as e:
                logger.error(f"Async operation failed: {e}")
                if callback:
                    QTimer.singleShot(0, lambda: callback(None))

        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        future.add_done_callback(done_callback)
        return future


class CSuiteBackend(QObject):
    """
    Backend connector for ag3ntwerk Dashboard.

    Manages:
    - LLM provider connection
    - Nexus instance and agent registry
    - Task submission and tracking
    - Real-time status updates
    """

    # Signals
    connected = Signal(bool, str)  # success, message
    task_created = Signal(dict)  # task info
    task_updated = Signal(dict)  # task info
    tasks_refreshed = Signal(list)  # all tasks
    coo_response = Signal(str)  # response text
    agent_status = Signal(dict)  # agent status dict
    metacognition_status = Signal(dict)  # metacognition stats
    drift_alerts = Signal(list)  # list of drift alert dicts
    coherence_data = Signal(list)  # list of coherence report dicts
    trend_data = Signal(dict)  # trend summary dict
    team_data = Signal(dict)  # team stats + pairs dict
    trait_map_data = Signal(dict)  # learned map + updates dict
    swarm_data = Signal(dict)  # swarm status dict

    def __init__(self, parent=None):
        super().__init__(parent)
        self._async_bridge = AsyncBridge()
        self._async_bridge.start()

        # Backend state
        self._llm_provider = None
        self._coo = None
        self._registry = None
        self._is_connected = False

        # Task tracking
        self._tasks: Dict[str, GUITask] = {}
        self._task_counter = 0

        # Refresh timer
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._on_refresh_timer)

    def connect_backend(self):
        """Initialize and connect to the ag3ntwerk backend."""

        async def _connect():
            try:
                # Import here to avoid circular imports
                from ag3ntwerk.llm import auto_connect, get_provider
                from ag3ntwerk.agents.overwatch import Overwatch
                from ag3ntwerk.orchestration.registry import AgentRegistry

                # Try to connect to Ollama first
                logger.info("Connecting to LLM provider...")
                provider = await auto_connect()

                if not provider:
                    # Try Ollama directly with explicit connection
                    provider = get_provider("ollama")
                    if not await provider.connect():
                        return False, "No LLM provider available. Start Ollama first."

                self._llm_provider = provider

                # Initialize Overwatch (internal coordinator)
                logger.info("Initializing Overwatch (Overwatch)...")
                self._coo = Overwatch(llm_provider=provider)

                # Initialize registry and register agents
                logger.info("Initializing Agent Registry...")
                self._registry = AgentRegistry(llm_provider=provider)

                # Register available agents with Overwatch
                available_codes = self._registry.get_available_codes()
                for code in available_codes:
                    if code not in ("Nexus", "Overwatch", "CKO"):
                        agent = self._registry.get(code)
                        if agent:
                            self._coo.register_subordinate(agent)
                            logger.info(f"Registered {code} with Overwatch")

                self._is_connected = True
                return True, f"Connected via {provider.__class__.__name__}"

            except Exception as e:
                logger.error(f"Backend connection failed: {e}")
                return False, str(e)

        def on_result(result):
            success, message = result if result else (False, "Connection failed")
            self._is_connected = success
            self.connected.emit(success, message)

            if success:
                # Start refresh timer
                self._refresh_timer.start(int(os.environ.get("AGENTWERK_GUI_REFRESH_MS", "5000")))
                # Initial status update
                self.refresh_status()

        self._async_bridge.run_async(_connect(), on_result)

    def disconnect_backend(self):
        """Disconnect from the backend."""
        self._refresh_timer.stop()

        async def _disconnect():
            if self._llm_provider:
                await self._llm_provider.disconnect()
            self._llm_provider = None
            self._coo = None
            self._registry = None
            self._is_connected = False
            return True

        self._async_bridge.run_async(
            _disconnect(), lambda _: self.connected.emit(False, "Disconnected")
        )

    def send_message(self, message: str):
        """
        Send a message/task to the Nexus.

        The Nexus will analyze and route to the appropriate agent.
        """
        if not self._is_connected or not self._coo:
            self.coo_response.emit("Not connected to backend. Please wait for connection.")
            return

        async def _process_message():
            try:
                from ag3ntwerk.core.base import Task

                # Create task from message
                self._task_counter += 1
                task_id = f"gui-{self._task_counter:04d}"

                # Let Nexus analyze the task type
                task = Task(
                    id=task_id,
                    description=message,
                    task_type="general",  # Nexus will determine actual type
                    context={"source": "gui", "user_message": message},
                )

                # Track the task
                gui_task = GUITask(
                    id=task_id,
                    description=message,
                    task_type="general",
                    assigned_to="Nexus",
                    status="in_progress",
                )
                self._tasks[task_id] = gui_task

                # Emit task created
                return {"type": "task_created", "task": self._task_to_dict(gui_task)}

            except Exception as e:
                logger.error(f"Failed to create task: {e}")
                return {"type": "error", "message": str(e)}

        def on_task_created(result):
            if result and result.get("type") == "task_created":
                self.task_created.emit(result["task"])
                # Now execute the task
                self._execute_task(result["task"]["id"])
            elif result:
                self.coo_response.emit(f"Error: {result.get('message', 'Unknown error')}")

        self._async_bridge.run_async(_process_message(), on_task_created)

    def _execute_task(self, task_id: str):
        """Execute a task through the Nexus."""
        gui_task = self._tasks.get(task_id)
        if not gui_task:
            return

        async def _execute():
            try:
                from ag3ntwerk.core.base import Task

                task = Task(
                    id=task_id,
                    description=gui_task.description,
                    task_type=gui_task.task_type,
                )

                # Execute via Nexus
                result = await self._coo.execute(task)

                # Update task state
                gui_task.status = "completed" if result.success else "failed"
                gui_task.result = result.output if result.success else None
                gui_task.error = result.error if not result.success else None

                # Determine which agent handled it
                if result.metrics and "handled_by" in result.metrics:
                    gui_task.assigned_to = result.metrics["handled_by"]
                elif result.metrics and "delegated_to" in result.metrics:
                    gui_task.assigned_to = result.metrics["delegated_to"]

                return {
                    "task": self._task_to_dict(gui_task),
                    "response": result.output or result.error or "Task completed.",
                }

            except Exception as e:
                logger.error(f"Task execution failed: {e}")
                gui_task.status = "failed"
                gui_task.error = str(e)
                return {
                    "task": self._task_to_dict(gui_task),
                    "response": f"Task failed: {e}",
                }

        def on_complete(result):
            if result:
                self.task_updated.emit(result["task"])
                self.coo_response.emit(result["response"])
                self.refresh_status()

        self._async_bridge.run_async(_execute(), on_complete)

    def refresh_status(self):
        """Refresh agent and task status."""
        if not self._is_connected or not self._coo:
            return

        async def _get_status():
            try:
                # Get Nexus system status
                status = await self._coo.get_system_status()

                # Get health info
                health = self._coo.get_agent_health()

                # Get metacognition data if available
                metacognition = {}
                drift = []
                coherence = []
                trends = {}
                team_info = {}
                trait_map_info = {}
                svc = self._coo.metacognition_service
                if svc is not None:
                    try:
                        metacognition = svc.get_stats()
                        if not isinstance(metacognition, dict):
                            logger.warning(
                                "get_stats() returned %s, expected dict",
                                type(metacognition).__name__,
                            )
                            metacognition = {}
                    except Exception as e:
                        logger.error("Failed to get metacognition stats: %s", e)
                        metacognition = {}

                    try:
                        drift = [a.to_dict() for a in svc.check_drift_alerts()]
                    except Exception as e:
                        logger.error("Failed to get drift alerts: %s", e)
                        drift = []

                    try:
                        trends = svc.get_trend_summary()
                        if not isinstance(trends, dict):
                            logger.warning(
                                "get_trend_summary() returned %s, expected dict",
                                type(trends).__name__,
                            )
                            trends = {}
                    except Exception as e:
                        logger.error("Failed to get trend summary: %s", e)
                        trends = {}

                    try:
                        coherence = []
                        for c in svc.get_all_profiles():
                            report = svc.compute_coherence(c)
                            if report is not None:
                                coherence.append(report.to_dict())
                    except Exception as e:
                        logger.error("Failed to get coherence data: %s", e)
                        coherence = []

                    try:
                        team_info = {
                            "stats": svc.get_team_stats(),
                            "pairs": svc.get_best_pairs(),
                        }
                    except Exception as e:
                        logger.error("Failed to get team data: %s", e)
                        team_info = {}

                    try:
                        trait_map_info = {
                            "learned": svc.get_learned_trait_map(),
                            "updates": [u.to_dict() for u in svc.trait_map_updates],
                        }
                    except Exception as e:
                        logger.error("Failed to get trait map data: %s", e)
                        trait_map_info = {}

                # Fetch Swarm status (non-blocking, failures OK)
                swarm_info = {"available": False}
                try:
                    from ag3ntwerk.modules.swarm_bridge import SwarmBridgeService

                    _svc = SwarmBridgeService()
                    if await _svc.is_swarm_available():
                        swarm_info = {"available": True, **(await _svc.get_swarm_status())}
                        swarm_info["models"] = await _svc.get_available_models()
                except Exception as e:
                    logger.debug("Swarm status fetch failed (non-critical): %s", e)

                return {
                    "coo_status": status,
                    "health": health,
                    "agents": self._registry.list_agents() if self._registry else [],
                    "metacognition": metacognition,
                    "drift_alerts": drift,
                    "coherence": coherence,
                    "trends": trends,
                    "team_info": team_info,
                    "trait_map_info": trait_map_info,
                    "swarm_info": swarm_info,
                }
            except Exception as e:
                logger.error(f"Status refresh failed: {e}")
                return None

        def on_status(result):
            if result:
                self.agent_status.emit(result)
                if result.get("metacognition"):
                    self.metacognition_status.emit(result["metacognition"])
                if "drift_alerts" in result:
                    self.drift_alerts.emit(result["drift_alerts"])
                if result.get("coherence"):
                    self.coherence_data.emit(result["coherence"])
                if result.get("trends"):
                    self.trend_data.emit(result["trends"])
                if result.get("team_info"):
                    self.team_data.emit(result["team_info"])
                if result.get("trait_map_info"):
                    self.trait_map_data.emit(result["trait_map_info"])
                if result.get("swarm_info"):
                    self.swarm_data.emit(result["swarm_info"])

        self._async_bridge.run_async(_get_status(), on_status)

    def get_tasks(self) -> List[Dict]:
        """Get all tracked tasks."""
        return [self._task_to_dict(t) for t in self._tasks.values()]

    def _task_to_dict(self, task: GUITask) -> Dict[str, Any]:
        """Convert GUITask to dict for Qt signals."""
        return {
            "id": task.id,
            "description": task.description,
            "task_type": task.task_type,
            "assigned_to": task.assigned_to,
            "status": task.status,
            "created_at": task.created_at.isoformat(),
            "result": task.result,
            "error": task.error,
        }

    def _on_refresh_timer(self):
        """Periodic status refresh."""
        self.refresh_status()
        self.tasks_refreshed.emit(self.get_tasks())

    def cleanup(self):
        """Cleanup resources."""
        self._refresh_timer.stop()
        self._async_bridge.stop()
