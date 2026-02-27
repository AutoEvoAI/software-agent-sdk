"""Spec agent for generating formal specifications."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from openhands.sdk import Agent
from openhands.sdk.context.agent_context import AgentContext
from openhands.sdk.logger import get_logger
from openhands.sdk.spec import FormalSpec, SpecType
from openhands.sdk.tool import Tool


if TYPE_CHECKING:
    from openhands.sdk.llm import LLM


logger = get_logger(__name__)


class SpecAgent(Agent):
    """Agent for generating formal specifications.

    The SpecAgent is responsible for:
    1. Converting natural language requirements to formal specs (TLA+/Z)
    2. Defining system state variables, invariants, and liveness properties
    3. Maintaining specification version control

    Example:
        >>> from openhands.sdk import LLM
        >>> from openhands.sdk.agent.supervisor import SpecAgent
        >>> llm = LLM(model="claude-sonnet-4-20250514")
        >>> agent = SpecAgent(llm=llm)
    """

    def __init__(
        self,
        llm: LLM,
        tools: list[Tool] | None = None,
        agent_context: AgentContext | None = None,
        system_prompt_filename: str = "system_prompt_spec_gen.j2",
        system_prompt_kwargs: dict[str, object] | None = None,
        condenser=None,
        mcp_config: dict[str, Any] | None = None,
        filter_tools_regex: str | None = None,
        include_default_tools: list[str] | None = None,
        spec_type: SpecType = SpecType.TLA_PLUS,
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
        self._spec_type = spec_type
        self._current_spec_build: dict[str, Any] | None = None

    @property
    def spec_type(self) -> SpecType:
        """Get the specification type being generated."""
        return self._spec_type

    def create_spec(
        self,
        name: str | None = None,
        description: str | None = None,
        content: str = "",
        invariants: list[str] | None = None,
        safety_properties: list[str] | None = None,
        liveness_properties: list[str] | None = None,
        version: str = "1.0.0",
    ) -> FormalSpec:
        """Create a formal specification from the current state.

        Args:
            name: Optional name for the specification.
            description: Optional description.
            content: Raw specification content.
            invariants: List of invariants.
            safety_properties: List of safety properties.
            liveness_properties: List of liveness properties.
            version: Version string.

        Returns:
            A FormalSpec instance.
        """
        return FormalSpec(
            spec_type=self._spec_type,
            name=name,
            description=description,
            content=content,
            invariants=invariants or [],
            safety_properties=safety_properties or [],
            liveness_properties=liveness_properties or [],
            version=version,
        )

    def add_invariant(self, invariant: str) -> None:
        """Add an invariant to the current spec being built."""
        if self._current_spec_build is None:
            self._current_spec_build = {}
        self._current_spec_build.setdefault("invariants", []).append(invariant)

    def add_safety_property(self, property: str) -> None:
        """Add a safety property to the current spec being built."""
        if self._current_spec_build is None:
            self._current_spec_build = {}
        self._current_spec_build.setdefault("safety_properties", []).append(property)

    def add_liveness_property(self, property: str) -> None:
        """Add a liveness property to the current spec being built."""
        if self._current_spec_build is None:
            self._current_spec_build = {}
        self._current_spec_build.setdefault("liveness_properties", []).append(property)

    def get_current_spec_data(self) -> dict[str, Any]:
        """Get the current spec data being built."""
        return self._current_spec_build or {}

    def clear_current_spec_data(self) -> None:
        """Clear the current spec data being built."""
        self._current_spec_build = None


def create_spec_agent(
    llm: LLM,
    tools: list[Tool] | None = None,
    spec_type: SpecType = SpecType.TLA_PLUS,
) -> SpecAgent:
    """Factory function to create a SpecAgent.

    Args:
        llm: The LLM to use for the spec agent.
        tools: Optional list of tools for the agent.
        spec_type: The type of formal specification to generate.

    Returns:
        A configured SpecAgent instance.
    """
    return SpecAgent(llm=llm, tools=tools, spec_type=spec_type)
