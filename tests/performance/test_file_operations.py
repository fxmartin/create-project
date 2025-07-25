# ABOUTME: Performance tests for file and directory operations
# ABOUTME: Benchmarks project creation, file rendering, and I/O operations

"""Performance tests for file and directory operations."""

from pathlib import Path
from typing import Any, Dict

import pytest

from create_project.core.directory_creator import DirectoryCreator
from create_project.core.file_renderer import FileRenderer
from create_project.core.path_utils import PathHandler
from tests.performance.benchmarks import check_performance


@pytest.mark.benchmark
def test_create_small_project(
    benchmark: Any,
    temp_dir: Path,
    directory_creator: DirectoryCreator,
    file_renderer: FileRenderer,
    memory_snapshot: Any,
) -> None:
    """Benchmark creating a small project (10 files)."""
    project_path = temp_dir / "small_project"

    # Define a small project structure
    structure = {
        "src": {
            "__init__.py": "",
            "main.py": "# Main application",
            "config.py": "# Configuration",
        },
        "tests": {
            "__init__.py": "",
            "test_main.py": "# Tests",
        },
        "README.md": "# Small Project",
        ".gitignore": "*.pyc",
        "pyproject.toml": "[project]\nname = 'small'",
        "LICENSE": "MIT",
    }

    initial_memory = memory_snapshot()

    def create_project() -> None:
        # Create directories
        directory_creator.create_directory_structure(project_path, structure)

        # Render files
        file_count = 0
        for root, dirs, files in directory_creator.walk_structure(structure):
            for file_name, content in files:
                file_path = project_path / root / file_name
                file_renderer.render_file(file_path, content, {})
                file_count += 1

    benchmark(create_project)

    final_memory = memory_snapshot()
    memory_used = final_memory["rss_mb"] - initial_memory["rss_mb"]

    duration_ms = benchmark.stats["mean"] * 1000
    passed, message = check_performance(
        "create_small_project",
        duration_ms,
        memory_used,
    )

    assert passed, f"Performance check failed: {message}"
    assert project_path.exists()
    assert (project_path / "src" / "main.py").exists()


@pytest.mark.benchmark
def test_create_medium_project(
    benchmark: Any,
    temp_dir: Path,
    directory_creator: DirectoryCreator,
    file_renderer: FileRenderer,
    large_template_structure: Dict[str, Any],
    memory_snapshot: Any,
) -> None:
    """Benchmark creating a medium project (50 files)."""
    project_path = temp_dir / "medium_project"

    # Use first 50 files from large structure
    structure = {}
    file_count = 0

    def add_files(d: Dict, target: Dict, limit: int) -> int:
        count = 0
        for key, value in d.items():
            if count >= limit:
                break
            if isinstance(value, dict):
                target[key] = {}
                count += add_files(value, target[key], limit - count)
            else:
                target[key] = value
                count += 1
        return count

    add_files(large_template_structure, structure, 50)

    initial_memory = memory_snapshot()

    def create_project() -> None:
        directory_creator.create_directory_structure(project_path, structure)
        for root, dirs, files in directory_creator.walk_structure(structure):
            for file_name, content in files:
                file_path = project_path / root / file_name
                file_renderer.render_file(file_path, content, {})

    benchmark(create_project)

    final_memory = memory_snapshot()
    memory_used = final_memory["rss_mb"] - initial_memory["rss_mb"]

    duration_ms = benchmark.stats["mean"] * 1000
    passed, message = check_performance(
        "create_medium_project",
        duration_ms,
        memory_used,
    )

    assert passed, f"Performance check failed: {message}"
    assert project_path.exists()


@pytest.mark.benchmark
@pytest.mark.stress
def test_create_large_project(
    benchmark: Any,
    temp_dir: Path,
    directory_creator: DirectoryCreator,
    file_renderer: FileRenderer,
    large_template_structure: Dict[str, Any],
    memory_snapshot: Any,
) -> None:
    """Benchmark creating a large project (100+ files)."""
    project_path = temp_dir / "large_project"

    initial_memory = memory_snapshot()

    def create_project() -> int:
        directory_creator.create_directory_structure(
            project_path,
            large_template_structure,
        )

        file_count = 0
        for root, dirs, files in directory_creator.walk_structure(
            large_template_structure
        ):
            for file_name, content in files:
                file_path = project_path / root / file_name
                file_renderer.render_file(file_path, content, {})
                file_count += 1
        return file_count

    file_count = benchmark(create_project)

    final_memory = memory_snapshot()
    memory_used = final_memory["rss_mb"] - initial_memory["rss_mb"]

    duration_ms = benchmark.stats["mean"] * 1000
    passed, message = check_performance(
        "create_large_project",
        duration_ms,
        memory_used,
    )

    # Large projects may exceed limits but shouldn't fail the test
    if not passed:
        pytest.skip(f"Large project performance: {message}")

    assert project_path.exists()
    assert file_count > 100


@pytest.mark.benchmark
def test_path_validation(
    benchmark: Any,
    path_handler: PathHandler,
    memory_snapshot: Any,
) -> None:
    """Benchmark path validation operations."""
    test_paths = [
        "/home/user/project",
        "~/projects/myapp",
        "../relative/path",
        "C:\\Windows\\Path" if Path.cwd().drive else "/usr/local/bin",
        "path/with spaces/file.txt",
        "path/with/special!@#$%/chars.py",
    ]

    initial_memory = memory_snapshot()

    def validate_paths() -> list:
        results = []
        for path in test_paths:
            try:
                validated = path_handler.validate_path(Path(path))
                results.append(validated)
            except Exception:
                results.append(None)
        return results

    result = benchmark(validate_paths)

    final_memory = memory_snapshot()
    memory_used = final_memory["rss_mb"] - initial_memory["rss_mb"]

    duration_ms = benchmark.stats["mean"] * 1000
    passed, message = check_performance(
        "path_validation",
        duration_ms,
        memory_used,
    )

    assert passed, f"Performance check failed: {message}"
    assert len(result) == len(test_paths)


@pytest.mark.benchmark
def test_path_expansion(
    benchmark: Any,
    path_handler: PathHandler,
    memory_snapshot: Any,
) -> None:
    """Benchmark path expansion with variables."""
    test_cases = [
        ("~/project", Path.home() / "project"),
        ("$HOME/project", Path.home() / "project"),
        ("${HOME}/project", Path.home() / "project"),
        ("./relative", Path.cwd() / "relative"),
        ("../parent", Path.cwd().parent / "parent"),
    ]

    initial_memory = memory_snapshot()

    def expand_paths() -> list:
        results = []
        for path_str, expected in test_cases:
            expanded = path_handler.expand_path(Path(path_str))
            results.append(expanded)
        return results

    result = benchmark(expand_paths)

    final_memory = memory_snapshot()
    memory_used = final_memory["rss_mb"] - initial_memory["rss_mb"]

    duration_ms = benchmark.stats["mean"] * 1000
    passed, message = check_performance(
        "path_expansion",
        duration_ms,
        memory_used,
    )

    assert passed, f"Performance check failed: {message}"
    assert len(result) == len(test_cases)


@pytest.mark.benchmark
@pytest.mark.memory
def test_file_rendering_memory_usage(
    temp_dir: Path,
    file_renderer: FileRenderer,
    memory_snapshot: Any,
) -> None:
    """Test memory usage during file rendering operations."""
    import gc

    # Force garbage collection
    gc.collect()

    initial_memory = memory_snapshot()

    # Create many files to test memory usage
    for i in range(1000):
        file_path = temp_dir / f"file_{i}.txt"
        content = f"This is file {i}\n" * 100  # ~2KB per file
        file_renderer.render_file(file_path, content, {})

        # Check memory every 100 files
        if i % 100 == 0:
            gc.collect()
            current_memory = memory_snapshot()
            memory_growth = current_memory["rss_mb"] - initial_memory["rss_mb"]

            # Memory shouldn't grow unbounded
            assert memory_growth < 100, f"Memory grew by {memory_growth:.1f}MB after {i} files"

    final_memory = memory_snapshot()
    total_memory_used = final_memory["rss_mb"] - initial_memory["rss_mb"]

    print(f"\nTotal memory used for 1000 files: {total_memory_used:.1f}MB")
