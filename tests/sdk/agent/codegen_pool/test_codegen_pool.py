"""Tests for CodeGenAgentPool."""

import pytest

from openhands.sdk.agent.codegen_pool import (
    CodeGenAgentPool,
    create_codegen_pool,
)
from openhands.sdk.agent.codegen_pool.candidate import CandidateStatus
from openhands.sdk.agent.codegen_pool.config import CodeGenConfig


class MockLLM:
    """Mock LLM for testing."""

    async def achat(self, messages):
        class Response:
            content = "def foo():\n    return 42"

        return Response()


class TestCodeGenAgentPool:
    """Tests for CodeGenAgentPool."""

    def test_init_single_model(self):
        """Test initialization in single-model mode."""
        pool = CodeGenAgentPool()

        assert pool.is_multi_model is False
        assert pool.model_count == 1
        assert pool.candidate_count == 0

    def test_init_multi_model(self):
        """Test initialization in multi-model mode."""
        config = CodeGenConfig(
            enable_multi_model=True,
            model_candidates=["gpt-4", "claude-sonnet"],
        )
        pool = CodeGenAgentPool(config=config)

        assert pool.is_multi_model is True
        assert pool.model_count == 2
        assert pool.candidate_count == 0

    @pytest.mark.asyncio
    async def test_generate_single_model(self):
        """Test code generation in single-model mode."""
        pool = CodeGenAgentPool()
        llm = MockLLM()

        candidates = await pool.generate(
            spec="def foo(): return 42",
            task_description="Create a function foo",
            llm=llm,
        )

        assert len(candidates) == 1
        assert pool.candidate_count == 1

    @pytest.mark.asyncio
    async def test_generate_with_retry(self):
        """Test generation with retry logic."""
        config = CodeGenConfig(max_retries=2)
        pool = CodeGenAgentPool(config=config)
        llm = MockLLM()

        candidates = await pool.generate_with_retry(
            spec="def foo(): return 42",
            task_description="Create a function foo",
            llm=llm,
        )

        assert len(candidates) >= 1

    @pytest.mark.asyncio
    async def test_get_candidates(self):
        """Test getting candidates."""
        pool = CodeGenAgentPool()
        llm = MockLLM()

        await pool.generate(
            spec="def foo(): return 42",
            task_description="Create a function foo",
            llm=llm,
        )

        all_candidates = pool.get_candidates()
        assert len(all_candidates) == 1

    @pytest.mark.asyncio
    async def test_get_candidates_by_status(self):
        """Test filtering candidates by status."""
        pool = CodeGenAgentPool()
        llm = MockLLM()

        await pool.generate(
            spec="def foo(): return 42",
            task_description="Create a function foo",
            llm=llm,
        )

        candidates = pool.get_candidates(status=CandidateStatus.PENDING)
        assert len(candidates) >= 0

    def test_clear_candidates(self):
        """Test clearing candidates."""
        from openhands.sdk.agent.codegen_pool.candidate import CodeCandidate

        pool = CodeGenAgentPool()
        pool._candidates.append(CodeCandidate(id="test", code="test", model="test"))
        assert pool.candidate_count == 1

        pool.clear_candidates()
        assert pool.candidate_count == 0

    def test_get_best_candidate_empty(self):
        """Test getting best candidate when none exist."""
        pool = CodeGenAgentPool()

        best = pool.get_best_candidate()
        assert best is None

    def test_create_codegen_pool_factory(self):
        """Test factory function."""
        pool = create_codegen_pool(
            enable_multi_model=False,
            model_candidates=["test-model"],
        )

        assert pool.is_multi_model is False
        assert pool.config.default_model == "test-model"


class TestCodeGenAgentPoolWithConfig:
    """Tests with custom configuration."""

    def test_custom_max_retries(self):
        """Test custom max retries."""
        config = CodeGenConfig(max_retries=5)
        pool = CodeGenAgentPool(config=config)

        assert pool.config.max_retries == 5

    def test_custom_timeout(self):
        """Test custom timeout."""
        config = CodeGenConfig(timeout=600)
        pool = CodeGenAgentPool(config=config)

        assert pool.config.timeout == 600
