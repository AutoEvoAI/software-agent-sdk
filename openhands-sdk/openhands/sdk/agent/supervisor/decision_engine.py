"""Decision engine for exception handling in SupervisorAgent.

This module provides the decision logic for handling exceptions,
determining recovery strategies, and managing the workflow.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


logger = logging.getLogger(__name__)


class DecisionType(str, Enum):
    """Types of decisions the engine can make."""

    RETRY = "retry"
    RECOVER = "recover"
    ESCALATE = "escalate"
    ABORT = "abort"
    PAUSE = "pause"
    CONTINUE = "continue"
    FALLBACK = "fallback"
    SKIP = "skip"
    HUMAN_INTERVENTION = "human_intervention"


class ErrorSeverity(str, Enum):
    """Severity levels for errors."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """Categories of errors."""

    VALIDATION_ERROR = "validation_error"
    EXECUTION_ERROR = "execution_error"
    TIMEOUT_ERROR = "timeout_error"
    RESOURCE_ERROR = "resource_error"
    SPECIFICATION_ERROR = "specification_error"
    NETWORK_ERROR = "network_error"
    AUTHENTICATION_ERROR = "authentication_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ErrorContext:
    """Context information about an error."""

    error_type: str
    error_message: str
    category: ErrorCategory
    severity: ErrorSeverity
    stack_trace: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    task_id: str | None = None
    agent_id: str | None = None


@dataclass
class Decision:
    """Represents a decision made by the engine."""

    decision_type: DecisionType
    reason: str
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
    next_action: str | None = None
    fallback_value: Any = None


class RecoveryStrategy:
    """Base class for recovery strategies."""

    def __init__(self, name: str):
        self.name = name

    def can_handle(self, context: ErrorContext) -> bool:
        """Check if this strategy can handle the error."""
        raise NotImplementedError

    def execute(self, context: ErrorContext) -> Decision:
        """Execute the recovery strategy."""
        raise NotImplementedError


class RetryStrategy(RecoveryStrategy):
    """Retry the failed operation."""

    def __init__(self, max_retries: int = 3, backoff_factor: float = 2.0):
        super().__init__("retry")
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    def can_handle(self, context: ErrorContext) -> bool:
        if context.retry_count >= self.max_retries:
            return False
        return context.category not in [
            ErrorCategory.AUTHENTICATION_ERROR,
            ErrorCategory.SPECIFICATION_ERROR,
        ]

    def execute(self, context: ErrorContext) -> Decision:
        delay = self.backoff_factor**context.retry_count
        return Decision(
            decision_type=DecisionType.RETRY,
            reason=f"Retrying operation (attempt {context.retry_count + 1})",
            metadata={"retry_delay": delay, "max_retries": self.max_retries},
            next_action="retry_operation",
        )


class FallbackStrategy(RecoveryStrategy):
    """Use fallback value or method."""

    def __init__(self, fallback_value: Any = None):
        super().__init__("fallback")
        self.fallback_value = fallback_value

    def can_handle(self, context: ErrorContext) -> bool:
        return context.severity in [ErrorSeverity.LOW, ErrorSeverity.MEDIUM]

    def execute(self, context: ErrorContext) -> Decision:  # noqa: ARG002
        """Execute the fallback strategy.

        Args:
            context: Error context (unused in fallback strategy)
        """
        return Decision(
            decision_type=DecisionType.FALLBACK,
            reason="Using fallback value",
            fallback_value=self.fallback_value,
            next_action="use_fallback",
        )


class EscalateStrategy(RecoveryStrategy):
    """Escalate to human intervention."""

    def __init__(self, escalation_threshold: ErrorSeverity = ErrorSeverity.HIGH):
        super().__init__("escalate")
        self.escalation_threshold = escalation_threshold

    def can_handle(self, context: ErrorContext) -> bool:
        severity_order = [
            ErrorSeverity.LOW,
            ErrorSeverity.MEDIUM,
            ErrorSeverity.HIGH,
            ErrorSeverity.CRITICAL,
        ]
        return severity_order.index(context.severity) >= severity_order.index(
            self.escalation_threshold
        )

    def execute(self, context: ErrorContext) -> Decision:
        return Decision(
            decision_type=DecisionType.ESCALATE,
            reason=f"Escalating due to {context.severity.value} severity error",
            metadata={"requires_human": True},
            next_action="escalate",
        )


class AbortStrategy(RecoveryStrategy):
    """Abort the operation."""

    def __init__(self):
        super().__init__("abort")

    def can_handle(self, context: ErrorContext) -> bool:
        return context.severity == ErrorSeverity.CRITICAL

    def execute(self, context: ErrorContext) -> Decision:  # noqa: ARG002
        """Execute the abort strategy..

        Args:
            context: Error context (unused in abort strategy)
        """
        return Decision(
            decision_type=DecisionType.ABORT,
            reason="Critical error - aborting operation",
            next_action="abort",
        )


class SkipStrategy(RecoveryStrategy):
    """Skip the failed operation."""

    def __init__(self, skip_optional: bool = True):
        super().__init__("skip")
        self.skip_optional = skip_optional

    def can_handle(self, context: ErrorContext) -> bool:
        if context.metadata.get("is_optional", False):
            return True
        return self.skip_optional and context.severity == ErrorSeverity.LOW

    def execute(self, context: ErrorContext) -> Decision:  # noqa: ARG002
        """Execute the skip strategy.

        Args:
            context: Error context (unused in skip strategy)
        """
        return Decision(
            decision_type=DecisionType.SKIP,
            reason="Skipping optional/failed operation",
            next_action="continue",
        )


def _get_default_strategies() -> list[RecoveryStrategy]:
    """Get default recovery strategies."""
    return [
        AbortStrategy(),
        EscalateStrategy(),
        RetryStrategy(),
        FallbackStrategy(),
        SkipStrategy(),
    ]


class DecisionEngine:
    """Decision engine for handling exceptions and determining recovery actions.

    The engine uses a set of recovery strategies to determine the appropriate
    action for different error types and severities.
    """

    def __init__(
        self,
        strategies: list[RecoveryStrategy] | None = None,
        custom_rules: dict[str, Callable[[ErrorContext], Decision]] | None = None,
    ):
        """Initialize the decision engine.

        Args:
            strategies: List of recovery strategies to use
            custom_rules: Custom decision rules keyed by error type
        """
        self.strategies = strategies or _get_default_strategies()
        self.custom_rules = custom_rules or {}
        self._decision_history: list[tuple[ErrorContext, Decision]] = []

    def decide(self, context: ErrorContext) -> Decision:
        """Make a decision based on the error context.

        Args:
            context: The error context

        Returns:
            The Decision object
        """
        if context.error_type in self.custom_rules:
            decision = self.custom_rules[context.error_type](context)
            self._decision_history.append((context, decision))
            return decision

        for strategy in self.strategies:
            if strategy.can_handle(context):
                decision = strategy.execute(context)
                self._decision_history.append((context, decision))
                logger.info(
                    f"Decision made: {decision.decision_type.value} - {decision.reason}"
                )
                return decision

        return Decision(
            decision_type=DecisionType.ABORT,
            reason="No strategy could handle the error",
        )

    def add_strategy(self, strategy: RecoveryStrategy) -> None:
        """Add a recovery strategy.

        Args:
            strategy: The strategy to add
        """
        self.strategies.append(strategy)

    def remove_strategy(self, name: str) -> None:
        """Remove a recovery strategy by name.

        Args:
            name: The name of the strategy to remove
        """
        self.strategies = [s for s in self.strategies if s.name != name]

    def add_custom_rule(
        self, error_type: str, rule: Callable[[ErrorContext], Decision]
    ) -> None:
        """Add a custom decision rule.

        Args:
            error_type: The error type to match
            rule: The decision function
        """
        self.custom_rules[error_type] = rule

    def get_decision_history(self) -> list[tuple[ErrorContext, Decision]]:
        """Get the decision history.

        Returns:
            List of (context, decision) tuples
        """
        return self._decision_history.copy()

    def clear_history(self) -> None:
        """Clear the decision history."""
        self._decision_history.clear()


def create_error_context(
    error_type: str,
    error_message: str,
    category: ErrorCategory,
    severity: ErrorSeverity,
    **kwargs: Any,
) -> ErrorContext:
    """Factory function to create an ErrorContext.

    Args:
        error_type: The error type
        error_message: The error message
        category: The error category
        severity: The error severity
        **kwargs: Additional context attributes

    Returns:
        An ErrorContext instance
    """
    return ErrorContext(
        error_type=error_type,
        error_message=error_message,
        category=category,
        severity=severity,
        **kwargs,
    )


def create_decision_engine(
    custom_strategies: list[RecoveryStrategy] | None = None,
) -> DecisionEngine:
    """Factory function to create a DecisionEngine.

    Args:
        custom_strategies: Optional list of custom strategies

    Returns:
        A DecisionEngine instance
    """
    return DecisionEngine(strategies=custom_strategies)
