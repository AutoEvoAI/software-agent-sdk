"""Integration tests for Phase 1-3: Full workflow from Supervisor to Planner."""

from openhands.sdk.agent.planner.dag_builder import (
    create_dag_builder,
)
from openhands.sdk.agent.planner.decomposer import (
    DecompositionStrategy,
    create_decomposer,
)
from openhands.sdk.agent.planner.dependency_analyzer import (
    create_dependency_analyzer,
)
from openhands.sdk.agent.planner.load_balancer import (
    BalancingStrategy,
    create_load_balancer,
)
from openhands.sdk.agent.supervisor.decision_engine import (
    ErrorCategory,
    ErrorSeverity,
    create_decision_engine,
    create_error_context,
)
from openhands.sdk.agent.supervisor.parser import (
    create_parser,
)
from openhands.sdk.agent.supervisor.state_machine import (
    WorkflowState,
    create_state_machine,
)
from openhands.sdk.agent.supervisor.validator import (
    create_validator,
)
from openhands.sdk.spec import FormalSpec, SpecType, TaskGraph, TaskNode


class TestPhase1DataModels:
    """Phase 1: Data models integration tests."""

    def test_formal_spec_creation(self):
        """Test creating and using FormalSpec."""
        spec = FormalSpec(
            name="TestSpec",
            description="Test specification",
            spec_type=SpecType.TLA_PLUS,
            content="---- MODULE TestSpec ----",
            invariants=["x > 0"],
            safety_properties=["x < 100"],
            liveness_properties=["eventually done"],
            version="1.0.0",
        )

        assert spec.name == "TestSpec"
        assert spec.spec_type == SpecType.TLA_PLUS
        assert len(spec.invariants) == 1

    def test_task_graph_creation(self):
        """Test creating and using TaskGraph."""
        graph = TaskGraph()

        task1 = TaskNode(name="task1", description="First task")
        task2 = TaskNode(
            name="task2", description="Second task", dependencies=[task1.id]
        )

        graph.add_node(task1)
        graph.add_node(task2)
        graph.add_edge(task1.id, task2.id)

        assert len(graph) == 2
        ready = graph.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].name == "task1"


class TestPhase2SupervisorIntegration:
    """Phase 2: Supervisor components integration tests."""

    def test_parser_to_spec_to_validator_workflow(self):
        """Test the full workflow from parser -> spec -> validator."""
        parser = create_parser()
        validator = create_validator()

        user_message = """
        Create a system that manages user authentication.
        The system must:
        - Support login and logout
        - Validate passwords securely
        - Have performance under 100ms
        - Be highly available
        """

        requirements = parser.parse(user_message)

        assert len(requirements.requirements) > 0
        assert requirements.domain == "security"

        spec = FormalSpec(
            name="AuthSpec",
            description="Authentication system specification",
            spec_type=SpecType.TLA_PLUS,
            content="---- MODULE AuthSpec ----\nVARIABLES authenticated",
            invariants=["authenticated \\in BOOLEAN"],
            safety_properties=["authenticated => logged_in"],
            liveness_properties=["eventually authenticated"],
            version="1.0.0",
        )

        validation_result = validator.validate(spec.content, spec.spec_type.value)

        assert validation_result is not None

    def test_state_machine_workflow(self):
        """Test state machine through full workflow."""
        sm = create_state_machine()
        sm.start()

        assert sm.current_state == WorkflowState.IDLE

        sm.transition(WorkflowState.PARSING_REQUIREMENTS)
        assert sm.current_state == WorkflowState.PARSING_REQUIREMENTS

        sm.transition(WorkflowState.GENERATING_SPEC)
        assert sm.current_state == WorkflowState.GENERATING_SPEC

        sm.transition(WorkflowState.VALIDATING_SPEC)
        assert sm.current_state == WorkflowState.VALIDATING_SPEC

        sm.transition(WorkflowState.DECOMPOSING_TASKS)
        assert sm.current_state == WorkflowState.DECOMPOSING_TASKS

        sm.transition(WorkflowState.ALLOCATING_ROLES)
        assert sm.current_state == WorkflowState.ALLOCATING_ROLES

        sm.transition(WorkflowState.EXECUTING_TASKS)
        assert sm.current_state == WorkflowState.EXECUTING_TASKS

        sm.transition(WorkflowState.VERIFYING_RESULTS)
        sm.transition(WorkflowState.EVALUATING_CANDIDATES)
        sm.transition(WorkflowState.COMPLETED)
        assert sm.current_state == WorkflowState.COMPLETED

        assert sm.get_state_progress() == 1.0

    def test_decision_engine_error_handling(self):
        """Test decision engine with various error scenarios."""
        engine = create_decision_engine()

        low_severity_error = create_error_context(
            error_type="Warning",
            error_message="Minor issue",
            category=ErrorCategory.VALIDATION_ERROR,
            severity=ErrorSeverity.LOW,
        )
        decision = engine.decide(low_severity_error)
        assert decision.decision_type.value in ["retry", "fallback", "skip", "continue"]

        critical_error = create_error_context(
            error_type="FatalError",
            error_message="System crash",
            category=ErrorCategory.EXECUTION_ERROR,
            severity=ErrorSeverity.CRITICAL,
        )
        decision = engine.decide(critical_error)
        assert decision.decision_type.value == "abort"

    def test_validator_with_invalid_spec(self):
        """Test validator with invalid specification."""
        validator = create_validator()

        invalid_content = """
        ---- MODULE BadSpec ----
        VARIABLES x
        Init == [
        ====
        """

        result = validator.validate(invalid_content, "tla+")

        assert len(result.errors) > 0


class TestPhase3PlannerIntegration:
    """Phase 3: Planner components integration tests."""

    def test_decomposer_to_dag_builder_workflow(self):
        """Test workflow from decomposer to DAG builder."""
        decomposer = create_decomposer(strategy=DecompositionStrategy.SEQUENTIAL)
        dag_builder = create_dag_builder()

        tasks = decomposer.decompose(
            spec_name="TestSpec",
            spec_content="Test content",
            domain="api",
        )

        assert len(tasks) > 0

        for task in tasks:
            dag_builder.add_node(
                node_id=task.name,
                name=task.name,
                description=task.description,
                task_type=task.task_type.value,
                required_capabilities=task.required_capabilities,
                priority=task.priority,
                optional=task.optional,
            )

        for task in tasks:
            for dep in task.dependencies:
                dag_builder.add_edge(dep, task.name)

        dag_builder.build()

        assert dag_builder.get_node_count() == len(tasks)
        assert dag_builder.get_edge_count() > 0

    def test_dependency_analyzer_integration(self):
        """Test dependency analyzer with DAG."""
        decomposer = create_decomposer()
        analyzer = create_dependency_analyzer()

        tasks = decomposer.decompose(
            spec_name="TestSpec",
            spec_content="Test content",
        )

        task_data = {}
        for task in tasks:
            task_data[task.name] = {
                "dependencies": task.dependencies.copy(),
            }

        analysis = analyzer.analyze(task_data)

        assert len(analysis.critical_path) > 0
        assert len(analysis.parallelizable_groups) > 0

    def test_load_balancer_integration(self):
        """Test load balancer with task allocation."""
        balancer = create_load_balancer(strategy=BalancingStrategy.LEAST_LOADED)

        balancer.register_agent("agent1", max_capacity=5, capabilities=["coding"])
        balancer.register_agent("agent2", max_capacity=3, capabilities=["testing"])
        balancer.register_agent(
            "agent3", max_capacity=10, capabilities=["coding", "testing"]
        )

        result1 = balancer.allocate_task(task_requirements={"capabilities": ["coding"]})
        assert result1.selected_agent_id is not None

        result2 = balancer.allocate_task(
            task_requirements={"capabilities": ["testing"]}
        )
        assert result2.selected_agent_id is not None

        stats = balancer.get_statistics()
        assert stats["total_agents"] == 3
        assert stats["strategy"] == "least_loaded"

    def test_full_planner_pipeline(self):
        """Test full planner pipeline: decompose -> build DAG -> analyze -> allocate."""
        decomposer = create_decomposer()
        dag_builder = create_dag_builder()
        analyzer = create_dependency_analyzer()
        balancer = create_load_balancer()

        tasks = decomposer.decompose(
            spec_name="TestSpec",
            spec_content="Test content",
            domain="api",
        )

        assert len(tasks) > 0

        for task in tasks:
            dag_builder.add_node(
                node_id=task.name,
                name=task.name,
                description=task.description,
                required_capabilities=task.required_capabilities,
                priority=task.priority,
            )

        for task in tasks:
            for dep in task.dependencies:
                dag_builder.add_edge(dep, task.name)

        dag_builder.build()

        task_data = {}
        for task in tasks:
            task_data[task.name] = {"dependencies": task.dependencies.copy()}

        analysis = analyzer.analyze(task_data)

        assert len(analysis.critical_path) > 0

        balancer.register_agent("agent1", max_capacity=10, capabilities=["coding"])
        balancer.register_agent("agent2", max_capacity=10, capabilities=["planning"])

        allocations = []
        for task in tasks[:3]:
            result = balancer.allocate_task(
                task_requirements={"capabilities": task.required_capabilities}
            )
            allocations.append(result.selected_agent_id)

        assert len(allocations) > 0


class TestCrossPhaseIntegration:
    """Integration tests spanning multiple phases."""

    def test_supervisor_to_planner_handoff(self):
        """Test handing off from Supervisor to Planner."""
        parser = create_parser()
        validator = create_validator()
        decomposer = create_decomposer()

        user_message = "Build an API service with authentication and data storage"

        requirements = parser.parse(user_message)

        spec = FormalSpec(
            name="APISpec",
            description=requirements.domain or "API",
            spec_type=SpecType.TLA_PLUS,
            content="---- MODULE APISpec ----",
            invariants=["state \\in BOOLEAN"],
            safety_properties=["state => authenticated"],
            liveness_properties=["eventually ready"],
            version="1.0.0",
        )

        validation_result = validator.validate(spec.content, spec.spec_type.value)
        assert validation_result is not None

        tasks = decomposer.decompose(
            spec_name=spec.name or "Unknown",
            spec_content=spec.content,
            domain=(spec.name or "unknown").lower(),
        )

        assert len(tasks) > 0

        task_graph = TaskGraph()
        node_map = {}
        for task in tasks:
            node = TaskNode(
                name=task.name,
                description=task.description,
                required_capabilities=task.required_capabilities,
            )
            task_graph.add_node(node)
            node_map[task.name] = node.id

        for task in tasks:
            for dep in task.dependencies:
                if dep in node_map and task.name in node_map:
                    task_graph.add_edge(node_map[dep], node_map[task.name])

        ready = task_graph.get_ready_tasks()
        assert len(ready) > 0

    def test_error_recovery_workflow(self):
        """Test error recovery through the workflow."""
        sm = create_state_machine()
        engine = create_decision_engine()

        sm.start()
        sm.transition(WorkflowState.PARSING_REQUIREMENTS)
        sm.transition(WorkflowState.GENERATING_SPEC)
        sm.transition(WorkflowState.VALIDATING_SPEC)
        sm.transition(WorkflowState.DECOMPOSING_TASKS)
        sm.transition(WorkflowState.ALLOCATING_ROLES)
        sm.transition(WorkflowState.EXECUTING_TASKS)

        error = create_error_context(
            error_type="ValidationError",
            error_message="Invalid spec",
            category=ErrorCategory.SPECIFICATION_ERROR,
            severity=ErrorSeverity.MEDIUM,
        )

        decision = engine.decide(error)

        if decision.decision_type.value == "retry":
            sm.transition(WorkflowState.PARSING_REQUIREMENTS)
            assert sm.current_state == WorkflowState.PARSING_REQUIREMENTS
        else:
            sm.transition(WorkflowState.VERIFYING_RESULTS)
            sm.transition(WorkflowState.FAILED)
            assert sm.current_state == WorkflowState.FAILED

    def test_complete_system_integration(self):
        """Test complete system from requirements to agent allocation."""
        parser = create_parser()
        decomposer = create_decomposer()
        dag_builder = create_dag_builder()
        analyzer = create_dependency_analyzer()
        balancer = create_load_balancer()

        requirements_text = """
        Create a web application with:
        - User authentication
        - REST API endpoints
        - Database integration
        - Unit tests
        """

        requirements = parser.parse(requirements_text)
        assert len(requirements.requirements) > 0

        spec = FormalSpec(
            name="WebAppSpec",
            description=requirements.domain or "Web Application",
            spec_type=SpecType.TLA_PLUS,
            content="---- MODULE WebAppSpec ----\nVARIABLES state",
            invariants=["state \\in BOOLEAN"],
            safety_properties=["authenticated => authorized"],
            liveness_properties=["eventually operational"],
            version="1.0.0",
        )

        tasks = decomposer.decompose(
            spec_name=spec.name or "WebAppSpec",
            spec_content=spec.content,
        )

        for task in tasks:
            dag_builder.add_node(
                node_id=task.name,
                name=task.name,
                description=task.description,
                required_capabilities=task.required_capabilities,
                priority=task.priority,
            )

        for task in tasks:
            for dep in task.dependencies:
                dag_builder.add_edge(dep, task.name)

        dag_builder.build()

        task_data = {
            task.name: {"dependencies": task.dependencies.copy()} for task in tasks
        }
        analyzer.analyze(task_data)

        balancer.register_agent(
            "coder-1", max_capacity=5, capabilities=["code_generation"]
        )
        balancer.register_agent(
            "coder-2", max_capacity=5, capabilities=["code_generation"]
        )
        balancer.register_agent("tester-1", max_capacity=3, capabilities=["testing"])
        balancer.register_agent("reviewer-1", max_capacity=2, capabilities=["review"])

        allocations = {}
        for task in tasks:
            result = balancer.allocate_task(
                task_requirements={"capabilities": task.required_capabilities}
            )
            if result.selected_agent_id:
                allocations[task.name] = result.selected_agent_id

        assert len(allocations) > 0

        final_stats = balancer.get_statistics()
        assert final_stats["total_agents"] == 4


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_requirements(self):
        """Test handling empty requirements."""
        parser = create_parser()
        result = parser.parse("")

        assert result.requirements == []
        assert result.overall_priority.value == "low"

    def test_circular_dependency_handling(self):
        """Test handling circular dependencies in DAG."""
        dag_builder = create_dag_builder()

        dag_builder.add_node("a", "Task A")
        dag_builder.add_node("b", "Task B")
        dag_builder.add_node("c", "Task C")

        dag_builder.add_edge("a", "b")
        dag_builder.add_edge("b", "c")
        dag_builder.add_edge("c", "a")

        dag_builder.build()

        assert dag_builder._validate_dag() is False

    def test_all_agents_busy(self):
        """Test handling when all agents are busy."""
        balancer = create_load_balancer()

        balancer.register_agent("agent1", max_capacity=1)
        balancer.register_agent("agent2", max_capacity=1)

        balancer.allocate_task()
        balancer.allocate_task()

        result = balancer.allocate_task()

        assert result is not None

    def test_spec_with_no_capabilities(self):
        """Test decomposer with tasks requiring no capabilities."""
        decomposer = create_decomposer()

        tasks = decomposer.decompose(
            spec_name="EmptySpec",
            spec_content="",
        )

        assert len(tasks) > 0

        for task in tasks:
            assert task.required_capabilities is not None
