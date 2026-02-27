"""Tests for planner and allocator."""

import pytest

from openhands.sdk.spec import (
    AgentCapability,
    AgentProfile,
    TaskGraph,
    TaskNode,
    TaskPriority,
)


class TestPlannerAgent:
    """Tests for PlannerAgent functionality."""

    def test_create_task_graph(self):
        """Test creating a task graph."""
        graph = TaskGraph()
        assert len(graph) == 0

    def test_add_task_to_graph(self):
        """Test adding a task to the graph."""
        graph = TaskGraph()
        task = TaskNode(
            name="test_task",
            description="A test task",
            required_capabilities=["code_generation"],
        )
        graph.add_node(task)

        assert len(graph) == 1
        assert graph.get_node(task.id) == task

    def test_task_with_dependencies(self):
        """Test tasks with dependencies."""
        graph = TaskGraph()

        task1 = TaskNode(name="task1")
        task2 = TaskNode(name="task2", dependencies=[task1.id])

        graph.add_node(task1)
        graph.add_node(task2)
        graph.add_edge(task1.id, task2.id)

        assert len(graph) == 2
        assert task2.id in graph.get_dependents(task1.id)

    def test_get_ready_tasks(self):
        """Test getting ready tasks."""
        graph = TaskGraph()

        task1 = TaskNode(name="task1")
        task2 = TaskNode(name="task2", dependencies=[task1.id])

        graph.add_node(task1)
        graph.add_node(task2)
        graph.add_edge(task1.id, task2.id)

        ready = graph.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].name == "task1"

    def test_execution_order(self):
        """Test topological sort for execution order."""
        graph = TaskGraph()

        task1 = TaskNode(name="task1")
        task2 = TaskNode(name="task2", dependencies=[task1.id])
        task3 = TaskNode(name="task3", dependencies=[task2.id])

        graph.add_node(task1)
        graph.add_node(task2)
        graph.add_node(task3)
        graph.add_edge(task1.id, task2.id)
        graph.add_edge(task2.id, task3.id)

        order = graph.get_execution_order()
        assert len(order) == 3
        assert order.index(task1.id) < order.index(task2.id)
        assert order.index(task2.id) < order.index(task3.id)

    def test_task_priority(self):
        """Test task priority handling."""
        low_task = TaskNode(name="low", priority=TaskPriority.LOW)
        high_task = TaskNode(name="high", priority=TaskPriority.HIGH)
        normal_task = TaskNode(name="normal", priority=TaskPriority.NORMAL)

        tasks = [low_task, high_task, normal_task]
        sorted_tasks = sorted(tasks, key=lambda t: t.priority.value, reverse=True)

        assert sorted_tasks[0].name == "high"
        assert sorted_tasks[1].name == "normal"
        assert sorted_tasks[2].name == "low"


class TestDynamicRoleAllocator:
    """Tests for DynamicRoleAllocator functionality."""

    def test_allocator_creation(self):
        """Test creating a DynamicRoleAllocator."""
        from openhands.sdk.agent.planner.allocator import DynamicRoleAllocator

        allocator = DynamicRoleAllocator()
        assert allocator is not None
        assert allocator.registry is not None

    def test_allocate_no_profiles(self):
        """Test allocation with no available profiles."""
        from openhands.sdk.agent.planner.allocator import DynamicRoleAllocator

        allocator = DynamicRoleAllocator()
        task = TaskNode(name="test_task", required_capabilities=["code_generation"])

        result = allocator.allocate(task, profiles=[])
        assert result is None

    def test_allocate_with_matching_capabilities(self):
        """Test allocation with matching capabilities."""
        from openhands.sdk.agent.planner.allocator import DynamicRoleAllocator
        from openhands.sdk.subagent.profile_registry import AgentProfileRegistry

        registry = AgentProfileRegistry()
        profile = AgentProfile(
            agent_id="test-agent",
            name="Test Agent",
            capabilities=[AgentCapability.CODE_GENERATION],
        )
        registry.register(profile)

        allocator = DynamicRoleAllocator(registry=registry)
        task = TaskNode(
            name="test_task",
            required_capabilities=["code_generation"],
        )

        result = allocator.allocate(task)
        assert result is not None
        assert result.agent_id == "test-agent"

    def test_allocate_without_required_capabilities(self):
        """Test allocation without required capabilities falls back to available."""
        from openhands.sdk.agent.planner.allocator import DynamicRoleAllocator
        from openhands.sdk.subagent.profile_registry import AgentProfileRegistry

        registry = AgentProfileRegistry()
        profile = AgentProfile(
            agent_id="test-agent",
            name="Test Agent",
            capabilities=[AgentCapability.CODE_GENERATION],
        )
        registry.register(profile)

        allocator = DynamicRoleAllocator(registry=registry)
        task = TaskNode(
            name="test_task",
            required_capabilities=["security_analysis"],
        )

        result = allocator.allocate(task)
        assert result is not None

    def test_release_agent(self):
        """Test releasing an agent after task completion."""
        from openhands.sdk.agent.planner.allocator import DynamicRoleAllocator
        from openhands.sdk.subagent.profile_registry import AgentProfileRegistry

        registry = AgentProfileRegistry()
        profile = AgentProfile(
            agent_id="test-agent",
            name="Test Agent",
            max_concurrent_tasks=2,
        )
        registry.register(profile)

        profile.increment_load()
        assert profile.current_load == 1

        allocator = DynamicRoleAllocator(registry=registry)
        result = allocator.release_agent("test-agent")
        assert result is True
        assert profile.current_load == 0

    def test_get_stats(self):
        """Test getting allocation statistics."""
        from openhands.sdk.agent.planner.allocator import DynamicRoleAllocator
        from openhands.sdk.subagent.profile_registry import AgentProfileRegistry

        registry = AgentProfileRegistry()
        profile1 = AgentProfile(
            agent_id="agent-1",
            name="Agent 1",
            success_rate=0.9,
        )
        profile2 = AgentProfile(
            agent_id="agent-2",
            name="Agent 2",
            success_rate=0.8,
        )
        registry.register(profile1)
        registry.register(profile2)

        allocator = DynamicRoleAllocator(registry=registry)
        stats = allocator.get_stats()

        assert stats["total_agents"] == 2
        assert stats["avg_success_rate"] == pytest.approx(0.85)


class TestTaskGraphDecomposition:
    """Tests for task graph decomposition from specification."""

    def test_decompose_simple_spec(self):
        """Test decomposing a simple specification into tasks."""
        graph = TaskGraph()

        analyze_task = TaskNode(
            name="analyze_requirements",
            description="Analyze user requirements",
            required_capabilities=["research"],
        )

        spec_task = TaskNode(
            name="generate_spec",
            description="Generate formal specification",
            dependencies=[analyze_task.id],
            required_capabilities=["planning", "verification"],
        )

        code_task = TaskNode(
            name="generate_code",
            description="Generate code from spec",
            dependencies=[spec_task.id],
            required_capabilities=["code_generation"],
        )

        test_task = TaskNode(
            name="generate_tests",
            description="Generate unit tests",
            dependencies=[code_task.id],
            required_capabilities=["testing"],
        )

        graph.add_node(analyze_task)
        graph.add_node(spec_task)
        graph.add_node(code_task)
        graph.add_node(test_task)

        graph.add_edge(analyze_task.id, spec_task.id)
        graph.add_edge(spec_task.id, code_task.id)
        graph.add_edge(code_task.id, test_task.id)

        ready = graph.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].name == "analyze_requirements"

        order = graph.get_execution_order()
        assert len(order) == 4

    def test_parallel_tasks(self):
        """Test task graph with parallel execution paths."""
        graph = TaskGraph()

        start = TaskNode(name="start")

        branch1 = TaskNode(name="branch1", dependencies=[start.id])
        branch2 = TaskNode(name="branch2", dependencies=[start.id])

        end = TaskNode(name="end", dependencies=[branch1.id, branch2.id])

        graph.add_node(start)
        graph.add_node(branch1)
        graph.add_node(branch2)
        graph.add_node(end)

        graph.add_edge(start.id, branch1.id)
        graph.add_edge(start.id, branch2.id)
        graph.add_edge(branch1.id, end.id)
        graph.add_edge(branch2.id, end.id)

        order = graph.get_execution_order()
        start_idx = order.index(start.id)
        branch1_idx = order.index(branch1.id)
        branch2_idx = order.index(branch2.id)
        end_idx = order.index(end.id)

        assert start_idx < branch1_idx
        assert start_idx < branch2_idx
        assert branch1_idx < end_idx
        assert branch2_idx < end_idx
