"""Evaluator agent for multi-dimensional scoring and ranking.

This module provides the EvaluatorAgent class that evaluates
generated code candidates using multiple metrics and ranks them.
"""

from __future__ import annotations

from typing import Any

from openhands.sdk.agent.codegen_pool.candidate import CodeCandidate
from openhands.sdk.logger import get_logger

from .metrics import (
    EvaluationResult,
    MetricType,
    ScoringMetrics,
    create_scoring_metrics,
)
from .ranker import RankingAlgorithm, RankingStrategy, create_ranker


logger = get_logger(__name__)


class EvaluatorAgent:
    """Agent for evaluating and ranking code candidates.

    The EvaluatorAgent uses multiple metrics to evaluate generated
    code candidates and ranks them based on the selected strategy.

    Example:
        >>> evaluator = EvaluatorAgent()
        >>> result = await evaluator.evaluate(candidates, spec)
        >>> best = evaluator.get_best(candidates)
    """

    def __init__(
        self,
        scoring_metrics: ScoringMetrics | None = None,
        ranker: RankingAlgorithm | None = None,
    ):
        """Initialize the evaluator agent.

        Args:
            scoring_metrics: Optional scoring metrics. Uses default if not provided.
            ranker: Optional ranking algorithm. Uses default if not provided.
        """
        self._scorer = scoring_metrics or create_scoring_metrics()
        self._ranker = ranker or create_ranker()
        self._last_evaluation: dict[str, EvaluationResult] = {}

    async def evaluate(
        self,
        candidates: list[CodeCandidate],
        spec: str | None = None,
        verification_results: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, EvaluationResult]:
        """Evaluate all candidates.

        Args:
            candidates: List of candidates to evaluate.
            spec: Optional specification for correctness evaluation.
            verification_results: Optional verification results keyed by candidate ID.

        Returns:
            Dictionary mapping candidate IDs to evaluation results.
        """
        results: dict[str, EvaluationResult] = {}

        for candidate in candidates:
            verification_result = None
            if verification_results and candidate.id in verification_results:
                verification_result = verification_results[candidate.id]

            result = self._scorer.evaluate_all(
                code=candidate.code,
                candidate_id=candidate.id,
                spec=spec,
                verification_result=verification_result,
            )

            candidate.set_score(result.total_score)
            results[candidate.id] = result
            self._last_evaluation[candidate.id] = result

            logger.info(
                f"Evaluated candidate {candidate.id[:8]}: "
                f"score={result.total_score:.3f}, passed={result.passed}"
            )

        return results

    async def evaluate_single(
        self,
        candidate: CodeCandidate,
        spec: str | None = None,
        verification_result: dict[str, Any] | None = None,
    ) -> EvaluationResult:
        """Evaluate a single candidate.

        Args:
            candidate: Candidate to evaluate.
            spec: Optional specification.
            verification_result: Optional verification result.

        Returns:
            Evaluation result.
        """
        result = self._scorer.evaluate_all(
            code=candidate.code,
            candidate_id=candidate.id,
            spec=spec,
            verification_result=verification_result,
        )

        candidate.set_score(result.total_score)
        self._last_evaluation[candidate.id] = result

        return result

    def rank(
        self,
        candidates: list[CodeCandidate],
    ) -> list[CodeCandidate]:
        """Rank candidates.

        Args:
            candidates: Candidates to rank.

        Returns:
            Sorted list of candidates.
        """
        return self._ranker.rank(candidates)

    def get_best(
        self,
        candidates: list[CodeCandidate],
    ) -> CodeCandidate | None:
        """Get the best candidate.

        Args:
            candidates: Candidates to select from.

        Returns:
            Best candidate or None.
        """
        ranked = self.rank(candidates)
        return ranked[0] if ranked else None

    def get_top(
        self,
        candidates: list[CodeCandidate],
        n: int = 3,
    ) -> list[CodeCandidate]:
        """Get top N candidates.

        Args:
            candidates: Candidates to select from.
            n: Number of top candidates.

        Returns:
            List of top N candidates.
        """
        return self._ranker.get_top(candidates, n)

    def get_evaluation(self, candidate_id: str) -> EvaluationResult | None:
        """Get evaluation result for a candidate.

        Args:
            candidate_id: ID of the candidate.

        Returns:
            Evaluation result or None.
        """
        return self._last_evaluation.get(candidate_id)

    def set_ranking_strategy(self, strategy: RankingStrategy) -> None:
        """Set the ranking strategy.

        Args:
            strategy: The strategy to use.
        """
        self._ranker = create_ranker(strategy)

    @property
    def scorer(self) -> ScoringMetrics:
        """Get the scoring metrics.

        Returns:
            ScoringMetrics instance.
        """
        return self._scorer

    @property
    def ranker(self) -> RankingAlgorithm:
        """Get the ranking algorithm.

        Returns:
            RankingAlgorithm instance.
        """
        return self._ranker


def create_evaluator_agent(
    weights: dict[MetricType, float] | None = None,
    strategy: RankingStrategy = RankingStrategy.HYBRID,
) -> EvaluatorAgent:
    """Factory function to create an EvaluatorAgent.

    Args:
        weights: Optional custom weights for metrics.
        strategy: The ranking strategy.

    Returns:
        EvaluatorAgent instance.
    """
    metrics = create_scoring_metrics(weights) if weights else None
    ranker = create_ranker(strategy)
    return EvaluatorAgent(scoring_metrics=metrics, ranker=ranker)
