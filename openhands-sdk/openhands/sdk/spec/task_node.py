"""Data models for task nodes in the task graph."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Status of a task node in the execution flow."""

    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class TaskPriority(int, Enum):
    """Priority level for task execution."""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class TaskNode(BaseModel):
    """Represents a single task in the task decomposition graph.

    Each task node contains the necessary information for execution,
    including dependencies, status, and result data.

    Attributes:
        id: Unique identifier for the task
        name: Human-readable name for the task
        description: Detailed description of what the task accomplishes
        status: Current execution status of the task
        priority: Priority level for execution order
        dependencies: List of task IDs that must complete before this task
        required_capabilities: List of capabilities required to execute this task
        input_data: Input data required for task execution
        output_data: Output data produced by the task
        assigned_agent: ID of the agent assigned to execute this task
        created_at: Timestamp when the task was created
        started_at: Timestamp when task execution started
        completed_at: Timestamp when task execution completed
        error_message: Error message if task failed
        metadata: Additional metadata for the task
    """

    model_config = {"extra": "forbid"}

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for the task",
    )
    name: str = Field(
        description="Human-readable name for the task",
    )
    description: str = Field(
        default="",
        description="Detailed description of what the task accomplishes",
    )
    status: TaskStatus = Field(
        default=TaskStatus.PENDING,
        description="Current execution status of the task",
    )
    priority: TaskPriority = Field(
        default=TaskPriority.NORMAL,
        description="Priority level for execution order",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="List of task IDs that must complete before this task",
    )
    required_capabilities: list[str] = Field(
        default_factory=list,
        description="List of capabilities required to execute this task",
    )
    input_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Input data required for task execution",
    )
    output_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Output data produced by the task",
    )
    assigned_agent: str | None = Field(
        default=None,
        description="ID of the agent assigned to execute this task",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the task was created",
    )
    started_at: datetime | None = Field(
        default=None,
        description="Timestamp when task execution started",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="Timestamp when task execution completed",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if task failed",
    )
    retry_count: int = Field(
        default=0,
        description="Number of times the task has been retried",
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of retries allowed",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for the task",
    )

    def mark_ready(self) -> None:
        """Mark the task as ready for execution."""
        self.status = TaskStatus.READY

    def mark_running(self) -> None:
        """Mark the task as currently running."""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.utcnow()

    def mark_completed(self, output_data: dict[str, Any] | None = None) -> None:
        """Mark the task as completed successfully."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        if output_data:
            self.output_data = output_data

    def mark_failed(self, error_message: str) -> None:
        """Mark the task as failed with an error message."""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message

    def can_retry(self) -> bool:
        """Check if the task can be retried."""
        return self.retry_count < self.max_retries

    def increment_retry(self) -> None:
        """Increment the retry count and reset status to ready."""
        self.retry_count += 1
        self.status = TaskStatus.READY
        self.started_at = None
        self.completed_at = None
        self.error_message = None

    def is_blocked_by(self, task_id: str) -> bool:
        """Check if this task is blocked by another task."""
        return task_id in self.dependencies

    def add_dependency(self, task_id: str) -> None:
        """Add a dependency to this task."""
        if task_id not in self.dependencies:
            self.dependencies.append(task_id)

    def remove_dependency(self, task_id: str) -> None:
        """Remove a dependency from this task."""
        if task_id in self.dependencies:
            self.dependencies.remove(task_id)
