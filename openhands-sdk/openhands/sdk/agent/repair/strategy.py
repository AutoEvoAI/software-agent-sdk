"""Repair strategies for the repair agent."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RepairStrategyType(str, Enum):
    """Types of repair strategies."""

    INCREMENTAL = "incremental"
    FULL_REGENERATE = "full_regenerate"
    TARGETED = "targeted"


@dataclass
class RepairInstruction:
    """Instruction for repairing code.

    Attributes:
        strategy: The repair strategy to use.
        feedback_summary: Summary of feedback.
        max_attempts: Maximum repair attempts.
    """

    strategy: RepairStrategyType
    feedback_summary: str
    max_attempts: int = 3


class RepairStrategy:
    """Base class for repair strategies."""

    def __init__(self, max_attempts: int = 3):
        """Initialize the repair strategy.

        Args:
            max_attempts: Maximum number of repair attempts.
        """
        self.max_attempts = max_attempts

    def prepare_instruction(
        self,
        feedback_list: list,
    ) -> RepairInstruction:
        """Prepare repair instruction from feedback.

        Args:
            feedback_list: List of feedback items.

        Returns:
            Repair instruction.
        """
        feedback_summary = self._summarize_feedback(feedback_list)
        strategy = self._determine_strategy(feedback_list)

        return RepairInstruction(
            strategy=strategy,
            feedback_summary=feedback_summary,
            max_attempts=self.max_attempts,
        )

    def prepare_prompt(
        self,
        original_code: str,
        instruction: RepairInstruction,
    ) -> str:
        """Prepare prompt for repair.

        Args:
            original_code: The original code to repair.
            instruction: Repair instruction.

        Returns:
            Prompt for the repair LLM.
        """
        raise NotImplementedError("Subclasses must implement prepare_prompt")

    def _summarize_feedback(self, feedback_list: list) -> str:
        """Summarize feedback into a prompt-friendly string.

        Args:
            feedback_list: List of feedback items.

        Returns:
            Summary string.
        """
        if not feedback_list:
            return "No specific feedback provided."

        summary_parts = []
        for fb in feedback_list:
            if hasattr(fb, "message"):
                summary_parts.append(f"- {fb.message}")
            else:
                summary_parts.append(f"- {fb}")

        return "\n".join(summary_parts[:5])

    def _determine_strategy(self, feedback_list: list) -> RepairStrategyType:
        """Determine the best repair strategy.

        Args:
            feedback_list: List of feedback items.

        Returns:
            Repair strategy type.
        """
        if not feedback_list:
            return RepairStrategyType.FULL_REGENERATE

        high_severity_count = 0
        for fb in feedback_list:
            if hasattr(fb, "severity") and fb.severity == "high":
                high_severity_count += 1

        if high_severity_count > 2:
            return RepairStrategyType.FULL_REGENERATE

        return RepairStrategyType.INCREMENTAL


class IncrementalRepairStrategy(RepairStrategy):
    """Incremental repair strategy.

    Makes targeted fixes based on feedback without full regeneration.
    """

    def prepare_prompt(
        self,
        original_code: str,
        instruction: RepairInstruction,
    ) -> str:
        """Prepare prompt for incremental repair.

        Args:
            original_code: The original code to repair.
            instruction: Repair instruction.

        Returns:
            Prompt for the repair LLM.
        """
        return (
            "You are a code repair expert. Fix the following code based on "
            "the feedback provided.\n\n"
            "Original Code:\n"
            f"```\n{original_code}\n```\n\n"
            "Feedback:\n"
            f"{instruction.feedback_summary}\n\n"
            "Instructions:\n"
            "1. Make targeted fixes based on the feedback\n"
            "2. Preserve working parts of the code\n"
            "3. Do not change functionality that is not related to the feedback\n"
            "4. Provide the corrected code only.\n\n"
            "Repaired Code:"
        )


class FullRegenerateStrategy(RepairStrategy):
    """Full regeneration strategy.

    Regenerates code from scratch based on specification and feedback.
    """

    def __init__(self, max_attempts: int = 3):
        """Initialize the strategy."""
        super().__init__(max_attempts)

    def prepare_prompt(
        self,
        original_code: str,
        instruction: RepairInstruction,
    ) -> str:
        """Prepare prompt for full regeneration.

        Args:
            original_code: The specification (used as code context).
            instruction: Repair instruction.

        Returns:
            Prompt for the regeneration LLM.
        """
        spec = original_code
        return (
            "You are an expert software developer. Regenerate the code based "
            "on the specification and address the feedback.\n\n"
            "Specification:\n"
            f"{spec}\n\n"
            "Feedback (must address):\n"
            f"{instruction.feedback_summary}\n\n"
            "Instructions:\n"
            "1. Regenerate the code addressing all feedback\n"
            "2. Ensure correctness, efficiency, and security\n"
            "3. Provide the complete corrected code.\n\n"
            "Corrected Code:"
        )


class TargetedRepairStrategy(RepairStrategy):
    """Targeted repair strategy.

    Focuses on specific locations mentioned in feedback.
    """

    def prepare_prompt(
        self,
        original_code: str,
        instruction: RepairInstruction,
        locations: list[dict] | None = None,
    ) -> str:
        """Prepare prompt for targeted repair.

        Args:
            original_code: The original code.
            instruction: Repair instruction.
            locations: Specific locations to repair.

        Returns:
            Prompt for targeted repair.
        """
        if locations is None:
            locations = []
        location_str = "\n".join(
            f"- Line {loc.get('line', 'unknown')}: {loc.get('description', '')}"
            for loc in locations
        )

        return f"""You are a code repair expert. Fix specific locations in the code.

Original Code:
```
{original_code}
```

Locations to fix:
{location_str}

Feedback:
{instruction.feedback_summary}

Instructions:
1. Fix only the mentioned locations
2. Preserve the rest of the code
3. Provide the corrected code only.

Corrected Code:"""


def create_repair_strategy(
    strategy_type: RepairStrategyType = RepairStrategyType.INCREMENTAL,
    max_attempts: int = 3,
) -> RepairStrategy:
    """Factory function to create a repair strategy.

    Args:
        strategy_type: Type of repair strategy.
        max_attempts: Maximum attempts.

    Returns:
        RepairStrategy instance.
    """
    if strategy_type == RepairStrategyType.INCREMENTAL:
        return IncrementalRepairStrategy(max_attempts)
    elif strategy_type == RepairStrategyType.FULL_REGENERATE:
        return FullRegenerateStrategy(max_attempts)
    else:
        return TargetedRepairStrategy(max_attempts)
