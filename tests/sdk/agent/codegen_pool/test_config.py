"""Tests for CodeGenConfig."""

from openhands.sdk.agent.codegen_pool.config import CodeGenConfig, create_codegen_config


class TestCodeGenConfig:
    """Tests for CodeGenConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = CodeGenConfig()

        assert config.enable_multi_model is False
        assert config.default_model == "claude-sonnet-4-20250514"
        assert config.temperature == 0.7
        assert config.max_tokens == 4096
        assert config.timeout == 300
        assert config.enable_verification is False
        assert config.max_retries == 3

    def test_model_candidates_default(self):
        """Test default model candidates."""
        config = CodeGenConfig()

        assert config.model_candidates == ["claude-sonnet-4-20250514"]

    def test_custom_config(self):
        """Test custom configuration."""
        config = CodeGenConfig(
            enable_multi_model=True,
            model_candidates=["gpt-4", "claude-sonnet"],
            temperature=0.5,
            max_tokens=2048,
        )

        assert config.enable_multi_model is True
        assert config.model_candidates == ["gpt-4", "claude-sonnet"]
        assert config.temperature == 0.5
        assert config.max_tokens == 2048

    def test_create_codegen_config(self):
        """Test factory function."""
        config = create_codegen_config(
            enable_multi_model=True,
            model_candidates=["model1", "model2"],
        )

        assert config.enable_multi_model is True
        assert config.model_candidates == ["model1", "model2"]


class TestCandidateStatus:
    """Tests for CandidateStatus enum."""

    def test_status_values(self):
        """Test enum values."""
        from openhands.sdk.agent.codegen_pool.candidate import CandidateStatus

        assert CandidateStatus.PENDING.value == "pending"
        assert CandidateStatus.GENERATING.value == "generating"
        assert CandidateStatus.VERIFIED.value == "verified"
        assert CandidateStatus.FAILED.value == "failed"
        assert CandidateStatus.REJECTED.value == "rejected"
        assert CandidateStatus.ACCEPTED.value == "accepted"
