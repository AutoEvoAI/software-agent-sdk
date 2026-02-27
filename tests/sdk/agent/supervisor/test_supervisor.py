"""Tests for supervisor and spec agents.

These tests focus on the spec-related functionality without requiring
full Agent initialization.
"""

from openhands.sdk.spec import FormalSpec, SpecType, TaskGraph, TaskNode


class TestFormalSpecIntegration:
    """Integration tests for FormalSpec used by SupervisorAgent and SpecAgent."""

    def test_create_spec_for_supervisor(self):
        """Test creating a formal specification for supervisor use."""
        spec = FormalSpec(
            name="OrderProcessingSpec",
            description="Specification for order processing system",
            spec_type=SpecType.TLA_PLUS,
            content="""
---- MODULE OrderProcessing ----
VARIABLES state
Invariant_TypeInvariant == state \\in {"new", "paid", "shipped"}
""",
            invariants=['state \\in {"new", "paid", "shipped"}'],
            safety_properties=['state = "shipped" => state = "paid"'],
            liveness_properties=['eventually state = "shipped"'],
            version="1.0.0",
        )

        assert spec.name == "OrderProcessingSpec"
        assert spec.spec_type == SpecType.TLA_PLUS
        assert len(spec.invariants) == 1
        assert len(spec.safety_properties) == 1
        assert len(spec.liveness_properties) == 1

    def test_spec_add_methods(self):
        """Test FormalSpec add methods."""
        spec = FormalSpec(name="TestSpec")

        spec.add_invariant("x > 0")
        spec.add_invariant("y > 0")
        assert len(spec.invariants) == 2

        spec.add_safety_property("x < 100")
        assert len(spec.safety_properties) == 1

        spec.add_liveness_property("eventually done")
        assert len(spec.liveness_properties) == 1

    def test_spec_to_tla_plus(self):
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


class TestTaskGraphIntegration:
    """Integration tests for TaskGraph used by SupervisorAgent."""

    def test_create_task_graph_for_planner(self):
        """Test creating a task graph for planner use."""
        graph = TaskGraph()

        task1 = TaskNode(
            name="analyze_requirements",
            description="Analyze user requirements",
            required_capabilities=["research"],
        )
        task2 = TaskNode(
            name="generate_spec",
            description="Generate formal specification",
            dependencies=[task1.id],
            required_capabilities=["planning"],
        )
        task3 = TaskNode(
            name="generate_code",
            description="Generate code from spec",
            dependencies=[task2.id],
            required_capabilities=["code_generation"],
        )

        graph.add_node(task1)
        graph.add_node(task2)
        graph.add_node(task3)
        graph.add_edge(task1.id, task2.id)
        graph.add_edge(task2.id, task3.id)

        assert len(graph) == 3

        ready = graph.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].name == "analyze_requirements"

    def test_task_graph_execution_order(self):
        """Test topological sort for task execution."""
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
        assert order.index(task1.id) < order.index(task2.id)
        assert order.index(task2.id) < order.index(task3.id)

    def test_supervisor_task_flow(self):
        """Test complete task flow from supervisor perspective."""
        graph = TaskGraph()

        task1 = TaskNode(
            name="parse_requirements",
            description="Parse user requirements",
            required_capabilities=["research"],
        )
        task2 = TaskNode(
            name="generate_spec",
            description="Generate formal specification",
            dependencies=[task1.id],
            required_capabilities=["planning", "verification"],
        )
        task3 = TaskNode(
            name="decompose_tasks",
            description="Decompose spec into tasks",
            dependencies=[task2.id],
            required_capabilities=["planning"],
        )

        graph.add_node(task1)
        graph.add_node(task2)
        graph.add_node(task3)
        graph.add_edge(task1.id, task2.id)
        graph.add_edge(task2.id, task3.id)

        ready = graph.get_ready_tasks()
        assert len(ready) == 1

        ready[0].mark_running()
        assert ready[0].status.value == "running"

        ready[0].mark_completed({"result": "requirements_parsed"})
        assert ready[0].status.value == "completed"

        ready = graph.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].name == "generate_spec"


class TestSpecType:
    """Tests for SpecType enum."""

    def test_spec_type_values(self):
        """Test SpecType enum values."""
        assert SpecType.TLA_PLUS.value == "tla+"
        assert SpecType.Z_NOTATION.value == "z"
        assert SpecType.CUSTOM.value == "custom"

    def test_spec_type_usage(self):
        """Test SpecType usage in FormalSpec."""
        spec_tla = FormalSpec(spec_type=SpecType.TLA_PLUS)
        assert spec_tla.spec_type == SpecType.TLA_PLUS

        spec_z = FormalSpec(spec_type=SpecType.Z_NOTATION)
        assert spec_z.spec_type == SpecType.Z_NOTATION
