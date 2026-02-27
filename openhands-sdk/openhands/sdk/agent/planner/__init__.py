"""Planner agent for task decomposition based on formal specifications."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from openhands.sdk import Agent
from openhands.sdk.context.agent_context import AgentContext
from openhands.sdk.logger import get_logger
from openhands.sdk.spec import FormalSpec, TaskGraph, TaskNode, TaskPriority
from openhands.sdk.tool import Tool


if TYPE_CHECKING:
    from openhands.sdk.llm import LLM


logger = get_logger(__name__)


class PlannerAgent(Agent):
    """Agent for task decomposition based on formal specifications.

    The PlannerAgent is responsible for:
    1. Decomposing formal specifications into executable tasks
    2. Building task dependency graphs (DAG)
    3. Analyzing dependencies between tasks

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

    @property
    def current_spec(self) -> FormalSpec | None:
        """Get the current formal specification being processed."""
        return self._current_spec

    @property
    def current_graph(self) -> TaskGraph | None:
        """Get the current task graph."""
        return self._current_graph

    def set_spec(self, spec: FormalSpec) -> None:
        """Set the formal specification to decompose."""
        self._current_spec = spec

    def create_task_graph(self) -> TaskGraph:
        """Create a new empty task graph."""
        self._current_graph = TaskGraph()
        return self._current_graph

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

    def clear_graph(self) -> None:
        """Clear the current task graph."""
        self._current_graph = None


def create_planner_agent(
    llm: LLM,
    tools: list[Tool] | None = None,
) -> PlannerAgent:
    """Factory function to create a PlannerAgent.

    Args:
        llm: The LLM to use for the planner agent.
        tools: Optional list of tools for the agent.

    Returns:
        A configured PlannerAgent instance.
    """
    return PlannerAgent(llm=llm, tools=tools)
