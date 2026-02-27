"""Tests for state machine module."""

import pytest

from openhands.sdk.agent.supervisor.state_machine import (
    InvalidTransitionError,
    StateMachine,
    StateMachineError,
    TransitionType,
    WorkflowState,
    create_state_machine,
)


class TestWorkflowState:
    """Tests for WorkflowState enum."""

    def test_workflow_state_values(self):
        """Test WorkflowState enum values."""
        assert WorkflowState.IDLE.value == "idle"
        assert WorkflowState.PARSING_REQUIREMENTS.value == "parsing_requirements"
        assert WorkflowState.COMPLETED.value == "completed"
        assert WorkflowState.FAILED.value == "failed"

    def test_all_states_defined(self):
        """Test all expected states are defined."""
        expected_states = [
            "idle",
            "parsing_requirements",
            "generating_spec",
            "validating_spec",
            "decomposing_tasks",
            "allocating_roles",
            "executing_tasks",
            "verifying_results",
            "evaluating_candidates",
            "repairing",
            "completed",
            "failed",
            "paused",
            "waiting_approval",
        ]
        for state in expected_states:
            assert any(s.value == state for s in WorkflowState)


class TestStateMachine:
    """Tests for StateMachine class."""

    def test_create_state_machine(self):
        """Test creating a state machine."""
        sm = StateMachine()
        assert sm.current_state == WorkflowState.IDLE
        assert sm.previous_state is None
        assert sm.transition_count == 0

    def test_initial_state_parameter(self):
        """Test initializing with custom initial state."""
        sm = StateMachine(initial_state=WorkflowState.PARSING_REQUIREMENTS)
        assert sm.current_state == WorkflowState.PARSING_REQUIREMENTS

    def test_valid_forward_transition(self):
        """Test valid forward state transition."""
        sm = StateMachine()
        transition = sm.transition(WorkflowState.PARSING_REQUIREMENTS)
        assert sm.current_state == WorkflowState.PARSING_REQUIREMENTS
        assert transition.from_state == WorkflowState.IDLE
        assert transition.to_state == WorkflowState.PARSING_REQUIREMENTS

    def test_invalid_transition_raises_error(self):
        """Test that invalid transition raises error."""
        sm = StateMachine()
        with pytest.raises(InvalidTransitionError):
            sm.transition(WorkflowState.EXECUTING_TASKS)

    def test_transition_history(self):
        """Test transition history tracking."""
        sm = StateMachine()
        sm.transition(WorkflowState.PARSING_REQUIREMENTS)
        sm.transition(WorkflowState.GENERATING_SPEC)

        assert len(sm.history) == 3
        assert sm.history[0] == WorkflowState.IDLE
        assert sm.history[1] == WorkflowState.PARSING_REQUIREMENTS
        assert sm.history[2] == WorkflowState.GENERATING_SPEC

    def test_can_transition(self):
        """Test can_transition method."""
        sm = StateMachine()
        assert sm.can_transition(WorkflowState.PARSING_REQUIREMENTS) is True
        assert sm.can_transition(WorkflowState.EXECUTING_TASKS) is False

    def test_pause_and_resume(self):
        """Test pause and resume functionality."""
        sm = StateMachine()
        sm.start()
        sm.transition(WorkflowState.PARSING_REQUIREMENTS)
        sm.transition(WorkflowState.GENERATING_SPEC)
        sm.transition(WorkflowState.VALIDATING_SPEC)
        sm.transition(WorkflowState.DECOMPOSING_TASKS)
        sm.transition(WorkflowState.ALLOCATING_ROLES)
        sm.transition(WorkflowState.EXECUTING_TASKS)

        sm.pause()
        assert sm.current_state == WorkflowState.PAUSED

        sm.resume()
        assert sm.current_state == WorkflowState.EXECUTING_TASKS

    def test_abort(self):
        """Test abort functionality."""
        sm = StateMachine()
        sm.transition(WorkflowState.PARSING_REQUIREMENTS)
        sm.transition(WorkflowState.GENERATING_SPEC)
        sm.transition(WorkflowState.VALIDATING_SPEC)
        sm.transition(WorkflowState.DECOMPOSING_TASKS)
        sm.transition(WorkflowState.ALLOCATING_ROLES)
        sm.transition(WorkflowState.EXECUTING_TASKS)
        transition = sm.abort(reason="Test abort")
        assert sm.current_state == WorkflowState.FAILED
        assert transition.reason == "Test abort"

    def test_retry_limit(self):
        """Test retry limit enforcement."""
        sm = StateMachine()
        sm._retry_count = 3

        with pytest.raises(StateMachineError):
            sm.retry()

    def test_retry(self):
        """Test retry functionality."""
        sm = StateMachine()
        sm._current_state = WorkflowState.FAILED

        initial_retry_count = 0
        sm._retry_count = initial_retry_count

        sm.retry()
        assert sm.current_state == WorkflowState.PARSING_REQUIREMENTS
        assert sm._retry_count == initial_retry_count + 1

    def test_can_retry(self):
        """Test can_retry method."""
        sm = StateMachine()
        sm._retry_count = 2

        assert sm.can_retry() is True

        sm._retry_count = 3
        assert sm.can_retry() is False

    def test_get_snapshot(self):
        """Test state snapshot creation."""
        sm = StateMachine()
        sm.transition(WorkflowState.PARSING_REQUIREMENTS)
        sm.transition(WorkflowState.GENERATING_SPEC)

        snapshot = sm.get_snapshot()

        assert snapshot.current_state == WorkflowState.GENERATING_SPEC
        assert snapshot.previous_state == WorkflowState.PARSING_REQUIREMENTS
        assert len(snapshot.transitions) == 2
        assert len(snapshot.history) == 3

    def test_restore_snapshot(self):
        """Test restoring from snapshot."""
        sm = StateMachine()
        sm.transition(WorkflowState.PARSING_REQUIREMENTS)
        sm.transition(WorkflowState.GENERATING_SPEC)

        snapshot = sm.get_snapshot()

        sm2 = StateMachine()
        sm2.restore(snapshot)

        assert sm2.current_state == WorkflowState.GENERATING_SPEC
        assert sm2.previous_state == WorkflowState.PARSING_REQUIREMENTS

    def test_metadata(self):
        """Test metadata storage."""
        sm = StateMachine()
        sm.set_metadata("key1", "value1")
        sm.set_metadata("key2", {"nested": "value"})

        assert sm.get_metadata("key1") == "value1"
        assert sm.get_metadata("key2") == {"nested": "value"}
        assert sm.get_metadata("nonexistent", "default") == "default"

    def test_get_state_progress(self):
        """Test progress calculation."""
        sm = StateMachine()
        assert sm.get_state_progress() == 0.0

        sm.transition(WorkflowState.PARSING_REQUIREMENTS)
        progress = sm.get_state_progress()
        assert 0 < progress < 1

        sm.transition(WorkflowState.GENERATING_SPEC)
        sm.transition(WorkflowState.VALIDATING_SPEC)
        sm.transition(WorkflowState.DECOMPOSING_TASKS)
        sm.transition(WorkflowState.ALLOCATING_ROLES)
        sm.transition(WorkflowState.EXECUTING_TASKS)
        sm.transition(WorkflowState.VERIFYING_RESULTS)
        sm.transition(WorkflowState.EVALUATING_CANDIDATES)
        sm.transition(WorkflowState.COMPLETED)
        assert sm.get_state_progress() == 1.0

    def test_transition_count(self):
        """Test transition count tracking."""
        sm = StateMachine()
        assert sm.transition_count == 0

        sm.transition(WorkflowState.PARSING_REQUIREMENTS)
        assert sm.transition_count == 1

        sm.transition(WorkflowState.GENERATING_SPEC)
        assert sm.transition_count == 2

    def test_is_running(self):
        """Test is_running property."""
        sm = StateMachine()
        assert sm.is_running is False

        sm.start()
        assert sm.is_running is True

        sm.stop()
        assert sm.is_running is False


class TestTransitionType:
    """Tests for TransitionType enum."""

    def test_transition_type_values(self):
        """Test TransitionType enum values."""
        assert TransitionType.FORWARD.value == "forward"
        assert TransitionType.BACKWARD.value == "backward"
        assert TransitionType.RETRY.value == "retry"
        assert TransitionType.ESCALATE.value == "escalate"


class TestFactory:
    """Tests for factory function."""

    def test_create_state_machine(self):
        """Test create_state_machine factory."""
        sm = create_state_machine()
        assert sm is not None
        assert isinstance(sm, StateMachine)

    def test_create_with_initial_state(self):
        """Test create_state_machine with initial state."""
        sm = create_state_machine(WorkflowState.PARSING_REQUIREMENTS)
        assert sm.current_state == WorkflowState.PARSING_REQUIREMENTS
