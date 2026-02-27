"""Code candidate model for code generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class CandidateStatus(str, Enum):
    """Status of a code candidate."""

    PENDING = "pending"
    GENERATING = "generating"
    VERIFIED = "verified"
    FAILED = "failed"
    REJECTED = "rejected"
    ACCEPTED = "accepted"


@dataclass
class CodeCandidate:
    """Represents a generated code candidate.

    Attributes:
        id: Unique identifier for the candidate.
        code: Generated code content.
        model: Model used to generate the code.
        status: Current status of the candidate.
        generation_time: Time taken to generate the code in seconds.
        verification_result: Result from formal verification (if enabled).
        error_message: Error message if generation or verification failed.
        metadata: Additional metadata about the generation.
        created_at: Timestamp when the candidate was created.
        score: Evaluation score (if evaluated).
    """

    id: str
    code: str
    model: str
    status: CandidateStatus = CandidateStatus.PENDING
    generation_time: float | None = None
    verification_result: dict[str, Any] | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    score: float | None = None

    def __post_init__(self) -> None:
        """Initialize default values after construction."""
        if self.created_at is None:
            self.created_at = datetime.now()

    def accept(self) -> None:
        """Mark the candidate as accepted."""
        self.status = CandidateStatus.ACCEPTED

    def reject(self, reason: str | None = None) -> None:
        """Mark the candidate as rejected.

        Args:
            reason: Optional reason for rejection.
        """
        self.status = CandidateStatus.REJECTED
        if reason:
            self.error_message = reason

    def set_score(self, score: float) -> None:
        """Set the evaluation score.

        Args:
            score: The evaluation score.
        """
        self.score = score

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary representation of the candidate.
        """
        return {
            "id": self.id,
            "code": self.code,
            "model": self.model,
            "status": self.status.value,
            "generation_time": self.generation_time,
            "verification_result": self.verification_result,
            "error_message": self.error_message,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "score": self.score,
        }
