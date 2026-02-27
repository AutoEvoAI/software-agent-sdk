"""Data models for formal specifications."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SpecType(str, Enum):
    """Type of formal specification language."""

    TLA_PLUS = "tla+"
    Z_NOTATION = "z"
    CUSTOM = "custom"


class FormalSpec(BaseModel):
    """Formal specification for code generation and verification.

    This model represents a machine-readable formal specification that can be
    used for code generation, verification, and validation. It supports
    TLA+ and Z notation specifications.

    Attributes:
        spec_type: The type of specification (TLA+, Z, or custom)
        content: The raw specification content
        invariants: List of invariant properties that must always hold
        safety_properties: Safety properties - something bad never happens
        liveness_properties: Liveness properties - something good eventually happens
        version: Version identifier for the specification
        created_at: Timestamp when the specification was created
        updated_at: Timestamp when the specification was last updated
        metadata: Additional metadata for the specification
    """

    model_config = {"extra": "forbid"}

    spec_type: SpecType = Field(
        default=SpecType.TLA_PLUS,
        description="Type of formal specification language",
    )
    content: str = Field(
        default="",
        description="Raw specification content in the specified language",
    )
    invariants: list[str] = Field(
        default_factory=list,
        description="List of invariant properties that must always hold",
    )
    safety_properties: list[str] = Field(
        default_factory=list,
        description="Safety properties - something bad never happens",
    )
    liveness_properties: list[str] = Field(
        default_factory=list,
        description="Liveness properties - something good eventually happens",
    )
    version: str = Field(
        default="1.0.0",
        description="Version identifier for the specification",
    )
    name: str | None = Field(
        default=None,
        description="Optional name for the specification",
    )
    description: str | None = Field(
        default=None,
        description="Optional description of what this specification defines",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the specification was created",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the specification was last updated",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for the specification",
    )

    def add_invariant(self, invariant: str) -> None:
        """Add an invariant property to the specification."""
        self.invariants.append(invariant)
        self.updated_at = datetime.utcnow()

    def add_safety_property(self, property: str) -> None:
        """Add a safety property to the specification."""
        self.safety_properties.append(property)
        self.updated_at = datetime.utcnow()

    def add_liveness_property(self, property: str) -> None:
        """Add a liveness property to the specification."""
        self.liveness_properties.append(property)
        self.updated_at = datetime.utcnow()

    def to_tla_plus(self) -> str:
        """Convert specification to TLA+ format.

        Returns:
            TLA+ formatted string representation of the specification.
        """
        if self.spec_type != SpecType.TLA_PLUS:
            return self.content

        lines = ["---- MODULE " + (self.name or "Spec") + " ----"]
        lines.append("\n(* Specification *)")

        if self.invariants:
            lines.append("\nVARIABLES")
            lines.append("    state")
            lines.append(r"\n\* Invariants")
            for inv in self.invariants:
                lines.append(f"Invariant_{inv.replace(' ', '_')} == {inv}")

        if self.safety_properties:
            lines.append(r"\n\* Safety Properties")
            for prop in self.safety_properties:
                lines.append(f"Safety_{prop.replace(' ', '_')} == {prop}")

        if self.liveness_properties:
            lines.append(r"\n\* Liveness Properties")
            for prop in self.liveness_properties:
                lines.append(f"Liveness_{prop.replace(' ', '_')} == {prop}")

        lines.append("\n=====")
        return "\n".join(lines)
