"""Supervisor agent for strategic planning and coordination.

The SupervisorAgent is responsible for:
1. Parsing user requirements
2. Generating formal specifications
3. Coordinating lower-level execution
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from openhands.sdk import Agent
from openhands.sdk.context.agent_context import AgentContext
from openhands.sdk.logger import get_logger
from openhands.sdk.spec import FormalSpec, TaskGraph
from openhands.sdk.tool import Tool


if TYPE_CHECKING:
    from openhands.sdk.llm import LLM


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

    @property
    def current_spec(self) -> FormalSpec | None:
        """Get the current formal specification being processed."""
        return self._current_spec

    @property
    def current_task_graph(self) -> TaskGraph | None:
        """Get the current task graph being processed."""
        return self._current_task_graph

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
