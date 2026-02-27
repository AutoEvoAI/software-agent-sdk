"""DAG builder for task graphs.

This module provides the DAG (Directed Acyclic Graph) building logic
for organizing tasks with their dependencies.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class EdgeData:
    """Data associated with an edge in the DAG."""

    dependency_type: str = "default"
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class NodeData:
    """Data associated with a node in the DAG."""

    name: str
    description: str = ""
    task_type: str = "default"
    required_capabilities: list[str] = field(default_factory=list)
    priority: int = 5
    optional: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class DAGBuilder:
    """Builds a Directed Acyclic Graph (DAG) for task execution.

    The DAG builder creates a graph structure from tasks and their
    dependencies, ensuring proper ordering and parallel execution.
    """

    def __init__(self):
        """Initialize the DAG builder."""
        self._nodes: dict[str, NodeData] = {}
        self._edges: list[tuple[str, str, EdgeData]] = []
        self._adjacency: dict[str, list[str]] = {}
        self._reverse_adjacency: dict[str, list[str]] = {}
        self._entry_points: set[str] = set()
        self._exit_points: set[str] = set()

    def add_node(
        self,
        node_id: str,
        name: str,
        description: str = "",
        task_type: str = "default",
        required_capabilities: list[str] | None = None,
        priority: int = 5,
        optional: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> DAGBuilder:
        """Add a node to the DAG.

        Args:
            node_id: Unique identifier for the node
            name: Display name of the node
            description: Description of the task
            task_type: Type of the task
            required_capabilities: Required agent capabilities
            priority: Task priority
            optional: Whether the task is optional
            metadata: Additional metadata

        Returns:
            Self for chaining
        """
        if node_id in self._nodes:
            logger.warning(f"Node {node_id} already exists, overwriting")

        self._nodes[node_id] = NodeData(
            name=name,
            description=description,
            task_type=task_type,
            required_capabilities=required_capabilities or [],
            priority=priority,
            optional=optional,
            metadata=metadata or {},
        )

        if node_id not in self._adjacency:
            self._adjacency[node_id] = []
        if node_id not in self._reverse_adjacency:
            self._reverse_adjacency[node_id] = []

        return self

    def add_edge(
        self,
        from_node: str,
        to_node: str,
        dependency_type: str = "default",
        weight: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> DAGBuilder:
        """Add an edge between two nodes.

        Args:
            from_node: Source node ID
            to_node: Target node ID
            dependency_type: Type of dependency
            weight: Weight of the edge
            metadata: Additional metadata

        Returns:
            Self for chaining
        """
        if from_node not in self._nodes:
            raise ValueError(f"Source node {from_node} does not exist")
        if to_node not in self._nodes:
            raise ValueError(f"Target node {to_node} does not exist")

        self._edges.append(
            (
                from_node,
                to_node,
                EdgeData(
                    dependency_type=dependency_type,
                    weight=weight,
                    metadata=metadata or {},
                ),
            )
        )

        self._adjacency[from_node].append(to_node)
        self._reverse_adjacency[to_node].append(from_node)

        self._entry_points.discard(to_node)
        self._entry_points.add(from_node)

        self._exit_points.discard(from_node)
        self._exit_points.add(to_node)

        if not self._entry_points:
            self._entry_points.add(from_node)
        if not self._exit_points:
            self._exit_points.add(to_node)

        return self

    def add_dependency(self, node: str, depends_on: str | list[str]) -> DAGBuilder:
        """Add a dependency for a node.

        Args:
            node: The dependent node
            depends_on: The node(s) that this node depends on

        Returns:
            Self for chaining
        """
        if isinstance(depends_on, str):
            depends_on = [depends_on]

        for dep in depends_on:
            self.add_edge(dep, node)

        return self

    def build(self) -> dict[str, NodeData]:
        """Build and return the DAG.

        Returns:
            Dictionary of node_id to NodeData
        """
        if not self._validate_dag():
            logger.warning("DAG validation failed - may contain cycles")

        return self._nodes.copy()

    def _validate_dag(self) -> bool:
        """Validate that the graph is a DAG (no cycles).

        Returns:
            True if valid DAG, False otherwise
        """
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in self._adjacency.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for node in self._nodes:
            if node not in visited:
                if has_cycle(node):
                    return False

        return True

    def get_execution_order(self) -> list[str]:
        """Get topological sort of nodes for execution.

        Returns:
            List of node IDs in execution order
        """
        in_degree = {node: 0 for node in self._nodes}

        for from_node, to_node, _ in self._edges:
            in_degree[to_node] += 1

        queue = [node for node, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)

            for neighbor in self._adjacency.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(self._nodes):
            logger.warning("Graph contains cycles, returning partial order")
            remaining = [n for n in self._nodes if n not in result]
            result.extend(remaining)

        return result

    def get_parallel_batches(self) -> list[list[str]]:
        """Get nodes grouped into parallel execution batches.

        Returns:
            List of batches, where each batch contains node IDs
            that can be executed in parallel
        """
        in_degree = {node: 0 for node in self._nodes}

        for from_node, to_node, _ in self._edges:
            in_degree[to_node] += 1

        batches: list[list[str]] = []
        remaining = set(self._nodes.keys())

        while remaining:
            batch = [node for node in remaining if in_degree[node] == 0]

            if not batch:
                logger.warning("Circular dependency detected, breaking")
                batch = list(remaining)
                remaining.clear()
            else:
                batches.append(batch)
                remaining -= set(batch)

                for node in batch:
                    for neighbor in self._adjacency.get(node, []):
                        if neighbor in remaining:
                            in_degree[neighbor] -= 1

        return batches

    def get_ready_nodes(self, completed: set[str]) -> list[str]:
        """Get nodes that are ready to execute given completed nodes.

        Args:
            completed: Set of completed node IDs

        Returns:
            List of node IDs that can now be executed
        """
        ready = []

        for node in self._nodes:
            if node in completed:
                continue

            dependencies = self._reverse_adjacency.get(node, [])
            if all(dep in completed for dep in dependencies):
                ready.append(node)

        return sorted(ready, key=lambda n: self._nodes[n].priority, reverse=True)

    def get_node_count(self) -> int:
        """Get the number of nodes in the DAG."""
        return len(self._nodes)

    def get_edge_count(self) -> int:
        """Get the number of edges in the DAG."""
        return len(self._edges)

    def get_entry_points(self) -> list[str]:
        """Get the entry points of the DAG."""
        return list(self._entry_points)

    def get_exit_points(self) -> list[str]:
        """Get the exit points of the DAG."""
        return list(self._exit_points)

    def get_dependencies(self, node: str) -> list[str]:
        """Get the dependencies of a node.

        Args:
            node: The node ID

        Returns:
            List of node IDs this node depends on
        """
        return self._reverse_adjacency.get(node, [])

    def get_dependents(self, node: str) -> list[str]:
        """Get the nodes that depend on this node.

        Args:
            node: The node ID

        Returns:
            List of node IDs that depend on this node
        """
        return self._adjacency.get(node, [])

    def visualize(self) -> str:
        """Create a text visualization of the DAG.

        Returns:
            String representation of the DAG
        """
        lines = ["DAG Structure:", "=" * 40]

        for node_id, node_data in self._nodes.items():
            lines.append(f"\nNode: {node_id}")
            lines.append(f"  Name: {node_data.name}")
            lines.append(f"  Type: {node_data.task_type}")
            lines.append(f"  Priority: {node_data.priority}")

            deps = self.get_dependencies(node_id)
            if deps:
                lines.append(f"  Dependencies: {', '.join(deps)}")

            dependents = self.get_dependents(node_id)
            if dependents:
                lines.append(f"  Dependents: {', '.join(dependents)}")

        return "\n".join(lines)


def create_dag_builder() -> DAGBuilder:
    """Factory function to create a DAGBuilder.

    Returns:
        A DAGBuilder instance
    """
    return DAGBuilder()
