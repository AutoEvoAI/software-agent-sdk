"""Requirements parser for SupervisorAgent."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import ClassVar


class RequirementType(str, Enum):
    """Type of requirement."""

    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"
    CONSTRAINT = "constraint"
    USER_STORY = "user_story"


class Priority(str, Enum):
    """Priority level."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Requirement:
    """Represents a parsed requirement."""

    type: RequirementType
    description: str
    priority: Priority
    entities: list[str]
    constraints: list[str]
    raw_text: str


@dataclass
class ParsedRequirements:
    """Container for all parsed requirements."""

    requirements: list[Requirement]
    entities: list[str]
    overall_priority: Priority
    domain: str | None


class RequirementsParser:
    """Parser for extracting structured requirements from natural language.

    This parser extracts:
    - Functional requirements
    - Non-functional requirements (performance, security, etc.)
    - Constraints
    - User stories
    - Key entities (objects, actions, states)
    """

    FUNCTIONAL_KEYWORDS: ClassVar[list[str]] = [
        "must",
        "should",
        "can",
        "able to",
        "provide",
        "allow",
        "create",
        "read",
        "update",
        "delete",
        "manage",
    ]

    NON_FUNCTIONAL_KEYWORDS: ClassVar[list[str]] = [
        "performance",
        "security",
        "reliability",
        "scalability",
        "availability",
        "maintainability",
        "usability",
    ]

    CONSTRAINT_KEYWORDS: ClassVar[list[str]] = [
        "only",
        "must not",
        "cannot",
        "limit",
        "maximum",
        "minimum",
        "must be",
        "required to",
        "must have",
    ]

    PRIORITY_PATTERNS: ClassVar[dict[Priority, list[str]]] = {
        Priority.CRITICAL: [r"\bcritical\b", r"\bessential\b", r"\bmust have\b"],
        Priority.HIGH: [r"\bimportant\b", r"\bshould have\b", r"\bhigh priority\b"],
        Priority.MEDIUM: [r"\bnice to have\b", r"\bshould\b"],
        Priority.LOW: [r"\blow priority\b", r"\boptional\b", r"\bif possible\b"],
    }

    def parse(self, user_message: str) -> ParsedRequirements:
        """Parse user message into structured requirements.

        Args:
            user_message: Natural language user requirements

        Returns:
            ParsedRequirements object
        """
        lines = user_message.split("\n")
        requirements = []

        all_entities = []
        max_priority = Priority.LOW

        for line in lines:
            line = line.strip()
            if not line:
                continue

            req_type = self._detect_type(line)
            priority = self._detect_priority(line)
            entities = self._extract_entities(line)
            constraints = self._extract_constraints(line)

            requirement = Requirement(
                type=req_type,
                description=line,
                priority=priority,
                entities=entities,
                constraints=constraints,
                raw_text=line,
            )
            requirements.append(requirement)
            all_entities.extend(entities)

            if priority == Priority.CRITICAL:
                max_priority = Priority.CRITICAL
            elif priority == Priority.HIGH and max_priority != Priority.CRITICAL:
                max_priority = Priority.HIGH
            elif priority == Priority.MEDIUM and max_priority in [
                Priority.LOW,
                Priority.MEDIUM,
            ]:
                max_priority = Priority.MEDIUM

        domain = self._detect_domain(user_message)

        return ParsedRequirements(
            requirements=requirements,
            entities=list(set(all_entities)),
            overall_priority=max_priority,
            domain=domain,
        )

    def _detect_type(self, text: str) -> RequirementType:
        """Detect requirement type from text."""
        text_lower = text.lower()

        for keyword in self.CONSTRAINT_KEYWORDS:
            if keyword in text_lower:
                return RequirementType.CONSTRAINT

        for keyword in self.NON_FUNCTIONAL_KEYWORDS:
            if keyword in text_lower:
                return RequirementType.NON_FUNCTIONAL

        for keyword in self.FUNCTIONAL_KEYWORDS:
            if keyword in text_lower:
                return RequirementType.FUNCTIONAL

        return RequirementType.USER_STORY

    def _detect_priority(self, text: str) -> Priority:
        """Detect priority from text."""
        text_lower = text.lower()

        for priority, patterns in self.PRIORITY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return priority

        return Priority.MEDIUM

    def _extract_entities(self, text: str) -> list[str]:
        """Extract key entities from text."""
        entities = []

        noun_patterns = [
            r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b",
            r"\b(\w+(?:tion|ment|ence|ance|ity))\b",
        ]

        for pattern in noun_patterns:
            matches = re.findall(pattern, text)
            entities.extend(matches)

        return list(set(entities))

    def _extract_constraints(self, text: str) -> list[str]:
        """Extract constraints from text."""
        constraints = []

        constraint_patterns = [
            r"(\w+\s+than\s+\w+)",
            r"(maximum\s+\w+)",
            r"(minimum\s+\w+)",
            r"(only\s+\w+)",
        ]

        for pattern in constraint_patterns:
            matches = re.findall(pattern, text.lower())
            constraints.extend(matches)

        return constraints

    def _detect_domain(self, text: str) -> str | None:
        """Detect application domain from text."""
        domain_keywords = {
            "e-commerce": ["order", "payment", "cart", "checkout", "product"],
            "api": ["endpoint", "request", "response", "rest", "graphql"],
            "database": ["query", "schema", "table", "index", "migration"],
            "web": ["frontend", "backend", "server", "client", "browser"],
            "security": ["auth", "authentication", "authorization", "permission"],
        }

        text_lower = text.lower()

        for domain, keywords in domain_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return domain

        return None


def create_parser() -> RequirementsParser:
    """Factory function to create a RequirementsParser.

    Returns:
        A RequirementsParser instance
    """
    return RequirementsParser()
