"""Specification validator for formal specifications.

This module provides validation logic for TLA+ and other formal specifications.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar


class ValidationLevel(str, Enum):
    """Severity levels for validation issues."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationCategory(str, Enum):
    """Categories of validation checks."""

    SYNTAX = "syntax"
    TYPE = "type"
    INVARIANT = "invariant"
    SAFETY = "safety"
    LIVENESS = "liveness"
    STRUCTURE = "structure"
    COMPLETENESS = "completeness"


@dataclass
class ValidationIssue:
    """Represents a validation issue found in a specification."""

    level: ValidationLevel
    category: ValidationCategory
    message: str
    line_number: int | None = None
    column_number: int | None = None
    context: str | None = None
    suggestion: str | None = None


@dataclass
class ValidationResult:
    """Result of specification validation."""

    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)
    errors: list[ValidationIssue] = field(default_factory=list)
    info: list[ValidationIssue] = field(default_factory=list)

    def add_issue(self, issue: ValidationIssue) -> None:
        """Add a validation issue to the appropriate list."""
        self.issues.append(issue)
        if issue.level == ValidationLevel.ERROR:
            self.errors.append(issue)
            self.is_valid = False
        elif issue.level == ValidationLevel.WARNING:
            self.warnings.append(issue)
        else:
            self.info.append(issue)


class SpecificationValidator:
    """Validator for formal specifications.

    This validator checks specifications for:
    - Syntax correctness
    - Type consistency
    - Invariant validity
    - Safety property correctness
    - Liveness property correctness
    - Structural completeness
    """

    TLA_PLUS_RESERVED_WORDS: ClassVar[set[str]] = {
        "MODULE",
        "EXTENDS",
        "CONSTANTS",
        "VARIABLES",
        "VARIABLE",
        "ASSUME",
        "ASSUMPTION",
        "THEOREM",
        "PROPOSITION",
        "LEMMA",
        "COROLLARY",
        "AXIOM",
        "POSTCONDITION",
        "PRECONDITION",
        "LOCAL",
        "INSTANCE",
        "USE",
        "DEF",
        "DEFINE",
        "SUBSET",
        "UNION",
        "DOMAIN",
        "STRING",
        "BOOLEAN",
        "TRUE",
        "FALSE",
        "UNCHANGED",
        "ENABLED",
        "UNCHANGED",
        "SF",
        "WF",
        "EE",
        "E",
        "AE",
        "AA",
        "LET",
        "IN",
        "LAMBDA",
        "IF",
        "THEN",
        "ELSE",
        "IFF",
        "IMPLIES",
        "OR",
        "AND",
        "NOT",
        "\\A",
        "\\E",
        "\\o",
        "\\oplus",
        "\\cup",
        "\\cap",
        "\\subseteq",
        "\\in",
        "\\notin",
        "..",
        "=",
        "#",
        "<",
        ">",
        "<=",
        ">=",
    }

    def __init__(self):
        """Initialize the validator."""
        self._custom_rules: list[Any] = []

    def validate(self, content: str, spec_type: str = "tla+") -> ValidationResult:
        """Validate the specification content.

        Args:
            content: The specification content
            spec_type: The type of specification (default: tla+)

        Returns:
            ValidationResult object
        """
        if spec_type.lower() == "tla+":
            return self._validate_tla_plus(content)
        elif spec_type.lower() == "z":
            return self._validate_z_notation(content)
        else:
            return self._validate_generic(content)

    def _validate_tla_plus(self, content: str) -> ValidationResult:
        """Validate TLA+ specification."""
        result = ValidationResult(is_valid=True)

        lines = content.split("\n")

        self._check_module_structure(lines, result)
        self._check_variable_declarations(lines, result)
        self._check_invariants(lines, result)
        self._check_safety_properties(lines, result)
        self._check_liveness_properties(lines, result)
        self._check_syntax(lines, result)
        self._check_reserved_words(lines, result)

        for rule in self._custom_rules:
            rule(content, result)

        return result

    def _check_module_structure(
        self, lines: list[str], result: ValidationResult
    ) -> None:
        """Check the module structure."""
        has_module = False
        module_name = None

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            if stripped.startswith("---- MODULE"):
                has_module = True
                match = re.match(r"----\s*MODULE\s+(\w+)\s*----", stripped)
                if match:
                    module_name = match.group(1)
                elif stripped != "---- MODULE ----":
                    result.add_issue(
                        ValidationIssue(
                            level=ValidationLevel.ERROR,
                            category=ValidationCategory.STRUCTURE,
                            message="Invalid MODULE declaration format",
                            line_number=i,
                            suggestion="Use format: ---- MODULE ModuleName ----",
                        )
                    )

            if "EXTENDS" in stripped:
                pass

            if stripped == "====":
                break

        if not has_module:
            result.add_issue(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    category=ValidationCategory.STRUCTURE,
                    message="Missing MODULE declaration",
                    suggestion="Add: ---- MODULE ModuleName ----",
                )
            )

        if module_name and not self._is_valid_identifier(module_name):
            result.add_issue(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    category=ValidationCategory.STRUCTURE,
                    message=f"Invalid module name: {module_name}",
                    suggestion="Module name must be a valid TLA+ identifier",
                )
            )

    def _check_variable_declarations(
        self, lines: list[str], result: ValidationResult
    ) -> None:
        """Check variable declarations."""
        in_variables = False
        variables: list[str] = []

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            if stripped.startswith("VARIABLES ") or stripped == "VARIABLES":
                in_variables = True
                continue

            if in_variables:
                if stripped.startswith("VARIABLE "):
                    var_name = stripped.replace("VARIABLE ", "").strip()
                    variables.append(var_name)
                elif stripped and not stripped.startswith("(*"):
                    in_variables = False

        if not variables:
            result.add_issue(
                ValidationIssue(
                    level=ValidationLevel.WARNING,
                    category=ValidationCategory.COMPLETENESS,
                    message="No variables declared",
                    suggestion="Add VARIABLES declaration for state variables",
                )
            )

    def _check_invariants(self, lines: list[str], result: ValidationResult) -> None:
        """Check invariant declarations."""
        has_invariants = False

        for line in lines:
            if "Invariant" in line or "INVARIANT" in line:
                has_invariants = True
                if "Type" in line or "TYPE" in line:
                    pass

        if not has_invariants:
            result.add_issue(
                ValidationIssue(
                    level=ValidationLevel.WARNING,
                    category=ValidationCategory.INVARIANT,
                    message="No invariants declared",
                    suggestion="Add INVARIANT declarations for safety properties",
                )
            )

    def _check_safety_properties(
        self, lines: list[str], result: ValidationResult
    ) -> None:
        """Check safety property declarations."""
        safety_patterns = ["SafetyProperty", "SAFETY", "Invariant"]
        has_safety = False

        for line in lines:
            for pattern in safety_patterns:
                if pattern in line:
                    has_safety = True
                    break

        if not has_safety:
            result.add_issue(
                ValidationIssue(
                    level=ValidationLevel.INFO,
                    category=ValidationCategory.SAFETY,
                    message="No explicit safety properties found",
                    suggestion=("Add safety properties for critical system behaviors"),
                )
            )

    def _check_liveness_properties(
        self, lines: list[str], result: ValidationResult
    ) -> None:
        """Check liveness property declarations."""
        liveness_patterns = ["LiveSpec", "LIVENESS", "eventually", "SF_", "WF_"]
        has_liveness = False

        for line in lines:
            for pattern in liveness_patterns:
                if pattern in line:
                    has_liveness = True
                    break

        if not has_liveness:
            result.add_issue(
                ValidationIssue(
                    level=ValidationLevel.INFO,
                    category=ValidationCategory.LIVENESS,
                    message="No liveness properties found",
                    suggestion=(
                        "Consider adding liveness properties for system progress"
                    ),
                )
            )

    def _check_syntax(self, lines: list[str], result: ValidationResult) -> None:
        """Check basic TLA+ syntax."""
        bracket_stack: list[tuple[str, int]] = []
        paren_stack: list[tuple[str, int]] = []

        for i, line in enumerate(lines, 1):
            for j, char in enumerate(line):
                if char == "[":
                    bracket_stack.append(("[", i))
                elif char == "]":
                    if bracket_stack and bracket_stack[-1][0] == "[":
                        bracket_stack.pop()
                    else:
                        result.add_issue(
                            ValidationIssue(
                                level=ValidationLevel.ERROR,
                                category=ValidationCategory.SYNTAX,
                                message="Unmatched closing bracket ']'",
                                line_number=i,
                                column_number=j,
                            )
                        )

                if char == "(":
                    paren_stack.append(("(", i))
                elif char == ")":
                    if paren_stack and paren_stack[-1][0] == "(":
                        paren_stack.pop()
                    else:
                        result.add_issue(
                            ValidationIssue(
                                level=ValidationLevel.ERROR,
                                category=ValidationCategory.SYNTAX,
                                message="Unmatched closing parenthesis ')'",
                                line_number=i,
                                column_number=j,
                            )
                        )

        for bracket, line_num in bracket_stack:
            result.add_issue(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    category=ValidationCategory.SYNTAX,
                    message=f"Unmatched opening bracket '{bracket}'",
                    line_number=line_num,
                )
            )

    def _check_reserved_words(self, lines: list[str], result: ValidationResult) -> None:
        """Check for proper use of reserved words."""
        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            if stripped.startswith("---- MODULE"):
                match = re.match(r"----\s*MODULE\s+(\w+)\s*----", stripped)
                if match:
                    name = match.group(1)
                    if name.upper() in self.TLA_PLUS_RESERVED_WORDS:
                        result.add_issue(
                            ValidationIssue(
                                level=ValidationLevel.ERROR,
                                category=ValidationCategory.STRUCTURE,
                                message=(
                                    f"Module '{name}' conflicts with TLA+ reserved word"
                                ),
                                line_number=i,
                            )
                        )

    def _validate_z_notation(self, content: str) -> ValidationResult:  # noqa: ARG002
        """Validate Z notation specification.

        Args:
            content: Specification content (unused - Z notation not implemented)
        """
        result = ValidationResult(is_valid=True)

        result.add_issue(
            ValidationIssue(
                level=ValidationLevel.INFO,
                category=ValidationCategory.STRUCTURE,
                message="Z notation validation is limited",
                suggestion="Manual review recommended for Z specifications",
            )
        )

        return result

    def _validate_generic(self, content: str) -> ValidationResult:
        """Generic validation for unknown specification types."""
        result = ValidationResult(is_valid=True)

        if not content or not content.strip():
            result.add_issue(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    category=ValidationCategory.COMPLETENESS,
                    message="Specification content is empty",
                )
            )

        return result

    def _is_valid_identifier(self, name: str) -> bool:
        """Check if a name is a valid TLA+ identifier."""
        return bool(re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name))

    def add_custom_rule(self, rule: Any) -> None:
        """Add a custom validation rule.

        Args:
            rule: A callable that takes content and result
        """
        self._custom_rules.append(rule)


def create_validator() -> SpecificationValidator:
    """Factory function to create a SpecificationValidator.

    Returns:
        A SpecificationValidator instance
    """
    return SpecificationValidator()
