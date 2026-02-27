"""Tests for RepairAgent and related components."""

import pytest

from openhands.sdk.agent.codegen_pool.candidate import CodeCandidate
from openhands.sdk.agent.repair import (
    RepairAgent,
    create_repair_agent,
)
from openhands.sdk.agent.repair.feedback_parser import (
    FeedbackParser,
    FeedbackType,
    RepairFeedback,
    create_feedback_parser,
)
from openhands.sdk.agent.repair.strategy import (
    RepairInstruction,
    RepairStrategy,
    RepairStrategyType,
    create_repair_strategy,
)


class TestFeedbackParser:
    """Tests for FeedbackParser."""

    def test_parse_verification_feedback_passed(self):
        """Test parsing verification that passed."""
        parser = FeedbackParser()

        result = {"passed": True, "errors": [], "warnings": []}
        feedback = parser.parse_verification_feedback(result)

        assert feedback == []

    def test_parse_verification_feedback_failed(self):
        """Test parsing failed verification."""
        parser = FeedbackParser()

        result = {
            "passed": False,
            "errors": [{"message": "Error at line 10", "location": {"line": 10}}],
        }
        feedback = parser.parse_verification_feedback(result)

        assert len(feedback) == 1
        assert feedback[0].feedback_type == FeedbackType.VERIFICATION_FAILED
        assert feedback[0].severity == "high"

    def test_parse_evaluation_feedback(self):
        """Test parsing evaluation feedback."""
        parser = FeedbackParser()

        result = {
            "passed": False,
            "feedback": ["Low score on correctness"],
            "metrics": [
                {"type": "correctness", "score": 0.3},
                {"type": "efficiency", "score": 0.8},
            ],
        }
        feedback = parser.parse_evaluation_feedback(result)

        assert len(feedback) == 2

    def test_parse_error_message(self):
        """Test parsing error message."""
        parser = FeedbackParser()

        feedback = parser.parse_error_message("Error at line 42, column 5")

        assert len(feedback) == 1
        assert feedback[0].feedback_type == FeedbackType.ERROR
        assert feedback[0].location == {"line": 42, "column": 5}

    def test_parse_security_feedback(self):
        """Test parsing security feedback."""
        parser = FeedbackParser()

        issues = [
            {
                "message": "SQL injection risk",
                "location": {"line": 15},
                "suggested_fix": "Use parameterized queries",
            }
        ]
        feedback = parser.parse_security_feedback(issues)

        assert len(feedback) == 1
        assert feedback[0].feedback_type == FeedbackType.SECURITY

    def test_parse_all_combined(self):
        """Test parsing combined feedback sources."""
        parser = FeedbackParser()

        verification = {"passed": False, "errors": [{"message": "Error"}]}
        evaluation = {"passed": False, "feedback": ["Feedback"]}

        feedback = parser.parse_all(
            verification_result=verification,
            evaluation_result=evaluation,
        )

        assert len(feedback) == 2

    def test_create_feedback_parser_factory(self):
        """Test factory function."""
        parser = create_feedback_parser()
        assert isinstance(parser, FeedbackParser)


class TestRepairStrategy:
    """Tests for RepairStrategy."""

    def test_prepare_instruction_no_feedback(self):
        """Test preparing instruction with no feedback."""
        strategy = RepairStrategy()

        instruction = strategy.prepare_instruction([])

        assert instruction.strategy == RepairStrategyType.FULL_REGENERATE

    def test_prepare_instruction_high_severity(self):
        """Test preparing instruction with high severity feedback."""
        strategy = RepairStrategy()

        feedback = [
            RepairFeedback(
                feedback_type=FeedbackType.ERROR,
                message="Error 1",
                severity="high",
            ),
            RepairFeedback(
                feedback_type=FeedbackType.ERROR,
                message="Error 2",
                severity="high",
            ),
            RepairFeedback(
                feedback_type=FeedbackType.ERROR,
                message="Error 3",
                severity="high",
            ),
        ]

        instruction = strategy.prepare_instruction(feedback)

        assert instruction.strategy == RepairStrategyType.FULL_REGENERATE

    def test_incremental_strategy_prompt(self):
        """Test incremental repair strategy prompt."""
        from openhands.sdk.agent.repair.strategy import IncrementalRepairStrategy

        strategy = IncrementalRepairStrategy()

        instruction = RepairInstruction(
            strategy=RepairStrategyType.INCREMENTAL,
            feedback_summary="Fix the error",
        )

        prompt = strategy.prepare_prompt("original code", instruction)

        assert "original code" in prompt
        assert "Fix the error" in prompt

    def test_full_regenerate_strategy_prompt(self):
        """Test full regenerate strategy prompt."""
        from openhands.sdk.agent.repair.strategy import FullRegenerateStrategy

        strategy = FullRegenerateStrategy()

        instruction = RepairInstruction(
            strategy=RepairStrategyType.FULL_REGENERATE,
            feedback_summary="Regenerate code",
        )

        prompt = strategy.prepare_prompt("spec", instruction)

        assert "spec" in prompt

    def test_targeted_strategy_prompt(self):
        """Test targeted repair strategy prompt."""
        from openhands.sdk.agent.repair.strategy import TargetedRepairStrategy

        strategy = TargetedRepairStrategy()

        instruction = RepairInstruction(
            strategy=RepairStrategyType.TARGETED,
            feedback_summary="Fix specific locations",
        )

        locations = [{"line": 10, "description": "Fix this"}]
        prompt = strategy.prepare_prompt("code", instruction, locations)

        assert "Fix specific locations" in prompt

    def test_create_repair_strategy_factory(self):
        """Test factory function."""
        strategy = create_repair_strategy(RepairStrategyType.INCREMENTAL)
        assert isinstance(strategy, RepairStrategy)

        strategy = create_repair_strategy(RepairStrategyType.FULL_REGENERATE)
        assert isinstance(strategy, RepairStrategy)


class TestRepairAgent:
    """Tests for RepairAgent."""

    def test_init(self):
        """Test initialization."""
        agent = RepairAgent()

        assert agent._parser is not None
        assert agent._strategy is not None
        assert agent.get_repair_history() == []

    @pytest.mark.asyncio
    async def test_repair_no_feedback(self):
        """Test repair with no feedback."""
        agent = RepairAgent()
        candidate = CodeCandidate(
            id="test-id",
            code="def foo(): pass",
            model="test",
        )

        result = await agent.repair(candidate)

        assert result is None

    @pytest.mark.asyncio
    async def test_repair_with_feedback_no_llm(self):
        """Test repair with feedback (no LLM - simulated)."""
        agent = RepairAgent()
        candidate = CodeCandidate(
            id="test-id",
            code="def foo(): pass",
            model="test",
        )

        verification = {"passed": False, "errors": [{"message": "Error"}]}

        result = await agent.repair(candidate, verification_result=verification)

        assert result is not None
        assert result.id != candidate.id
        assert "Error" in result.code

    @pytest.mark.asyncio
    async def test_repair_updates_history(self):
        """Test that repair updates history."""
        agent = RepairAgent()
        candidate = CodeCandidate(
            id="test-id",
            code="def foo(): pass",
            model="test",
        )

        verification = {"passed": False, "errors": [{"message": "Error"}]}

        await agent.repair(candidate, verification_result=verification)

        history = agent.get_repair_history()
        assert len(history) == 1
        assert history[0]["original_id"] == candidate.id

    def test_set_strategy(self):
        """Test setting repair strategy."""
        agent = RepairAgent()

        agent.set_strategy(RepairStrategyType.FULL_REGENERATE)

        assert isinstance(agent.strategy, RepairStrategy)

    @pytest.mark.asyncio
    async def test_repair_with_retry(self):
        """Test repair with retry."""
        agent = RepairAgent()
        candidate = CodeCandidate(
            id="test-id",
            code="def foo(): pass",
            model="test",
        )

        verification = {"passed": False, "errors": [{"message": "Error"}]}

        result = await agent.repair_with_retry(
            candidate,
            verification_result=verification,
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_repair_with_retry_success(self):
        """Test repair with retry that succeeds."""
        agent = RepairAgent()
        candidate = CodeCandidate(
            id="test-id",
            code="def foo(): pass",
            model="test",
        )

        verification = {"passed": True}

        result = await agent.repair_with_retry(
            candidate,
            verification_result=verification,
        )

        assert result is not None

    def test_create_repair_agent_factory(self):
        """Test factory function."""
        agent = create_repair_agent(RepairStrategyType.INCREMENTAL)

        assert isinstance(agent, RepairAgent)
