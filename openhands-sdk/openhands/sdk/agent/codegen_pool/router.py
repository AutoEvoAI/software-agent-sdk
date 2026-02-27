"""Multi-model router for parallel code generation (optional)."""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any

from openhands.sdk.logger import get_logger

from .candidate import CandidateStatus, CodeCandidate
from .config import CodeGenConfig
from .generator import GenerationPrompt


logger = get_logger(__name__)


class RoutingStrategy(str, Enum):
    """Strategy for selecting models in multi-model mode."""

    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    FALLBACK = "fallback"


@dataclass
class ModelResult:
    """Result from a single model generation.

    Attributes:
        model: Model name.
        candidate: Generated candidate.
        success: Whether generation succeeded.
    """

    model: str
    candidate: CodeCandidate
    success: bool


class MultiModelRouter:
    """Multi-model router for code generation (optional feature).

    This router can generate code using multiple models in parallel
    or sequentially, providing diversity in generated candidates.
    Use when enable_multi_model is True.
    """

    def __init__(self, config: CodeGenConfig):
        """Initialize the multi-model router.

        Args:
            config: Configuration for code generation.
        """
        self.config = config
        self.strategy = RoutingStrategy.PARALLEL
        self._generation_count = 0

    async def generate(
        self,
        prompt: GenerationPrompt,
        llm_factory: Any,
    ) -> list[CodeCandidate]:
        """Generate code using multiple models.

        Args:
            prompt: The generation prompt containing spec and context.
            llm_factory: Factory to create LLM instances for different models.

        Returns:
            List of CodeCandidates from different models.
        """
        logger.info(
            f"Generating code with {len(self.config.model_candidates)} models "
            f"using strategy: {self.strategy.value}"
        )

        if self.strategy == RoutingStrategy.PARALLEL:
            return await self._generate_parallel(prompt, llm_factory)
        elif self.strategy == RoutingStrategy.SEQUENTIAL:
            return await self._generate_sequential(prompt, llm_factory)
        else:
            return await self._generate_fallback(prompt, llm_factory)

    async def _generate_parallel(
        self,
        prompt: GenerationPrompt,
        llm_factory: Any,
    ) -> list[CodeCandidate]:
        """Generate code from all models in parallel.

        Args:
            prompt: The generation prompt.
            llm_factory: Factory to create LLM instances.

        Returns:
            List of candidates from all models.
        """
        tasks = []
        for model in self.config.model_candidates:
            task = self._generate_with_model(prompt, llm_factory, model)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        candidates = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Model generation failed: {result}")
            else:
                candidates.append(result)

        self._generation_count += len(candidates)
        return candidates

    async def _generate_sequential(
        self,
        prompt: GenerationPrompt,
        llm_factory: Any,
    ) -> list[CodeCandidate]:
        """Generate code from models sequentially.

        Args:
            prompt: The generation prompt.
            llm_factory: Factory to create LLM instances.

        Returns:
            List of candidates from all models.
        """
        candidates = []

        for model in self.config.model_candidates:
            try:
                candidate = await self._generate_with_model(prompt, llm_factory, model)
                candidates.append(candidate)
            except Exception as e:
                logger.error(f"Model {model} generation failed: {e}")

        self._generation_count += len(candidates)
        return candidates

    async def _generate_fallback(
        self,
        prompt: GenerationPrompt,
        llm_factory: Any,
    ) -> list[CodeCandidate]:
        """Generate code with fallback strategy.

        Tries models in order until one succeeds.

        Args:
            prompt: The generation prompt.
            llm_factory: Factory to create LLM instances.

        Returns:
            List with one successful candidate (or all failures).
        """
        for model in self.config.model_candidates:
            try:
                candidate = await self._generate_with_model(prompt, llm_factory, model)
                if candidate.status != CandidateStatus.FAILED:
                    self._generation_count += 1
                    return [candidate]
            except Exception as e:
                logger.warning(f"Model {model} failed, trying next: {e}")

        self._generation_count += 1
        return [
            CodeCandidate(
                id=str(uuid.uuid4()),
                code="",
                model="all_failed",
                status=CandidateStatus.FAILED,
                error_message="All models failed",
            )
        ]

    async def _generate_with_model(
        self,
        prompt: GenerationPrompt,
        llm_factory: Any,
        model: str,
    ) -> CodeCandidate:
        """Generate code with a specific model.

        Args:
            prompt: The generation prompt.
            llm_factory: Factory to create LLM instances.
            model: Model name to use.

        Returns:
            Generated candidate.
        """
        candidate_id = str(uuid.uuid4())
        start_time = time.time()

        logger.info(f"Generating with model: {model}")

        try:
            llm = llm_factory(model)

            messages = self._build_messages(prompt)

            response = await llm.achat(
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

            code = response.content if hasattr(response, "content") else str(response)

            generation_time = time.time() - start_time

            logger.info(f"Model {model} completed in {generation_time:.2f}s")

            return CodeCandidate(
                id=candidate_id,
                code=code,
                model=model,
                status=CandidateStatus.PENDING,
                generation_time=generation_time,
                metadata={
                    "prompt_type": "multi_model",
                    "router_strategy": self.strategy.value,
                },
            )

        except Exception as e:
            generation_time = time.time() - start_time
            logger.error(f"Model {model} generation failed: {e}")

            return CodeCandidate(
                id=candidate_id,
                code="",
                model=model,
                status=CandidateStatus.FAILED,
                generation_time=generation_time,
                error_message=str(e),
            )

    def _build_messages(self, prompt: GenerationPrompt) -> list[dict[str, Any]]:
        """Build messages for the LLM.

        Args:
            prompt: The generation prompt.

        Returns:
            List of message dictionaries.
        """
        system_message = """You are an expert software developer.
Generate code based on the provided specification.
The code should be correct, efficient, and well-documented."""

        user_message = f"""Task: {prompt.task_description}

Specification:
{prompt.spec}

"""

        if prompt.context:
            user_message += "Additional Context:\n"
            for key, value in prompt.context.items():
                user_message += f"- {key}: {value}\n"

        user_message += "\nPlease generate the complete implementation code."

        return [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ]

    def set_strategy(self, strategy: RoutingStrategy) -> None:
        """Set the routing strategy.

        Args:
            strategy: The strategy to use.
        """
        self.strategy = strategy
        logger.info(f"Routing strategy set to: {strategy.value}")

    @property
    def generation_count(self) -> int:
        """Get the number of generation rounds.

        Returns:
            Number of generation rounds.
        """
        return self._generation_count


def create_multi_model_router(
    config: CodeGenConfig | None = None,
) -> MultiModelRouter:
    """Factory function to create a MultiModelRouter.

    Args:
        config: Optional configuration. Uses default if not provided.

    Returns:
        MultiModelRouter instance.
    """
    if config is None:
        config = CodeGenConfig()
    return MultiModelRouter(config)
