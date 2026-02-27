"""Code generation agent pool.

This module provides the CodeGenAgentPool class that coordinates
code generation using either single model (default) or multi-model
(optional) approaches.
"""

from __future__ import annotations

from typing import Any

from openhands.sdk.logger import get_logger

from .candidate import CandidateStatus, CodeCandidate
from .config import CodeGenConfig, create_codegen_config
from .generator import (
    GenerationPrompt,
    SingleModelGenerator,
    create_single_model_generator,
)
from .router import MultiModelRouter, create_multi_model_router


logger = get_logger(__name__)

__all__ = [
    "CodeGenAgentPool",
    "CodeCandidate",
    "CandidateStatus",
    "CodeGenConfig",
    "create_codegen_config",
    "create_codegen_pool",
    "SingleModelGenerator",
    "create_single_model_generator",
    "MultiModelRouter",
    "create_multi_model_router",
    "GenerationPrompt",
]


class CodeGenAgentPool:
    """Pool for code generation with single or multi-model support.

    This pool coordinates code generation based on the configuration:
    - Single model (default): Uses one model for generation
    - Multi-model (optional): Uses multiple models for diverse candidates

    Example:
        >>> config = CodeGenConfig(enable_multi_model=False)
        >>> pool = CodeGenAgentPool(config=config)
        >>> candidates = await pool.generate(prompt, llm)
    """

    def __init__(self, config: CodeGenConfig | None = None):
        """Initialize the code generation pool.

        Args:
            config: Optional configuration. Uses default if not provided.
        """
        self.config = config or CodeGenConfig()

        if self.config.enable_multi_model:
            self._generator: MultiModelRouter = create_multi_model_router(self.config)
            logger.info(
                f"CodeGenAgentPool initialized in multi-model mode "
                f"with models: {self.config.model_candidates}"
            )
        else:
            # Using object.__setattr__ to bypass type checking for dynamic attribute
            object.__setattr__(
                self, "_generator", create_single_model_generator(self.config)
            )
            logger.info(
                f"CodeGenAgentPool initialized in single-model mode "
                f"with model: {self.config.default_model}"
            )

        self._candidates: list[CodeCandidate] = []

    async def generate(
        self,
        spec: str,
        task_description: str,
        llm: Any,
        context: dict[str, Any] | None = None,
    ) -> list[CodeCandidate]:
        """Generate code candidates based on specification.

        Args:
            spec: The formal specification to generate code from.
            task_description: Description of the task.
            llm: The LLM instance (or factory for multi-model).
            context: Optional additional context.

        Returns:
            List of generated code candidates.
        """
        prompt = GenerationPrompt(
            spec=spec,
            task_description=task_description,
            context=context,
        )

        if self.config.enable_multi_model:
            new_candidates = await self._generator.generate(prompt, llm)  # type: ignore[assignment]
        else:
            candidate = await self._generator.generate(prompt, llm)  # type: ignore[assignment]
            new_candidates = [candidate]

        self._candidates.extend(new_candidates)  # type: ignore[arg]
        logger.info(f"Generated {len(new_candidates)} candidate(s)")

        return new_candidates  # type: ignore[return-value]

    async def generate_with_retry(
        self,
        spec: str,
        task_description: str,
        llm: Any,
        context: dict[str, Any] | None = None,
    ) -> list[CodeCandidate]:
        """Generate code with retry on failure.

        Args:
            spec: The formal specification.
            task_description: Description of the task.
            llm: The LLM instance.
            context: Optional additional context.

        Returns:
            List of generated candidates (including retries).
        """
        all_candidates = []
        max_attempts = self.config.max_retries

        for attempt in range(max_attempts):
            candidates = await self.generate(spec, task_description, llm, context)
            all_candidates.extend(candidates)

            successful = [c for c in candidates if c.status != CandidateStatus.FAILED]
            if successful:
                logger.info(f"Successfully generated on attempt {attempt + 1}")
                break

            if attempt < max_attempts - 1:
                logger.warning(f"Attempt {attempt + 1} failed, retrying...")

        return all_candidates

    def get_candidates(
        self,
        status: CandidateStatus | None = None,
    ) -> list[CodeCandidate]:
        """Get generated candidates.

        Args:
            status: Optional filter by status.

        Returns:
            List of candidates.
        """
        if status is None:
            return self._candidates.copy()

        return [c for c in self._candidates if c.status == status]

    def get_best_candidate(self) -> CodeCandidate | None:
        """Get the best candidate based on score.

        Returns:
            The highest scoring candidate, or None if no candidates.
        """
        scored = [c for c in self._candidates if c.score is not None]
        if not scored:
            return None

        return max(scored, key=lambda c: c.score if c.score is not None else 0.0)

    def clear_candidates(self) -> None:
        """Clear all stored candidates."""
        self._candidates.clear()
        logger.info("Candidates cleared")

    @property
    def candidate_count(self) -> int:
        """Get the number of generated candidates.

        Returns:
            Number of candidates.
        """
        return len(self._candidates)

    @property
    def is_multi_model(self) -> bool:
        """Check if running in multi-model mode.

        Returns:
            True if multi-model mode is enabled.
        """
        return self.config.enable_multi_model

    @property
    def model_count(self) -> int:
        """Get the number of models being used.

        Returns:
            Number of models.
        """
        if self.config.enable_multi_model:
            return len(self.config.model_candidates)
        return 1


def create_codegen_pool(
    enable_multi_model: bool = False,
    model_candidates: list[str] | None = None,
    **kwargs: Any,
) -> CodeGenAgentPool:
    """Factory function to create a CodeGenAgentPool.

    Args:
        enable_multi_model: Whether to enable multi-model mode.
        model_candidates: List of model names for multi-model mode.
        **kwargs: Additional configuration options.

    Returns:
        CodeGenAgentPool instance.
    """
    candidates = model_candidates or ["claude-sonnet-4-20250514"]
    config = create_codegen_config(
        enable_multi_model=enable_multi_model,
        model_candidates=candidates,
        default_model=candidates[0]
        if not enable_multi_model
        else kwargs.get("default_model"),
        **kwargs,
    )
    return CodeGenAgentPool(config=config)
