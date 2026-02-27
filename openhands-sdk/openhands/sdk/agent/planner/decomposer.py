"""Task decomposition logic for PlannerAgent.

This module provides the task decomposition logic that breaks down
formal specifications into executable tasks.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar


logger = logging.getLogger(__name__)


class TaskType(str, Enum):
    """Types of tasks in the decomposition."""

    ANALYSIS = "analysis"
    DESIGN = "design"
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    VERIFICATION = "verification"
    DOCUMENTATION = "documentation"
    INTEGRATION = "integration"
    DEPLOYMENT = "deployment"


class DecompositionStrategy(str, Enum):
    """Strategies for task decomposition."""

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HYBRID = "hybrid"
    PIPELINE = "pipeline"


@dataclass
class TaskTemplate:
    """Template for generating tasks."""

    name: str
    description: str
    task_type: TaskType
    required_capabilities: list[str]
    dependencies: list[str] = field(default_factory=list)
    priority: int = 5
    optional: bool = False
    estimated_duration: int | None = None


@dataclass
class DecomposedTask:
    """A task resulting from decomposition."""

    name: str
    description: str
    task_type: TaskType
    required_capabilities: list[str]
    dependencies: list[str] = field(default_factory=list)
    priority: int = 5
    optional: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class TaskDecomposer:
    """Decomposes specifications into executable tasks.

    The decomposer analyzes specifications and generates a set of
    tasks that can be executed by agents.
    """

    DEFAULT_TASK_TEMPLATES: ClassVar[dict[str, list[TaskTemplate]]] = {
        "api": [
            TaskTemplate(
                name="design_api_schema",
                description="Design REST API schema and endpoints",
                task_type=TaskType.DESIGN,
                required_capabilities=["api_design", "rest"],
            ),
            TaskTemplate(
                name="implement_api",
                description="Implement API endpoints",
                task_type=TaskType.IMPLEMENTATION,
                required_capabilities=["code_generation", "backend"],
                dependencies=["design_api_schema"],
            ),
            TaskTemplate(
                name="write_api_tests",
                description="Write API integration tests",
                task_type=TaskType.TESTING,
                required_capabilities=["testing", "api_testing"],
                dependencies=["implement_api"],
            ),
        ],
        "database": [
            TaskTemplate(
                name="design_schema",
                description="Design database schema",
                task_type=TaskType.DESIGN,
                required_capabilities=["database_design", "sql"],
            ),
            TaskTemplate(
                name="create_migrations",
                description="Create database migrations",
                task_type=TaskType.IMPLEMENTATION,
                required_capabilities=["database", "migration"],
                dependencies=["design_schema"],
            ),
            TaskTemplate(
                name="write_migration_tests",
                description="Write migration tests",
                task_type=TaskType.TESTING,
                required_capabilities=["testing", "database_testing"],
                dependencies=["create_migrations"],
            ),
        ],
        "web": [
            TaskTemplate(
                name="design_ui",
                description="Design user interface components",
                task_type=TaskType.DESIGN,
                required_capabilities=["ui_design", "frontend"],
            ),
            TaskTemplate(
                name="implement_components",
                description="Implement UI components",
                task_type=TaskType.IMPLEMENTATION,
                required_capabilities=["code_generation", "frontend"],
                dependencies=["design_ui"],
            ),
            TaskTemplate(
                name="write_component_tests",
                description="Write component tests",
                task_type=TaskType.TESTING,
                required_capabilities=["testing", "frontend_testing"],
                dependencies=["implement_components"],
            ),
        ],
    }

    CORE_TASKS: ClassVar[list[TaskTemplate]] = [
        TaskTemplate(
            name="analyze_requirements",
            description="Analyze and understand requirements",
            task_type=TaskType.ANALYSIS,
            required_capabilities=["research", "analysis"],
            priority=10,
        ),
        TaskTemplate(
            name="generate_spec",
            description="Generate formal specification",
            task_type=TaskType.DESIGN,
            required_capabilities=["spec_generation", "formal_methods"],
            dependencies=["analyze_requirements"],
            priority=9,
        ),
        TaskTemplate(
            name="validate_spec",
            description="Validate specification correctness",
            task_type=TaskType.VERIFICATION,
            required_capabilities=["verification", "formal_methods"],
            dependencies=["generate_spec"],
            priority=9,
        ),
        TaskTemplate(
            name="decompose_tasks",
            description="Decompose specification into tasks",
            task_type=TaskType.ANALYSIS,
            required_capabilities=["planning", "decomposition"],
            dependencies=["validate_spec"],
            priority=8,
        ),
        TaskTemplate(
            name="allocate_roles",
            description="Allocate agents to tasks",
            task_type=TaskType.ANALYSIS,
            required_capabilities=["agent_matching", "planning"],
            dependencies=["decompose_tasks"],
            priority=7,
        ),
        TaskTemplate(
            name="generate_code",
            description="Generate implementation code",
            task_type=TaskType.IMPLEMENTATION,
            required_capabilities=["code_generation"],
            dependencies=["allocate_roles"],
            priority=7,
        ),
        TaskTemplate(
            name="verify_code",
            description="Verify code against specification",
            task_type=TaskType.VERIFICATION,
            required_capabilities=["verification", "testing"],
            dependencies=["generate_code"],
            priority=6,
        ),
        TaskTemplate(
            name="evaluate_candidates",
            description="Evaluate generated code candidates",
            task_type=TaskType.TESTING,
            required_capabilities=["evaluation", "ranking"],
            dependencies=["verify_code"],
            priority=5,
        ),
        TaskTemplate(
            name="write_tests",
            description="Write unit and integration tests",
            task_type=TaskType.TESTING,
            required_capabilities=["testing"],
            dependencies=["generate_code"],
            priority=5,
            optional=True,
        ),
        TaskTemplate(
            name="create_documentation",
            description="Create code documentation",
            task_type=TaskType.DOCUMENTATION,
            required_capabilities=["documentation"],
            dependencies=["generate_code"],
            priority=3,
            optional=True,
        ),
    ]

    def __init__(
        self,
        custom_templates: dict[str, list[TaskTemplate]] | None = None,
        strategy: DecompositionStrategy = DecompositionStrategy.HYBRID,
    ):
        """Initialize the task decomposer.

        Args:
            custom_templates: Custom task templates for specific domains
            strategy: The decomposition strategy to use
        """
        self._templates = self.DEFAULT_TASK_TEMPLATES.copy()
        if custom_templates:
            self._templates.update(custom_templates)
        self.strategy = strategy

    def decompose(
        self,
        spec_name: str,
        spec_content: str,  # noqa: ARG002
        domain: str | None = None,
    ) -> list[DecomposedTask]:
        """Decompose a specification into tasks.

        Args:
            spec_name: Name of the specification
            spec_content: Content of the specification (passed for compatibility)
            domain: Optional domain for template selection

        Returns:
            List of DecomposedTask objects
        """
        tasks: list[DecomposedTask] = []

        tasks.extend(self._get_core_tasks())

        if domain and domain in self._templates:
            tasks.extend(self._get_domain_tasks(domain))

        tasks = self._resolve_dependencies(tasks)

        tasks = self._prioritize_tasks(tasks)

        logger.info(f"Decomposed spec '{spec_name}' into {len(tasks)} tasks")

        return tasks

    def _get_core_tasks(self) -> list[DecomposedTask]:
        """Get the core tasks for any specification."""
        return [
            DecomposedTask(
                name=template.name,
                description=template.description,
                task_type=template.task_type,
                required_capabilities=template.required_capabilities,
                dependencies=template.dependencies.copy(),
                priority=template.priority,
                optional=template.optional,
            )
            for template in self.CORE_TASKS
        ]

    def _get_domain_tasks(self, domain: str) -> list[DecomposedTask]:
        """Get domain-specific tasks."""
        templates = self._templates.get(domain, [])
        return [
            DecomposedTask(
                name=template.name,
                description=template.description,
                task_type=template.task_type,
                required_capabilities=template.required_capabilities,
                dependencies=template.dependencies.copy(),
                priority=template.priority,
                optional=template.optional,
            )
            for template in templates
        ]

    def _resolve_dependencies(
        self, tasks: list[DecomposedTask]
    ) -> list[DecomposedTask]:
        """Resolve and validate task dependencies."""
        {task.name for task in tasks}

        resolved_tasks: list[DecomposedTask] = []
        resolved_names: set[str] = set()

        while len(resolved_tasks) < len(tasks):
            made_progress = False

            for task in tasks:
                if task.name in resolved_names:
                    continue

                unresolved_deps = [
                    dep for dep in task.dependencies if dep not in resolved_names
                ]

                if not unresolved_deps:
                    resolved_tasks.append(task)
                    resolved_names.add(task.name)
                    made_progress = True

            if not made_progress:
                logger.warning(
                    "Circular dependency detected, "
                    "adding remaining tasks without resolution"
                )
                remaining = [t for t in tasks if t.name not in resolved_names]
                resolved_tasks.extend(remaining)
                break

        return resolved_tasks

    def _prioritize_tasks(self, tasks: list[DecomposedTask]) -> list[DecomposedTask]:
        """Prioritize tasks based on strategy."""
        if self.strategy == DecompositionStrategy.SEQUENTIAL:
            return sorted(tasks, key=lambda t: t.priority, reverse=True)

        elif self.strategy == DecompositionStrategy.PARALLEL:
            return tasks

        elif self.strategy == DecompositionStrategy.HYBRID:
            sequential_phases = [
                TaskType.ANALYSIS,
                TaskType.DESIGN,
            ]
            parallel_phases = [
                TaskType.IMPLEMENTATION,
                TaskType.TESTING,
            ]

            prioritized = []
            for phase in sequential_phases:
                phase_tasks = [t for t in tasks if t.task_type == phase]
                prioritized.extend(
                    sorted(phase_tasks, key=lambda t: t.priority, reverse=True)
                )

            parallel_tasks = [t for t in tasks if t.task_type in parallel_phases]
            prioritized.extend(parallel_tasks)

            for phase in [TaskType.VERIFICATION, TaskType.DOCUMENTATION]:
                phase_tasks = [t for t in tasks if t.task_type == phase]
                prioritized.extend(
                    sorted(phase_tasks, key=lambda t: t.priority, reverse=True)
                )

            return prioritized

        return tasks

    def add_template(self, domain: str, template: TaskTemplate) -> None:
        """Add a task template for a domain.

        Args:
            domain: The domain name
            template: The task template to add
        """
        if domain not in self._templates:
            self._templates[domain] = []
        self._templates[domain].append(template)

    def get_template(self, domain: str, name: str) -> TaskTemplate | None:
        """Get a specific template.

        Args:
            domain: The domain name
            name: The template name

        Returns:
            The TaskTemplate or None if not found
        """
        for template in self._templates.get(domain, []):
            if template.name == name:
                return template
        return None


def create_decomposer(
    custom_templates: dict[str, list[TaskTemplate]] | None = None,
    strategy: DecompositionStrategy = DecompositionStrategy.HYBRID,
) -> TaskDecomposer:
    """Factory function to create a TaskDecomposer.

    Args:
        custom_templates: Optional custom task templates
        strategy: The decomposition strategy

    Returns:
        A TaskDecomposer instance
    """
    return TaskDecomposer(custom_templates=custom_templates, strategy=strategy)
