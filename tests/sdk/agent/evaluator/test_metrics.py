"""Tests for ScoringMetrics."""

from openhands.sdk.agent.evaluator.metrics import (
    EvaluationResult,
    MetricScore,
    MetricType,
    ScoringMetrics,
)


class TestScoringMetrics:
    """Tests for ScoringMetrics."""

    def test_default_weights(self):
        """Test default metric weights."""
        metrics = ScoringMetrics()

        assert metrics.weights[MetricType.CORRECTNESS] == 0.30
        assert metrics.weights[MetricType.EFFICIENCY] == 0.20
        assert metrics.weights[MetricType.READABILITY] == 0.15
        assert metrics.weights[MetricType.SECURITY] == 0.15

    def test_custom_weights(self):
        """Test custom weights."""
        weights = {MetricType.CORRECTNESS: 0.5, MetricType.EFFICIENCY: 0.5}
        metrics = ScoringMetrics(weights=weights)

        assert metrics.weights[MetricType.CORRECTNESS] == 0.5

    def test_evaluate_correctness_passed(self):
        """Test correctness evaluation with passed verification."""
        metrics = ScoringMetrics()

        result = metrics.evaluate_correctness(
            code="def foo(): pass",
            spec="spec",
            verification_result={"passed": True},
        )

        assert result.metric_type == MetricType.CORRECTNESS
        assert result.score == 1.0

    def test_evaluate_correctness_failed(self):
        """Test correctness evaluation with failed verification."""
        metrics = ScoringMetrics()

        result = metrics.evaluate_correctness(
            code="def foo(): pass",
            spec="spec",
            verification_result={"passed": False, "errors": [{"message": "error"}]},
        )

        assert result.score == 0.0

    def test_evaluate_efficiency(self):
        """Test efficiency evaluation."""
        metrics = ScoringMetrics()

        code_with_loops = """
for i in range(10):
    print(i)
"""
        result = metrics.evaluate_efficiency(code_with_loops)

        assert result.metric_type == MetricType.EFFICIENCY
        assert result.score >= 0.0

    def test_evaluate_readability(self):
        """Test readability evaluation."""
        metrics = ScoringMetrics()

        code = """
# This is a comment
def hello():
    print("Hello, world!")
"""
        result = metrics.evaluate_readability(code)

        assert result.metric_type == MetricType.READABILITY

    def test_evaluate_security_clean(self):
        """Test security evaluation with clean code."""
        metrics = ScoringMetrics()

        code = "def safe_function(x): return x + 1"
        result = metrics.evaluate_security(code)

        assert result.metric_type == MetricType.SECURITY
        assert result.score == 1.0

    def test_evaluate_security_dangerous(self):
        """Test security evaluation with dangerous code."""
        metrics = ScoringMetrics()

        code = "result = eval(user_input)"
        result = metrics.evaluate_security(code)

        assert result.score < 1.0

    def test_evaluate_style(self):
        """Test style evaluation."""
        metrics = ScoringMetrics()

        code = "def foo():\n    pass\n"
        result = metrics.evaluate_style(code)

        assert result.metric_type == MetricType.STYLE

    def test_evaluate_testability(self):
        """Test testability evaluation."""
        metrics = ScoringMetrics()

        code = """
def add(a, b):
    return a + b

def test_add():
    assert add(1, 2) == 3
"""
        result = metrics.evaluate_testability(code)

        assert result.metric_type == MetricType.TESTABILITY

    def test_evaluate_documentation(self):
        """Test documentation evaluation."""
        metrics = ScoringMetrics()

        code = '''
def hello():
    """Say hello."""
    print("Hello")
'''
        result = metrics.evaluate_documentation(code)

        assert result.metric_type == MetricType.DOCUMENTATION

    def test_evaluate_all(self):
        """Test complete evaluation."""
        metrics = ScoringMetrics()

        code = '''
def add(a, b):
    """Add two numbers."""
    return a + b
'''
        result = metrics.evaluate_all(
            code=code,
            candidate_id="test-123",
            verification_result={"passed": True},
        )

        assert result.candidate_id == "test-123"
        assert result.total_score >= 0.0
        assert result.passed is True
        assert result.metrics is not None
        assert len(result.metrics) == 7


class TestMetricScore:
    """Tests for MetricScore."""

    def test_weighted_score(self):
        """Test weighted score calculation."""
        metric = MetricScore(
            metric_type=MetricType.CORRECTNESS,
            score=0.8,
            weight=0.5,
        )

        assert metric.weighted_score() == 0.4


class TestEvaluationResult:
    """Tests for EvaluationResult."""

    def test_add_metric(self):
        """Test adding metrics."""
        result = EvaluationResult(candidate_id="test")
        result.add_metric(
            MetricScore(metric_type=MetricType.CORRECTNESS, score=0.9, weight=0.3)
        )

        assert result.metrics is not None
        assert len(result.metrics) == 1

    def test_to_dict(self):
        """Test dictionary conversion."""
        result = EvaluationResult(candidate_id="test")
        object.__setattr__(result, "overall_score", 0.85)
        result.passed = True

        d = result.to_dict()

        assert d["candidate_id"] == "test"
        assert d["overall_score"] == 0.85
        assert d["overall_score"] == 0.85
        assert d["passed"] is True
