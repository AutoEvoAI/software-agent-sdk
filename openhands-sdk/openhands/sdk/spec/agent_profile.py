"""Data models for agent capability profiles."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AgentCapability(str, Enum):
    """Capabilities that an agent can possess."""

    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    DEBUGGING = "debugging"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    REFACTORING = "refactoring"
    SECURITY_ANALYSIS = "security_analysis"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    DATA_ANALYSIS = "data_analysis"
    RESEARCH = "research"
    PLANNING = "planning"
    VERIFICATION = "verification"
    REPAIR = "repair"
    FILE_EDITING = "file_editing"
    TERMINAL = "terminal"
    BROWSER = "browser"
    WEB_SEARCH = "web_search"


class AgentProfile(BaseModel):
    """Profile of an agent's capabilities for dynamic task allocation.

    This model represents the capabilities, skills, and performance
    characteristics of an agent for the purpose of intelligent task routing.

    Attributes:
        agent_id: Unique identifier for the agent
        name: Human-readable name for the agent
        description: Description of what the agent does
        capabilities: List of capabilities the agent possesses
        languages: Programming languages the agent is proficient in
        frameworks: Frameworks the agent is familiar with
        success_rate: Historical success rate (0.0 to 1.0)
        avg_execution_time: Average execution time in seconds
        max_concurrent_tasks: Maximum number of tasks the agent can handle
        current_load: Current number of running tasks
        is_available: Whether the agent is available for new tasks
        cost_per_hour: Cost per hour for using this agent
        metadata: Additional metadata about the agent
        registered_at: Timestamp when the agent was registered
        last_used_at: Timestamp when the agent was last used
    """

    model_config = {"extra": "forbid"}

    agent_id: str = Field(
        description="Unique identifier for the agent",
    )
    name: str = Field(
        description="Human-readable name for the agent",
    )
    description: str = Field(
        default="",
        description="Description of what the agent does",
    )
    capabilities: list[AgentCapability] = Field(
        default_factory=list,
        description="List of capabilities the agent possesses",
    )
    languages: list[str] = Field(
        default_factory=list,
        description="Programming languages the agent is proficient in",
    )
    frameworks: list[str] = Field(
        default_factory=list,
        description="Frameworks the agent is familiar with",
    )
    success_rate: float = Field(
        default=1.0,
        description="Historical success rate (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
    )
    avg_execution_time: float = Field(
        default=60.0,
        description="Average execution time in seconds",
        ge=0.0,
    )
    max_concurrent_tasks: int = Field(
        default=5,
        description="Maximum number of tasks the agent can handle",
        ge=1,
    )
    current_load: int = Field(
        default=0,
        description="Current number of running tasks",
        ge=0,
    )
    is_available: bool = Field(
        default=True,
        description="Whether the agent is available for new tasks",
    )
    cost_per_hour: float = Field(
        default=0.0,
        description="Cost per hour for using this agent",
        ge=0.0,
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the agent",
    )
    registered_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the agent was registered",
    )
    last_used_at: datetime | None = Field(
        default=None,
        description="Timestamp when the agent was last used",
    )

    def has_capability(self, capability: AgentCapability) -> bool:
        """Check if the agent has a specific capability.

        Args:
            capability: The capability to check for

        Returns:
            True if the agent has the capability
        """
        return capability in self.capabilities

    def can_handle_task(self, required_capabilities: list[AgentCapability]) -> bool:
        """Check if the agent can handle a task with given requirements.

        Args:
            required_capabilities: List of capabilities required for the task

        Returns:
            True if the agent has all required capabilities
        """
        return all(cap in self.capabilities for cap in required_capabilities)

    def can_accept_task(self) -> bool:
        """Check if the agent can accept a new task.

        Returns:
            True if the agent is available and has capacity
        """
        return self.is_available and self.current_load < self.max_concurrent_tasks

    def increment_load(self) -> None:
        """Increment the current load when assigned a task."""
        if self.current_load < self.max_concurrent_tasks:
            self.current_load += 1
            self.last_used_at = datetime.utcnow()

    def decrement_load(self) -> None:
        """Decrement the current load when a task completes."""
        if self.current_load > 0:
            self.current_load -= 1

    def add_capability(self, capability: AgentCapability) -> None:
        """Add a capability to the agent.

        Args:
            capability: The capability to add
        """
        if capability not in self.capabilities:
            self.capabilities.append(capability)

    def remove_capability(self, capability: AgentCapability) -> None:
        """Remove a capability from the agent.

        Args:
            capability: The capability to remove
        """
        if capability in self.capabilities:
            self.capabilities.remove(capability)

    def update_success_rate(self, success: bool) -> None:
        """Update the success rate based on task outcome.

        Args:
            success: Whether the task succeeded
        """
        # Simple moving average with weight 0.1
        if success:
            self.success_rate = 0.9 * self.success_rate + 0.1 * 1.0
        else:
            self.success_rate = 0.9 * self.success_rate + 0.1 * 0.0

    def supports_language(self, language: str) -> bool:
        """Check if the agent supports a programming language.

        Args:
            language: The programming language to check

        Returns:
            True if the agent supports the language
        """
        return language.lower() in [lang.lower() for lang in self.languages]

    def supports_framework(self, framework: str) -> bool:
        """Check if the agent supports a framework.

        Args:
            framework: The framework to check

        Returns:
            True if the agent supports the framework
        """
        return framework.lower() in [fw.lower() for fw in self.frameworks]
