"""Data models for directed acyclic graph (DAG) based task decomposition."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from openhands.sdk.spec.task_node import TaskNode, TaskStatus


class TaskGraph(BaseModel):
    """Directed Acyclic Graph (DAG) for task decomposition.

    This model represents a collection of tasks with their dependencies,
    forming a DAG that can be executed in topological order.

    Attributes:
        nodes: Dictionary of task nodes keyed by task ID
        edges: List of directed edges (from_id, to_id) representing dependencies
        metadata: Additional metadata for the task graph
    """

    model_config = {"extra": "forbid"}

    nodes: dict[str, TaskNode] = Field(
        default_factory=dict,
        description="Dictionary of task nodes keyed by task ID",
    )
    edges: list[tuple[str, str]] = Field(
        default_factory=list,
        description="List of directed edges (from_id, to_id) representing dependencies",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for the task graph",
    )

    def add_node(self, node: TaskNode) -> None:
        """Add a task node to the graph.

        Args:
            node: The task node to add
        """
        self.nodes[node.id] = node

    def add_edge(self, from_id: str, to_id: str) -> None:
        """Add a directed edge between two nodes.

        Args:
            from_id: ID of the source task (must complete first)
            to_id: ID of the target task (depends on source)

        Raises:
            ValueError: If either node doesn't exist in the graph
        """
        if from_id not in self.nodes:
            raise ValueError(f"Source node {from_id} not found in graph")
        if to_id not in self.nodes:
            raise ValueError(f"Target node {to_id} not found in graph")

        edge = (from_id, to_id)
        if edge not in self.edges:
            self.edges.append(edge)
            # Add to_id's dependency to from_id
            self.nodes[to_id].add_dependency(from_id)

    def get_node(self, task_id: str) -> TaskNode | None:
        """Get a task node by ID.

        Args:
            task_id: The ID of the task to retrieve

        Returns:
            The task node if found, None otherwise
        """
        return self.nodes.get(task_id)

    def get_ready_tasks(self) -> list[TaskNode]:
        """Get tasks that are ready to execute.

        A task is ready if:
        - Its status is PENDING
        - All its dependencies have completed

        Returns:
            List of task nodes that are ready to execute
        """
        ready = []
        for node in self.nodes.values():
            if node.status != TaskStatus.PENDING:
                continue
            if self._all_dependencies_completed(node):
                ready.append(node)
        return sorted(ready, key=lambda n: n.priority.value, reverse=True)

    def get_running_tasks(self) -> list[TaskNode]:
        """Get all currently running tasks.

        Returns:
            List of task nodes with RUNNING status
        """
        return [
            node for node in self.nodes.values() if node.status == TaskStatus.RUNNING
        ]

    def get_completed_tasks(self) -> list[TaskNode]:
        """Get all completed tasks.

        Returns:
            List of task nodes with COMPLETED status
        """
        return [
            node for node in self.nodes.values() if node.status == TaskStatus.COMPLETED
        ]

    def get_failed_tasks(self) -> list[TaskNode]:
        """Get all failed tasks.

        Returns:
            List of task nodes with FAILED status
        """
        return [
            node for node in self.nodes.values() if node.status == TaskStatus.FAILED
        ]

    def get_blocked_tasks(self) -> list[TaskNode]:
        """Get all blocked tasks.

        A task is blocked if any of its dependencies have failed.

        Returns:
            List of task nodes that are blocked
        """
        blocked = []
        for node in self.nodes.values():
            if node.status != TaskStatus.PENDING:
                continue
            if self._has_failed_dependency(node):
                blocked.append(node)
        return blocked

    def is_complete(self) -> bool:
        """Check if all tasks are completed.

        Returns:
            True if all tasks have COMPLETED status
        """
        return all(node.status == TaskStatus.COMPLETED for node in self.nodes.values())

    def has_failures(self) -> bool:
        """Check if any tasks have failed.

        Returns:
            True if any task has FAILED status
        """
        return any(node.status == TaskStatus.FAILED for node in self.nodes.values())

    def get_execution_order(self) -> list[str]:
        """Get topological order of tasks for execution.

        Returns:
            List of task IDs in topological order

        Raises:
            ValueError: If the graph contains a cycle
        """
        in_degree = {node_id: 0 for node_id in self.nodes}
        for _, to_id in self.edges:
            in_degree[to_id] += 1

        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            node_id = queue.pop(0)
            result.append(node_id)

            for from_id, to_id in self.edges:
                if from_id == node_id:
                    in_degree[to_id] -= 1
                    if in_degree[to_id] == 0:
                        queue.append(to_id)

        if len(result) != len(self.nodes):
            raise ValueError("Graph contains a cycle")

        return result

    def _all_dependencies_completed(self, node: TaskNode) -> bool:
        """Check if all dependencies of a node have completed."""
        for dep_id in node.dependencies:
            dep_node = self.nodes.get(dep_id)
            if dep_node is None or dep_node.status != TaskStatus.COMPLETED:
                return False
        return True

    def _has_failed_dependency(self, node: TaskNode) -> bool:
        """Check if any dependency of a node has failed."""
        for dep_id in node.dependencies:
            dep_node = self.nodes.get(dep_id)
            if dep_node is not None and dep_node.status == TaskStatus.FAILED:
                return True
        return False

    def get_dependencies(self, task_id: str) -> list[str]:
        """Get all tasks that a given task depends on.

        Args:
            task_id: The ID of the task

        Returns:
            List of task IDs that must complete before the given task
        """
        node = self.nodes.get(task_id)
        return node.dependencies if node else []

    def get_dependents(self, task_id: str) -> list[str]:
        """Get all tasks that depend on a given task.

        Args:
            task_id: The ID of the task

        Returns:
            List of task IDs that depend on the given task
        """
        dependents = []
        for from_id, to_id in self.edges:
            if from_id == task_id:
                dependents.append(to_id)
        return dependents

    def iterate_nodes(self):
        """Iterate over all task nodes in the graph."""
        return iter(self.nodes.values())

    def __len__(self) -> int:
        """Get the number of tasks in the graph."""
        return len(self.nodes)
