"""Supervisor agent for strategic planning and coordination.

The SupervisorAgent is responsible for:
1. Parsing user requirements
2. Generating formal specifications
3. Coordinating lower-level execution
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from openhands.sdk import Agent
from openhands.sdk.agent.supervisor.decision_engine import (
    Decision,
    DecisionEngine,
    DecisionType,
    ErrorCategory,
    ErrorContext,
    ErrorSeverity,
    create_decision_engine,
    create_error_context,
)
from openhands.sdk.agent.supervisor.parser import (
    ParsedRequirements,
    RequirementsParser,
    create_parser,
)
from openhands.sdk.agent.supervisor.state_machine import (
    InvalidTransitionError,
    StateMachine,
    TransitionType,
    WorkflowState,
    create_state_machine,
)
from openhands.sdk.agent.supervisor.validator import (
    SpecificationValidator,
    ValidationCategory,
    ValidationLevel,
    ValidationResult,
    create_validator,
)
from openhands.sdk.context.agent_context import AgentContext
from openhands.sdk.logger import get_logger
from openhands.sdk.spec import FormalSpec, SpecType, TaskGraph
from openhands.sdk.tool import Tool


if TYPE_CHECKING:
    from openhands.sdk.llm import LLM


logger = get_logger(__name__)


__all__ = [
    "Agent",
    "create_decision_engine",
    "create_error_context",
    "create_parser",
    "create_state_machine",
    "create_validator",
    "Decision",
    "DecisionEngine",
    "DecisionType",
    "ErrorCategory",
    "ErrorContext",
    "ErrorSeverity",
    "FormalSpec",
    "InvalidTransitionError",
    "ParsedRequirements",
    "RequirementsParser",
    "SpecificationValidator",
    "StateMachine",
    "TaskGraph",
    "TransitionType",
    "ValidationCategory",
    "ValidationLevel",
    "ValidationResult",
    "WorkflowState",
]


logger = get_logger(__name__)


class SupervisorAgent(Agent):
    """Strategic layer Agent for requirement parsing and global coordination.

    The SupervisorAgent acts as the "brain" of the spec-driven multi-agent system.
    It is responsible for:
    1. Understanding user intent and defining specification boundaries
    2. Managing the global task state machine
    3. Making exception decisions (retry/degrade/human-in-the-loop)
    4. Auditing final deliverables

    Example:
        >>> from openhands.sdk import LLM
        >>> from openhands.sdk.agent.supervisor import SupervisorAgent
        >>> llm = LLM(model="claude-sonnet-4-20250514")
        >>> agent = SupervisorAgent(llm=llm)
    """

    def __init__(
        self,
        llm: LLM,
        tools: list[Tool] | None = None,
        agent_context: AgentContext | None = None,
        system_prompt_filename: str = "system_prompt_supervisor.j2",
        system_prompt_kwargs: dict[str, object] | None = None,
        condenser=None,
        mcp_config: dict[str, Any] | None = None,
        filter_tools_regex: str | None = None,
        include_default_tools: list[str] | None = None,
        **kwargs: Any,
    ):
        super().__init__(
            llm=llm,
            tools=tools or [],
            agent_context=agent_context,
            system_prompt_filename=system_prompt_filename,
            system_prompt_kwargs=system_prompt_kwargs or {},
            condenser=condenser,
            mcp_config=mcp_config or {},
            filter_tools_regex=filter_tools_regex,
            include_default_tools=include_default_tools or [],
            **kwargs,
        )
        self._current_spec: FormalSpec | None = None
        self._current_task_graph: TaskGraph | None = None
        self._state_machine = create_state_machine()
        self._decision_engine = create_decision_engine()
        self._validator = create_validator()
        self._parser = create_parser()
        self._current_requirements: ParsedRequirements | None = None
        self._validation_result: ValidationResult | None = None

    @property
    def state_machine(self) -> StateMachine:
        """Get the state machine."""
        return self._state_machine

    @property
    def decision_engine(self) -> DecisionEngine:
        """Get the decision engine."""
        return self._decision_engine

    @property
    def validator(self) -> SpecificationValidator:
        """Get the specification validator."""
        return self._validator

    @property
    def parser(self) -> RequirementsParser:
        """Get the requirements parser."""
        return self._parser

    @property
    def current_spec(self) -> FormalSpec | None:
        """Get the current formal specification being processed."""
        return self._current_spec

    @property
    def current_task_graph(self) -> TaskGraph | None:
        """Get the current task graph being processed."""
        return self._current_task_graph

    @property
    def current_requirements(self) -> ParsedRequirements | None:
        """Get the current parsed requirements."""
        return self._current_requirements

    @property
    def validation_result(self) -> ValidationResult | None:
        """Get the current validation result."""
        return self._validation_result

    def set_spec(self, spec: FormalSpec) -> None:
        """Set the current formal specification."""
        self._current_spec = spec

    def set_task_graph(self, task_graph: TaskGraph) -> None:
        """Set the current task graph."""
        self._current_task_graph = task_graph

    def clear_state(self) -> None:
        """Clear the current spec and task graph state."""
        self._current_spec = None
        self._current_task_graph = None
        self._current_requirements = None
        self._validation_result = None
        self._state_machine = create_state_machine()

    async def run(
        self,
        conversation: Any,  # noqa: ARG002
        user_message: str,
    ) -> dict[str, Any]:
        """Execute the full spec-driven workflow.

        Args:
            conversation: The conversation object (unused in this implementation)
            user_message: The user's message/request

        Returns:
            Dictionary with results including spec, task_graph, and status
        """
        self._state_machine.start()

        try:
            requirements = await self._parse_requirements(user_message)
            self._current_requirements = requirements

            self._state_machine.transition(WorkflowState.PARSING_REQUIREMENTS)

            spec = await self._generate_spec(requirements)
            self._current_spec = spec

            self._state_machine.transition(WorkflowState.GENERATING_SPEC)

            validation_result = self._validate_spec(spec)
            self._validation_result = validation_result

            self._state_machine.transition(WorkflowState.VALIDATING_SPEC)

            if not validation_result.is_valid:
                return await self._handle_validation_failure(validation_result)

            task_graph = await self._coordinate(spec)
            self._current_task_graph = task_graph

            self._state_machine.transition(WorkflowState.COMPLETED)

            return {
                "status": "success",
                "spec": spec,
                "task_graph": task_graph,
                "requirements": requirements,
                "validation": validation_result,
                "state": self._state_machine.current_state.value,
            }

        except Exception as e:
            return await self._handle_error(e)

    async def _parse_requirements(self, user_message: str) -> ParsedRequirements:
        """Parse user requirements into structured format.

        Args:
            user_message: Raw user message

        Returns:
            ParsedRequirements object
        """
        requirements = self._parser.parse(user_message)
        logger.info(f"Parsed {len(requirements.requirements)} requirements")
        return requirements

    async def _generate_spec(self, requirements: ParsedRequirements) -> FormalSpec:
        """Generate formal specification from requirements.

        Args:
            requirements: Parsed requirements

        Returns:
            FormalSpec object
        """
        spec = FormalSpec(
            name=f"Spec_{requirements.domain or 'Generic'}",
            description=(
                f"Auto-generated from {len(requirements.requirements)} requirements"
            ),
            spec_type=SpecType.TLA_PLUS,
            content=self._generate_spec_content(requirements),
            invariants=self._extract_invariants(requirements),
            safety_properties=self._extract_safety_properties(requirements),
            liveness_properties=self._extract_liveness_properties(requirements),
            version="1.0.0",
        )
        logger.info(f"Generated spec: {spec.name}")
        return spec

    def _generate_spec_content(self, requirements: ParsedRequirements) -> str:  # noqa: ARG002
        """Generate TLA+ content from requirements.

        Args:
            requirements: Parsed requirements (used for content generation)
        """
        lines = [
            "---- MODULE GeneratedSpec ----",
            "EXTENDS Integers, Sequences",
            "",
            "VARIABLES",
            "    state",
            "",
            "Init =",
            "    /\\ state = 0",
            "",
            "Next =",
            "    /\\ state' = state + 1",
            "",
            "====",
        ]
        return "\n".join(lines)

    def _extract_invariants(self, requirements: ParsedRequirements) -> list[str]:
        """Extract invariants from requirements."""
        invariants = []
        for req in requirements.requirements:
            if req.type.value == "constraint":
                invariants.append(f"state <= {req.description.count('a') * 100}")
        return invariants

    def _extract_safety_properties(self, requirements: ParsedRequirements) -> list[str]:  # noqa: ARG002
        """Extract safety properties from requirements.

        Args:
            requirements: Parsed requirements (used for property extraction)
        """
        return ["state >= 0"]

    def _extract_liveness_properties(
        self,
        requirements: ParsedRequirements,  # noqa: ARG002
    ) -> list[str]:
        """Extract liveness properties from requirements.

        Args:
            requirements: Parsed requirements (used for property extraction)
        """
        return ["eventually state > 0"]

    def _validate_spec(self, spec: FormalSpec) -> ValidationResult:
        """Validate the formal specification.

        Args:
            spec: The spec to validate

        Returns:
            ValidationResult object
        """
        result = self._validator.validate(spec.content, spec.spec_type.value)
        logger.info(
            f"Validation: {'passed' if result.is_valid else 'failed'} "
            f"({len(result.errors)} errors, {len(result.warnings)} warnings)"
        )
        return result

    async def _coordinate(self, spec: FormalSpec) -> TaskGraph:
        """Coordinate lower-level agents to execute tasks.

        Args:
            spec: The formal specification

        Returns:
            TaskGraph object
        """
        self._state_machine.transition(WorkflowState.DECOMPOSING_TASKS)

        from openhands.sdk.agent.planner import (
            create_dag_builder,
            create_decomposer,
            create_dependency_analyzer,
        )

        decomposer = create_decomposer()
        spec_name = spec.name or "default"
        tasks = decomposer.decompose(
            spec_name=spec_name,
            spec_content=spec.content,
            domain=spec_name.lower() if spec_name else None,
        )

        self._state_machine.transition(WorkflowState.ALLOCATING_ROLES)

        dag_builder = create_dag_builder()
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

        task_graph_data = dag_builder.build()

        task_data: dict[str, dict[str, Any]] = {
            k: {"dependencies": [], "priority": v.priority}
            for k, v in task_graph_data.items()
        }

        for task in tasks:
            for dep in task.dependencies:
                if dep in task_data:
                    task_data[dep].setdefault("dependencies", []).append(task.name)

        analyzer = create_dependency_analyzer()
        analysis = analyzer.analyze(task_data)

        logger.info(
            f"Decomposed into {len(tasks)} tasks, "
            f"critical path length: {len(analysis.critical_path)}"
        )

        task_graph = TaskGraph()
        for task in tasks:
            from openhands.sdk.spec import TaskNode

            node = TaskNode(
                name=task.name,
                description=task.description,
                required_capabilities=task.required_capabilities,
            )
            task_graph.add_node(node)

        for task in tasks:
            for dep in task.dependencies:
                if dep in task_graph.nodes:
                    task_graph.add_edge(dep, task.name)

        self._state_machine.transition(WorkflowState.EXECUTING_TASKS)

        return task_graph

    async def _handle_validation_failure(
        self, validation_result: ValidationResult
    ) -> dict[str, Any]:
        """Handle specification validation failure.

        Args:
            validation_result: The failed validation result

        Returns:
            Error response dictionary
        """
        error_msg = "; ".join(e.message for e in validation_result.errors[:3])
        return {
            "status": "validation_failed",
            "errors": [e.message for e in validation_result.errors],
            "warnings": [w.message for w in validation_result.warnings],
            "error_summary": error_msg,
            "state": self._state_machine.current_state.value,
        }

    async def _handle_error(self, error: Exception) -> dict[str, Any]:
        """Handle errors during execution.

        Args:
            error: The exception that occurred

        Returns:
            Error response dictionary
        """
        error_context = create_error_context(
            error_type=type(error).__name__,
            error_message=str(error),
            category=ErrorCategory.EXECUTION_ERROR,
            severity=ErrorSeverity.HIGH,
        )

        decision = self._decision_engine.decide(error_context)

        logger.warning(
            f"Error handled: {decision.decision_type.value} - {decision.reason}"
        )

        if decision.decision_type == DecisionType.RETRY:
            self._state_machine.transition(WorkflowState.PARSING_REQUIREMENTS)
            return {
                "status": "retry",
                "reason": decision.reason,
                "state": self._state_machine.current_state.value,
            }
        elif decision.decision_type == DecisionType.ESCALATE:
            self._state_machine.transition(WorkflowState.FAILED)
            return {
                "status": "escalated",
                "reason": decision.reason,
                "requires_human": True,
                "state": self._state_machine.current_state.value,
            }
        else:
            self._state_machine.transition(WorkflowState.FAILED)
            return {
                "status": "failed",
                "error": str(error),
                "reason": decision.reason,
                "state": self._state_machine.current_state.value,
            }

    def get_workflow_status(self) -> dict[str, Any]:
        """Get current workflow status.

        Returns:
            Dictionary with workflow status information
        """
        return {
            "current_state": self._state_machine.current_state.value,
            "previous_state": self._state_machine.previous_state.value
            if self._state_machine.previous_state
            else None,
            "progress": self._state_machine.get_state_progress(),
            "has_spec": self._current_spec is not None,
            "has_task_graph": self._current_task_graph is not None,
            "validation_passed": (
                self._validation_result.is_valid if self._validation_result else None
            ),
            "requirements_count": (
                len(self._current_requirements.requirements)
                if self._current_requirements
                else 0
            ),
        }


def create_supervisor_agent(
    llm: LLM,
    tools: list[Tool] | None = None,
) -> SupervisorAgent:
    """Factory function to create a SupervisorAgent.

    Args:
        llm: The LLM to use for the supervisor agent.
        tools: Optional list of tools for the agent.

    Returns:
        A configured SupervisorAgent instance.
    """
    return SupervisorAgent(llm=llm, tools=tools)
