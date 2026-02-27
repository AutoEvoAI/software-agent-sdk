"""Dependency analyzer for task graphs.

This module provides dependency analysis for tasks, including
detecting implicit dependencies, circular references, and optimization opportunities.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar


logger = logging.getLogger(__name__)


class DependencyType(str, Enum):
    """Types of dependencies between tasks."""

    REQUIRED = "required"
    OPTIONAL = "optional"
    SOFT = "soft"
    IMPLIED = "implied"


class DependencyStrength(str, Enum):
    """Strength of dependency relationship."""

    STRONG = "strong"
    MEDIUM = "medium"
    WEAK = "weak"


@dataclass
class Dependency:
    """Represents a dependency between two tasks."""

    source: str
    target: str
    dependency_type: DependencyType = DependencyType.REQUIRED
    strength: DependencyStrength = DependencyStrength.STRONG
    description: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DependencyAnalysis:
    """Results of dependency analysis."""

    dependencies: list[Dependency] = field(default_factory=list)
    implied_dependencies: list[Dependency] = field(default_factory=list)
    circular_refs: list[list[str]] = field(default_factory=list)
    isolated_nodes: list[str] = field(default_factory=list)
    critical_path: list[str] = field(default_factory=list)
    parallelizable_groups: list[list[str]] = field(default_factory=list)


class DependencyAnalyzer:
    """Analyzes dependencies between tasks.

    The analyzer detects:
    - Explicit dependencies
    - Implied dependencies (from shared resources, data flow)
    - Circular references
    - Critical path
    - Parallelization opportunities
    """

    RESOURCE_PATTERNS: ClassVar[dict[str, list[str]]] = {
        "database": ["query", "schema", "table", "migration", "transaction"],
        "file": ["read", "write", "file", "path", "directory"],
        "api": ["endpoint", "request", "response", "http", "rest"],
        "memory": ["cache", "store", "session", "variable"],
    }

    def __init__(self):
        """Initialize the dependency analyzer."""
        self._dependencies: list[Dependency] = []

    def add_dependency(
        self,
        source: str,
        target: str,
        dependency_type: DependencyType = DependencyType.REQUIRED,
        strength: DependencyStrength = DependencyStrength.STRONG,
        description: str | None = None,
    ) -> None:
        """Add a dependency.

        Args:
            source: Source task ID
            target: Target task ID
            dependency_type: Type of dependency
            strength: Strength of dependency
            description: Optional description
        """
        self._dependencies.append(
            Dependency(
                source=source,
                target=target,
                dependency_type=dependency_type,
                strength=strength,
                description=description,
            )
        )

    def analyze(
        self,
        tasks: dict[str, dict[str, Any]],
    ) -> DependencyAnalysis:
        """Analyze dependencies between tasks.

        Args:
            tasks: Dictionary of task_id to task data

        Returns:
            DependencyAnalysis object
        """
        analysis = DependencyAnalysis()

        for task_id, task_data in tasks.items():
            deps = task_data.get("dependencies", [])
            if isinstance(deps, str):
                deps = [deps]
            for dep in deps:
                self.add_dependency(dep, task_id)

        analysis.dependencies = self._dependencies.copy()

        analysis.implied_dependencies = self._find_implied_dependencies(tasks)

        analysis.circular_refs = self._find_circular_references(tasks)

        analysis.isolated_nodes = self._find_isolated_nodes(tasks)

        analysis.critical_path = self._find_critical_path(tasks)

        analysis.parallelizable_groups = self._find_parallelizable_groups(tasks)

        return analysis

    def _find_implied_dependencies(
        self, tasks: dict[str, dict[str, Any]]
    ) -> list[Dependency]:
        """Find implied dependencies based on resource usage.

        Args:
            tasks: Dictionary of task_id to task data

        Returns:
            List of implied dependencies
        """
        implied: list[Dependency] = []
        resource_map: dict[str, list[str]] = {}

        for task_id, task_data in tasks.items():
            resources = task_data.get("resources", [])
            for resource in resources:
                if resource not in resource_map:
                    resource_map[resource] = []
                resource_map[resource].append(task_id)

        for resource, task_ids in resource_map.items():
            if len(task_ids) > 1:
                for i in range(len(task_ids) - 1):
                    implied.append(
                        Dependency(
                            source=task_ids[i],
                            target=task_ids[i + 1],
                            dependency_type=DependencyType.IMPLIED,
                            strength=DependencyStrength.MEDIUM,
                            description=(
                                f"Implied dependency via shared resource: {resource}"
                            ),
                        )
                    )

        return implied

    def _find_circular_references(
        self, tasks: dict[str, dict[str, Any]]
    ) -> list[list[str]]:
        """Find circular references in the task dependencies.

        Args:
            tasks: Dictionary of task_id to task data

        Returns:
            List of circular reference paths
        """
        cycles: list[list[str]] = []
        visited: set[str] = set()
        rec_stack: set[str] = set()

        adjacency = self._build_adjacency(tasks)

        def find_cycle(node: str, path: list[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in adjacency.get(node, []):
                if neighbor not in visited:
                    find_cycle(neighbor, path.copy())
                elif neighbor in rec_stack:
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    if cycle not in cycles:
                        cycles.append(cycle)

            rec_stack.remove(node)

        for task_id in tasks:
            if task_id not in visited:
                find_cycle(task_id, [])

        return cycles

    def _find_isolated_nodes(self, tasks: dict[str, dict[str, Any]]) -> list[str]:
        """Find nodes with no dependencies.

        Args:
            tasks: Dictionary of task_id to task data

        Returns:
            List of isolated node IDs
        """
        isolated = []
        all_deps: set[str] = set()

        for task_data in tasks.values():
            deps = task_data.get("dependencies", [])
            if isinstance(deps, str):
                deps = [deps]
            all_deps.update(deps)

        for task_id in tasks:
            if task_id not in all_deps:
                deps = tasks[task_id].get("dependencies", [])
                if isinstance(deps, str):
                    deps = [deps]
                if not deps:
                    isolated.append(task_id)

        return isolated

    def _find_critical_path(self, tasks: dict[str, dict[str, Any]]) -> list[str]:
        """Find the critical path through the task graph.

        Args:
            tasks: Dictionary of task_id to task data

        Returns:
            List of task IDs on the critical path
        """
        adjacency = self._build_adjacency(tasks)
        reverse_adj = self._build_reverse_adjacency(tasks)

        in_degree = {task_id: len(reverse_adj.get(task_id, [])) for task_id in tasks}
        out_degree = {task_id: len(adjacency.get(task_id, [])) for task_id in tasks}

        entry_points = [t for t, d in in_degree.items() if d == 0]
        exit_points = [t for t, d in out_degree.items() if d == 0]

        if not entry_points:
            return []

        earliest: dict[str, float] = {}
        latest: dict[str, float] = {}

        for task_id in tasks:
            earliest[task_id] = 0
            latest[task_id] = float("inf")

        for node in self._topological_sort(tasks):
            for neighbor in adjacency.get(node, []):
                if neighbor not in earliest:
                    continue
                duration = tasks[neighbor].get("duration", 1)
                earliest[neighbor] = max(earliest[neighbor], earliest[node] + duration)

        if not exit_points:
            exit_points = list(tasks.keys())

        max_finish = max(earliest.get(ep, 0) for ep in exit_points)

        for task_id in exit_points:
            latest[task_id] = max_finish

        reverse_sorted = list(reversed(self._topological_sort(tasks)))

        for node in reverse_sorted:
            for neighbor in adjacency.get(node, []):
                if neighbor not in latest:
                    continue
                latest[node] = min(
                    latest[node], latest[neighbor] - tasks[neighbor].get("duration", 1)
                )

        critical_path = []
        current = entry_points[0] if entry_points else None

        while current:
            critical_path.append(current)
            next_nodes = adjacency.get(current, [])

            if not next_nodes:
                break

            next_critical = None
            for next_node in next_nodes:
                if (
                    latest[next_node] - tasks[next_node].get("duration", 1)
                    == latest[current]
                ):
                    next_critical = next_node
                    break

            current = next_critical

        return critical_path

    def _find_parallelizable_groups(
        self, tasks: dict[str, dict[str, Any]]
    ) -> list[list[str]]:
        """Find groups of tasks that can be executed in parallel.

        Args:
            tasks: Dictionary of task_id to task data

        Returns:
            List of parallelizable task groups
        """
        groups: list[list[str]] = []
        reverse_adj = self._build_reverse_adjacency(tasks)

        remaining = set(tasks.keys())
        completed: set[str] = set()

        while remaining:
            ready = [
                task_id
                for task_id in remaining
                if all(dep in completed for dep in reverse_adj.get(task_id, []))
            ]

            if not ready:
                logger.warning("Circular dependency detected, breaking")
                groups.append(list(remaining))
                break

            groups.append(ready)
            completed.update(ready)
            remaining -= set(ready)

        return groups

    def _build_adjacency(
        self, tasks: dict[str, dict[str, Any]]
    ) -> dict[str, list[str]]:
        """Build adjacency list from tasks.

        Args:
            tasks: Dictionary of task_id to task data

        Returns:
            Adjacency list
        """
        adjacency: dict[str, list[str]] = {task_id: [] for task_id in tasks}

        for task_id, task_data in tasks.items():
            deps = task_data.get("dependencies", [])
            if isinstance(deps, str):
                deps = [deps]
            for dep in deps:
                if dep in adjacency:
                    adjacency[dep].append(task_id)

        return adjacency

    def _build_reverse_adjacency(
        self, tasks: dict[str, dict[str, Any]]
    ) -> dict[str, list[str]]:
        """Build reverse adjacency list from tasks.

        Args:
            tasks: Dictionary of task_id to task data

        Returns:
            Reverse adjacency list
        """
        reverse_adj: dict[str, list[str]] = {task_id: [] for task_id in tasks}

        for task_id, task_data in tasks.items():
            deps = task_data.get("dependencies", [])
            if isinstance(deps, str):
                deps = [deps]
            for dep in deps:
                if dep in reverse_adj:
                    reverse_adj[task_id].append(dep)

        return reverse_adj

    def _topological_sort(self, tasks: dict[str, dict[str, Any]]) -> list[str]:
        """Perform topological sort on tasks.

        Args:
            tasks: Dictionary of task_id to task data

        Returns:
            Topologically sorted list of task IDs
        """
        reverse_adj = self._build_reverse_adjacency(tasks)
        in_degree = {task_id: len(reverse_adj.get(task_id, [])) for task_id in tasks}

        queue = [task_id for task_id, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)

            for neighbor in self._build_adjacency(tasks).get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return result


def create_dependency_analyzer() -> DependencyAnalyzer:
    """Factory function to create a DependencyAnalyzer.

    Returns:
        A DependencyAnalyzer instance
    """
    return DependencyAnalyzer()
