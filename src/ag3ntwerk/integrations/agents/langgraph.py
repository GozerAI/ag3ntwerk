"""
LangGraph Integration for ag3ntwerk.

Provides graph-based agent orchestration using LangGraph.
Enables complex multi-agent workflows, state machines, and conditional routing.

Requirements:
    - pip install langgraph langchain-core

LangGraph is ideal for:
    - Multi-agent coordination (Nexus orchestrating multiple agents)
    - Stateful conversations with complex logic
    - Conditional routing based on task analysis
    - Human-in-the-loop workflows
"""

import asyncio
import inspect
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Sequence, TypeVar, Union
from enum import Enum
from uuid import uuid4

logger = logging.getLogger(__name__)

# Type variable for state
StateType = TypeVar("StateType", bound=Dict[str, Any])


class NodeType(str, Enum):
    """Types of nodes in a LangGraph workflow."""

    AGENT = "agent"  # An AI agent node
    TOOL = "tool"  # A tool execution node
    ROUTER = "router"  # A routing/decision node
    HUMAN = "human"  # Human-in-the-loop node
    TRANSFORM = "transform"  # Data transformation node
    CHECKPOINT = "checkpoint"  # State checkpoint node
    END = "end"  # Terminal node


@dataclass
class GraphState:
    """
    State object for LangGraph workflows.

    The state is passed between nodes and can be modified at each step.
    """

    messages: List[Dict[str, Any]] = field(default_factory=list)
    current_agent: Optional[str] = None
    task: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    results: Dict[str, Any] = field(default_factory=dict)
    iteration: int = 0
    max_iterations: int = 10
    should_continue: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary."""
        return {
            "messages": self.messages,
            "current_agent": self.current_agent,
            "task": self.task,
            "context": self.context,
            "results": self.results,
            "iteration": self.iteration,
            "max_iterations": self.max_iterations,
            "should_continue": self.should_continue,
            "error": self.error,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphState":
        """Create state from dictionary."""
        return cls(
            messages=data.get("messages", []),
            current_agent=data.get("current_agent"),
            task=data.get("task"),
            context=data.get("context", {}),
            results=data.get("results", {}),
            iteration=data.get("iteration", 0),
            max_iterations=data.get("max_iterations", 10),
            should_continue=data.get("should_continue", True),
            error=data.get("error"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class GraphNode:
    """
    Represents a node in the workflow graph.

    Nodes can be agents, tools, routers, or other processing units.
    """

    id: str
    name: str
    node_type: NodeType = NodeType.AGENT
    handler: Optional[Callable] = None
    description: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self):
        return hash(self.id)


@dataclass
class GraphEdge:
    """
    Represents an edge (connection) between nodes.

    Edges can be conditional based on state.
    """

    source: str  # Source node ID
    target: str  # Target node ID
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    label: str = ""
    priority: int = 0  # Higher priority edges are evaluated first

    def should_traverse(self, state: Dict[str, Any]) -> bool:
        """Check if this edge should be traversed given the current state."""
        if self.condition is None:
            return True
        return self.condition(state)


@dataclass
class GraphWorkflow:
    """
    A complete workflow definition.

    Contains nodes, edges, and execution configuration.
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    nodes: Dict[str, GraphNode] = field(default_factory=dict)
    edges: List[GraphEdge] = field(default_factory=list)
    entry_point: str = ""
    checkpointer: Optional[Any] = None  # LangGraph checkpointer
    interrupt_before: List[str] = field(default_factory=list)
    interrupt_after: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def add_node(self, node: GraphNode) -> None:
        """Add a node to the workflow."""
        self.nodes[node.id] = node

    def add_edge(self, edge: GraphEdge) -> None:
        """Add an edge to the workflow."""
        self.edges.append(edge)

    def connect(
        self,
        source: str,
        target: str,
        condition: Optional[Callable] = None,
        label: str = "",
    ) -> None:
        """Convenience method to connect two nodes."""
        self.add_edge(
            GraphEdge(
                source=source,
                target=target,
                condition=condition,
                label=label,
            )
        )

    def get_outgoing_edges(self, node_id: str) -> List[GraphEdge]:
        """Get all edges leaving a node."""
        return [e for e in self.edges if e.source == node_id]


class LangGraphIntegration:
    """
    Integration with LangGraph for complex agent orchestration.

    This integration allows ag3ntwerk to leverage LangGraph's powerful
    graph-based workflow system for multi-agent coordination.

    Features:
    - Define agent workflows as directed graphs
    - Conditional routing based on state
    - State persistence and checkpointing
    - Human-in-the-loop support
    - Parallel node execution

    Example:
        integration = LangGraphIntegration()

        # Create a workflow
        workflow = integration.create_workflow("task_routing")

        # Add nodes
        workflow.add_node(GraphNode(
            id="router",
            name="Task Router",
            node_type=NodeType.ROUTER,
            handler=route_task,
        ))
        workflow.add_node(GraphNode(
            id="cto",
            name="Forge Agent",
            node_type=NodeType.AGENT,
            handler=cto_handler,
        ))

        # Connect nodes
        workflow.connect("router", "cto", condition=lambda s: s["task_type"] == "technical")

        # Compile and run
        graph = integration.compile(workflow)
        result = await integration.run(graph, {"task": "Review code"})
    """

    def __init__(
        self,
        default_max_iterations: int = 25,
        enable_checkpointing: bool = False,
    ):
        """
        Initialize LangGraph integration.

        Args:
            default_max_iterations: Default max iterations for workflows
            enable_checkpointing: Enable state checkpointing
        """
        self.default_max_iterations = default_max_iterations
        self.enable_checkpointing = enable_checkpointing
        self._workflows: Dict[str, GraphWorkflow] = {}
        self._compiled_graphs: Dict[str, Any] = {}

    def create_workflow(
        self,
        name: str,
        description: str = "",
    ) -> GraphWorkflow:
        """
        Create a new workflow.

        Args:
            name: Workflow name
            description: Workflow description

        Returns:
            New GraphWorkflow instance
        """
        workflow = GraphWorkflow(
            name=name,
            description=description,
        )
        self._workflows[workflow.id] = workflow
        return workflow

    def compile(self, workflow: GraphWorkflow) -> Any:
        """
        Compile a workflow into a LangGraph StateGraph.

        Args:
            workflow: GraphWorkflow to compile

        Returns:
            Compiled LangGraph graph
        """
        try:
            from langgraph.graph import StateGraph, END
            from typing import TypedDict
        except ImportError:
            logger.warning("LangGraph not installed. Using mock implementation.")
            return self._compile_mock(workflow)

        # Define state schema
        class WorkflowState(TypedDict):
            messages: List[Dict[str, Any]]
            current_agent: Optional[str]
            task: Optional[str]
            context: Dict[str, Any]
            results: Dict[str, Any]
            iteration: int
            max_iterations: int
            should_continue: bool
            error: Optional[str]
            metadata: Dict[str, Any]

        # Create graph
        graph = StateGraph(WorkflowState)

        # Add nodes
        for node_id, node in workflow.nodes.items():
            if node.node_type == NodeType.END:
                continue  # END is handled by LangGraph

            if node.handler:
                graph.add_node(node_id, node.handler)
            else:
                # Create default handler
                graph.add_node(node_id, self._create_default_handler(node))

        # Add edges
        for edge in workflow.edges:
            if (
                edge.target == "END"
                or workflow.nodes.get(edge.target, GraphNode("", "", NodeType.END)).node_type
                == NodeType.END
            ):
                target = END
            else:
                target = edge.target

            if edge.condition:
                # Conditional edge - need to create a routing function
                graph.add_conditional_edges(
                    edge.source,
                    self._create_router(workflow, edge.source),
                )
            else:
                graph.add_edge(edge.source, target)

        # Set entry point
        if workflow.entry_point:
            graph.set_entry_point(workflow.entry_point)

        # Compile
        if self.enable_checkpointing and workflow.checkpointer:
            compiled = graph.compile(
                checkpointer=workflow.checkpointer,
                interrupt_before=workflow.interrupt_before,
                interrupt_after=workflow.interrupt_after,
            )
        else:
            compiled = graph.compile()

        self._compiled_graphs[workflow.id] = compiled
        return compiled

    def _compile_mock(self, workflow: GraphWorkflow) -> "MockGraph":
        """Create a mock graph when LangGraph is not installed."""
        return MockGraph(workflow, self)

    def _create_default_handler(self, node: GraphNode) -> Callable:
        """Create a default handler for a node without a custom handler."""

        async def default_handler(state: Dict[str, Any]) -> Dict[str, Any]:
            state["current_agent"] = node.name
            state["iteration"] = state.get("iteration", 0) + 1

            if state["iteration"] >= state.get("max_iterations", self.default_max_iterations):
                state["should_continue"] = False

            return state

        return default_handler

    def _create_router(self, workflow: GraphWorkflow, source_id: str) -> Callable:
        """Create a routing function for conditional edges."""
        edges = workflow.get_outgoing_edges(source_id)

        def router(state: Dict[str, Any]) -> str:
            # Sort by priority (highest first)
            sorted_edges = sorted(edges, key=lambda e: -e.priority)

            for edge in sorted_edges:
                if edge.should_traverse(state):
                    return edge.target

            # Default to END if no conditions match
            return "END"

        return router

    async def run(
        self,
        graph: Any,
        initial_state: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Run a compiled graph.

        Args:
            graph: Compiled LangGraph graph
            initial_state: Initial state dictionary
            config: Runtime configuration

        Returns:
            Final state after execution
        """
        state = initial_state or {}

        # Set defaults
        state.setdefault("messages", [])
        state.setdefault("context", {})
        state.setdefault("results", {})
        state.setdefault("iteration", 0)
        state.setdefault("max_iterations", self.default_max_iterations)
        state.setdefault("should_continue", True)
        state.setdefault("metadata", {})

        if isinstance(graph, MockGraph):
            return await graph.run(state)

        # Run the actual LangGraph
        try:
            result = await graph.ainvoke(state, config=config)
            return result
        except Exception as e:
            logger.error(f"Graph execution error: {e}")
            state["error"] = str(e)
            state["should_continue"] = False
            return state

    async def stream(
        self,
        graph: Any,
        initial_state: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Stream execution of a graph, yielding state at each step.

        Args:
            graph: Compiled LangGraph graph
            initial_state: Initial state dictionary
            config: Runtime configuration

        Yields:
            State updates at each step
        """
        state = initial_state or {}
        state.setdefault("messages", [])
        state.setdefault("context", {})
        state.setdefault("results", {})
        state.setdefault("iteration", 0)
        state.setdefault("max_iterations", self.default_max_iterations)
        state.setdefault("should_continue", True)

        if isinstance(graph, MockGraph):
            async for step_state in graph.stream(state):
                yield step_state
            return

        try:
            async for step in graph.astream(state, config=config):
                yield step
        except Exception as e:
            logger.error(f"Graph stream error: {e}")
            yield {"error": str(e)}

    def get_workflow(self, workflow_id: str) -> Optional[GraphWorkflow]:
        """Get a workflow by ID."""
        return self._workflows.get(workflow_id)

    def list_workflows(self) -> List[GraphWorkflow]:
        """List all workflows."""
        return list(self._workflows.values())


class MockGraph:
    """Mock graph implementation when LangGraph is not installed."""

    def __init__(self, workflow: GraphWorkflow, integration: LangGraphIntegration):
        self.workflow = workflow
        self.integration = integration

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the mock graph."""
        current_node_id = self.workflow.entry_point

        while current_node_id and state.get("should_continue", True):
            node = self.workflow.nodes.get(current_node_id)
            if not node:
                break

            if node.node_type == NodeType.END:
                break

            # Execute node handler
            if node.handler:
                if inspect.iscoroutinefunction(node.handler):
                    state = await node.handler(state)
                else:
                    state = node.handler(state)

            state["iteration"] = state.get("iteration", 0) + 1

            if state["iteration"] >= state.get("max_iterations", 10):
                state["should_continue"] = False
                break

            # Find next node
            edges = self.workflow.get_outgoing_edges(current_node_id)
            next_node_id = None

            for edge in sorted(edges, key=lambda e: -e.priority):
                if edge.should_traverse(state):
                    next_node_id = edge.target
                    break

            current_node_id = next_node_id

        return state

    async def stream(self, state: Dict[str, Any]):
        """Stream mock graph execution."""
        current_node_id = self.workflow.entry_point

        while current_node_id and state.get("should_continue", True):
            node = self.workflow.nodes.get(current_node_id)
            if not node or node.node_type == NodeType.END:
                break

            if node.handler:
                if inspect.iscoroutinefunction(node.handler):
                    state = await node.handler(state)
                else:
                    state = node.handler(state)

            yield {current_node_id: state.copy()}

            state["iteration"] = state.get("iteration", 0) + 1

            if state["iteration"] >= state.get("max_iterations", 10):
                break

            edges = self.workflow.get_outgoing_edges(current_node_id)
            next_node_id = None

            for edge in sorted(edges, key=lambda e: -e.priority):
                if edge.should_traverse(state):
                    next_node_id = edge.target
                    break

            current_node_id = next_node_id


class CSuiteWorkflowBuilder:
    """
    Helper class to build common ag3ntwerk workflow patterns.

    Provides pre-built workflow templates for common agent patterns.
    """

    def __init__(self, integration: LangGraphIntegration):
        self.integration = integration

    def create_task_routing_workflow(
        self,
        agents: Dict[str, Callable],
        router: Callable,
    ) -> GraphWorkflow:
        """
        Create a workflow that routes tasks to appropriate agents.

        Args:
            agents: Dict mapping agent codes to handlers
            router: Function that returns agent code based on state

        Returns:
            Configured GraphWorkflow
        """
        workflow = self.integration.create_workflow(
            name="Task Routing",
            description="Routes tasks to appropriate ag3ntwerk agents",
        )

        # Add router node
        workflow.add_node(
            GraphNode(
                id="router",
                name="Task Router",
                node_type=NodeType.ROUTER,
                handler=router,
            )
        )
        workflow.entry_point = "router"

        # Add agent nodes
        for code, handler in agents.items():
            workflow.add_node(
                GraphNode(
                    id=code.lower(),
                    name=f"{code} Agent",
                    node_type=NodeType.AGENT,
                    handler=handler,
                )
            )

            # Connect router to agent
            workflow.connect(
                "router",
                code.lower(),
                condition=lambda s, c=code: s.get("target_agent") == c,
            )

        # Add end node
        workflow.add_node(
            GraphNode(
                id="end",
                name="End",
                node_type=NodeType.END,
            )
        )

        # Connect agents to end
        for code in agents.keys():
            workflow.connect(code.lower(), "end")

        return workflow

    def create_sequential_workflow(
        self,
        steps: List[tuple],
    ) -> GraphWorkflow:
        """
        Create a workflow that executes steps sequentially.

        Args:
            steps: List of (name, handler) tuples

        Returns:
            Configured GraphWorkflow
        """
        workflow = self.integration.create_workflow(
            name="Sequential Workflow",
            description="Executes steps in sequence",
        )

        prev_node_id = None
        for i, (name, handler) in enumerate(steps):
            node_id = f"step_{i}"
            workflow.add_node(
                GraphNode(
                    id=node_id,
                    name=name,
                    node_type=NodeType.AGENT,
                    handler=handler,
                )
            )

            if prev_node_id:
                workflow.connect(prev_node_id, node_id)
            else:
                workflow.entry_point = node_id

            prev_node_id = node_id

        # Add end
        workflow.add_node(
            GraphNode(
                id="end",
                name="End",
                node_type=NodeType.END,
            )
        )
        workflow.connect(prev_node_id, "end")

        return workflow

    def create_parallel_workflow(
        self,
        parallel_tasks: List[tuple],
        aggregator: Callable,
    ) -> GraphWorkflow:
        """
        Create a workflow that executes tasks in parallel then aggregates.

        Args:
            parallel_tasks: List of (name, handler) tuples to run in parallel
            aggregator: Handler to aggregate results

        Returns:
            Configured GraphWorkflow
        """
        workflow = self.integration.create_workflow(
            name="Parallel Workflow",
            description="Executes tasks in parallel then aggregates",
        )

        # Add splitter node
        async def splitter(state: Dict[str, Any]) -> Dict[str, Any]:
            state["parallel_results"] = {}
            return state

        workflow.add_node(
            GraphNode(
                id="splitter",
                name="Task Splitter",
                node_type=NodeType.TRANSFORM,
                handler=splitter,
            )
        )
        workflow.entry_point = "splitter"

        # Add parallel task nodes
        for i, (name, handler) in enumerate(parallel_tasks):
            node_id = f"parallel_{i}"
            workflow.add_node(
                GraphNode(
                    id=node_id,
                    name=name,
                    node_type=NodeType.AGENT,
                    handler=handler,
                )
            )
            workflow.connect("splitter", node_id)

        # Add aggregator node
        workflow.add_node(
            GraphNode(
                id="aggregator",
                name="Result Aggregator",
                node_type=NodeType.TRANSFORM,
                handler=aggregator,
            )
        )

        # Connect parallel tasks to aggregator
        for i in range(len(parallel_tasks)):
            workflow.connect(f"parallel_{i}", "aggregator")

        # Add end
        workflow.add_node(
            GraphNode(
                id="end",
                name="End",
                node_type=NodeType.END,
            )
        )
        workflow.connect("aggregator", "end")

        return workflow

    def create_human_in_loop_workflow(
        self,
        agent_handler: Callable,
        review_handler: Callable,
        approval_condition: Callable,
    ) -> GraphWorkflow:
        """
        Create a workflow with human-in-the-loop approval.

        Args:
            agent_handler: Main agent handler
            review_handler: Human review handler
            approval_condition: Function returning True if approved

        Returns:
            Configured GraphWorkflow
        """
        workflow = self.integration.create_workflow(
            name="Human-in-Loop Workflow",
            description="Agent execution with human approval",
        )

        # Add agent node
        workflow.add_node(
            GraphNode(
                id="agent",
                name="Agent",
                node_type=NodeType.AGENT,
                handler=agent_handler,
            )
        )
        workflow.entry_point = "agent"

        # Add human review node
        workflow.add_node(
            GraphNode(
                id="human_review",
                name="Human Review",
                node_type=NodeType.HUMAN,
                handler=review_handler,
            )
        )
        workflow.connect("agent", "human_review")

        # Add routing based on approval
        workflow.add_node(
            GraphNode(
                id="end",
                name="End",
                node_type=NodeType.END,
            )
        )

        # If approved, end. If not, go back to agent.
        workflow.connect(
            "human_review",
            "end",
            condition=approval_condition,
        )
        workflow.connect(
            "human_review",
            "agent",
            condition=lambda s: not approval_condition(s),
        )

        # Mark for interrupt before human review
        workflow.interrupt_before = ["human_review"]

        return workflow
