"""Configuration for CodeGenAgentPool."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CodeGenConfig:
    """Configuration for code generation.

    Attributes:
        enable_multi_model: Whether to enable multi-model parallel generation.
            Default is False (single model).
        model_candidates: List of model names to use for generation.
            Used when enable_multi_model is True.
        default_model: Default model to use for single-model generation.
        temperature: Temperature for LLM generation.
        max_tokens: Maximum tokens to generate.
        timeout: Timeout for generation in seconds.
        enable_verification: Whether to enable formal verification.
        max_retries: Maximum number of retries for failed generation.
    """

    enable_multi_model: bool = False
    model_candidates: list[str] = field(
        default_factory=lambda: ["claude-sonnet-4-20250514"]
    )
    default_model: str = "claude-sonnet-4-20250514"
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 300
    enable_verification: bool = False
    max_retries: int = 3


def create_codegen_config(**kwargs: Any) -> CodeGenConfig:
    """Create a CodeGenConfig with optional overrides.

    Args:
        **kwargs: Optional configuration overrides.

    Returns:
        CodeGenConfig instance.
    """
    return CodeGenConfig(**kwargs)
