"""Tests for CodeCandidate model."""

from openhands.sdk.agent.codegen_pool.candidate import (
    CandidateStatus,
    CodeCandidate,
)


class TestCodeCandidate:
    """Tests for CodeCandidate."""

    def test_create_candidate(self):
        """Test basic candidate creation."""
        candidate = CodeCandidate(
            id="test-123",
            code="print('hello')",
            model="claude-sonnet",
        )

        assert candidate.id == "test-123"
        assert candidate.code == "print('hello')"
        assert candidate.model == "claude-sonnet"
        assert candidate.status == CandidateStatus.PENDING
        assert candidate.created_at is not None

    def test_accept(self):
        """Test accepting a candidate."""
        candidate = CodeCandidate(id="test", code="code", model="model")
        candidate.accept()

        assert candidate.status == CandidateStatus.ACCEPTED

    def test_reject(self):
        """Test rejecting a candidate."""
        candidate = CodeCandidate(id="test", code="code", model="model")
        candidate.reject("Too many errors")

        assert candidate.status == CandidateStatus.REJECTED
        assert candidate.error_message == "Too many errors"

    def test_set_score(self):
        """Test setting evaluation score."""
        candidate = CodeCandidate(id="test", code="code", model="model")
        candidate.set_score(0.85)

        assert candidate.score == 0.85

    def test_to_dict(self):
        """Test dictionary conversion."""
        candidate = CodeCandidate(
            id="test-123",
            code="print('hello')",
            model="claude-sonnet",
            score=0.9,
        )

        result = candidate.to_dict()

        assert result["id"] == "test-123"
        assert result["code"] == "print('hello')"
        assert result["model"] == "claude-sonnet"
        assert result["score"] == 0.9
        assert result["status"] == "pending"

    def test_generation_time(self):
        """Test generation time tracking."""
        candidate = CodeCandidate(
            id="test",
            code="code",
            model="model",
            generation_time=1.5,
        )

        assert candidate.generation_time == 1.5

    def test_metadata(self):
        """Test metadata storage."""
        candidate = CodeCandidate(
            id="test",
            code="code",
            model="model",
            metadata={"key": "value"},
        )

        assert candidate.metadata["key"] == "value"
