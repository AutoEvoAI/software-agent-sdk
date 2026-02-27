"""Agent capability profile registry for dynamic task allocation.

This module provides a registry for managing agent capability profiles,
enabling intelligent task routing based on agent capabilities.
"""

from collections.abc import Iterator
from threading import RLock

from openhands.sdk.logger import get_logger
from openhands.sdk.spec import AgentCapability, AgentProfile


logger = get_logger(__name__)


class AgentProfileRegistry:
    """Registry for managing agent capability profiles.

    This registry maintains profiles for all available agents,
    enabling dynamic task allocation based on capabilities.

    Example usage:
        from openhands.sdk.subagent import AgentProfileRegistry

        registry = AgentProfileRegistry()

        # Register an agent profile
        registry.register(
            AgentProfile(
                agent_id="codegen-1",
                name="Code Generator",
                capabilities=[AgentCapability.CODE_GENERATION],
                languages=["python", "javascript"],
            )
        )

        # Find agents with required capabilities
        suitable_agents = registry.find_by_capabilities(
            [AgentCapability.CODE_GENERATION]
        )
    """

    def __init__(self) -> None:
        """Initialize the agent profile registry."""
        self._profiles: dict[str, AgentProfile] = {}
        self._lock = RLock()

    def register(self, profile: AgentProfile) -> None:
        """Register an agent profile.

        Args:
            profile: The agent profile to register

        Raises:
            ValueError: If an agent with the same ID already exists
        """
        with self._lock:
            if profile.agent_id in self._profiles:
                raise ValueError(
                    f"Agent profile '{profile.agent_id}' already registered"
                )
            self._profiles[profile.agent_id] = profile
            logger.info(
                f"Registered agent profile: {profile.name} ({profile.agent_id})"
            )

    def register_if_absent(self, profile: AgentProfile) -> bool:
        """Register an agent profile if no profile with that ID exists.

        Args:
            profile: The agent profile to register

        Returns:
            True if the profile was registered, False if a profile with
            that ID already existed.
        """
        with self._lock:
            if profile.agent_id in self._profiles:
                return False
            self._profiles[profile.agent_id] = profile
            logger.info(
                f"Registered agent profile: {profile.name} ({profile.agent_id})"
            )
            return True

    def unregister(self, agent_id: str) -> bool:
        """Unregister an agent profile.

        Args:
            agent_id: The ID of the agent profile to remove

        Returns:
            True if the profile was removed, False if it didn't exist
        """
        with self._lock:
            if agent_id in self._profiles:
                del self._profiles[agent_id]
                logger.info(f"Unregistered agent profile: {agent_id}")
                return True
            return False

    def get(self, agent_id: str) -> AgentProfile | None:
        """Get an agent profile by ID.

        Args:
            agent_id: The ID of the agent profile to retrieve

        Returns:
            The agent profile if found, None otherwise
        """
        with self._lock:
            return self._profiles.get(agent_id)

    def update(self, profile: AgentProfile) -> None:
        """Update an existing agent profile.

        Args:
            profile: The updated agent profile

        Raises:
            ValueError: If no profile with the given ID exists
        """
        with self._lock:
            if profile.agent_id not in self._profiles:
                raise ValueError(f"Agent profile '{profile.agent_id}' not found")
            self._profiles[profile.agent_id] = profile

    def find_by_capabilities(
        self,
        required_capabilities: list[AgentCapability],
        must_have_all: bool = True,
    ) -> list[AgentProfile]:
        """Find agents with required capabilities.

        Args:
            required_capabilities: List of capabilities to search for
            must_have_all: If True, agents must have ALL capabilities.
                          If False, agents must have AT LEAST ONE capability.

        Returns:
            List of agent profiles that match the criteria
        """
        with self._lock:
            matching = []
            for profile in self._profiles.values():
                if not profile.can_accept_task():
                    continue

                if must_have_all:
                    if profile.can_handle_task(required_capabilities):
                        matching.append(profile)
                else:
                    if any(
                        cap in profile.capabilities for cap in required_capabilities
                    ):
                        matching.append(profile)

            return sorted(
                matching,
                key=lambda p: (p.success_rate, -p.avg_execution_time),
                reverse=True,
            )

    def find_by_language(
        self,
        language: str,
    ) -> list[AgentProfile]:
        """Find agents that support a specific programming language.

        Args:
            language: The programming language to search for

        Returns:
            List of agent profiles that support the language
        """
        with self._lock:
            return [
                p
                for p in self._profiles.values()
                if p.supports_language(language) and p.can_accept_task()
            ]

    def find_by_framework(
        self,
        framework: str,
    ) -> list[AgentProfile]:
        """Find agents that support a specific framework.

        Args:
            framework: The framework to search for

        Returns:
            List of agent profiles that support the framework
        """
        with self._lock:
            return [
                p
                for p in self._profiles.values()
                if p.supports_framework(framework) and p.can_accept_task()
            ]

    def find_available(self) -> list[AgentProfile]:
        """Find all agents that can accept new tasks.

        Returns:
            List of available agent profiles
        """
        with self._lock:
            return [p for p in self._profiles.values() if p.can_accept_task()]

    def list_all(self) -> list[AgentProfile]:
        """List all registered agent profiles.

        Returns:
            List of all agent profiles
        """
        with self._lock:
            return list(self._profiles.values())

    def __len__(self) -> int:
        """Get the number of registered profiles."""
        with self._lock:
            return len(self._profiles)

    def __iter__(self) -> Iterator[AgentProfile]:
        """Iterate over all registered profiles."""
        with self._lock:
            return iter(list(self._profiles.values()))


# Global registry instance
_global_registry: AgentProfileRegistry | None = None
_registry_lock = RLock()


def get_global_registry() -> AgentProfileRegistry:
    """Get the global agent profile registry.

    Returns:
        The global AgentProfileRegistry instance
    """
    global _global_registry
    with _registry_lock:
        if _global_registry is None:
            _global_registry = AgentProfileRegistry()
        return _global_registry


def register_profile(profile: AgentProfile) -> None:
    """Register an agent profile in the global registry.

    Args:
        profile: The agent profile to register
    """
    get_global_registry().register(profile)


def register_profile_if_absent(profile: AgentProfile) -> bool:
    """Register an agent profile in the global registry if absent.

    Args:
        profile: The agent profile to register

    Returns:
        True if registered, False if already existed
    """
    return get_global_registry().register_if_absent(profile)


def get_profile(agent_id: str) -> AgentProfile | None:
    """Get an agent profile from the global registry.

    Args:
        agent_id: The ID of the agent profile

    Returns:
        The profile if found, None otherwise
    """
    return get_global_registry().get(agent_id)


def find_profiles_by_capabilities(
    required_capabilities: list[AgentCapability],
    must_have_all: bool = True,
) -> list[AgentProfile]:
    """Find agent profiles in the global registry.

    Args:
        required_capabilities: List of capabilities to search for
        must_have_all: If True, agents must have ALL capabilities

    Returns:
        List of matching agent profiles
    """
    return get_global_registry().find_by_capabilities(
        required_capabilities, must_have_all
    )


def _reset_registry_for_tests() -> None:
    """Clear the global registry for tests."""
    global _global_registry
    with _registry_lock:
        _global_registry = None
