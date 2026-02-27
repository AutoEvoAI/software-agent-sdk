"""Tests for decision engine module."""

from openhands.sdk.agent.supervisor.decision_engine import (
    AbortStrategy,
    Decision,
    DecisionEngine,
    DecisionType,
    ErrorCategory,
    ErrorContext,
    ErrorSeverity,
    EscalateStrategy,
    FallbackStrategy,
    RecoveryStrategy,
    RetryStrategy,
    SkipStrategy,
    create_decision_engine,
    create_error_context,
)


class TestDecisionType:
    """Tests for DecisionType enum."""

    def test_decision_type_values(self):
        """Test DecisionType enum values."""
        assert DecisionType.RETRY.value == "retry"
        assert DecisionType.ESCALATE.value == "escalate"
        assert DecisionType.ABORT.value == "abort"
        assert DecisionType.CONTINUE.value == "continue"


class TestErrorSeverity:
    """Tests for ErrorSeverity enum."""

    def test_error_severity_values(self):
        """Test ErrorSeverity enum values."""
        assert ErrorSeverity.LOW.value == "low"
        assert ErrorSeverity.MEDIUM.value == "medium"
        assert ErrorSeverity.HIGH.value == "high"
        assert ErrorSeverity.CRITICAL.value == "critical"


class TestErrorCategory:
    """Tests for ErrorCategory enum."""

    def test_error_category_values(self):
        """Test ErrorCategory enum values."""
        assert ErrorCategory.VALIDATION_ERROR.value == "validation_error"
        assert ErrorCategory.EXECUTION_ERROR.value == "execution_error"
        assert ErrorCategory.TIMEOUT_ERROR.value == "timeout_error"


class TestErrorContext:
    """Tests for ErrorContext dataclass."""

    def test_create_error_context(self):
        """Test creating an ErrorContext."""
        context = ErrorContext(
            error_type="ValueError",
            error_message="Invalid value",
            category=ErrorCategory.VALIDATION_ERROR,
            severity=ErrorSeverity.MEDIUM,
        )

        assert context.error_type == "ValueError"
        assert context.error_message == "Invalid value"
        assert context.category == ErrorCategory.VALIDATION_ERROR
        assert context.severity == ErrorSeverity.MEDIUM
        assert context.retry_count == 0


class TestDecision:
    """Tests for Decision dataclass."""

    def test_create_decision(self):
        """Test creating a Decision."""
        decision = Decision(
            decision_type=DecisionType.RETRY,
            reason="Retrying operation",
            confidence=0.8,
        )

        assert decision.decision_type == DecisionType.RETRY
        assert decision.reason == "Retrying operation"
        assert decision.confidence == 0.8


class TestRetryStrategy:
    """Tests for RetryStrategy."""

    def test_retry_strategy_can_handle(self):
        """Test RetryStrategy can_handle method."""
        strategy = RetryStrategy(max_retries=3)

        context = ErrorContext(
            error_type="TimeoutError",
            error_message="Request timed out",
            category=ErrorCategory.TIMEOUT_ERROR,
            severity=ErrorSeverity.MEDIUM,
            retry_count=0,
        )
        assert strategy.can_handle(context) is True

        context.retry_count = 3
        assert strategy.can_handle(context) is False

    def test_retry_strategy_execute(self):
        """Test RetryStrategy execute method."""
        strategy = RetryStrategy(max_retries=3, backoff_factor=2.0)

        context = ErrorContext(
            error_type="TimeoutError",
            error_message="Request timed out",
            category=ErrorCategory.TIMEOUT_ERROR,
            severity=ErrorSeverity.MEDIUM,
            retry_count=0,
        )

        decision = strategy.execute(context)

        assert decision.decision_type == DecisionType.RETRY
        assert decision.next_action is not None and "retry" in decision.next_action


class TestFallbackStrategy:
    """Tests for FallbackStrategy."""

    def test_fallback_strategy_can_handle(self):
        """Test FallbackStrategy can_handle method."""
        strategy = FallbackStrategy(fallback_value="default")

        low_context = ErrorContext(
            error_type="Error",
            error_message="Error",
            category=ErrorCategory.UNKNOWN_ERROR,
            severity=ErrorSeverity.LOW,
        )
        assert strategy.can_handle(low_context) is True

        critical_context = ErrorContext(
            error_type="Error",
            error_message="Error",
            category=ErrorCategory.UNKNOWN_ERROR,
            severity=ErrorSeverity.CRITICAL,
        )
        assert strategy.can_handle(critical_context) is False


class TestEscalateStrategy:
    """Tests for EscalateStrategy."""

    def test_escalate_strategy_can_handle(self):
        """Test EscalateStrategy can_handle method."""
        strategy = EscalateStrategy(escalation_threshold=ErrorSeverity.HIGH)

        low_context = ErrorContext(
            error_type="Error",
            error_message="Error",
            category=ErrorCategory.UNKNOWN_ERROR,
            severity=ErrorSeverity.LOW,
        )
        assert strategy.can_handle(low_context) is False

        high_context = ErrorContext(
            error_type="Error",
            error_message="Error",
            category=ErrorCategory.UNKNOWN_ERROR,
            severity=ErrorSeverity.HIGH,
        )
        assert strategy.can_handle(high_context) is True


class TestAbortStrategy:
    """Tests for AbortStrategy."""

    def test_abort_strategy_can_handle(self):
        """Test AbortStrategy can_handle method."""
        strategy = AbortStrategy()

        critical_context = ErrorContext(
            error_type="Error",
            error_message="Critical error",
            category=ErrorCategory.UNKNOWN_ERROR,
            severity=ErrorSeverity.CRITICAL,
        )
        assert strategy.can_handle(critical_context) is True

        low_context = ErrorContext(
            error_type="Error",
            error_message="Minor error",
            category=ErrorCategory.UNKNOWN_ERROR,
            severity=ErrorSeverity.LOW,
        )
        assert strategy.can_handle(low_context) is False


class TestSkipStrategy:
    """Tests for SkipStrategy."""

    def test_skip_strategy_can_handle(self):
        """Test SkipStrategy can_handle method."""
        strategy = SkipStrategy(skip_optional=True)

        optional_context = ErrorContext(
            error_type="Error",
            error_message="Error",
            category=ErrorCategory.UNKNOWN_ERROR,
            severity=ErrorSeverity.LOW,
            metadata={"is_optional": True},
        )
        assert strategy.can_handle(optional_context) is True


class TestDecisionEngine:
    """Tests for DecisionEngine class."""

    def test_create_decision_engine(self):
        """Test creating a DecisionEngine."""
        engine = DecisionEngine()
        assert engine is not None
        assert len(engine.strategies) > 0

    def test_decide_retry(self):
        """Test decision for retryable error."""
        engine = DecisionEngine()

        context = ErrorContext(
            error_type="TimeoutError",
            error_message="Request timed out",
            category=ErrorCategory.TIMEOUT_ERROR,
            severity=ErrorSeverity.MEDIUM,
            retry_count=0,
        )

        decision = engine.decide(context)
        assert decision.decision_type == DecisionType.RETRY

    def test_decide_abort(self):
        """Test decision for critical error."""
        engine = DecisionEngine()

        context = ErrorContext(
            error_type="FatalError",
            error_message="Fatal error",
            category=ErrorCategory.EXECUTION_ERROR,
            severity=ErrorSeverity.CRITICAL,
        )

        decision = engine.decide(context)
        assert decision.decision_type == DecisionType.ABORT

    def test_decide_escalate(self):
        """Test decision for high severity error."""
        engine = DecisionEngine()

        context = ErrorContext(
            error_type="SecurityError",
            error_message="Security breach",
            category=ErrorCategory.AUTHENTICATION_ERROR,
            severity=ErrorSeverity.HIGH,
        )

        decision = engine.decide(context)
        assert decision.decision_type == DecisionType.ESCALATE

    def test_custom_rule(self):
        """Test custom decision rule."""
        engine = DecisionEngine()

        def custom_handler(context: ErrorContext) -> Decision:
            return Decision(
                decision_type=DecisionType.SKIP,
                reason="Custom handler executed",
            )

        engine.add_custom_rule("CustomError", custom_handler)

        context = ErrorContext(
            error_type="CustomError",
            error_message="Custom error",
            category=ErrorCategory.UNKNOWN_ERROR,
            severity=ErrorSeverity.LOW,
        )

        decision = engine.decide(context)
        assert decision.decision_type == DecisionType.SKIP

    def test_decision_history(self):
        """Test decision history tracking."""
        engine = DecisionEngine()

        context1 = ErrorContext(
            error_type="TimeoutError",
            error_message="Timeout",
            category=ErrorCategory.TIMEOUT_ERROR,
            severity=ErrorSeverity.MEDIUM,
        )
        context2 = ErrorContext(
            error_type="Error",
            error_message="Error",
            category=ErrorCategory.EXECUTION_ERROR,
            severity=ErrorSeverity.CRITICAL,
        )

        engine.decide(context1)
        engine.decide(context2)

        history = engine.get_decision_history()
        assert len(history) == 2

    def test_clear_history(self):
        """Test clearing decision history."""
        engine = DecisionEngine()

        context = ErrorContext(
            error_type="Error",
            error_message="Error",
            category=ErrorCategory.UNKNOWN_ERROR,
            severity=ErrorSeverity.LOW,
        )
        engine.decide(context)

        engine.clear_history()
        assert len(engine.get_decision_history()) == 0

    def test_add_strategy(self):
        """Test adding custom strategy."""
        engine = DecisionEngine()
        initial_count = len(engine.strategies)

        class CustomStrategy(RecoveryStrategy):
            def __init__(self):
                super().__init__("custom")

            def can_handle(self, context: ErrorContext) -> bool:
                return True

            def execute(self, context: ErrorContext) -> Decision:
                return Decision(
                    decision_type=DecisionType.CONTINUE,
                    reason="Custom strategy",
                )

        engine.add_strategy(CustomStrategy())
        assert len(engine.strategies) == initial_count + 1

    def test_remove_strategy(self):
        """Test removing strategy."""
        engine = DecisionEngine()
        initial_count = len(engine.strategies)

        engine.remove_strategy("retry")
        assert len(engine.strategies) == initial_count - 1


class TestFactory:
    """Tests for factory functions."""

    def test_create_error_context(self):
        """Test create_error_context factory."""
        context = create_error_context(
            error_type="ValueError",
            error_message="Invalid value",
            category=ErrorCategory.VALIDATION_ERROR,
            severity=ErrorSeverity.HIGH,
        )

        assert context.error_type == "ValueError"
        assert context.category == ErrorCategory.VALIDATION_ERROR

    def test_create_decision_engine(self):
        """Test create_decision_engine factory."""
        engine = create_decision_engine()
        assert isinstance(engine, DecisionEngine)
