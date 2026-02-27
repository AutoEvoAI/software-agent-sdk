"""Feedback parser for repair agent."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


class FeedbackType(str, Enum):
    """Types of feedback for repair."""

    ERROR = "error"
    WARNING = "warning"
    SUGGESTION = "suggestion"
    VERIFICATION_FAILED = "verification_failed"
    EVALUATION_FAILED = "evaluation_failed"
    STYLE = "style"
    SECURITY = "security"


@dataclass
class RepairFeedback:
    """Feedback that triggers a repair.

    Attributes:
        feedback_type: Type of feedback.
        message: Feedback message.
        location: Optional location (file, line, column).
        severity: Severity level (low, medium, high).
        suggested_fix: Optional suggested fix.
    """

    feedback_type: FeedbackType
    message: str
    location: dict[str, Any] | None = None
    severity: str = "medium"
    suggested_fix: str | None = None


class FeedbackParser:
    """Parser for extracting repair feedback from various sources.

    Parses feedback from verification results, evaluation results,
    and other sources into structured RepairFeedback objects.
    """

    def parse_verification_feedback(
        self,
        verification_result: dict[str, Any],
    ) -> list[RepairFeedback]:
        """Parse feedback from verification results.

        Args:
            verification_result: Verification result dictionary.

        Returns:
            List of repair feedback.
        """
        feedback_list = []

        if not verification_result.get("passed", True):
            errors = verification_result.get("errors", [])
            for error in errors:
                feedback = RepairFeedback(
                    feedback_type=FeedbackType.VERIFICATION_FAILED,
                    message=str(error.get("message", "Verification failed")),
                    location=error.get("location"),
                    severity="high",
                )
                feedback_list.append(feedback)

        warnings = verification_result.get("warnings", [])
        for warning in warnings:
            feedback = RepairFeedback(
                feedback_type=FeedbackType.WARNING,
                message=str(warning.get("message", "Verification warning")),
                location=warning.get("location"),
                severity="medium",
            )
            feedback_list.append(feedback)

        return feedback_list

    def parse_evaluation_feedback(
        self,
        evaluation_result: dict[str, Any],
    ) -> list[RepairFeedback]:
        """Parse feedback from evaluation results.

        Args:
            evaluation_result: Evaluation result dictionary.

        Returns:
            List of repair feedback.
        """
        feedback_list = []

        if not evaluation_result.get("passed", True):
            feedback_msgs = evaluation_result.get("feedback", [])
            for msg in feedback_msgs:
                feedback = RepairFeedback(
                    feedback_type=FeedbackType.EVALUATION_FAILED,
                    message=msg,
                    severity="medium",
                )
                feedback_list.append(feedback)

            metrics = evaluation_result.get("metrics", [])
            for metric in metrics:
                if metric.get("score", 1.0) < 0.5:
                    metric_type = metric.get("type", "unknown")
                    score = metric.get("score", 0)
                    feedback = RepairFeedback(
                        feedback_type=FeedbackType.SUGGESTION,
                        message=f"Low score on {metric_type}: {score}",
                        severity="low",
                    )
                    feedback_list.append(feedback)

        return feedback_list

    def parse_error_message(
        self,
        error_message: str,
    ) -> list[RepairFeedback]:
        """Parse feedback from error messages.

        Args:
            error_message: Raw error message.

        Returns:
            List of repair feedback.
        """
        feedback_list = []

        line_match = re.search(r"line (\d+)", error_message)
        location = None
        if line_match:
            location = {"line": int(line_match.group(1))}

        col_match = re.search(r"column (\d+)", error_message)
        if col_match and location:
            location["column"] = int(col_match.group(1))

        feedback = RepairFeedback(
            feedback_type=FeedbackType.ERROR,
            message=error_message,
            location=location,
            severity="high",
        )
        feedback_list.append(feedback)

        return feedback_list

    def parse_security_feedback(
        self,
        security_issues: list[dict[str, Any]],
    ) -> list[RepairFeedback]:
        """Parse security-related feedback.

        Args:
            security_issues: List of security issues.

        Returns:
            List of repair feedback.
        """
        feedback_list = []

        for issue in security_issues:
            feedback = RepairFeedback(
                feedback_type=FeedbackType.SECURITY,
                message=issue.get("message", "Security issue detected"),
                location=issue.get("location"),
                severity="high",
                suggested_fix=issue.get("suggested_fix"),
            )
            feedback_list.append(feedback)

        return feedback_list

    def parse_all(
        self,
        verification_result: dict[str, Any] | None = None,
        evaluation_result: dict[str, Any] | None = None,
        error_message: str | None = None,
        security_issues: list[dict[str, Any]] | None = None,
    ) -> list[RepairFeedback]:
        """Parse all sources of feedback.

        Args:
            verification_result: Optional verification result.
            evaluation_result: Optional evaluation result.
            error_message: Optional error message.
            security_issues: Optional security issues.

        Returns:
            Combined list of repair feedback.
        """
        feedback_list = []

        if verification_result:
            feedback_list.extend(self.parse_verification_feedback(verification_result))

        if evaluation_result:
            feedback_list.extend(self.parse_evaluation_feedback(evaluation_result))

        if error_message:
            feedback_list.extend(self.parse_error_message(error_message))

        if security_issues:
            feedback_list.extend(self.parse_security_feedback(security_issues))

        return feedback_list


def create_feedback_parser() -> FeedbackParser:
    """Factory function to create a FeedbackParser.

    Returns:
        FeedbackParser instance.
    """
    return FeedbackParser()
