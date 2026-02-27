"""Dynamic role allocator for task-agent matching."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from openhands.sdk.logger import get_logger
from openhands.sdk.spec import AgentCapability, AgentProfile, TaskNode
from openhands.sdk.subagent.profile_registry import (
    AgentProfileRegistry,
    get_global_registry,
)


if TYPE_CHECKING:
    pass


logger = get_logger(__name__)


class DynamicRoleAllocator:
    """Dynamic role allocator for matching tasks to optimal agents.

    The DynamicRoleAllocator is responsible for:
    1. Matching tasks to agents based on required capabilities
    2. Load balancing across available agents
    3. Selecting optimal agents based on success rate and performance

    Example:
        >>> from openhands.sdk.agent.planner import DynamicRoleAllocator
        >>> allocator = DynamicRoleAllocator()
        >>> best_agent = allocator.allocate(task, available_agents)
    """

    def __init__(
        self,
        registry: AgentProfileRegistry | None = None,
    ):
        """Initialize the dynamic role allocator.

        Args:
            registry: Optional agent profile registry.
            Uses global registry if not provided.
        """
        self._registry = registry or get_global_registry()

    @property
    def registry(self) -> AgentProfileRegistry:
        """Get the agent profile registry."""
        return self._registry

    def allocate(
        self,
        task: TaskNode,
        profiles: list[AgentProfile] | None = None,
    ) -> AgentProfile | None:
        """Allocate the best agent for a given task.

        Args:
            task: The task to allocate an agent for
            profiles: Optional list of profiles to choose from.
                     If None, uses all available profiles from registry.

        Returns:
            The best matching AgentProfile, or None if no suitable agent found
        """
        if profiles is None:
            profiles = self._registry.find_available()

        if not profiles:
            logger.warning("No available agents found for task: %s", task.name)
            return None

        required_caps = [
            AgentCapability(cap) if isinstance(cap, str) else cap
            for cap in task.required_capabilities
        ]

        if not required_caps:
            return self._select_best_by_load(profiles)

        matching = self._registry.find_by_capabilities(
            required_caps,
            must_have_all=True,
        )

        if not matching:
            matching = self._registry.find_by_capabilities(
                required_caps,
                must_have_all=False,
            )

        if not matching:
            logger.warning(
                "No agents with required capabilities for task: %s",
                task.name,
            )
            return self._select_best_by_load(profiles)

        return self._select_best_by_load(matching)

    def allocate_batch(
        self,
        tasks: list[TaskNode],
    ) -> dict[str, AgentProfile | None]:
        """Allocate agents for multiple tasks.

        Args:
            tasks: List of tasks to allocate agents for

        Returns:
            Dictionary mapping task IDs to allocated AgentProfiles
        """
        results = {}
        available = list(self._registry.find_available())

        for task in tasks:
            profile = self._allocate_with_tracking(task, available)
            results[task.id] = profile

            if profile:
                profile.increment_load()

        return results

    def _allocate_with_tracking(
        self,
        task: TaskNode,
        available: list[AgentProfile],
    ) -> AgentProfile | None:
        """Allocate an agent and track the selection."""
        return self.allocate(task, available)

    def _select_best_by_load(
        self,
        profiles: list[AgentProfile],
    ) -> AgentProfile | None:
        """Select the best profile based on load and success rate.

        Args:
            profiles: List of candidate profiles

        Returns:
            The best profile based on load and success rate
        """
        if not profiles:
            return None

        available = [p for p in profiles if p.can_accept_task()]
        if not available:
            return profiles[0]

        return max(
            available,
            key=lambda p: (
                p.success_rate,
                -p.avg_execution_time,
                p.current_load,
            ),
        )

    def release_agent(self, agent_id: str) -> bool:
        """Release an agent (decrement load) after task completion.

        Args:
            agent_id: The ID of the agent to release

        Returns:
            True if successful, False if agent not found
        """
        profile = self._registry.get(agent_id)
        if profile:
            profile.decrement_load()
            return True
        return False

    def get_stats(self) -> dict[str, Any]:
        """Get allocation statistics.

        Returns:
            Dictionary with allocation stats
        """
        all_profiles = self._registry.list_all()
        available = self._registry.find_available()

        return {
            "total_agents": len(all_profiles),
            "available_agents": len(available),
            "total_load": sum(p.current_load for p in all_profiles),
            "avg_success_rate": (
                sum(p.success_rate for p in all_profiles) / len(all_profiles)
                if all_profiles
                else 0.0
            ),
        }


def create_allocator(
    registry: AgentProfileRegistry | None = None,
) -> DynamicRoleAllocator:
    """Factory function to create a DynamicRoleAllocator.

    Args:
        registry: Optional agent profile registry.

    Returns:
        A configured DynamicRoleAllocator instance.
    """
    return DynamicRoleAllocator(registry=registry)
