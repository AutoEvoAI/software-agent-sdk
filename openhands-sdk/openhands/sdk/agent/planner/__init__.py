"""Planner agent for task decomposition based on formal specifications."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from openhands.sdk import Agent
from openhands.sdk.agent.planner.dag_builder import (
    DAGBuilder,
    EdgeData,
    NodeData,
    create_dag_builder,
)
from openhands.sdk.agent.planner.decomposer import (
    DecomposedTask,
    DecompositionStrategy,
    TaskDecomposer,
    TaskTemplate,
    TaskType,
    create_decomposer,
)
from openhands.sdk.agent.planner.dependency_analyzer import (
    Dependency,
    DependencyAnalysis,
    DependencyAnalyzer,
    DependencyStrength,
    DependencyType,
    create_dependency_analyzer,
)
from openhands.sdk.agent.planner.load_balancer import (
    AgentLoad,
    BalancingStrategy,
    LoadBalancer,
    LoadBalancingResult,
    create_load_balancer,
)
from openhands.sdk.context.agent_context import AgentContext
from openhands.sdk.logger import get_logger
from openhands.sdk.spec import FormalSpec, TaskGraph, TaskNode, TaskPriority
from openhands.sdk.tool import Tool


if TYPE_CHECKING:
    from openhands.sdk.llm import LLM


logger = get_logger(__name__)


__all__ = [
    "Agent",
    "BalancingStrategy",
    "DAGBuilder",
    "DecomposedTask",
    "DecompositionStrategy",
    "Dependency",
    "DependencyAnalysis",
    "DependencyAnalyzer",
    "DependencyStrength",
    "DependencyType",
    "EdgeData",
    "LoadBalancer",
    "LoadBalancingResult",
    "NodeData",
    "PlannerAgent",
    "TaskDecomposer",
    "TaskGraph",
    "TaskNode",
    "TaskPriority",
    "TaskTemplate",
    "TaskType",
    "create_dag_builder",
    "create_decomposer",
    "create_dependency_analyzer",
    "create_load_balancer",
    "AgentLoad",
]


class PlannerAgent(Agent):
    """Agent for task decomposition based on formal specifications.

    The PlannerAgent is responsible for:
    1. Decomposing formal specifications into executable tasks
    2. Building task dependency graphs (DAG)
    3. Analyzing dependencies between tasks
    4. Allocating agents to tasks

    Example:
        >>> from openhands.sdk import LLM
        >>> from openhands.sdk.agent.planner import PlannerAgent
        >>> llm = LLM(model="claude-sonnet-4-20250514")
        >>> agent = PlannerAgent(llm=llm)
    """

    def __init__(
        self,
        llm: LLM,
        tools: list[Tool] | None = None,
        agent_context: AgentContext | None = None,
        system_prompt_filename: str = "system_prompt_planner.j2",
        system_prompt_kwargs: dict[str, object] | None = None,
        condenser=None,
        mcp_config: dict[str, Any] | None = None,
        filter_tools_regex: str | None = None,
        include_default_tools: list[str] | None = None,
        decomposition_strategy: DecompositionStrategy = DecompositionStrategy.HYBRID,
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
        self._current_graph: TaskGraph | None = None
        self._decomposer = create_decomposer(strategy=decomposition_strategy)
        self._dag_builder = create_dag_builder()
        self._dependency_analyzer = create_dependency_analyzer()
        self._load_balancer = create_load_balancer()
        self._decomposed_tasks: list[DecomposedTask] = []
        self._dependency_analysis: DependencyAnalysis | None = None

    @property
    def decomposer(self) -> TaskDecomposer:
        """Get the task decomposer."""
        return self._decomposer

    @property
    def dag_builder(self) -> DAGBuilder:
        """Get the DAG builder."""
        return self._dag_builder

    @property
    def dependency_analyzer(self) -> DependencyAnalyzer:
        """Get the dependency analyzer."""
        return self._dependency_analyzer

    @property
    def load_balancer(self) -> LoadBalancer:
        """Get the load balancer."""
        return self._load_balancer

    @property
    def current_spec(self) -> FormalSpec | None:
        """Get the current formal specification being processed."""
        return self._current_spec

    @property
    def current_graph(self) -> TaskGraph | None:
        """Get the current task graph."""
        return self._current_graph

    @property
    def decomposed_tasks(self) -> list[DecomposedTask]:
        """Get the decomposed tasks."""
        return self._decomposed_tasks

    @property
    def dependency_analysis(self) -> DependencyAnalysis | None:
        """Get the dependency analysis result."""
        return self._dependency_analysis

    def set_spec(self, spec: FormalSpec) -> None:
        """Set the formal specification to decompose."""
        self._current_spec = spec

    def create_task_graph(self) -> TaskGraph:
        """Create a new empty task graph."""
        self._current_graph = TaskGraph()
        return self._current_graph

    async def run(
        self,
        _conversation: Any,
        spec: FormalSpec | None = None,
    ) -> dict[str, Any]:
        """Execute the full planning workflow.

        Args:
            conversation: The conversation object (unused in this implementation)
            spec: Optional FormalSpec to decompose

        Returns:
            Dictionary with results including task graph and analysis
        """
        if spec:
            self.set_spec(spec)

        if not self._current_spec:
            return {"status": "error", "message": "No specification provided"}

        try:
            decomposed_tasks = await self._decompose_spec()
            self._decomposed_tasks = decomposed_tasks

            task_graph = await self._build_dag(decomposed_tasks)
            self._current_graph = task_graph

            analysis = await self._analyze_dependencies(task_graph)
            self._dependency_analysis = analysis

            allocations = await self._allocate_agents(decomposed_tasks)

            return {
                "status": "success",
                "task_graph": task_graph,
                "decomposed_tasks": decomposed_tasks,
                "dependency_analysis": {
                    "critical_path": analysis.critical_path,
                    "parallel_groups": analysis.parallelizable_groups,
                    "circular_refs": analysis.circular_refs,
                },
                "allocations": allocations,
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _decompose_spec(self) -> list[DecomposedTask]:
        """Decompose the specification into tasks.

        Returns:
            List of DecomposedTask objects
        """
        if not self._current_spec:
            raise ValueError("No specification set")

        spec_name = self._current_spec.name or "default"
        tasks = self._decomposer.decompose(
            spec_name=spec_name,
            spec_content=self._current_spec.content,
            domain=spec_name.lower(),
        )

        logger.info(f"Decomposed spec into {len(tasks)} tasks")
        return tasks

    async def _build_dag(self, tasks: list[DecomposedTask]) -> TaskGraph:
        """Build DAG from decomposed tasks.

        Args:
            tasks: List of decomposed tasks

        Returns:
            TaskGraph object
        """
        for task in tasks:
            self._dag_builder.add_node(
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
                self._dag_builder.add_edge(dep, task.name)

        self._dag_builder.build()

        task_graph = TaskGraph()
        for task in tasks:
            node = TaskNode(
                name=task.name,
                description=task.description,
                required_capabilities=task.required_capabilities,
                priority=TaskPriority(task.priority),
            )
            task_graph.add_node(node)

        for task in tasks:
            for dep in task.dependencies:
                if dep in task_graph.nodes:
                    task_graph.add_edge(dep, task.name)

        logger.info(f"Built DAG with {len(task_graph.nodes)} nodes")
        return task_graph

    async def _analyze_dependencies(self, task_graph: TaskGraph) -> DependencyAnalysis:
        """Analyze dependencies in the task graph.

        Args:
            task_graph: The task graph to analyze

        Returns:
            DependencyAnalysis object
        """
        task_data = {}
        for node_id in task_graph.nodes:
            node = task_graph.get_node(node_id)
            if node:
                task_data[node_id] = {
                    "dependencies": [],
                }

        analysis = self._dependency_analyzer.analyze(task_data)

        logger.info(
            f"Dependency analysis: critical_path={len(analysis.critical_path)}, "
            f"parallel_groups={len(analysis.parallelizable_groups)}"
        )

        return analysis

    async def _allocate_agents(self, tasks: list[DecomposedTask]) -> dict[str, str]:
        """Allocate agents to tasks using load balancer.

        Args:
            tasks: List of tasks to allocate

        Returns:
            Dictionary mapping task names to agent IDs
        """
        allocations = {}

        for task in tasks:
            result = self._load_balancer.allocate_task(
                task_requirements={"capabilities": task.required_capabilities}
            )

            if result.selected_agent_id:
                allocations[task.name] = result.selected_agent_id

        logger.info(f"Allocated agents to {len(allocations)} tasks")
        return allocations

    def add_task(
        self,
        name: str,
        description: str,
        dependencies: list[str] | None = None,
        required_capabilities: list[str] | None = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        input_data: dict[str, Any] | None = None,
    ) -> TaskNode:
        """Add a task to the current task graph.

        Args:
            name: Task name
            description: Task description
            dependencies: List of task IDs this task depends on
            required_capabilities: Capabilities required to execute this task
            priority: Task priority
            input_data: Input data for the task

        Returns:
            The created TaskNode
        """
        if self._current_graph is None:
            self.create_task_graph()

        assert self._current_graph is not None

        task = TaskNode(
            name=name,
            description=description,
            dependencies=dependencies or [],
            required_capabilities=required_capabilities or [],
            priority=priority,
            input_data=input_data or {},
        )
        self._current_graph.add_node(task)

        for dep_id in dependencies or []:
            if dep_id in self._current_graph.nodes:
                self._current_graph.add_edge(dep_id, task.id)

        return task

    def get_ready_tasks(self) -> list[TaskNode]:
        """Get tasks that are ready to execute."""
        if self._current_graph is None:
            return []
        return self._current_graph.get_ready_tasks()

    def get_execution_order(self) -> list[str]:
        """Get the topological order of tasks for execution."""
        if self._current_graph is None:
            return []
        return self._current_graph.get_execution_order()

    def get_parallel_batches(self) -> list[list[str]]:
        """Get tasks grouped into parallel execution batches."""
        return self._dag_builder.get_parallel_batches()

    def clear_graph(self) -> None:
        """Clear the current task graph."""
        self._current_graph = None
        self._decomposed_tasks = []
        self._dependency_analysis = None
        self._dag_builder = create_dag_builder()


def create_planner_agent(
    llm: LLM,
    tools: list[Tool] | None = None,
    decomposition_strategy: DecompositionStrategy = DecompositionStrategy.HYBRID,
) -> PlannerAgent:
    """Factory function to create a PlannerAgent.

    Args:
        llm: The LLM to use for the planner agent.
        tools: Optional list of tools for the agent.
        decomposition_strategy: The task decomposition strategy.

    Returns:
        A configured PlannerAgent instance.
    """
    return PlannerAgent(
        llm=llm,
        tools=tools,
        decomposition_strategy=decomposition_strategy,
    )
