"""Tests for RankingAlgorithm."""

from openhands.sdk.agent.codegen_pool.candidate import CandidateStatus, CodeCandidate
from openhands.sdk.agent.evaluator.ranker import (
    RankingAlgorithm,
    RankingStrategy,
    create_ranker,
)


def make_candidate(
    id: str,
    score: float | None = None,
    generation_time: float | None = None,
    verification_passed: bool | None = None,
    status: CandidateStatus = CandidateStatus.PENDING,
) -> CodeCandidate:
    """Helper to create a test candidate."""
    verification_result = None
    if verification_passed is not None:
        verification_result = {"passed": verification_passed}

    return CodeCandidate(
        id=id,
        code="def test(): pass",
        model="test-model",
        score=score,
        generation_time=generation_time,
        verification_result=verification_result,
        status=status,
    )


class TestRankingStrategy:
    """Tests for RankingStrategy enum."""

    def test_enum_values(self):
        """Test enum values."""
        assert RankingStrategy.SCORE.value == "score"
        assert RankingStrategy.SPEED.value == "speed"
        assert RankingStrategy.VERIFICATION.value == "verification"
        assert RankingStrategy.HYBRID.value == "hybrid"


class TestRankingAlgorithm:
    """Tests for RankingAlgorithm."""

    def test_rank_by_score(self):
        """Test ranking by score."""
        ranker = RankingAlgorithm(strategy=RankingStrategy.SCORE)

        candidates = [
            make_candidate("c1", score=0.5),
            make_candidate("c2", score=0.9),
            make_candidate("c3", score=0.7),
        ]

        ranked = ranker.rank(candidates)

        assert ranked[0].id == "c2"
        assert ranked[1].id == "c3"
        assert ranked[2].id == "c1"

    def test_rank_by_score_with_none(self):
        """Test ranking by score with unscored candidates."""
        ranker = RankingAlgorithm(strategy=RankingStrategy.SCORE)

        candidates = [
            make_candidate("c1", score=0.5),
            make_candidate("c2", score=None),
            make_candidate("c3", score=0.9),
        ]

        ranked = ranker.rank(candidates)

        assert ranked[0].id == "c3"
        assert ranked[1].id == "c1"
        assert ranked[2].id == "c2"

    def test_rank_by_speed(self):
        """Test ranking by speed."""
        ranker = RankingAlgorithm(strategy=RankingStrategy.SPEED)

        candidates = [
            make_candidate("c1", generation_time=2.0),
            make_candidate("c2", generation_time=0.5),
            make_candidate("c3", generation_time=1.0),
        ]

        ranked = ranker.rank(candidates)

        assert ranked[0].id == "c2"
        assert ranked[1].id == "c3"
        assert ranked[2].id == "c1"

    def test_rank_by_speed_with_none(self):
        """Test ranking by speed with candidates without timing."""
        ranker = RankingAlgorithm(strategy=RankingStrategy.SPEED)

        candidates = [
            make_candidate("c1", generation_time=2.0),
            make_candidate("c2", generation_time=None),
            make_candidate("c3", generation_time=1.0),
        ]

        ranked = ranker.rank(candidates)

        assert ranked[0].id == "c3"
        assert ranked[1].id == "c1"
        assert ranked[2].id == "c2"

    def test_rank_by_verification(self):
        """Test ranking by verification."""
        ranker = RankingAlgorithm(strategy=RankingStrategy.VERIFICATION)

        candidates = [
            make_candidate("c1", status=CandidateStatus.FAILED),
            make_candidate("c2", verification_passed=True),
            make_candidate("c3", status=CandidateStatus.GENERATING),
        ]

        ranked = ranker.rank(candidates)

        assert ranked[0].id == "c2"
        assert len(ranked) == 3

    def test_rank_hybrid(self):
        """Test hybrid ranking."""
        ranker = RankingAlgorithm(strategy=RankingStrategy.HYBRID)

        candidates = [
            make_candidate("c1", score=0.5, verification_passed=True),
            make_candidate("c2", score=0.9, verification_passed=True),
            make_candidate("c3", score=0.8, verification_passed=False),
            make_candidate("c4", score=None, verification_passed=False),
        ]

        ranked = ranker.rank(candidates)

        assert ranked[0].id == "c2"
        assert ranked[1].id == "c1"
        assert ranked[2].id == "c3"
        assert ranked[3].id == "c4"

    def test_get_top(self):
        """Test getting top N candidates."""
        ranker = RankingAlgorithm(strategy=RankingStrategy.SCORE)

        candidates = [
            make_candidate("c1", score=0.5),
            make_candidate("c2", score=0.9),
            make_candidate("c3", score=0.7),
            make_candidate("c4", score=0.8),
        ]

        top2 = ranker.get_top(candidates, n=2)

        assert len(top2) == 2
        assert top2[0].id == "c2"
        assert top2[1].id == "c4"

    def test_get_top_more_than_available(self):
        """Test getting top N when N > candidates."""
        ranker = RankingAlgorithm(strategy=RankingStrategy.SCORE)

        candidates = [
            make_candidate("c1", score=0.9),
        ]

        top5 = ranker.get_top(candidates, n=5)

        assert len(top5) == 1

    def test_empty_candidates(self):
        """Test ranking empty list."""
        ranker = RankingAlgorithm(strategy=RankingStrategy.SCORE)

        ranked = ranker.rank([])
        assert ranked == []

    def test_create_ranker_factory(self):
        """Test factory function."""
        ranker = create_ranker(strategy=RankingStrategy.SPEED)

        assert ranker.strategy == RankingStrategy.SPEED
