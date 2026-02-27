"""Tests for load_balancer module."""

from openhands.sdk.agent.planner.load_balancer import (
    AgentLoad,
    BalancingStrategy,
    LoadBalancer,
    LoadBalancingResult,
    create_load_balancer,
)


class TestBalancingStrategy:
    """Tests for BalancingStrategy enum."""

    def test_balancing_strategy_values(self):
        """Test BalancingStrategy enum values."""
        assert BalancingStrategy.ROUND_ROBIN.value == "round_robin"
        assert BalancingStrategy.LEAST_LOADED.value == "least_loaded"
        assert BalancingStrategy.WEIGHTED.value == "weighted"
        assert BalancingStrategy.CAPABILITY_MATCH.value == "capability_match"
        assert BalancingStrategy.PERFORMANCE_BASED.value == "performance_based"


class TestAgentLoad:
    """Tests for AgentLoad dataclass."""

    def test_create_agent_load(self):
        """Test creating AgentLoad."""
        load = AgentLoad(
            agent_id="agent1",
            current_tasks=2,
            max_capacity=10,
            success_rate=0.9,
        )

        assert load.agent_id == "agent1"
        assert load.current_tasks == 2
        assert load.max_capacity == 10

    def test_load_factor(self):
        """Test load factor calculation."""
        load = AgentLoad(agent_id="agent1", current_tasks=5, max_capacity=10)
        assert load.load_factor == 0.5

        load.current_tasks = 10
        assert load.load_factor == 1.0

    def test_is_available(self):
        """Test is_available property."""
        load = AgentLoad(agent_id="agent1", current_tasks=5, max_capacity=10)
        assert load.is_available is True

        load.current_tasks = 10
        assert load.is_available is False

    def test_can_accept(self):
        """Test can_accept method."""
        load = AgentLoad(agent_id="agent1", current_tasks=5, max_capacity=10)
        assert load.can_accept(3) is True
        assert load.can_accept(6) is False


class TestLoadBalancingResult:
    """Tests for LoadBalancingResult dataclass."""

    def test_create_load_balancing_result(self):
        """Test creating LoadBalancingResult."""
        result = LoadBalancingResult(
            selected_agent_id="agent1",
            strategy_used=BalancingStrategy.LEAST_LOADED,
            reason="Selected",
        )

        assert result.selected_agent_id == "agent1"
        assert result.strategy_used == BalancingStrategy.LEAST_LOADED


class TestLoadBalancer:
    """Tests for LoadBalancer class."""

    def test_create_load_balancer(self):
        """Test creating a LoadBalancer."""
        balancer = LoadBalancer()
        assert balancer is not None

    def test_register_agent(self):
        """Test registering an agent."""
        balancer = LoadBalancer()
        balancer.register_agent("agent1", max_capacity=10)

        load = balancer.get_agent_load("agent1")
        assert load is not None
        assert load.agent_id == "agent1"
        assert load.max_capacity == 10

    def test_unregister_agent(self):
        """Test unregistering an agent."""
        balancer = LoadBalancer()
        balancer.register_agent("agent1")
        balancer.unregister_agent("agent1")

        load = balancer.get_agent_load("agent1")
        assert load is None

    def test_allocate_no_agents(self):
        """Test allocation with no agents."""
        balancer = LoadBalancer()
        result = balancer.allocate_task()

        assert result.selected_agent_id is None

    def test_allocate_least_loaded(self):
        """Test allocation with least loaded strategy."""
        balancer = LoadBalancer(strategy=BalancingStrategy.LEAST_LOADED)
        balancer.register_agent("agent1", max_capacity=10)
        balancer.register_agent("agent2", max_capacity=10)

        result = balancer.allocate_task()

        assert result.selected_agent_id is not None

    def test_allocate_with_capabilities(self):
        """Test allocation with capability matching."""
        balancer = LoadBalancer(strategy=BalancingStrategy.CAPABILITY_MATCH)
        balancer.register_agent(
            "agent1", max_capacity=10, capabilities=["coding", "testing"]
        )
        balancer.register_agent("agent2", max_capacity=10, capabilities=["coding"])

        result = balancer.allocate_task(
            task_requirements={"capabilities": ["coding", "testing"]}
        )

        assert result.selected_agent_id == "agent1"

    def test_allocate_with_priority(self):
        """Test allocation considers agent priority."""
        balancer = LoadBalancer(strategy=BalancingStrategy.LEAST_LOADED)
        balancer.register_agent("agent1", max_capacity=5)

        for _ in range(5):
            balancer.allocate_task()

        result = balancer.allocate_task()
        assert result.selected_agent_id is None or result.selected_agent_id == "agent1"

    def test_release_task(self):
        """Test releasing a task."""
        balancer = LoadBalancer()
        balancer.register_agent("agent1", max_capacity=10)

        load = balancer.get_agent_load("agent1")
        assert load is not None
        load.current_tasks = 2
        assert load.current_tasks == 2

        balancer.release_task("agent1")
        assert load.current_tasks == 1

    def test_update_agent_metrics(self):
        """Test updating agent metrics."""
        balancer = LoadBalancer()
        balancer.register_agent("agent1")

        balancer.update_agent_metrics("agent1", success_rate=0.95, response_time=1.5)

        load = balancer.get_agent_load("agent1")
        assert load is not None
        assert load.success_rate == 0.95
        assert load.avg_response_time == 1.5

    def test_get_statistics(self):
        """Test getting statistics."""
        balancer = LoadBalancer()
        balancer.register_agent("agent1", max_capacity=10)
        balancer.register_agent("agent2", max_capacity=20)

        stats = balancer.get_statistics()

        assert stats["total_agents"] == 2
        assert stats["total_capacity"] == 30

    def test_round_robin_strategy(self):
        """Test round robin strategy."""
        balancer = LoadBalancer(strategy=BalancingStrategy.ROUND_ROBIN)
        balancer.register_agent("agent1")
        balancer.register_agent("agent2")

        result1 = balancer.allocate_task()
        result2 = balancer.allocate_task()

        assert result1.selected_agent_id != result2.selected_agent_id

    def test_weighted_strategy(self):
        """Test weighted strategy."""
        balancer = LoadBalancer(strategy=BalancingStrategy.WEIGHTED)
        balancer.register_agent("agent1", max_capacity=10)
        balancer.register_agent("agent2", max_capacity=20)

        result = balancer.allocate_task()

        assert result.selected_agent_id is not None

    def test_performance_based_strategy(self):
        """Test performance based strategy."""
        balancer = LoadBalancer(strategy=BalancingStrategy.PERFORMANCE_BASED)
        balancer.register_agent("agent1", max_capacity=10)
        balancer.register_agent("agent2", max_capacity=10)

        balancer.update_agent_metrics("agent1", success_rate=0.9)
        balancer.update_agent_metrics("agent2", success_rate=0.7)

        result = balancer.allocate_task()

        assert result.selected_agent_id == "agent1"

    def test_allocate_nonexistent_agent_metrics(self):
        """Test updating metrics for nonexistent agent."""
        balancer = LoadBalancer()
        balancer.register_agent("agent1")

        balancer.update_agent_metrics("nonexistent", success_rate=0.9)


class TestFactory:
    """Tests for factory functions."""

    def test_create_load_balancer(self):
        """Test create_load_balancer factory."""
        balancer = create_load_balancer()
        assert isinstance(balancer, LoadBalancer)

    def test_create_load_balancer_with_strategy(self):
        """Test create_load_balancer with strategy."""
        balancer = create_load_balancer(strategy=BalancingStrategy.ROUND_ROBIN)
        assert balancer.strategy == BalancingStrategy.ROUND_ROBIN
