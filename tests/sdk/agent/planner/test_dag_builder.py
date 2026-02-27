"""Tests for dag_builder module."""

import pytest

from openhands.sdk.agent.planner.dag_builder import (
    DAGBuilder,
    EdgeData,
    NodeData,
    create_dag_builder,
)


class TestNodeData:
    """Tests for NodeData dataclass."""

    def test_create_node_data(self):
        """Test creating NodeData."""
        node = NodeData(
            name="TestNode",
            description="Test description",
            task_type="implementation",
            required_capabilities=["coding"],
            priority=5,
        )

        assert node.name == "TestNode"
        assert node.task_type == "implementation"
        assert node.priority == 5


class TestEdgeData:
    """Tests for EdgeData dataclass."""

    def test_create_edge_data(self):
        """Test creating EdgeData."""
        edge = EdgeData(
            dependency_type="required",
            weight=1.0,
        )

        assert edge.dependency_type == "required"
        assert edge.weight == 1.0


class TestDAGBuilder:
    """Tests for DAGBuilder class."""

    def test_create_dag_builder(self):
        """Test creating a DAGBuilder."""
        builder = DAGBuilder()
        assert builder is not None

    def test_add_node(self):
        """Test adding a node."""
        builder = DAGBuilder()
        builder.add_node("node1", "Node 1")

        assert builder.get_node_count() == 1

    def test_add_multiple_nodes(self):
        """Test adding multiple nodes."""
        builder = DAGBuilder()
        builder.add_node("node1", "Node 1")
        builder.add_node("node2", "Node 2")
        builder.add_node("node3", "Node 3")

        assert builder.get_node_count() == 3

    def test_add_node_with_priority(self):
        """Test adding node with priority."""
        builder = DAGBuilder()
        builder.add_node("node1", "Node 1", priority=10)
        builder.add_node("node2", "Node 2", priority=5)

        dag = builder.build()
        assert dag["node1"].priority == 10
        assert dag["node2"].priority == 5

    def test_add_edge(self):
        """Test adding an edge."""
        builder = DAGBuilder()
        builder.add_node("node1", "Node 1")
        builder.add_node("node2", "Node 2")
        builder.add_edge("node1", "node2")

        assert builder.get_edge_count() == 1

    def test_add_edge_invalid_source(self):
        """Test adding edge with invalid source."""
        builder = DAGBuilder()
        builder.add_node("node1", "Node 1")

        with pytest.raises(ValueError):
            builder.add_edge("nonexistent", "node1")

    def test_add_dependency(self):
        """Test adding dependency."""
        builder = DAGBuilder()
        builder.add_node("node1", "Node 1")
        builder.add_node("node2", "Node 2")
        builder.add_dependency("node2", "node1")

        assert builder.get_edge_count() == 1
        assert "node1" in builder.get_dependencies("node2")

    def test_add_multiple_dependencies(self):
        """Test adding multiple dependencies."""
        builder = DAGBuilder()
        builder.add_node("node1", "Node 1")
        builder.add_node("node2", "Node 2")
        builder.add_node("node3", "Node 3")
        builder.add_dependency("node3", ["node1", "node2"])

        assert builder.get_edge_count() == 2

    def test_get_dependencies(self):
        """Test getting dependencies."""
        builder = DAGBuilder()
        builder.add_node("node1", "Node 1")
        builder.add_node("node2", "Node 2")
        builder.add_edge("node1", "node2")

        deps = builder.get_dependencies("node2")
        assert "node1" in deps

    def test_get_dependents(self):
        """Test getting dependents."""
        builder = DAGBuilder()
        builder.add_node("node1", "Node 1")
        builder.add_node("node2", "Node 2")
        builder.add_edge("node1", "node2")

        dependents = builder.get_dependents("node1")
        assert "node2" in dependents

    def test_execution_order(self):
        """Test topological sort execution order."""
        builder = DAGBuilder()
        builder.add_node("a", "A")
        builder.add_node("b", "B")
        builder.add_node("c", "C")
        builder.add_edge("a", "b")
        builder.add_edge("b", "c")

        order = builder.get_execution_order()
        assert order.index("a") < order.index("b")
        assert order.index("b") < order.index("c")

    def test_parallel_batches(self):
        """Test getting parallel execution batches."""
        builder = DAGBuilder()
        builder.add_node("a", "A")
        builder.add_node("b", "B")
        builder.add_node("c", "C")
        builder.add_node("d", "D")
        builder.add_edge("a", "b")
        builder.add_edge("a", "c")
        builder.add_edge("b", "d")
        builder.add_edge("c", "d")

        batches = builder.get_parallel_batches()

        assert len(batches) >= 2
        assert "a" in batches[0]
        assert "d" in batches[-1]

    def test_get_ready_nodes(self):
        """Test getting ready nodes."""
        builder = DAGBuilder()
        builder.add_node("a", "A")
        builder.add_node("b", "B")
        builder.add_node("c", "C")
        builder.add_edge("a", "b")
        builder.add_edge("b", "c")

        ready = builder.get_ready_nodes(set())
        assert "a" in ready

        ready = builder.get_ready_nodes({"a"})
        assert "b" in ready
        assert "a" not in ready

    def test_get_ready_nodes_with_priority(self):
        """Test ready nodes are sorted by priority."""
        builder = DAGBuilder()
        builder.add_node("a", "A", priority=1)
        builder.add_node("b", "B", priority=10)
        builder.add_edge("a", "b")

        ready = builder.get_ready_nodes(set())
        assert "a" in ready

    def test_entry_points(self):
        """Test getting entry points."""
        builder = DAGBuilder()
        builder.add_node("a", "A")
        builder.add_node("b", "B")
        builder.add_node("c", "C")
        builder.add_edge("a", "b")
        builder.add_edge("b", "c")

        entries = builder.get_entry_points()
        assert "a" in entries

    def test_exit_points(self):
        """Test getting exit points."""
        builder = DAGBuilder()
        builder.add_node("a", "A")
        builder.add_node("b", "B")
        builder.add_node("c", "C")
        builder.add_edge("a", "b")
        builder.add_edge("b", "c")

        exits = builder.get_exit_points()
        assert "c" in exits

    def test_validate_dag(self):
        """Test DAG validation."""
        builder = DAGBuilder()
        builder.add_node("a", "A")
        builder.add_node("b", "B")
        builder.add_edge("a", "b")

        assert builder._validate_dag() is True

    def test_validate_dag_with_cycle(self):
        """Test DAG validation with cycle."""
        builder = DAGBuilder()
        builder.add_node("a", "A")
        builder.add_node("b", "B")
        builder.add_node("c", "C")
        builder.add_edge("a", "b")
        builder.add_edge("b", "c")
        builder.add_edge("c", "a")

        assert builder._validate_dag() is False

    def test_visualize(self):
        """Test visualization output."""
        builder = DAGBuilder()
        builder.add_node("a", "A")
        builder.add_node("b", "B")
        builder.add_edge("a", "b")

        viz = builder.visualize()
        assert "DAG Structure" in viz
        assert "node1" in viz or "a" in viz


class TestFactory:
    """Tests for factory functions."""

    def test_create_dag_builder(self):
        """Test create_dag_builder factory."""
        builder = create_dag_builder()
        assert isinstance(builder, DAGBuilder)
