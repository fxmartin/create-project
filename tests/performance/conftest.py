# ABOUTME: Performance testing configuration and fixtures
# ABOUTME: Provides common benchmarking utilities and test data

"""Performance testing fixtures and configuration."""

import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Callable, Dict

import pytest
from pytest_benchmark.fixture import BenchmarkFixture  # type: ignore

from create_project.config.config_manager import ConfigManager
from create_project.core.directory_creator import DirectoryCreator
from create_project.core.file_renderer import FileRenderer
from create_project.core.path_utils import PathHandler
from create_project.core.project_generator import ProjectGenerator
from create_project.templates.engine import TemplateEngine
from create_project.templates.loader import TemplateLoader


@pytest.fixture
def temp_dir() -> Iterator[Path]:
    """Provide a temporary directory for performance tests."""
    temp_path = tempfile.mkdtemp(prefix="perf_test_")
    yield Path(temp_path)
    shutil.rmtree(temp_path)


@pytest.fixture
def large_template_structure() -> Dict[str, Any]:
    """Create a large template structure for stress testing."""
    structure = {
        "src": {
            "__init__.py": "",
            "main.py": "# Main application",
            "config.py": "# Configuration",
            "utils": {
                "__init__.py": "",
                "helpers.py": "# Helper functions",
                "validators.py": "# Validators",
                "formatters.py": "# Formatters",
            },
            "models": {
                "__init__.py": "",
            },
            "views": {
                "__init__.py": "",
            },
            "controllers": {
                "__init__.py": "",
            },
        },
        "tests": {
            "__init__.py": "",
            "conftest.py": "# Test configuration",
            "unit": {
                "__init__.py": "",
            },
            "integration": {
                "__init__.py": "",
            },
        },
        "docs": {
            "README.md": "# Documentation",
            "api": {},
            "guides": {},
        },
        "scripts": {},
        ".gitignore": "*.pyc\\n__pycache__/",
        "pyproject.toml": "[project]\\nname = 'test'",
        "README.md": "# Test Project",
        "LICENSE": "MIT License",
    }

    # Flatten nested model/view/controller definitions
    for category in ["models", "views", "controllers"]:
        category_dict = {}
        category_dict["__init__.py"] = ""
        for i in range(10):
            category_dict[f"{category[:-1]}_{i}.py"] = f"# {category[:-1].title()} {i}"
        structure["src"][category] = category_dict

    # Flatten test definitions
    unit_dict = {"__init__.py": ""}
    for i in range(10):
        unit_dict[f"test_model_{i}.py"] = f"# Test model {i}"
    structure["tests"]["unit"] = unit_dict

    integration_dict = {"__init__.py": ""}
    for i in range(5):
        integration_dict[f"test_integration_{i}.py"] = f"# Integration test {i}"
    structure["tests"]["integration"] = integration_dict

    # Flatten docs definitions
    api_dict = {}
    for i in range(5):
        api_dict[f"api_{i}.md"] = f"# API doc {i}"
    structure["docs"]["api"] = api_dict

    guides_dict = {}
    for i in range(5):
        guides_dict[f"guide_{i}.md"] = f"# Guide {i}"
    structure["docs"]["guides"] = guides_dict

    # Flatten scripts
    scripts_dict = {}
    for i in range(5):
        scripts_dict[f"script_{i}.py"] = f"# Script {i}"
    structure["scripts"] = scripts_dict

    return structure


@pytest.fixture
def sample_template_variables() -> Dict[str, Any]:
    """Provide sample template variables for rendering."""
    return {
        "project_name": "test_project",
        "author": "Test Author",
        "email": "test@example.com",
        "description": "A test project for performance benchmarking",
        "version": "0.1.0",
        "python_version": "3.9",
        "license": "MIT",
        "github_username": "testuser",
        "current_year": "2025",
    }


@pytest.fixture
def path_handler() -> PathHandler:
    """Create a PathHandler instance."""
    return PathHandler()


@pytest.fixture
def directory_creator(path_handler: PathHandler) -> DirectoryCreator:
    """Create a DirectoryCreator instance."""
    return DirectoryCreator(path_handler)


@pytest.fixture
def file_renderer(path_handler: PathHandler) -> FileRenderer:
    """Create a FileRenderer instance."""
    return FileRenderer(path_handler)


@pytest.fixture
def config_manager(temp_dir: Path) -> ConfigManager:
    """Create a ConfigManager instance with test configuration."""
    config_path = temp_dir / "config"
    config_path.mkdir(exist_ok=True)
    return ConfigManager(config_path=config_path)


@pytest.fixture
def template_engine(config_manager: ConfigManager) -> TemplateEngine:
    """Create a TemplateEngine instance."""
    return TemplateEngine(config_manager)


@pytest.fixture
def template_loader(config_manager: ConfigManager) -> TemplateLoader:
    """Create a TemplateLoader instance."""
    return TemplateLoader(config_manager)


@pytest.fixture
def project_generator(
    config_manager: ConfigManager,
    template_engine: TemplateEngine,
) -> ProjectGenerator:
    """Create a ProjectGenerator instance."""
    return ProjectGenerator(config_manager, template_engine)


@pytest.fixture
def memory_snapshot() -> Callable[[], Dict[str, float]]:
    """Provide a function to capture memory usage snapshot."""
    import gc

    import psutil

    def snapshot() -> Dict[str, float]:
        gc.collect()
        process = psutil.Process()
        memory_info = process.memory_info()
        return {
            "rss_mb": memory_info.rss / 1024 / 1024,
            "vms_mb": memory_info.vms / 1024 / 1024,
            "percent": process.memory_percent(),
        }

    return snapshot


@pytest.fixture
def benchmark_config(benchmark: BenchmarkFixture) -> None:
    """Configure benchmark settings."""
    benchmark.pedantic = True
    benchmark.warmup = True
    benchmark.disable_gc = True
    benchmark.stats.rounds = 5
    benchmark.stats.iterations = 10


# Performance test markers
pytest.mark.benchmark = pytest.mark.benchmark
pytest.mark.memory = pytest.mark.memory
pytest.mark.stress = pytest.mark.stress
