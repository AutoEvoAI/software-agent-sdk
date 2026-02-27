"""Tests for decomposer module."""

from openhands.sdk.agent.planner.decomposer import (
    DecompositionStrategy,
    TaskDecomposer,
    TaskTemplate,
    TaskType,
    create_decomposer,
)


class TestTaskType:
    """Tests for TaskType enum."""

    def test_task_type_values(self):
        """Test TaskType enum values."""
        assert TaskType.ANALYSIS.value == "analysis"
        assert TaskType.DESIGN.value == "design"
        assert TaskType.IMPLEMENTATION.value == "implementation"
        assert TaskType.TESTING.value == "testing"
        assert TaskType.VERIFICATION.value == "verification"


class TestDecompositionStrategy:
    """Tests for DecompositionStrategy enum."""

    def test_decomposition_strategy_values(self):
        """Test DecompositionStrategy values."""
        assert DecompositionStrategy.SEQUENTIAL.value == "sequential"
        assert DecompositionStrategy.PARALLEL.value == "parallel"
        assert DecompositionStrategy.HYBRID.value == "hybrid"


class TestTaskTemplate:
    """Tests for TaskTemplate dataclass."""

    def test_create_task_template(self):
        """Test creating a TaskTemplate."""
        template = TaskTemplate(
            name="test_task",
            description="Test task description",
            task_type=TaskType.IMPLEMENTATION,
            required_capabilities=["coding"],
            priority=5,
        )

        assert template.name == "test_task"
        assert template.task_type == TaskType.IMPLEMENTATION
        assert template.priority == 5


class TestTaskDecomposer:
    """Tests for TaskDecomposer class."""

    def test_create_decomposer(self):
        """Test creating a TaskDecomposer."""
        decomposer = TaskDecomposer()
        assert decomposer is not None
        assert decomposer.strategy == DecompositionStrategy.HYBRID

    def test_decompose_spec(self):
        """Test decomposing a specification."""
        decomposer = TaskDecomposer()

        tasks = decomposer.decompose(
            spec_name="TestSpec",
            spec_content="Test content",
        )

        assert len(tasks) > 0
        assert any(t.name == "analyze_requirements" for t in tasks)
        assert any(t.name == "generate_spec" for t in tasks)
        assert any(t.name == "generate_code" for t in tasks)

    def test_decompose_with_domain(self):
        """Test decomposing with domain."""
        decomposer = TaskDecomposer()

        tasks = decomposer.decompose(
            spec_name="TestSpec",
            spec_content="Test content",
            domain="api",
        )

        task_names = [t.name for t in tasks]
        assert "analyze_requirements" in task_names
        assert "design_api_schema" in task_names

    def test_task_dependencies(self):
        """Test task dependencies are resolved."""
        decomposer = TaskDecomposer()

        tasks = decomposer.decompose(
            spec_name="TestSpec",
            spec_content="Test content",
        )

        generate_spec_task = next(t for t in tasks if t.name == "generate_spec")
        assert "analyze_requirements" in generate_spec_task.dependencies

    def test_task_priorities(self):
        """Test task priorities are set."""
        decomposer = TaskDecomposer()

        tasks = decomposer.decompose(
            spec_name="TestSpec",
            spec_content="Test content",
        )

        analyze_task = next(t for t in tasks if t.name == "analyze_requirements")
        generate_task = next(t for t in tasks if t.name == "generate_code")

        assert analyze_task.priority > generate_task.priority

    def test_sequential_strategy(self):
        """Test sequential decomposition strategy."""
        decomposer = TaskDecomposer(strategy=DecompositionStrategy.SEQUENTIAL)

        tasks = decomposer.decompose(
            spec_name="TestSpec",
            spec_content="Test content",
        )

        priorities = [t.priority for t in tasks]
        assert priorities == sorted(priorities, reverse=True)

    def test_parallel_strategy(self):
        """Test parallel decomposition strategy."""
        decomposer = TaskDecomposer(strategy=DecompositionStrategy.PARALLEL)

        tasks = decomposer.decompose(
            spec_name="TestSpec",
            spec_content="Test content",
        )

        assert len(tasks) > 0

    def test_add_template(self):
        """Test adding custom template."""
        decomposer = TaskDecomposer()

        template = TaskTemplate(
            name="custom_task",
            description="Custom task",
            task_type=TaskType.IMPLEMENTATION,
            required_capabilities=["custom"],
        )

        decomposer.add_template("custom", template)

        tasks = decomposer.decompose(
            spec_name="TestSpec",
            spec_content="Test",
            domain="custom",
        )

        assert any(t.name == "custom_task" for t in tasks)

    def test_get_template(self):
        """Test getting a template."""
        decomposer = TaskDecomposer()

        template = decomposer.get_template("api", "design_api_schema")
        assert template is not None
        assert template.name == "design_api_schema"

    def test_get_template_not_found(self):
        """Test getting non-existent template."""
        decomposer = TaskDecomposer()

        template = decomposer.get_template("nonexistent", "task")
        assert template is None


class TestFactory:
    """Tests for factory functions."""

    def test_create_decomposer(self):
        """Test create_decomposer factory."""
        decomposer = create_decomposer()
        assert isinstance(decomposer, TaskDecomposer)

    def test_create_decomposer_with_strategy(self):
        """Test create_decomposer with strategy."""
        decomposer = create_decomposer(strategy=DecompositionStrategy.SEQUENTIAL)
        assert decomposer.strategy == DecompositionStrategy.SEQUENTIAL
