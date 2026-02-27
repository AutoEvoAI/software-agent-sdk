"""State machine management for SupervisorAgent.

This module provides the state machine logic for managing the workflow
states in the spec-driven multi-agent system.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, ClassVar


logger = logging.getLogger(__name__)


class WorkflowState(str, Enum):
    """Represents the possible states in the spec-driven workflow."""

    IDLE = "idle"
    PARSING_REQUIREMENTS = "parsing_requirements"
    GENERATING_SPEC = "generating_spec"
    VALIDATING_SPEC = "validating_spec"
    DECOMPOSING_TASKS = "decomposing_tasks"
    ALLOCATING_ROLES = "allocating_roles"
    EXECUTING_TASKS = "executing_tasks"
    VERIFYING_RESULTS = "verifying_results"
    EVALUATING_CANDIDATES = "evaluating_candidates"
    REPAIRING = "repairing"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    WAITING_APPROVAL = "waiting_approval"


class TransitionType(str, Enum):
    """Types of state transitions."""

    FORWARD = "forward"
    BACKWARD = "backward"
    RETRY = "retry"
    RECOVER = "recover"
    ESCALATE = "escalate"
    PAUSE = "pause"
    RESUME = "resume"
    ABORT = "abort"


@dataclass
class StateTransition:
    """Represents a state transition event."""

    from_state: WorkflowState
    to_state: WorkflowState
    transition_type: TransitionType
    timestamp: datetime = field(default_factory=datetime.now)
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StateSnapshot:
    """Snapshot of the current state machine state."""

    current_state: WorkflowState
    previous_state: WorkflowState | None
    transitions: list[StateTransition]
    history: list[WorkflowState]
    metadata: dict[str, Any] = field(default_factory=dict)
    error_count: int = 0
    retry_count: int = 0
    started_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class StateMachineError(Exception):
    """Base exception for state machine errors."""

    pass


class InvalidTransitionError(StateMachineError):
    """Raised when an invalid state transition is attempted."""

    pass


class StateMachine:
    """State machine for managing spec-driven workflow.

    The state machine manages transitions between workflow states
    and maintains history for auditing and recovery.
    """

    VALID_TRANSITIONS: ClassVar[dict[WorkflowState, set[WorkflowState]]] = {
        WorkflowState.IDLE: {
            WorkflowState.PARSING_REQUIREMENTS,
        },
        WorkflowState.PARSING_REQUIREMENTS: {
            WorkflowState.GENERATING_SPEC,
            WorkflowState.IDLE,
        },
        WorkflowState.GENERATING_SPEC: {
            WorkflowState.VALIDATING_SPEC,
            WorkflowState.PARSING_REQUIREMENTS,
            WorkflowState.IDLE,
        },
        WorkflowState.VALIDATING_SPEC: {
            WorkflowState.DECOMPOSING_TASKS,
            WorkflowState.GENERATING_SPEC,
            WorkflowState.FAILED,
        },
        WorkflowState.DECOMPOSING_TASKS: {
            WorkflowState.ALLOCATING_ROLES,
            WorkflowState.VALIDATING_SPEC,
            WorkflowState.FAILED,
        },
        WorkflowState.ALLOCATING_ROLES: {
            WorkflowState.EXECUTING_TASKS,
            WorkflowState.DECOMPOSING_TASKS,
            WorkflowState.FAILED,
        },
        WorkflowState.EXECUTING_TASKS: {
            WorkflowState.VERIFYING_RESULTS,
            WorkflowState.REPAIRING,
            WorkflowState.FAILED,
            WorkflowState.PAUSED,
        },
        WorkflowState.VERIFYING_RESULTS: {
            WorkflowState.EVALUATING_CANDIDATES,
            WorkflowState.REPAIRING,
            WorkflowState.EXECUTING_TASKS,
            WorkflowState.FAILED,
        },
        WorkflowState.EVALUATING_CANDIDATES: {
            WorkflowState.COMPLETED,
            WorkflowState.REPAIRING,
            WorkflowState.EXECUTING_TASKS,
            WorkflowState.FAILED,
        },
        WorkflowState.REPAIRING: {
            WorkflowState.EXECUTING_TASKS,
            WorkflowState.WAITING_APPROVAL,
            WorkflowState.FAILED,
        },
        WorkflowState.WAITING_APPROVAL: {
            WorkflowState.EXECUTING_TASKS,
            WorkflowState.COMPLETED,
            WorkflowState.FAILED,
        },
        WorkflowState.COMPLETED: {
            WorkflowState.IDLE,
        },
        WorkflowState.FAILED: {
            WorkflowState.IDLE,
            WorkflowState.PARSING_REQUIREMENTS,
        },
        WorkflowState.PAUSED: {
            WorkflowState.EXECUTING_TASKS,
            WorkflowState.IDLE,
        },
    }

    MAX_RETRIES: ClassVar[int] = 3

    def __init__(self, initial_state: WorkflowState = WorkflowState.IDLE):
        """Initialize the state machine.

        Args:
            initial_state: The starting state. Defaults to IDLE.
        """
        self._current_state = initial_state
        self._previous_state: WorkflowState | None = None
        self._transitions: list[StateTransition] = []
        self._history: list[WorkflowState] = [initial_state]
        self._metadata: dict[str, Any] = {}
        self._error_count = 0
        self._retry_count = 0
        self._started_at = datetime.now()
        self._is_running = False

    @property
    def current_state(self) -> WorkflowState:
        """Get the current state."""
        return self._current_state

    @property
    def previous_state(self) -> WorkflowState | None:
        """Get the previous state."""
        return self._previous_state

    @property
    def history(self) -> list[WorkflowState]:
        """Get the state history."""
        return self._history.copy()

    @property
    def transition_count(self) -> int:
        """Get the number of transitions made."""
        return len(self._transitions)

    @property
    def is_running(self) -> bool:
        """Check if the workflow is currently running."""
        return self._is_running

    def can_transition(self, to_state: WorkflowState) -> bool:
        """Check if a transition to the given state is valid.

        Args:
            to_state: The target state

        Returns:
            True if the transition is valid, False otherwise
        """
        valid_targets = self.VALID_TRANSITIONS.get(self._current_state, set())
        return to_state in valid_targets

    def transition(
        self,
        to_state: WorkflowState,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> StateTransition:
        """Perform a state transition.

        Args:
            to_state: The target state
            reason: Optional reason for the transition
            metadata: Optional metadata for the transition

        Returns:
            The StateTransition object

        Raises:
            InvalidTransitionError: If the transition is not valid
        """
        if not self.can_transition(to_state):
            raise InvalidTransitionError(
                f"Invalid transition from {self._current_state} to {to_state}"
            )

        from_state = self._current_state
        transition_type = self._determine_transition_type(from_state, to_state)

        transition = StateTransition(
            from_state=from_state,
            to_state=to_state,
            transition_type=transition_type,
            reason=reason,
            metadata=metadata or {},
        )

        self._transitions.append(transition)
        self._previous_state = from_state
        self._current_state = to_state
        self._history.append(to_state)

        if transition_type == TransitionType.RETRY:
            self._retry_count += 1
        elif transition_type == TransitionType.RECOVER:
            self._retry_count += 1
        elif transition_type == TransitionType.BACKWARD:
            self._error_count += 1

        logger.info(
            f"State transition: {from_state} -> {to_state} "
            f"(type: {transition_type.value}, reason: {reason})"
        )

        return transition

    def _determine_transition_type(
        self, from_state: WorkflowState, to_state: WorkflowState
    ) -> TransitionType:
        """Determine the type of transition.

        Args:
            from_state: The source state
            to_state: The target state

        Returns:
            The TransitionType
        """
        if from_state == WorkflowState.FAILED:
            return TransitionType.RECOVER
        if to_state == WorkflowState.PAUSED:
            return TransitionType.PAUSE
        if from_state == WorkflowState.PAUSED:
            return TransitionType.RESUME
        if to_state in [
            WorkflowState.PARSING_REQUIREMENTS,
            WorkflowState.GENERATING_SPEC,
            WorkflowState.EXECUTING_TASKS,
        ] and from_state in [
            WorkflowState.VERIFYING_RESULTS,
            WorkflowState.EVALUATING_CANDIDATES,
            WorkflowState.REPAIRING,
        ]:
            return TransitionType.RETRY

        state_order = list(WorkflowState)
        from_index = state_order.index(from_state)
        to_index = state_order.index(to_state)

        if to_index > from_index:
            return TransitionType.FORWARD
        return TransitionType.BACKWARD

    def start(self) -> None:
        """Start the workflow."""
        if self._current_state != WorkflowState.IDLE:
            raise StateMachineError(f"Cannot start from state {self._current_state}")
        self._is_running = True
        logger.info("Workflow started")

    def stop(self) -> None:
        """Stop the workflow."""
        self._is_running = False
        logger.info("Workflow stopped")

    def pause(self, reason: str | None = None) -> StateTransition:
        """Pause the workflow.

        Args:
            reason: Optional reason for pausing

        Returns:
            The StateTransition object
        """
        return self.transition(
            WorkflowState.PAUSED,
            reason=reason or "User requested pause",
        )

    def resume(self) -> StateTransition:
        """Resume the workflow from paused state.

        Returns:
            The StateTransition object

        Raises:
            InvalidTransitionError: If not currently paused
        """
        if self._current_state != WorkflowState.PAUSED:
            raise InvalidTransitionError("Can only resume from PAUSED state")

        if self._previous_state:
            return self.transition(self._previous_state, reason="Resuming from pause")

        return self.transition(
            WorkflowState.EXECUTING_TASKS, reason="Resuming from pause"
        )

    def abort(self, reason: str | None = None) -> StateTransition:
        """Abort the workflow.

        Args:
            reason: Optional reason for aborting

        Returns:
            The StateTransition object
        """
        return self.transition(
            WorkflowState.FAILED,
            reason=reason or "Workflow aborted",
            metadata={"aborted": True},
        )

    def retry(self, reason: str | None = None) -> StateTransition:
        """Retry from current failure point.

        Args:
            reason: Optional reason for retry

        Returns:
            The StateTransition object

        Raises:
            StateMachineError: If retry limit exceeded
        """
        if self._retry_count >= self.MAX_RETRIES:
            raise StateMachineError(
                f"Maximum retry limit ({self.MAX_RETRIES}) exceeded"
            )

        retry_state = self._get_retry_target()
        return self.transition(
            retry_state,
            reason=reason or "Retrying after failure",
            metadata={"retry_number": self._retry_count + 1},
        )

    def _get_retry_target(self) -> WorkflowState:
        """Get the target state for retry."""
        if self._current_state == WorkflowState.FAILED:
            return WorkflowState.PARSING_REQUIREMENTS
        if self._current_state == WorkflowState.REPAIRING:
            return WorkflowState.EXECUTING_TASKS

        return WorkflowState.PARSING_REQUIREMENTS

    def can_retry(self) -> bool:
        """Check if retry is possible."""
        return self._retry_count < self.MAX_RETRIES

    def get_snapshot(self) -> StateSnapshot:
        """Get a snapshot of the current state.

        Returns:
            StateSnapshot object
        """
        return StateSnapshot(
            current_state=self._current_state,
            previous_state=self._previous_state,
            transitions=self._transitions.copy(),
            history=self._history.copy(),
            metadata=self._metadata.copy(),
            error_count=self._error_count,
            retry_count=self._retry_count,
            started_at=self._started_at,
            updated_at=datetime.now(),
        )

    def restore(self, snapshot: StateSnapshot) -> None:
        """Restore state from a snapshot.

        Args:
            snapshot: The StateSnapshot to restore from
        """
        self._current_state = snapshot.current_state
        self._previous_state = snapshot.previous_state
        self._transitions = snapshot.transitions.copy()
        self._history = snapshot.history.copy()
        self._metadata = snapshot.metadata.copy()
        self._error_count = snapshot.error_count
        self._retry_count = snapshot.retry_count

    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata.

        Args:
            key: The metadata key
            value: The metadata value
        """
        self._metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata.

        Args:
            key: The metadata key
            default: Default value if key not found

        Returns:
            The metadata value or default
        """
        return self._metadata.get(key, default)

    def get_state_progress(self) -> float:
        """Get the progress percentage of the workflow.

        Returns:
            Progress as a float between 0 and 1
        """
        final_states = {WorkflowState.COMPLETED, WorkflowState.FAILED}
        if self._current_state in final_states:
            return 1.0 if self._current_state == WorkflowState.COMPLETED else 1.0

        state_order = [
            WorkflowState.IDLE,
            WorkflowState.PARSING_REQUIREMENTS,
            WorkflowState.GENERATING_SPEC,
            WorkflowState.VALIDATING_SPEC,
            WorkflowState.DECOMPOSING_TASKS,
            WorkflowState.ALLOCATING_ROLES,
            WorkflowState.EXECUTING_TASKS,
            WorkflowState.VERIFYING_RESULTS,
            WorkflowState.EVALUATING_CANDIDATES,
            WorkflowState.COMPLETED,
        ]

        try:
            current_index = state_order.index(self._current_state)
            return current_index / (len(state_order) - 1)
        except ValueError:
            return 0.0


def create_state_machine(
    initial_state: WorkflowState = WorkflowState.IDLE,
) -> StateMachine:
    """Factory function to create a StateMachine.

    Args:
        initial_state: The starting state

    Returns:
        A StateMachine instance
    """
    return StateMachine(initial_state=initial_state)
