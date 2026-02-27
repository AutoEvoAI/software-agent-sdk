"""Ranking algorithm for code candidates."""

from __future__ import annotations

from enum import Enum

from openhands.sdk.agent.codegen_pool.candidate import CodeCandidate


class RankingStrategy(str, Enum):
    """Strategy for ranking candidates."""

    SCORE = "score"
    SPEED = "speed"
    VERIFICATION = "verification"
    HYBRID = "hybrid"


class RankingAlgorithm:
    """Ranking algorithm for sorting code candidates.

    Provides various strategies for ranking generated code candidates
    based on different criteria.
    """

    def __init__(self, strategy: RankingStrategy = RankingStrategy.HYBRID):
        """Initialize the ranker.

        Args:
            strategy: The ranking strategy to use.
        """
        self.strategy = strategy

    def rank(
        self,
        candidates: list[CodeCandidate],
    ) -> list[CodeCandidate]:
        """Rank candidates based on the selected strategy.

        Args:
            candidates: List of candidates to rank.

        Returns:
            Sorted list of candidates (best first).
        """
        if self.strategy == RankingStrategy.SCORE:
            return self._rank_by_score(candidates)
        elif self.strategy == RankingStrategy.SPEED:
            return self._rank_by_speed(candidates)
        elif self.strategy == RankingStrategy.VERIFICATION:
            return self._rank_by_verification(candidates)
        else:
            return self._rank_hybrid(candidates)

    def _rank_by_score(self, candidates: list[CodeCandidate]) -> list[CodeCandidate]:
        """Rank by evaluation score.

        Args:
            candidates: Candidates to rank.

        Returns:
            Sorted candidates.
        """
        scored = [c for c in candidates if c.score is not None]
        unscored = [c for c in candidates if c.score is None]

        scored.sort(key=lambda c: c.score if c.score is not None else 0.0, reverse=True)

        return scored + unscored

    def _rank_by_speed(self, candidates: list[CodeCandidate]) -> list[CodeCandidate]:
        """Rank by generation speed (fastest first).

        Args:
            candidates: Candidates to rank.

        Returns:
            Sorted candidates.
        """
        with_time = [c for c in candidates if c.generation_time is not None]
        without_time = [c for c in candidates if c.generation_time is None]

        with_time.sort(
            key=lambda c: (
                c.generation_time if c.generation_time is not None else float("inf")
            )
        )

        return with_time + without_time

    def _rank_by_verification(
        self, candidates: list[CodeCandidate]
    ) -> list[CodeCandidate]:
        """Rank by verification status.

        Args:
            candidates: Candidates to rank.

        Returns:
            Sorted candidates.
        """
        verified = []
        pending = []
        failed = []

        for c in candidates:
            if c.verification_result and c.verification_result.get("passed"):
                verified.append(c)
            elif c.status.value == "pending":
                pending.append(c)
            else:
                failed.append(c)

        return verified + pending + failed

    def _rank_hybrid(self, candidates: list[CodeCandidate]) -> list[CodeCandidate]:
        """Rank using hybrid approach.

        Priority:
        1. Verified + high score
        2. Verified + any score
        3. High score
        4. Others

        Args:
            candidates: Candidates to rank.

        Returns:
            Sorted candidates.
        """
        category1 = []
        category2 = []
        category3 = []
        category4 = []

        for c in candidates:
            is_verified = c.verification_result and c.verification_result.get("passed")
            has_score = c.score is not None and c.score >= 0.7

            if is_verified and has_score:
                category1.append(c)
            elif is_verified:
                category2.append(c)
            elif has_score:
                category3.append(c)
            else:
                category4.append(c)

        category1.sort(key=lambda c: c.score or 0, reverse=True)
        category2.sort(key=lambda c: c.score or 0, reverse=True)
        category3.sort(key=lambda c: c.score or 0, reverse=True)

        return category1 + category2 + category3 + category4

    def get_top(
        self,
        candidates: list[CodeCandidate],
        n: int = 1,
    ) -> list[CodeCandidate]:
        """Get top N candidates.

        Args:
            candidates: Candidates to select from.
            n: Number of top candidates to return.

        Returns:
            Top N candidates.
        """
        ranked = self.rank(candidates)
        return ranked[:n]


def create_ranker(
    strategy: RankingStrategy = RankingStrategy.HYBRID,
) -> RankingAlgorithm:
    """Factory function to create a RankingAlgorithm.

    Args:
        strategy: The ranking strategy.

    Returns:
        RankingAlgorithm instance.
    """
    return RankingAlgorithm(strategy=strategy)
