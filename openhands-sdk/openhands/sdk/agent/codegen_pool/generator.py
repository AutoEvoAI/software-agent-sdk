"""Single model code generator (default)."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any

from openhands.sdk.logger import get_logger

from .candidate import CandidateStatus, CodeCandidate
from .config import CodeGenConfig


logger = get_logger(__name__)


@dataclass
class GenerationPrompt:
    """Prompt for code generation.

    Attributes:
        spec: The formal specification to generate code from.
        task_description: Description of the task.
        context: Additional context for generation.
    """

    spec: str
    task_description: str
    context: dict[str, Any] | None = None


class SingleModelGenerator:
    """Single model code generator (default mode).

    This generator uses a single LLM model to generate code candidates
    based on the provided specification. This is the default mode
    when enable_multi_model is False.
    """

    def __init__(self, config: CodeGenConfig):
        """Initialize the single model generator.

        Args:
            config: Configuration for code generation.
        """
        self.config = config
        self._generate_count = 0

    async def generate(
        self,
        prompt: GenerationPrompt,
        llm: Any,
    ) -> CodeCandidate:
        """Generate code using a single model.

        Args:
            prompt: The generation prompt containing spec and context.
            llm: The LLM instance to use for generation.

        Returns:
            CodeCandidate with generated code.
        """
        candidate_id = str(uuid.uuid4())
        start_time = time.time()

        logger.info(f"Generating code with model: {self.config.default_model}")

        try:
            messages = self._build_messages(prompt)

            response = await llm.achat(
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

            code = response.content if hasattr(response, "content") else str(response)

            generation_time = time.time() - start_time

            candidate = CodeCandidate(
                id=candidate_id,
                code=code,
                model=self.config.default_model,
                status=CandidateStatus.PENDING,
                generation_time=generation_time,
                metadata={"prompt_type": "single_model"},
            )

            self._generate_count += 1
            logger.info(f"Code generation completed in {generation_time:.2f}s")

            return candidate

        except Exception as e:
            generation_time = time.time() - start_time
            logger.error(f"Code generation failed: {e}")

            return CodeCandidate(
                id=candidate_id,
                code="",
                model=self.config.default_model,
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

    @property
    def generation_count(self) -> int:
        """Get the number of generations performed.

        Returns:
            Number of generations.
        """
        return self._generate_count

    def reset_count(self) -> None:
        """Reset the generation counter."""
        self._generate_count = 0


def create_single_model_generator(
    config: CodeGenConfig | None = None,
) -> SingleModelGenerator:
    """Factory function to create a SingleModelGenerator.

    Args:
        config: Optional configuration. Uses default if not provided.

    Returns:
        SingleModelGenerator instance.
    """
    if config is None:
        config = CodeGenConfig()
    return SingleModelGenerator(config)
