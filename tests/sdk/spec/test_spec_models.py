"""Tests for spec module data models."""

from openhands.sdk.spec import (
    AgentCapability,
    AgentProfile,
    FormalSpec,
    SpecType,
    TaskGraph,
    TaskNode,
    TaskStatus,
)


class TestFormalSpec:
    """Tests for FormalSpec model."""

    def test_create_basic_spec(self):
        """Test creating a basic formal spec."""
        spec = FormalSpec(
            spec_type=SpecType.TLA_PLUS,
            content="---- MODULE Test ----",
            name="TestSpec",
        )
        assert spec.name == "TestSpec"
        assert spec.spec_type == SpecType.TLA_PLUS
        assert spec.version == "1.0.0"

    def test_add_invariant(self):
        """Test adding invariants to a spec."""
        spec = FormalSpec()
        spec.add_invariant("x > 0")
        assert "x > 0" in spec.invariants

    def test_add_safety_property(self):
        """Test adding safety properties to a spec."""
        spec = FormalSpec()
        spec.add_safety_property("x < 100")
        assert "x < 100" in spec.safety_properties

    def test_add_liveness_property(self):
        """Test adding liveness properties to a spec."""
        spec = FormalSpec()
        spec.add_liveness_property("eventually x > 0")
        assert "eventually x > 0" in spec.liveness_properties

    def test_to_tla_plus(self):
        """Test TLA+ conversion."""
        spec = FormalSpec(
            name="TestSpec",
            invariants=["x > 0"],
            safety_properties=["x < 100"],
            liveness_properties=["eventually done"],
        )
        tla = spec.to_tla_plus()
        assert "TestSpec" in tla
        assert "x > 0" in tla
        assert "x < 100" in tla
        assert "done" in tla


class TestTaskNode:
    """Tests for TaskNode model."""

    def test_create_task(self):
        """Test creating a task node."""
        task = TaskNode(
            name="test_task",
            description="A test task",
        )
        assert task.status == TaskStatus.PENDING
        assert task.retry_count == 0
        assert task.max_retries == 3

    def test_mark_running(self):
        """Test marking a task as running."""
        task = TaskNode(name="test")
        task.mark_running()
        assert task.status == TaskStatus.RUNNING
        assert task.started_at is not None

    def test_mark_completed(self):
        """Test marking a task as completed."""
        task = TaskNode(name="test")
        task.mark_completed({"result": "success"})
        assert task.status == TaskStatus.COMPLETED
        assert task.output_data == {"result": "success"}

    def test_mark_failed(self):
        """Test marking a task as failed."""
        task = TaskNode(name="test")
        task.mark_failed("Something went wrong")
        assert task.status == TaskStatus.FAILED
        assert task.error_message == "Something went wrong"

    def test_retry_logic(self):
        """Test retry logic."""
        task = TaskNode(name="test", max_retries=2)
        task.mark_failed("Error")
        assert task.can_retry() is True

        task.increment_retry()
        assert task.retry_count == 1
        assert task.status == TaskStatus.READY

        task.mark_failed("Error")
        task.increment_retry()
        assert task.retry_count == 2
        assert task.can_retry() is False


class TestTaskGraph:
    """Tests for TaskGraph model."""

    def test_create_graph(self):
        """Test creating an empty task graph."""
        graph = TaskGraph()
        assert len(graph) == 0
        assert graph.is_complete() is True

    def test_add_node(self):
        """Test adding nodes to the graph."""
        graph = TaskGraph()
        task1 = TaskNode(name="task1")
        task2 = TaskNode(name="task2")
        graph.add_node(task1)
        graph.add_node(task2)
        assert len(graph) == 2

    def test_add_edge(self):
        """Test adding edges between nodes."""
        graph = TaskGraph()
        task1 = TaskNode(name="task1")
        task2 = TaskNode(name="task2")
        graph.add_node(task1)
        graph.add_node(task2)
        graph.add_edge(task1.id, task2.id)

        assert task2.id in graph.get_dependents(task1.id)

    def test_get_ready_tasks(self):
        """Test getting ready tasks."""
        graph = TaskGraph()
        task1 = TaskNode(name="task1")
        task2 = TaskNode(name="task2", dependencies=[task1.id])
        graph.add_node(task1)
        graph.add_node(task2)

        ready = graph.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].name == "task1"

    def test_execution_order(self):
        """Test topological sort for execution order."""
        graph = TaskGraph()
        task1 = TaskNode(name="task1")
        task2 = TaskNode(name="task2", dependencies=[task1.id])
        task3 = TaskNode(name="task3", dependencies=[task1.id, task2.id])
        graph.add_node(task1)
        graph.add_node(task2)
        graph.add_node(task3)
        graph.add_edge(task1.id, task2.id)
        graph.add_edge(task2.id, task3.id)

        order = graph.get_execution_order()
        assert order.index(task1.id) < order.index(task2.id)
        assert order.index(task2.id) < order.index(task3.id)

    def test_is_complete(self):
        """Test checking if all tasks are complete."""
        graph = TaskGraph()
        task = TaskNode(name="task")
        graph.add_node(task)
        assert graph.is_complete() is False

        task.mark_completed()
        assert graph.is_complete() is True


class TestAgentProfile:
    """Tests for AgentProfile model."""

    def test_create_profile(self):
        """Test creating an agent profile."""
        profile = AgentProfile(
            agent_id="test-agent",
            name="Test Agent",
            capabilities=[AgentCapability.CODE_GENERATION],
            languages=["python", "javascript"],
        )
        assert profile.agent_id == "test-agent"
        assert profile.success_rate == 1.0
        assert profile.current_load == 0

    def test_has_capability(self):
        """Test checking capabilities."""
        profile = AgentProfile(
            agent_id="test",
            name="Test",
            capabilities=[AgentCapability.CODE_GENERATION, AgentCapability.TESTING],
        )
        assert profile.has_capability(AgentCapability.CODE_GENERATION) is True
        assert profile.has_capability(AgentCapability.DEBUGGING) is False

    def test_can_handle_task(self):
        """Test checking if agent can handle a task."""
        profile = AgentProfile(
            agent_id="test",
            name="Test",
            capabilities=[AgentCapability.CODE_GENERATION, AgentCapability.TESTING],
        )
        assert profile.can_handle_task([AgentCapability.CODE_GENERATION]) is True
        assert (
            profile.can_handle_task(
                [AgentCapability.CODE_GENERATION, AgentCapability.TESTING]
            )
            is True
        )
        assert (
            profile.can_handle_task(
                [AgentCapability.CODE_GENERATION, AgentCapability.SECURITY_ANALYSIS]
            )
            is False
        )

    def test_load_management(self):
        """Test incrementing and decrementing load."""
        profile = AgentProfile(
            agent_id="test",
            name="Test",
            max_concurrent_tasks=2,
        )
        assert profile.can_accept_task() is True

        profile.increment_load()
        assert profile.current_load == 1
        assert profile.can_accept_task() is True

        profile.increment_load()
        assert profile.current_load == 2
        assert profile.can_accept_task() is False

        profile.decrement_load()
        assert profile.current_load == 1
        assert profile.can_accept_task() is True

    def test_supports_language(self):
        """Test checking language support."""
        profile = AgentProfile(
            agent_id="test",
            name="Test",
            languages=["Python", "JavaScript"],
        )
        assert profile.supports_language("python") is True
        assert profile.supports_language("JavaScript") is True
        assert profile.supports_language("Go") is False
