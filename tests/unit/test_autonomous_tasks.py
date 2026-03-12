"""
Unit tests for autonomous test tasks.

Tests verify:
1. Task definitions are valid
2. Task routing matches expected agents
3. Goal alignment is correct
4. Priority ordering works
5. Task collection functions work
"""

import pytest
from uuid import UUID

from ag3ntwerk.api.autonomous_test_tasks import (
    ALL_AGENT_TASKS,
    GOAL_ALIGNED_TASKS,
    PRIORITY_ORDERED_TASKS,
    AutonomousTask,
    GoalAlignment,
    TaskPriority,
    get_critical_tasks,
    get_q1_priority_tasks,
    get_task_summary,
    get_tasks_by_agent,
    get_tasks_by_goal,
    get_tasks_by_priority,
    CTO_TASKS,
    CIO_TASKS,
    CSECO_TASKS,
    CFO_TASKS,
    CSO_TASKS,
    CRO_TASKS,
    CDO_TASKS,
    CCOMO_TASKS,
    CRIO_TASKS,
    CMO_TASKS,
    CPO_TASKS,
    CCO_TASKS,
    CREVO_TASKS,
    CENGO_TASKS,
)

# Expected routing rules from Overwatch
EXPECTED_ROUTING = {
    "code_review": "Forge",
    "code_generation": "Forge",
    "architecture": "Forge",
    "deployment": "Forge",
    "testing": "Forge",
    "security_scan": "Sentinel",
    "security_review": "Sentinel",
    "vulnerability_check": "Citadel",
    "incident_response": "Citadel",
    "access_control": "Sentinel",
    "budget_analysis": "Keystone",
    "cost_optimization": "Keystone",
    "financial_report": "Keystone",
    "strategic_analysis": "Compass",
    "market_research": "Compass",
    "competitive_analysis": "Compass",
    "research": "Axiom",
    "data_analysis": "Axiom",
    "data_governance": "Index",
    "knowledge_management": "Index",
    "compliance_check": "Accord",
    "audit": "Accord",
    "policy_review": "Accord",
    "risk_assessment": "Aegis",
    "risk_mitigation": "Aegis",
    "campaign_creation": "Echo",
    "content_strategy": "Echo",
    "brand_analysis": "Echo",
    "product_strategy": "Blueprint",
    "feature_planning": "Blueprint",
    "customer_feedback": "Beacon",
    "customer_success": "Beacon",
    "revenue_optimization": "Vector",
    "sales_strategy": "Vector",
    "infrastructure": "Foundry",
    "devops": "Foundry",
}


class TestTaskDefinitions:
    """Test that all task definitions are valid."""

    def test_all_executives_have_tasks(self):
        """Verify every agent has at least one task."""
        expected_executives = {
            "Forge",
            "Sentinel",
            "Citadel",
            "Keystone",
            "Compass",
            "Axiom",
            "Index",
            "Accord",
            "Aegis",
            "Echo",
            "Blueprint",
            "Beacon",
            "Vector",
            "Foundry",
        }
        actual_executives = set(ALL_AGENT_TASKS.keys())
        assert expected_executives == actual_executives

    def test_each_executive_has_multiple_tasks(self):
        """Verify each agent has at least 2 tasks."""
        for agent_code, tasks in ALL_AGENT_TASKS.items():
            assert len(tasks) >= 2, f"{agent_code} should have at least 2 tasks"

    def test_task_ids_are_unique(self):
        """Verify all task IDs are unique."""
        all_ids = [task.id for task in PRIORITY_ORDERED_TASKS]
        assert len(all_ids) == len(set(all_ids)), "Task IDs must be unique"

    def test_task_ids_have_executive_prefix(self):
        """Verify task IDs have agent prefix."""
        for agent_code, tasks in ALL_AGENT_TASKS.items():
            for task in tasks:
                expected_prefix = agent_code.lower()
                assert task.id.startswith(
                    expected_prefix
                ), f"Task {task.id} should start with {expected_prefix}"

    def test_all_tasks_have_required_fields(self):
        """Verify all tasks have required fields."""
        for task in PRIORITY_ORDERED_TASKS:
            assert task.id, "Task must have ID"
            assert task.title, "Task must have title"
            assert task.description, "Task must have description"
            assert task.task_type, "Task must have task_type"
            assert task.target_agent, "Task must have target_agent"
            assert task.priority, "Task must have priority"
            assert task.goal_alignment, "Task must have goal_alignment"

    def test_task_priorities_are_valid(self):
        """Verify all tasks have valid priority."""
        for task in PRIORITY_ORDERED_TASKS:
            assert isinstance(task.priority, TaskPriority)

    def test_task_goal_alignments_are_valid(self):
        """Verify all tasks have valid goal alignment."""
        for task in PRIORITY_ORDERED_TASKS:
            assert isinstance(task.goal_alignment, GoalAlignment)


class TestTaskRouting:
    """Test that task routing matches expected agents."""

    def test_cto_tasks_have_cto_routing(self):
        """Verify Forge tasks route to Forge."""
        cto_task_types = {"code_review", "architecture", "testing", "deployment", "code_generation"}
        for task in CTO_TASKS:
            assert task.target_agent == "Forge"
            assert (
                task.task_type in cto_task_types
            ), f"Forge task {task.id} has unexpected type: {task.task_type}"

    def test_cio_tasks_have_cio_routing(self):
        """Verify Sentinel tasks route to Sentinel."""
        cio_task_types = {"security_review", "access_control", "security_scan", "threat_analysis"}
        for task in CIO_TASKS:
            assert task.target_agent == "Sentinel"
            assert (
                task.task_type in cio_task_types
            ), f"Sentinel task {task.id} has unexpected type: {task.task_type}"

    def test_cseco_tasks_have_cseco_routing(self):
        """Verify Citadel tasks route to Citadel."""
        cseco_task_types = {"vulnerability_check", "incident_response"}
        for task in CSECO_TASKS:
            assert task.target_agent == "Citadel"
            assert task.task_type in cseco_task_types

    def test_cfo_tasks_have_cfo_routing(self):
        """Verify Keystone tasks route to Keystone."""
        cfo_task_types = {"budget_analysis", "cost_optimization", "financial_report"}
        for task in CFO_TASKS:
            assert task.target_agent == "Keystone"
            assert task.task_type in cfo_task_types

    def test_cso_tasks_have_cso_routing(self):
        """Verify Compass tasks route to Compass."""
        cso_task_types = {"strategic_analysis", "competitive_analysis", "market_research"}
        for task in CSO_TASKS:
            assert task.target_agent == "Compass"
            assert task.task_type in cso_task_types

    def test_cro_tasks_have_cro_routing(self):
        """Verify Axiom tasks route to Axiom."""
        cro_task_types = {"research", "data_analysis", "insights"}
        for task in CRO_TASKS:
            assert task.target_agent == "Axiom"
            assert task.task_type in cro_task_types

    def test_cdo_tasks_have_cdo_routing(self):
        """Verify Index tasks route to Index."""
        cdo_task_types = {"data_governance", "knowledge_management", "data_quality"}
        for task in CDO_TASKS:
            assert task.target_agent == "Index"
            assert task.task_type in cdo_task_types

    def test_ccomo_tasks_have_ccomo_routing(self):
        """Verify Accord tasks route to Accord."""
        ccomo_task_types = {"audit", "policy_review", "compliance_check"}
        for task in CCOMO_TASKS:
            assert task.target_agent == "Accord"
            assert task.task_type in ccomo_task_types

    def test_crio_tasks_have_crio_routing(self):
        """Verify Aegis tasks route to Aegis."""
        crio_task_types = {"risk_assessment", "risk_mitigation"}
        for task in CRIO_TASKS:
            assert task.target_agent == "Aegis"
            assert task.task_type in crio_task_types

    def test_cmo_tasks_have_cmo_routing(self):
        """Verify Echo tasks route to Echo."""
        cmo_task_types = {"content_strategy", "brand_analysis", "campaign_creation"}
        for task in CMO_TASKS:
            assert task.target_agent == "Echo"
            assert task.task_type in cmo_task_types

    def test_cpo_tasks_have_cpo_routing(self):
        """Verify Blueprint tasks route to Blueprint."""
        cpo_task_types = {"product_strategy", "feature_planning", "user_research"}
        for task in CPO_TASKS:
            assert task.target_agent == "Blueprint"
            assert task.task_type in cpo_task_types

    def test_cco_tasks_have_cco_routing(self):
        """Verify Beacon tasks route to Beacon."""
        cco_task_types = {"customer_feedback", "customer_success"}
        for task in CCO_TASKS:
            assert task.target_agent == "Beacon"
            assert task.task_type in cco_task_types

    def test_crevo_tasks_have_crevo_routing(self):
        """Verify Vector tasks route to Vector."""
        crevo_task_types = {"revenue_optimization", "sales_strategy"}
        for task in CREVO_TASKS:
            assert task.target_agent == "Vector"
            assert task.task_type in crevo_task_types

    def test_cengo_tasks_have_cengo_routing(self):
        """Verify Foundry tasks route to Foundry."""
        cengo_task_types = {"infrastructure", "devops", "platform_engineering"}
        for task in CENGO_TASKS:
            assert task.target_agent == "Foundry"
            assert task.task_type in cengo_task_types


class TestGoalAlignment:
    """Test that tasks are properly aligned with strategic goals."""

    def test_all_goals_have_tasks(self):
        """Verify all strategic goals have at least one task."""
        for goal in GoalAlignment:
            tasks = get_tasks_by_goal(goal)
            assert len(tasks) > 0, f"Goal {goal.value} has no tasks"

    def test_phase_1_tasks_focus_on_foundation(self):
        """Verify Phase 1 tasks focus on foundation."""
        phase_1_tasks = get_tasks_by_goal(GoalAlignment.PHASE_1_FOUNDATION)
        assert len(phase_1_tasks) >= 2
        # Check that foundation-related agents have tasks
        agents = {t.target_agent for t in phase_1_tasks}
        assert "Forge" in agents or "Compass" in agents or "Axiom" in agents

    def test_phase_2_tasks_focus_on_ollama(self):
        """Verify Phase 2 tasks focus on Ollama migration."""
        phase_2_tasks = get_tasks_by_goal(GoalAlignment.PHASE_2_OLLAMA)
        assert len(phase_2_tasks) >= 2
        # Forge and Keystone should have Ollama-related tasks
        agents = {t.target_agent for t in phase_2_tasks}
        assert (
            "Forge" in agents
            or "Keystone" in agents
            or "Axiom" in agents
            or "Foundry" in agents
        )

    def test_q1_priority_tasks_focus_on_cost(self):
        """Verify Q1 priority tasks focus on cost elimination."""
        q1_tasks = get_q1_priority_tasks()
        assert len(q1_tasks) >= 2
        # Keystone and Aegis should have cost-related tasks
        agents = {t.target_agent for t in q1_tasks}
        assert "Keystone" in agents or "Aegis" in agents


class TestPriorityOrdering:
    """Test priority ordering functions."""

    def test_priority_ordered_tasks_are_sorted(self):
        """Verify tasks are sorted by priority."""
        priority_order = {
            TaskPriority.CRITICAL: 0,
            TaskPriority.HIGH: 1,
            TaskPriority.MEDIUM: 2,
            TaskPriority.LOW: 3,
        }

        prev_priority = 0
        for task in PRIORITY_ORDERED_TASKS:
            current_priority = priority_order[task.priority]
            assert current_priority >= prev_priority, f"Task {task.id} is out of priority order"
            prev_priority = current_priority

    def test_get_critical_tasks(self):
        """Verify get_critical_tasks returns only critical tasks."""
        critical = get_critical_tasks()
        for task in critical:
            assert task.priority == TaskPriority.CRITICAL

    def test_get_tasks_by_priority(self):
        """Verify get_tasks_by_priority filters correctly."""
        for priority in TaskPriority:
            tasks = get_tasks_by_priority(priority)
            for task in tasks:
                assert task.priority == priority


class TestTaskCollections:
    """Test task collection functions."""

    def test_get_tasks_by_agent(self):
        """Verify get_tasks_by_agent returns correct tasks."""
        for agent_code in ALL_AGENT_TASKS.keys():
            tasks = get_tasks_by_agent(agent_code)
            assert len(tasks) > 0
            for task in tasks:
                assert task.target_agent == agent_code

    def test_get_tasks_by_goal(self):
        """Verify get_tasks_by_goal returns correct tasks."""
        for goal in GoalAlignment:
            tasks = get_tasks_by_goal(goal)
            for task in tasks:
                assert task.goal_alignment == goal

    def test_get_task_summary(self):
        """Verify get_task_summary returns valid summary."""
        summary = get_task_summary()

        assert "total_tasks" in summary
        assert summary["total_tasks"] == len(PRIORITY_ORDERED_TASKS)

        assert "by_agent" in summary
        for agent_code in ALL_AGENT_TASKS.keys():
            assert agent_code in summary["by_agent"]

        assert "by_priority" in summary
        for priority in TaskPriority:
            assert priority.value in summary["by_priority"]

        assert "by_goal" in summary
        for goal in GoalAlignment:
            assert goal.value in summary["by_goal"]


class TestTaskToDict:
    """Test task serialization."""

    def test_to_dict_includes_all_fields(self):
        """Verify to_dict includes all required fields."""
        task = PRIORITY_ORDERED_TASKS[0]
        task_dict = task.to_dict()

        assert "id" in task_dict
        assert "title" in task_dict
        assert "description" in task_dict
        assert "task_type" in task_dict
        assert "target_agent" in task_dict
        assert "priority" in task_dict
        assert "goal_alignment" in task_dict
        assert "context" in task_dict
        assert "expected_outputs" in task_dict
        assert "success_criteria" in task_dict
        assert "created_at" in task_dict

    def test_to_dict_serializes_enums(self):
        """Verify to_dict serializes enums to strings."""
        task = PRIORITY_ORDERED_TASKS[0]
        task_dict = task.to_dict()

        assert isinstance(task_dict["priority"], str)
        assert isinstance(task_dict["goal_alignment"], str)


class TestTaskCounts:
    """Test task counts and distribution."""

    def test_total_task_count(self):
        """Verify total task count matches sum of agent tasks."""
        total_from_executives = sum(len(tasks) for tasks in ALL_AGENT_TASKS.values())
        assert len(PRIORITY_ORDERED_TASKS) == total_from_executives

    def test_minimum_task_coverage(self):
        """Verify minimum task coverage."""
        # At least 20 tasks total
        assert len(PRIORITY_ORDERED_TASKS) >= 20

        # At least 2 critical tasks
        assert len(get_critical_tasks()) >= 2

        # At least 2 Q1 priority tasks
        assert len(get_q1_priority_tasks()) >= 2

    def test_goal_distribution(self):
        """Verify tasks are distributed across all goals."""
        for goal in GoalAlignment:
            tasks = GOAL_ALIGNED_TASKS.get(goal, [])
            assert len(tasks) >= 1, f"Goal {goal.value} needs at least 1 task"
