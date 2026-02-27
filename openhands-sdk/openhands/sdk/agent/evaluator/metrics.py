"""Scoring metrics for code evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, ClassVar


class MetricType(str, Enum):
    """Types of evaluation metrics."""

    CORRECTNESS = "correctness"
    EFFICIENCY = "efficiency"
    READABILITY = "readability"
    SECURITY = "security"
    STYLE = "style"
    TESTABILITY = "testability"
    DOCUMENTATION = "documentation"


@dataclass
class MetricScore:
    """Score for a single metric.

    Attributes:
        metric_type: The type of metric.
        score: The score value (0-1).
        weight: The weight of this metric in the overall score.
        details: Additional details about the score.
    """

    metric_type: MetricType
    score: float
    weight: float = 0.0
    details: dict[str, Any] | None = None

    def weighted_score(self) -> float:
        """Calculate the weighted score.

        Returns:
            The weighted score (score * weight).
        """
        return self.score * self.weight


@dataclass
class EvaluationResult:
    """Result of a multi-dimensional evaluation.

    Attributes:
        candidate_id: ID of the candidate being evaluated.
        overall_score: Weighted average of all metric scores.
        metrics: List of individual metric scores.
        passed: Whether the candidate passed the evaluation.
    """

    candidate_id: str
    overall_score: float = 0.0
    metrics: list[MetricScore] | None = None
    passed: bool = False
    feedback: list[str] | None = None

    def __post_init__(self) -> None:
        """Initialize default values."""
        if self.metrics is None:
            self.metrics = []
        if self.feedback is None:
            self.feedback = []

    @property
    def total_score(self) -> float:
        """Alias for overall_score for backward compatibility."""
        return self.overall_score

    def __setattr__(self, name: str, value: Any) -> None:
        """Handle total_score as alias for overall_score."""
        if name == "total_score":
            name = "overall_score"
        super().__setattr__(name, value)

    def add_metric(self, metric: MetricScore) -> None:
        """Add a metric to the evaluation result.

        Args:
            metric: The metric to add.
        """
        assert self.metrics is not None
        self.metrics.append(metric)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary representation of the evaluation result.
        """
        assert self.metrics is not None
        return {
            "candidate_id": self.candidate_id,
            "overall_score": self.overall_score,
            "passed": self.passed,
            "metrics": [
                {
                    "type": m.metric_type.value,
                    "score": m.score,
                    "weight": m.weight,
                    "weighted_score": m.weighted_score(),
                    "details": m.details,
                }
                for m in self.metrics
            ],
        }


class ScoringMetrics:
    """Scoring metrics for code evaluation.

    Provides methods to calculate various metrics for evaluating
    generated code candidates.
    """

    DEFAULT_WEIGHTS: ClassVar[dict[MetricType, float]] = {
        MetricType.CORRECTNESS: 0.30,
        MetricType.EFFICIENCY: 0.20,
        MetricType.READABILITY: 0.15,
        MetricType.SECURITY: 0.15,
        MetricType.STYLE: 0.10,
        MetricType.TESTABILITY: 0.05,
        MetricType.DOCUMENTATION: 0.05,
    }

    def __init__(self, weights: dict[MetricType, float] | None = None):
        """Initialize with optional custom weights.

        Args:
            weights: Optional custom weights for metrics.
        """
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()

    def evaluate_correctness(
        self,
        code: str,
        spec: str,
        verification_result: dict[str, Any] | None = None,
    ) -> MetricScore:
        """Evaluate code correctness.

        Args:
            code: The generated code (unused, kept for interface compatibility).
            spec: The specification (unused, kept for interface compatibility).
            verification_result: Optional formal verification result.

        Returns:
            MetricScore for correctness.
        """
        del code, spec  # unused, kept for interface compatibility
        score = 0.5
        details: dict[str, Any] = {}

        if verification_result:
            if verification_result.get("passed", False):
                score = 1.0
                details["verification"] = "passed"
            else:
                score = 0.0
                details["verification"] = "failed"
                details["errors"] = verification_result.get("errors", [])

        return MetricScore(
            metric_type=MetricType.CORRECTNESS,
            score=score,
            weight=self.weights.get(MetricType.CORRECTNESS, 0.3),
            details=details,
        )

    def evaluate_efficiency(self, code: str) -> MetricScore:
        """Evaluate code efficiency.

        Args:
            code: The generated code.

        Returns:
            MetricScore for efficiency.
        """
        score = 0.7
        details: dict[str, Any] = {}

        code_lower = code.lower()

        has_loops = "for " in code_lower or "while " in code_lower
        has_complexity = "O(n" in code or "O(" in code

        if has_loops:
            details["has_loops"] = True
        if has_complexity:
            details["mentions_complexity"] = True

        if "TODO" in code or "FIXME" in code:
            score -= 0.1

        score = max(0.0, min(1.0, score))

        return MetricScore(
            metric_type=MetricType.EFFICIENCY,
            score=score,
            weight=self.weights.get(MetricType.EFFICIENCY, 0.2),
            details=details,
        )

    def evaluate_readability(self, code: str) -> MetricScore:
        """Evaluate code readability.

        Args:
            code: The generated code.

        Returns:
            MetricScore for readability.
        """
        details: dict[str, Any] = {}

        lines = code.split("\n")
        non_empty_lines = [line for line in lines if line.strip()]

        avg_line_length = sum(len(line) for line in non_empty_lines) / max(
            len(non_empty_lines), 1
        )

        score = 0.8

        if avg_line_length > 100:
            score -= 0.2
            details["long_lines"] = True
        elif avg_line_length > 80:
            score -= 0.1

        has_comments = "#" in code or "//" in code or "/*" in code
        if has_comments:
            details["has_comments"] = True
        else:
            score -= 0.1

        snake_case = sum(1 for c in code if c.islower())
        camel_case = sum(1 for c in code if c.isupper())
        if snake_case > camel_case:
            score += 0.1

        score = max(0.0, min(1.0, score))

        return MetricScore(
            metric_type=MetricType.READABILITY,
            score=score,
            weight=self.weights.get(MetricType.READABILITY, 0.15),
            details=details,
        )

    def evaluate_security(self, code: str) -> MetricScore:
        """Evaluate code security.

        Args:
            code: The generated code.

        Returns:
            MetricScore for security.
        """
        score = 1.0
        details: dict[str, Any] = {}

        dangerous_patterns = [
            "eval(",
            "exec(",
            "os.system",
            "subprocess.call",
            "input(",
            "pickle.load",
            "yaml.load",
        ]

        for pattern in dangerous_patterns:
            if pattern in code:
                score -= 0.2
                details.setdefault("warnings", []).append(
                    f"Potential security issue: {pattern}"
                )

        if "password" in code.lower() or "secret" in code.lower():
            if "=" not in code or "#" in code:
                score -= 0.1

        score = max(0.0, min(1.0, score))

        return MetricScore(
            metric_type=MetricType.SECURITY,
            score=score,
            weight=self.weights.get(MetricType.SECURITY, 0.15),
            details=details,
        )

    def evaluate_style(self, code: str) -> MetricScore:
        """Evaluate code style.

        Args:
            code: The generated code.

        Returns:
            MetricScore for style.
        """
        score = 0.8
        details: dict[str, Any] = {}

        lines = code.split("\n")
        has_trailing_whitespace = any(line != line.rstrip() for line in lines)
        if has_trailing_whitespace:
            score -= 0.1
            details["trailing_whitespace"] = True

        has_inconsistent_indent = False
        for line in lines:
            if line.strip() and (" " in line and "\t" in line):
                has_inconsistent_indent = True
                break

        if has_inconsistent_indent:
            score -= 0.1
            details["inconsistent_indent"] = True

        score = max(0.0, min(1.0, score))

        return MetricScore(
            metric_type=MetricType.STYLE,
            score=score,
            weight=self.weights.get(MetricType.STYLE, 0.1),
            details=details,
        )

    def evaluate_testability(self, code: str) -> MetricScore:
        """Evaluate code testability.

        Args:
            code: The generated code.

        Returns:
            MetricScore for testability.
        """
        score = 0.6
        details: dict[str, Any] = {}

        has_functions = "def " in code or "function " in code
        has_classes = "class " in code

        if has_functions:
            score += 0.2
            details["has_functions"] = True

        if has_classes:
            score += 0.1
            details["has_classes"] = True

        if "test" in code.lower() or "mock" in code.lower():
            score += 0.1
            details["has_tests"] = True

        score = max(0.0, min(1.0, score))

        return MetricScore(
            metric_type=MetricType.TESTABILITY,
            score=score,
            weight=self.weights.get(MetricType.TESTABILITY, 0.05),
            details=details,
        )

    def evaluate_documentation(self, code: str) -> MetricScore:
        """Evaluate code documentation.

        Args:
            code: The generated code.

        Returns:
            MetricScore for documentation.
        """
        score = 0.5
        details: dict[str, Any] = {}

        docstring_patterns = ['"""', "'''", '"""', "'''"]
        has_docstrings = any(p in code for p in docstring_patterns)

        if has_docstrings:
            score += 0.3
            details["has_docstrings"] = True

        comment_lines = sum(
            1 for c in code.split("\n") if c.strip().startswith(("#", "//"))
        )
        if comment_lines > 0:
            score += 0.2
            details["comment_count"] = comment_lines

        score = max(0.0, min(1.0, score))

        return MetricScore(
            metric_type=MetricType.DOCUMENTATION,
            score=score,
            weight=self.weights.get(MetricType.DOCUMENTATION, 0.05),
            details=details,
        )

    def evaluate_all(
        self,
        code: str,
        candidate_id: str,
        spec: str | None = None,
        verification_result: dict[str, Any] | None = None,
    ) -> EvaluationResult:
        """Evaluate code on all metrics.

        Args:
            code: The generated code.
            candidate_id: ID of the candidate.
            spec: Optional specification.
            verification_result: Optional verification result.

        Returns:
            Complete evaluation result.
        """
        result = EvaluationResult(candidate_id=candidate_id)

        result.add_metric(
            self.evaluate_correctness(code, spec or "", verification_result)
        )
        result.add_metric(self.evaluate_efficiency(code))
        result.add_metric(self.evaluate_readability(code))
        result.add_metric(self.evaluate_security(code))
        result.add_metric(self.evaluate_style(code))
        result.add_metric(self.evaluate_testability(code))
        result.add_metric(self.evaluate_documentation(code))

        assert result.metrics is not None
        result.overall_score = sum(m.weighted_score() for m in result.metrics)
        result.passed = result.overall_score >= 0.5

        assert result.feedback is not None
        if result.passed:
            result.feedback.append(
                f"Passed evaluation with score {result.overall_score:.2f}"
            )
        else:
            result.feedback.append(
                f"Failed evaluation with score {result.overall_score:.2f}"
            )

        return result


def create_scoring_metrics(
    weights: dict[MetricType, float] | None = None,
) -> ScoringMetrics:
    """Factory function to create ScoringMetrics.

    Args:
        weights: Optional custom weights.

    Returns:
        ScoringMetrics instance.
    """
    return ScoringMetrics(weights=weights)
