"""Load balancer for agent allocation.

This module provides load balancing logic for distributing tasks
across multiple agents based on their current load, capabilities, and performance.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


logger = logging.getLogger(__name__)


class BalancingStrategy(str, Enum):
    """Load balancing strategies."""

    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    WEIGHTED = "weighted"
    CAPABILITY_MATCH = "capability_match"
    PERFORMANCE_BASED = "performance_based"


@dataclass
class AgentLoad:
    """Represents the current load of an agent."""

    agent_id: str
    current_tasks: int = 0
    max_capacity: int = 10
    success_rate: float = 1.0
    avg_response_time: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def load_factor(self) -> float:
        """Calculate the load factor (0-1)."""
        if self.max_capacity == 0:
            return 1.0
        return self.current_tasks / self.max_capacity

    @property
    def is_available(self) -> bool:
        """Check if agent can accept more tasks."""
        return self.current_tasks < self.max_capacity

    def can_accept(self, task_load: int = 1) -> bool:
        """Check if agent can accept a task.

        Args:
            task_load: The load the task would add

        Returns:
            True if agent can accept the task
        """
        return self.current_tasks + task_load <= self.max_capacity


@dataclass
class LoadBalancingResult:
    """Result of load balancing decision."""

    selected_agent_id: str | None
    strategy_used: BalancingStrategy
    all_agent_loads: list[AgentLoad] = field(default_factory=list)
    reason: str = ""


class LoadBalancer:
    """Load balancer for distributing tasks across agents.

    The load balancer considers:
    - Current agent load
    - Agent capabilities
    - Historical performance
    - Task requirements
    """

    def __init__(
        self,
        strategy: BalancingStrategy = BalancingStrategy.LEAST_LOADED,
    ):
        """Initialize the load balancer.

        Args:
            strategy: The load balancing strategy to use
        """
        self.strategy = strategy
        self._agent_loads: dict[str, AgentLoad] = {}
        self._round_robin_index: int = 0
        self._capability_index: dict[str, int] = {}

    def register_agent(
        self,
        agent_id: str,
        max_capacity: int = 10,
        capabilities: list[str] | None = None,
    ) -> None:
        """Register an agent with the load balancer.

        Args:
            agent_id: Unique identifier for the agent
            max_capacity: Maximum concurrent tasks the agent can handle
            capabilities: List of agent capabilities
        """
        self._agent_loads[agent_id] = AgentLoad(
            agent_id=agent_id,
            max_capacity=max_capacity,
            metadata={"capabilities": capabilities or []},
        )
        logger.info(f"Registered agent {agent_id} with capacity {max_capacity}")

    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent.

        Args:
            agent_id: The agent to unregister
        """
        if agent_id in self._agent_loads:
            del self._agent_loads[agent_id]
            logger.info(f"Unregistered agent {agent_id}")

    def get_agent_load(self, agent_id: str) -> AgentLoad | None:
        """Get the current load of an agent.

        Args:
            agent_id: The agent ID

        Returns:
            AgentLoad object or None if agent not found
        """
        return self._agent_loads.get(agent_id)

    def update_agent_metrics(
        self,
        agent_id: str,
        success_rate: float | None = None,
        response_time: float | None = None,
    ) -> None:
        """Update agent performance metrics.

        Args:
            agent_id: The agent ID
            success_rate: New success rate (0-1)
            response_time: New average response time
        """
        if agent_id not in self._agent_loads:
            logger.warning(f"Agent {agent_id} not found for metric update")
            return

        load = self._agent_loads[agent_id]
        if success_rate is not None:
            load.success_rate = success_rate
        if response_time is not None:
            load.avg_response_time = response_time

    def allocate_task(
        self,
        task_requirements: dict[str, Any] | None = None,
    ) -> LoadBalancingResult:
        """Allocate a task to an agent.

        Args:
            task_requirements: Requirements for the task (capabilities, priority, etc.)

        Returns:
            LoadBalancingResult object
        """
        if not self._agent_loads:
            return LoadBalancingResult(
                selected_agent_id=None,
                strategy_used=self.strategy,
                reason="No agents available",
            )

        task_requirements = task_requirements or {}
        required_capabilities = task_requirements.get("capabilities", [])

        available_agents = self._get_available_agents()

        if not available_agents:
            return LoadBalancingResult(
                selected_agent_id=None,
                strategy_used=self.strategy,
                all_agent_loads=list(self._agent_loads.values()),
                reason="No agents with available capacity",
            )

        if self.strategy == BalancingStrategy.ROUND_ROBIN:
            return self._round_robin_select(available_agents, task_requirements)
        elif self.strategy == BalancingStrategy.LEAST_LOADED:
            return self._least_loaded_select(available_agents, task_requirements)
        elif self.strategy == BalancingStrategy.WEIGHTED:
            return self._weighted_select(available_agents, task_requirements)
        elif self.strategy == BalancingStrategy.CAPABILITY_MATCH:
            return self._capability_match_select(
                available_agents, required_capabilities
            )
        elif self.strategy == BalancingStrategy.PERFORMANCE_BASED:
            return self._performance_based_select(available_agents, task_requirements)
        else:
            return self._least_loaded_select(available_agents, task_requirements)

    def release_task(self, agent_id: str) -> bool:
        """Release a task allocation, reducing agent load.

        Args:
            agent_id: The agent ID

        Returns:
            True if successful, False otherwise
        """
        if agent_id not in self._agent_loads:
            return False

        load = self._agent_loads[agent_id]
        if load.current_tasks > 0:
            load.current_tasks -= 1
            return True
        return False

    def get_statistics(self) -> dict[str, Any]:
        """Get load balancing statistics.

        Returns:
            Dictionary of statistics
        """
        total_capacity = sum(load.max_capacity for load in self._agent_loads.values())
        total_load = sum(load.current_tasks for load in self._agent_loads.values())
        available_agents = len(self._get_available_agents())

        return {
            "total_agents": len(self._agent_loads),
            "available_agents": available_agents,
            "total_capacity": total_capacity,
            "current_load": total_load,
            "utilization": total_load / total_capacity if total_capacity > 0 else 0,
            "strategy": self.strategy.value,
        }

    def _get_available_agents(self) -> list[AgentLoad]:
        """Get list of available agents."""
        return [load for load in self._agent_loads.values() if load.is_available]

    def _round_robin_select(
        self,
        available_agents: list[AgentLoad],
        _task_requirements: dict[str, Any],
    ) -> LoadBalancingResult:
        """Select agent using round-robin strategy."""
        if not available_agents:
            return LoadBalancingResult(
                selected_agent_id=None,
                strategy_used=self.strategy,
                all_agent_loads=list(self._agent_loads.values()),
                reason="No available agents",
            )

        agent_ids = list(self._agent_loads.keys())
        while len(agent_ids) > 0:
            selected = agent_ids[self._round_robin_index % len(agent_ids)]
            self._round_robin_index += 1

            if selected in [a.agent_id for a in available_agents]:
                return LoadBalancingResult(
                    selected_agent_id=selected,
                    strategy_used=self.strategy,
                    all_agent_loads=list(self._agent_loads.values()),
                    reason="Round-robin selection",
                )

        return LoadBalancingResult(
            selected_agent_id=None,
            strategy_used=self.strategy,
            all_agent_loads=list(self._agent_loads.values()),
            reason="No suitable agent found",
        )

    def _least_loaded_select(
        self,
        available_agents: list[AgentLoad],
        _task_requirements: dict[str, Any],
    ) -> LoadBalancingResult:
        """Select agent with least current load."""
        if not available_agents:
            return LoadBalancingResult(
                selected_agent_id=None,
                strategy_used=self.strategy,
                all_agent_loads=list(self._agent_loads.values()),
                reason="No available agents",
            )

        selected = min(available_agents, key=lambda a: a.load_factor)

        return LoadBalancingResult(
            selected_agent_id=selected.agent_id,
            strategy_used=self.strategy,
            all_agent_loads=list(self._agent_loads.values()),
            reason=f"Selected agent with load factor {selected.load_factor:.2f}",
        )

    def _weighted_select(
        self,
        available_agents: list[AgentLoad],
        _task_requirements: dict[str, Any],
    ) -> LoadBalancingResult:
        """Select agent using weighted algorithm based on capacity."""
        if not available_agents:
            return LoadBalancingResult(
                selected_agent_id=None,
                strategy_used=self.strategy,
                all_agent_loads=list(self._agent_loads.values()),
                reason="No available agents",
            )

        weights = []
        for agent in available_agents:
            weight = (agent.max_capacity - agent.current_tasks) / agent.max_capacity
            weights.append(max(weight, 0.01))

        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]

        import random

        threshold = random.random()
        cumulative = 0

        for i, weight in enumerate(normalized_weights):
            cumulative += weight
            if cumulative >= threshold:
                return LoadBalancingResult(
                    selected_agent_id=available_agents[i].agent_id,
                    strategy_used=self.strategy,
                    all_agent_loads=list(self._agent_loads.values()),
                    reason="Weighted random selection",
                )

        return LoadBalancingResult(
            selected_agent_id=available_agents[-1].agent_id,
            strategy_used=self.strategy,
            all_agent_loads=list(self._agent_loads.values()),
            reason="Default to last available agent",
        )

    def _capability_match_select(
        self,
        available_agents: list[AgentLoad],
        required_capabilities: list[str],
    ) -> LoadBalancingResult:
        """Select agent with best capability match."""
        if not required_capabilities:
            return self._least_loaded_select(available_agents, {})

        candidates = []
        for agent in available_agents:
            agent_caps = agent.metadata.get("capabilities", [])
            matches = sum(1 for cap in required_capabilities if cap in agent_caps)
            if matches > 0:
                candidates.append((agent, matches, agent.load_factor))

        if not candidates:
            return LoadBalancingResult(
                selected_agent_id=None,
                strategy_used=self.strategy,
                all_agent_loads=list(self._agent_loads.values()),
                reason="No agent matches required capabilities",
            )

        candidates.sort(key=lambda x: (-x[1], x[2]))
        selected = candidates[0][0]

        return LoadBalancingResult(
            selected_agent_id=selected.agent_id,
            strategy_used=self.strategy,
            all_agent_loads=list(self._agent_loads.values()),
            reason=f"Best capability match (score: {candidates[0][1]})",
        )

    def _performance_based_select(
        self,
        available_agents: list[AgentLoad],
        _task_requirements: dict[str, Any],
    ) -> LoadBalancingResult:
        """Select agent based on performance metrics."""
        if not available_agents:
            return LoadBalancingResult(
                selected_agent_id=None,
                strategy_used=self.strategy,
                all_agent_loads=list(self._agent_loads.values()),
                reason="No available agents",
            )

        scores = []
        for agent in available_agents:
            success_score = agent.success_rate
            load_score = 1 - agent.load_factor
            time_score = 1 / (agent.avg_response_time + 0.1)

            combined_score = (
                (success_score * 0.5) + (load_score * 0.3) + (time_score * 0.2)
            )
            scores.append((agent, combined_score))

        scores.sort(key=lambda x: x[1], reverse=True)
        selected = scores[0][0]

        return LoadBalancingResult(
            selected_agent_id=selected.agent_id,
            strategy_used=self.strategy,
            all_agent_loads=list(self._agent_loads.values()),
            reason=f"Performance score: {scores[0][1]:.2f}",
        )


def create_load_balancer(
    strategy: BalancingStrategy = BalancingStrategy.LEAST_LOADED,
) -> LoadBalancer:
    """Factory function to create a LoadBalancer.

    Args:
        strategy: The load balancing strategy

    Returns:
        A LoadBalancer instance
    """
    return LoadBalancer(strategy=strategy)
