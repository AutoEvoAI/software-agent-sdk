"""Tests for dependency_analyzer module."""

from openhands.sdk.agent.planner.dependency_analyzer import (
    Dependency,
    DependencyAnalyzer,
    DependencyStrength,
    DependencyType,
    create_dependency_analyzer,
)


class TestDependencyType:
    """Tests for DependencyType enum."""

    def test_dependency_type_values(self):
        """Test DependencyType enum values."""
        assert DependencyType.REQUIRED.value == "required"
        assert DependencyType.OPTIONAL.value == "optional"
        assert DependencyType.SOFT.value == "soft"
        assert DependencyType.IMPLIED.value == "implied"


class TestDependencyStrength:
    """Tests for DependencyStrength enum."""

    def test_dependency_strength_values(self):
        """Test DependencyStrength values."""
        assert DependencyStrength.STRONG.value == "strong"
        assert DependencyStrength.MEDIUM.value == "medium"
        assert DependencyStrength.WEAK.value == "weak"


class TestDependency:
    """Tests for Dependency dataclass."""

    def test_create_dependency(self):
        """Test creating a Dependency."""
        dep = Dependency(
            source="task1",
            target="task2",
            dependency_type=DependencyType.REQUIRED,
            strength=DependencyStrength.STRONG,
        )

        assert dep.source == "task1"
        assert dep.target == "task2"
        assert dep.dependency_type == DependencyType.REQUIRED


class TestDependencyAnalyzer:
    """Tests for DependencyAnalyzer class."""

    def test_create_dependency_analyzer(self):
        """Test creating a DependencyAnalyzer."""
        analyzer = DependencyAnalyzer()
        assert analyzer is not None

    def test_analyze_simple_tasks(self):
        """Test analyzing simple task dependencies."""
        analyzer = DependencyAnalyzer()

        tasks = {
            "task1": {"dependencies": []},
            "task2": {"dependencies": ["task1"]},
            "task3": {"dependencies": ["task2"]},
        }

        analysis = analyzer.analyze(tasks)

        assert len(analysis.dependencies) == 2
        assert "task1" in analysis.critical_path

    def test_analyze_parallel_tasks(self):
        """Test analyzing parallel tasks."""
        analyzer = DependencyAnalyzer()

        tasks = {
            "task1": {"dependencies": []},
            "task2": {"dependencies": []},
            "task3": {"dependencies": ["task1", "task2"]},
        }

        analysis = analyzer.analyze(tasks)

        assert len(analysis.parallelizable_groups) >= 2

    def test_analyze_with_circular_dependency(self):
        """Test detecting circular dependencies."""
        analyzer = DependencyAnalyzer()

        tasks = {
            "task1": {"dependencies": ["task3"]},
            "task2": {"dependencies": ["task1"]},
            "task3": {"dependencies": ["task2"]},
        }

        analysis = analyzer.analyze(tasks)

        assert len(analysis.circular_refs) > 0

    def test_analyze_with_resources(self):
        """Test finding implied dependencies via resources."""
        analyzer = DependencyAnalyzer()

        tasks = {
            "task1": {"dependencies": [], "resources": ["database"]},
            "task2": {"dependencies": [], "resources": ["database"]},
            "task3": {"dependencies": ["task1"], "resources": []},
        }

        analysis = analyzer.analyze(tasks)

        assert len(analysis.implied_dependencies) > 0

    def test_find_critical_path(self):
        """Test finding critical path."""
        analyzer = DependencyAnalyzer()

        tasks = {
            "task1": {"dependencies": [], "duration": 3},
            "task2": {"dependencies": ["task1"], "duration": 2},
            "task3": {"dependencies": ["task1"], "duration": 4},
            "task4": {"dependencies": ["task2", "task3"], "duration": 1},
        }

        analysis = analyzer.analyze(tasks)

        assert len(analysis.critical_path) > 0

    def test_find_parallelizable_groups(self):
        """Test finding parallelizable groups."""
        analyzer = DependencyAnalyzer()

        tasks = {
            "task1": {"dependencies": []},
            "task2": {"dependencies": []},
            "task3": {"dependencies": ["task1", "task2"]},
        }

        analysis = analyzer.analyze(tasks)

        assert len(analysis.parallelizable_groups) >= 2

    def test_add_dependency(self):
        """Test adding explicit dependency."""
        analyzer = DependencyAnalyzer()
        analyzer.add_dependency(
            "task1",
            "task2",
            dependency_type=DependencyType.REQUIRED,
            strength=DependencyStrength.STRONG,
        )

        tasks = {"task1": {"dependencies": []}, "task2": {"dependencies": []}}
        analysis = analyzer.analyze(tasks)

        assert len(analysis.dependencies) == 1
        assert analysis.dependencies[0].source == "task1"
        assert analysis.dependencies[0].target == "task2"


class TestFactory:
    """Tests for factory functions."""

    def test_create_dependency_analyzer(self):
        """Test create_dependency_analyzer factory."""
        analyzer = create_dependency_analyzer()
        assert isinstance(analyzer, DependencyAnalyzer)
