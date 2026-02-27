"""Tests for validator module."""

from openhands.sdk.agent.supervisor.validator import (
    SpecificationValidator,
    ValidationCategory,
    ValidationIssue,
    ValidationLevel,
    ValidationResult,
    create_validator,
)


class TestValidationLevel:
    """Tests for ValidationLevel enum."""

    def test_validation_level_values(self):
        """Test ValidationLevel enum values."""
        assert ValidationLevel.ERROR.value == "error"
        assert ValidationLevel.WARNING.value == "warning"
        assert ValidationLevel.INFO.value == "info"


class TestValidationCategory:
    """Tests for ValidationCategory enum."""

    def test_validation_category_values(self):
        """Test ValidationCategory enum values."""
        assert ValidationCategory.SYNTAX.value == "syntax"
        assert ValidationCategory.TYPE.value == "type"
        assert ValidationCategory.INVARIANT.value == "invariant"
        assert ValidationCategory.SAFETY.value == "safety"
        assert ValidationCategory.LIVENESS.value == "liveness"


class TestValidationIssue:
    """Tests for ValidationIssue dataclass."""

    def test_create_validation_issue(self):
        """Test creating a ValidationIssue."""
        issue = ValidationIssue(
            level=ValidationLevel.ERROR,
            category=ValidationCategory.SYNTAX,
            message="Missing semicolon",
            line_number=10,
            column_number=5,
        )

        assert issue.level == ValidationLevel.ERROR
        assert issue.category == ValidationCategory.SYNTAX
        assert issue.line_number == 10
        assert issue.column_number == 5


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_create_validation_result(self):
        """Test creating a ValidationResult."""
        result = ValidationResult(is_valid=True)
        assert result.is_valid is True
        assert len(result.issues) == 0

    def test_add_issue_error(self):
        """Test adding error issue."""
        result = ValidationResult(is_valid=True)
        issue = ValidationIssue(
            level=ValidationLevel.ERROR,
            category=ValidationCategory.SYNTAX,
            message="Error",
        )
        result.add_issue(issue)

        assert result.is_valid is False
        assert len(result.errors) == 1

    def test_add_issue_warning(self):
        """Test adding warning issue."""
        result = ValidationResult(is_valid=True)
        issue = ValidationIssue(
            level=ValidationLevel.WARNING,
            category=ValidationCategory.SYNTAX,
            message="Warning",
        )
        result.add_issue(issue)

        assert result.is_valid is True
        assert len(result.warnings) == 1


class TestSpecificationValidator:
    """Tests for SpecificationValidator class."""

    def test_create_validator(self):
        """Test creating a validator."""
        validator = SpecificationValidator()
        assert validator is not None

    def test_validate_empty_content(self):
        """Test validating empty content."""
        validator = SpecificationValidator()
        result = validator.validate("")

        assert result.is_valid is False

    def test_validate_valid_tla_plus_module(self):
        """Test validating valid TLA+ module."""
        content = r"""
---- MODULE TestSpec ----
EXTENDS Integers

VARIABLES x, y

Init ==
    /\ x = 0
    /\ y = 0

Next ==
    /\ x' = x + 1
    /\ y' = y + 1

TypeInvariant ==
    /\ x \in Int
    /\ y \in Int

====
"""
        validator = SpecificationValidator()
        result = validator.validate(content, "tla+")

        assert result.is_valid is True

    def test_validate_missing_module_declaration(self):
        """Test validating content without module declaration."""
        content = """
VARIABLES x
Init == x = 0
"""
        validator = SpecificationValidator()
        result = validator.validate(content, "tla+")

        has_module_error = any("MODULE" in issue.message for issue in result.errors)
        assert has_module_error is True

    def test_validate_invalid_module_name(self):
        """Test validating with invalid module name."""
        content = """
---- MODULE 123Invalid ----
VARIABLES x
====
"""
        validator = SpecificationValidator()
        result = validator.validate(content, "tla+")

        assert any("Invalid" in issue.message for issue in result.errors)

    def test_validate_matching_brackets(self):
        """Test bracket matching validation."""
        content = """
---- MODULE TestSpec ----
VARIABLES x
Init == x = 0
====
"""
        validator = SpecificationValidator()
        result = validator.validate(content, "tla+")

        assert result.is_valid is True

    def test_validate_unmatched_brackets(self):
        """Test detecting unmatched brackets."""
        content = """
---- MODULE TestSpec ----
VARIABLES x
Init == x = [0
====
"""
        validator = SpecificationValidator()
        result = validator.validate(content, "tla+")

        has_bracket_error = any(
            issue.category == ValidationCategory.SYNTAX for issue in result.errors
        )
        assert has_bracket_error is True

    def test_validate_no_variables_warning(self):
        """Test warning for missing variables."""
        content = """
---- MODULE TestSpec ----
Init == TRUE
====
"""
        validator = SpecificationValidator()
        result = validator.validate(content, "tla+")

        has_warning = any(
            "variable" in issue.message.lower() for issue in result.warnings
        )
        assert has_warning is True

    def test_validate_invariants_warning(self):
        """Test warning for missing invariants."""
        content = """
---- MODULE TestSpec ----
VARIABLES x
Init == x = 0
====
"""
        validator = SpecificationValidator()
        result = validator.validate(content, "tla+")

        has_invariant_warning = any(
            "invariant" in issue.message.lower() for issue in result.warnings
        )
        assert has_invariant_warning is True

    def test_validate_liveness_info(self):
        """Test info for missing liveness properties."""
        content = """
---- MODULE TestSpec ----
VARIABLES x
Init == x = 0
====
"""
        validator = SpecificationValidator()
        result = validator.validate(content, "tla+")

        has_liveness_info = any(
            "liveness" in issue.message.lower() for issue in result.info
        )
        assert has_liveness_info is True

    def test_validate_z_notation(self):
        """Test Z notation validation."""
        content = """
[Author :: Name]
"""
        validator = SpecificationValidator()
        result = validator.validate(content, "z")

        assert result.is_valid is True

    def test_validate_generic_empty(self):
        """Test generic validation for empty content."""
        validator = SpecificationValidator()
        result = validator.validate("", "custom")

        assert result.is_valid is False

    def test_custom_rule(self):
        """Test adding custom validation rule."""
        validator = SpecificationValidator()

        def custom_rule(content: str, result: ValidationResult):
            if "CUSTOM_ERROR" in content:
                result.add_issue(
                    ValidationIssue(
                        level=ValidationLevel.ERROR,
                        category=ValidationCategory.STRUCTURE,
                        message="Custom error found",
                    )
                )

        validator.add_custom_rule(custom_rule)

        result = validator.validate("CUSTOM_ERROR", "tla+")
        assert result.is_valid is False


class TestFactory:
    """Tests for factory functions."""

    def test_create_validator(self):
        """Test create_validator factory."""
        validator = create_validator()
        assert isinstance(validator, SpecificationValidator)
