"""Repair agent for feedback-based code repair.

This module provides the RepairAgent class that repairs
generated code based on feedback from verification and evaluation.
"""

from __future__ import annotations

import uuid
from typing import Any

from openhands.sdk.agent.codegen_pool.candidate import CandidateStatus, CodeCandidate
from openhands.sdk.logger import get_logger

from .feedback_parser import FeedbackParser, create_feedback_parser
from .strategy import (
    RepairInstruction,
    RepairStrategy,
    RepairStrategyType,
    create_repair_strategy,
)


logger = get_logger(__name__)


class RepairAgent:
    """Agent for repairing code based on feedback.

    The RepairAgent takes failed or low-scoring candidates and
    repairs them based on feedback from verification and evaluation.

    Example:
        >>> repair_agent = RepairAgent()
        >>> fixed = await repair_agent.repair(candidate, feedback, llm)
    """

    def __init__(
        self,
        feedback_parser: FeedbackParser | None = None,
        strategy: RepairStrategy | None = None,
    ):
        """Initialize the repair agent.

        Args:
            feedback_parser: Optional feedback parser.
            strategy: Optional repair strategy.
        """
        self._parser = feedback_parser or create_feedback_parser()
        self._strategy = strategy or create_repair_strategy()
        self._repair_history: list[dict[str, Any]] = []

    async def repair(
        self,
        candidate: CodeCandidate,
        verification_result: dict[str, Any] | None = None,
        evaluation_result: dict[str, Any] | None = None,
        llm: Any | None = None,
    ) -> CodeCandidate | None:
        """Repair a candidate based on feedback.

        Args:
            candidate: The candidate to repair.
            verification_result: Optional verification result.
            evaluation_result: Optional evaluation result.
            llm: Optional LLM for repair generation.

        Returns:
            Repaired candidate or None if repair fails.
        """
        logger.info(f"Repairing candidate {candidate.id[:8]}")

        feedback_list = self._parser.parse_all(
            verification_result=verification_result,
            evaluation_result=evaluation_result,
        )

        if not feedback_list:
            logger.warning("No feedback to repair from")
            return None

        instruction = self._strategy.prepare_instruction(feedback_list)

        logger.info(f"Using repair strategy: {instruction.strategy.value}")

        if llm is None:
            repaired = self._simulate_repair(candidate, feedback_list)
        else:
            repaired = await self._llm_repair(candidate, instruction, llm)

        if repaired:
            self._repair_history.append(
                {
                    "original_id": candidate.id,
                    "repaired_id": repaired.id,
                    "strategy": instruction.strategy.value,
                    "feedback_count": len(feedback_list),
                }
            )

        return repaired

    async def _llm_repair(
        self,
        candidate: CodeCandidate,
        instruction: RepairInstruction,
        llm: Any,
    ) -> CodeCandidate | None:
        """Repair using LLM.

        Args:
            candidate: Candidate to repair.
            instruction: Repair instruction.
            llm: LLM instance.

        Returns:
            Repaired candidate or None.
        """
        try:
            prompt = self._strategy.prepare_prompt(candidate.code, instruction)

            messages = [
                {"role": "system", "content": "You are a code repair expert."},
                {"role": "user", "content": prompt},
            ]

            response = await llm.achat(messages=messages)
            fixed_code = (
                response.content if hasattr(response, "content") else str(response)
            )

            repaired = CodeCandidate(
                id=str(uuid.uuid4()),
                code=fixed_code,
                model=candidate.model,
                status=CandidateStatus.PENDING,
                metadata={
                    "repaired_from": candidate.id,
                    "strategy": instruction.strategy.value,
                },
            )

            logger.info(f"Repaired candidate {candidate.id[:8]} -> {repaired.id[:8]}")
            return repaired

        except Exception as e:
            logger.error(f"LLM repair failed: {e}")
            return None

    def _simulate_repair(
        self,
        candidate: CodeCandidate,
        feedback_list: list,
    ) -> CodeCandidate:
        """Simulate repair without LLM (for testing).

        Args:
            candidate: Candidate to repair.
            feedback_list: Feedback list.

        Returns:
            Simulated repaired candidate.
        """
        feedback_summary = "\n".join(fb.message for fb in feedback_list[:3])

        repaired = CodeCandidate(
            id=str(uuid.uuid4()),
            code=(
                f"# Repaired based on feedback:\n"
                f"# {feedback_summary}\n\n"
                f"{candidate.code}"
            ),
            model=candidate.model,
            status=CandidateStatus.PENDING,
            metadata={
                "repaired_from": candidate.id,
                "strategy": "simulated",
            },
        )

        logger.info(f"Simulated repair: {candidate.id[:8]} -> {repaired.id[:8]}")
        return repaired

    async def repair_with_retry(
        self,
        candidate: CodeCandidate,
        verification_result: dict[str, Any] | None = None,
        evaluation_result: dict[str, Any] | None = None,
        llm: Any | None = None,
    ) -> CodeCandidate | None:
        """Repair with multiple attempts.

        Args:
            candidate: Candidate to repair.
            verification_result: Optional verification result.
            evaluation_result: Optional evaluation result.
            llm: Optional LLM.

        Returns:
            Repaired candidate or None.
        """
        current = candidate

        for attempt in range(self._strategy.max_attempts):
            logger.info(f"Repair attempt {attempt + 1}/{self._strategy.max_attempts}")

            repaired = await self.repair(
                current,
                verification_result,
                evaluation_result,
                llm,
            )

            if repaired is None:
                logger.warning(f"Repair attempt {attempt + 1} returned None")
                break

            if verification_result and verification_result.get("passed"):
                logger.info(f"Repair successful on attempt {attempt + 1}")
                return repaired

            current = repaired

        logger.warning(f"All {self._strategy.max_attempts} repair attempts completed")
        return current

    def get_repair_history(self) -> list[dict[str, Any]]:
        """Get repair history.

        Returns:
            List of repair records.
        """
        return self._repair_history.copy()

    def set_strategy(self, strategy_type: RepairStrategyType) -> None:
        """Set the repair strategy.

        Args:
            strategy_type: Type of strategy to use.
        """
        self._strategy = create_repair_strategy(strategy_type)

    @property
    def strategy(self) -> RepairStrategy:
        """Get the current repair strategy.

        Returns:
            RepairStrategy instance.
        """
        return self._strategy


def create_repair_agent(
    strategy_type: RepairStrategyType = RepairStrategyType.INCREMENTAL,
) -> RepairAgent:
    """Factory function to create a RepairAgent.

    Args:
        strategy_type: Type of repair strategy.

    Returns:
        RepairAgent instance.
    """
    strategy = create_repair_strategy(strategy_type)
    return RepairAgent(strategy=strategy)
