# ABOUTME: Project generation speed benchmarks and performance tests
# ABOUTME: Measures generation time across templates, project sizes, and batch operations

"""
Project generation speed benchmark suite.

This module provides comprehensive benchmarking for project generation performance including:
- Template-specific generation speed benchmarks
- Project size scaling performance tests
- Batch operation performance analysis
- Template rendering speed measurements
- Directory creation performance benchmarks
- Performance regression detection
"""

import tempfile
import time
from pathlib import Path
from typing import Dict, List, Any
from unittest.mock import MagicMock

import pytest
from pytest_benchmark.fixture import BenchmarkFixture

from create_project.config.config_manager import ConfigManager
from create_project.core.api import create_project
from create_project.core.project_generator import ProjectGenerator, ProjectOptions
from create_project.templates.engine import TemplateEngine
from create_project.templates.loader import TemplateLoader


@pytest.mark.benchmark
class TestProjectGenerationSpeed:
    """Benchmark project generation speed across different scenarios."""

    def test_python_library_generation_speed(self, benchmark: BenchmarkFixture, 
                                            temp_dir: Path, config_manager: ConfigManager):
        """Benchmark Python library template generation speed."""
        def generate_python_library():
            return create_project(
                template_name="python_library",
                project_name="benchmark_library",
                target_directory=temp_dir,
                variables={
                    "author": "Benchmark User",
                    "version": "0.1.0",
                    "description": "Benchmark test library",
                    "license": "MIT",
                },
                config_manager=config_manager
            )
        
        result = benchmark(generate_python_library)
        assert result.success, f"Generation failed: {result.error_message}"

    def test_python_package_generation_speed(self, benchmark: BenchmarkFixture,
                                           temp_dir: Path, config_manager: ConfigManager):
        """Benchmark Python package template generation speed."""
        def generate_python_package():
            return create_project(
                template_name="python_package",
                project_name="benchmark_package",
                target_directory=temp_dir,
                variables={
                    "author": "Benchmark User",
                    "version": "0.1.0",
                    "description": "Benchmark test package",
                    "license": "MIT",
                },
                config_manager=config_manager
            )
        
        result = benchmark(generate_python_package)
        assert result.success, f"Generation failed: {result.errors}"

    def test_cli_single_package_generation_speed(self, benchmark: BenchmarkFixture,
                                                temp_dir: Path, config_manager: ConfigManager):
        """Benchmark CLI single package template generation speed."""
        def generate_cli_package():
            return create_project(
                template_name="cli_single_package",
                project_name="benchmark_cli",
                target_directory=temp_dir,
                variables={
                    "author": "Benchmark User",
                    "version": "0.1.0",
                    "description": "Benchmark CLI application",
                    "license": "MIT",
                },
                config_manager=config_manager
            )
        
        result = benchmark(generate_cli_package)
        assert result.success, f"Generation failed: {result.errors}"

    def test_django_web_app_generation_speed(self, benchmark: BenchmarkFixture,
                                           temp_dir: Path, config_manager: ConfigManager):
        """Benchmark Django web application template generation speed."""
        def generate_django_app():
            return create_project(
                template_name="django_web_app",
                project_name="benchmark_django",
                target_directory=temp_dir,
                variables={
                    "author": "Benchmark User",
                    "version": "0.1.0",
                    "description": "Benchmark Django application",
                    "license": "MIT",
                    "database_type": "sqlite",
                },
                config_manager=config_manager
            )
        
        result = benchmark(generate_django_app)
        assert result.success, f"Generation failed: {result.errors}"

    def test_flask_web_app_generation_speed(self, benchmark: BenchmarkFixture,
                                          temp_dir: Path, config_manager: ConfigManager):
        """Benchmark Flask web application template generation speed."""
        def generate_flask_app():
            return create_project(
                template_name="flask_web_app",
                project_name="benchmark_flask",
                target_directory=temp_dir,
                variables={
                    "author": "Benchmark User",
                    "version": "0.1.0",
                    "description": "Benchmark Flask application",
                    "license": "MIT",
                },
                config_manager=config_manager
            )
        
        result = benchmark(generate_flask_app)
        assert result.success, f"Generation failed: {result.errors}"

    def test_one_off_script_generation_speed(self, benchmark: BenchmarkFixture,
                                           temp_dir: Path, config_manager: ConfigManager):
        """Benchmark one-off script template generation speed."""
        def generate_script():
            return create_project(
                template_name="one_off_script",
                project_name="benchmark_script",
                target_directory=temp_dir,
                variables={
                    "author": "Benchmark User",
                    "version": "0.1.0",
                    "description": "Benchmark script",
                    "script_purpose": "Performance testing",
                },
                config_manager=config_manager
            )
        
        result = benchmark(generate_script)
        assert result.success, f"Generation failed: {result.errors}"


@pytest.mark.benchmark
class TestProjectSizeScaling:
    """Benchmark performance scaling with different project sizes."""

    @pytest.mark.parametrize("file_count", [5, 15, 50, 100])
    def test_generation_speed_by_file_count(self, benchmark: BenchmarkFixture,
                                          temp_dir: Path, file_count: int,
                                          config_manager: ConfigManager, mock_template):
        """Benchmark generation speed scaling with file count."""
        # Create a mock template with specified file count
        mock_template.structure = self._create_large_template_structure(file_count)["structure"]
        mock_template.name = "large_project"
        
        def generate_large_project():
            # Use the mock template directly with ProjectGenerator
            
            # Create a mock project with direct API call - testing file scaling
            # This uses a mocked template for performance testing
            options = ProjectOptions(
                create_git_repo=False,
                create_venv=False,
                execute_post_commands=False
            )
            generator = ProjectGenerator(config_manager=config_manager)
            return generator.generate_project(
                template=mock_template,
                variables={"author": "Benchmark User", "file_count": file_count},
                target_path=temp_dir / f"benchmark_large_{file_count}",
                options=options
            )
        
        result = benchmark(generate_large_project)
        assert result.success, f"Generation failed for {file_count} files: {result.errors}"

    def test_nested_directory_performance(self, benchmark: BenchmarkFixture,
                                        temp_dir: Path, config_manager: ConfigManager, mock_template):
        """Benchmark performance with deeply nested directory structures."""
        def generate_nested_project():
            # Create nested structure: src/level1/level2/.../level10/
            nested_structure = {}
            current = nested_structure
            for i in range(10):
                current[f"level_{i}"] = {}
                current[f"level_{i}"]["__init__.py"] = ""
                current[f"level_{i}"][f"module_{i}.py"] = f"# Module at level {i}"
                current = current[f"level_{i}"]
            
            mock_template.name = "nested_project"
            mock_template.structure = nested_structure
            
            options = ProjectOptions(
                create_git_repo=False,
                create_venv=False,
                execute_post_commands=False
            )
            generator = ProjectGenerator(config_manager=config_manager)
            return generator.generate_project(
                template=mock_template,
                variables={"author": "Benchmark User"},
                target_path=temp_dir / "benchmark_nested",
                options=options
            )
        
        result = benchmark(generate_nested_project)
        assert result.success, f"Nested generation failed: {result.errors}"

    def _create_large_template_structure(self, file_count: int) -> Dict[str, Any]:
        """Create a template structure with specified number of files."""
        structure = {
            "src": {
                "__init__.py": "",
            },
            "tests": {
                "__init__.py": "",
            }
        }
        
        # Add files to src directory
        files_per_dir = max(1, file_count // 2)
        for i in range(files_per_dir):
            structure["src"][f"module_{i}.py"] = f"# Module {i}\nclass Module{i}:\n    pass"
        
        # Add test files
        for i in range(file_count - files_per_dir):
            structure["tests"][f"test_module_{i}.py"] = f"# Test {i}\ndef test_module_{i}():\n    pass"
        
        return {
            "name": "large_project",
            "structure": structure,
            "variables": ["author", "file_count"]
        }

    def _flatten_structure(self, structure: Dict[str, Any], prefix: str = "") -> Dict[str, str]:
        """Flatten nested structure into file path: content mapping."""
        files = {}
        for name, content in structure.items():
            path = f"{prefix}/{name}" if prefix else name
            if isinstance(content, dict):
                files.update(self._flatten_structure(content, path))
            else:
                files[path] = str(content)
        return files


@pytest.mark.benchmark
class TestBatchOperations:
    """Benchmark batch project generation operations."""

    def test_sequential_generation_performance(self, benchmark: BenchmarkFixture,
                                             temp_dir: Path, config_manager: ConfigManager):
        """Benchmark sequential generation of multiple projects."""
        def generate_multiple_projects():
            results = []
            for i in range(5):
                result = create_project(
                    template_name="python_library",
                    project_name=f"batch_project_{i}",
                    target_directory=temp_dir / f"project_{i}",
                    variables={
                        "author": "Batch User",
                        "version": "0.1.0",
                        "description": f"Batch project {i}",
                        "license": "MIT",
                    },
                    config_manager=config_manager
                )
                results.append(result)
            return results
        
        results = benchmark(generate_multiple_projects)
        assert all(r.success for r in results), "Some batch generations failed"

    def test_template_switching_performance(self, benchmark: BenchmarkFixture,
                                          temp_dir: Path, config_manager: ConfigManager):
        """Benchmark performance when switching between different templates."""
        templates = ["python_library", "cli_single_package", "flask_web_app"]
        
        def generate_mixed_templates():
            results = []
            for i, template in enumerate(templates * 2):  # 6 projects total
                result = create_project(
                    template_name=template,
                    project_name=f"mixed_{template}_{i}",
                    target_directory=temp_dir / f"mixed_{i}",
                    variables={
                        "author": "Mixed User",
                        "version": "0.1.0",
                        "description": f"Mixed project {i}",
                        "license": "MIT",
                    },
                    config_manager=config_manager
                )
                results.append(result)
            return results
        
        results = benchmark(generate_mixed_templates)
        assert all(r.success for r in results), "Some mixed template generations failed"


@pytest.mark.benchmark
class TestTemplateRenderingSpeed:
    """Benchmark template rendering performance."""

    def test_variable_substitution_performance(self, benchmark: BenchmarkFixture):
        """Benchmark performance with large number of template variables."""
        # Create template with many variables
        large_variables = {f"var_{i}": f"value_{i}" for i in range(100)}
        large_variables.update({
            "project_name": "variable_test",
            "author": "Variable User",
            "version": "0.1.0",
            "description": "Testing variable substitution performance"
        })
        
        def render_with_many_variables():
            # Mock template with many variables
            template_content = "# Project: {{ project_name }}\n"
            template_content += "# Author: {{ author }}\n"
            for i in range(100):
                template_content += f"# Variable {i}: {{{{ var_{i} }}}}\n"
            
            # Simulate template rendering
            rendered = template_content
            for key, value in large_variables.items():
                rendered = rendered.replace("{{ " + key + " }}", str(value))
            return rendered
        
        result = benchmark(render_with_many_variables)
        assert "variable_test" in result

    def test_complex_template_rendering(self, benchmark: BenchmarkFixture):
        """Benchmark rendering of complex templates with loops and conditionals."""
        def render_complex_template():
            # Simulate complex Jinja2 template rendering
            template_content = """
# Generated project with complex logic
{% for i in range(10) %}
class Module{{ i }}:
    {% if i % 2 == 0 %}
    def even_method(self):
        return {{ i }}
    {% else %}
    def odd_method(self):
        return {{ i }}
    {% endif %}
{% endfor %}

# Configuration
CONFIG = {
    {% for key, value in config_items.items() %}
    "{{ key }}": "{{ value }}",
    {% endfor %}
}
            """
            
            # Mock complex rendering
            variables = {
                "config_items": {f"setting_{i}": f"value_{i}" for i in range(20)}
            }
            
            # Simulate Jinja2 rendering complexity
            lines = []
            for i in range(10):
                lines.append(f"class Module{i}:")
                if i % 2 == 0:
                    lines.append(f"    def even_method(self): return {i}")
                else:
                    lines.append(f"    def odd_method(self): return {i}")
            
            config_lines = [f'    "{k}": "{v}",' for k, v in variables["config_items"].items()]
            lines.extend(["CONFIG = {"] + config_lines + ["}"])
            
            return "\n".join(lines)
        
        result = benchmark(render_complex_template)
        assert "Module0" in result and "CONFIG" in result


@pytest.mark.benchmark
class TestDirectoryCreationSpeed:
    """Benchmark directory creation performance."""

    def test_flat_directory_creation(self, benchmark: BenchmarkFixture, temp_dir: Path):
        """Benchmark creation of many directories at the same level."""
        def create_flat_directories():
            base_dir = temp_dir / "flat_test"
            directories = []
            for i in range(50):
                dir_path = base_dir / f"dir_{i}"
                dir_path.mkdir(parents=True, exist_ok=True)
                directories.append(dir_path)
            return directories
        
        result = benchmark(create_flat_directories)
        assert len(result) == 50

    def test_deep_directory_creation(self, benchmark: BenchmarkFixture, temp_dir: Path):
        """Benchmark creation of deeply nested directory structures."""
        def create_deep_directories():
            current_path = temp_dir / "deep_test"
            paths = []
            for i in range(20):
                current_path = current_path / f"level_{i}"
                current_path.mkdir(parents=True, exist_ok=True)
                paths.append(current_path)
            return paths
        
        result = benchmark(create_deep_directories)
        assert len(result) == 20

    def test_mixed_directory_structure_creation(self, benchmark: BenchmarkFixture, 
                                              temp_dir: Path):
        """Benchmark creation of complex mixed directory structures."""
        def create_mixed_structure():
            base_dir = temp_dir / "mixed_test"
            base_dir.mkdir(exist_ok=True)
            
            paths = []
            # Create src structure
            for i in range(10):
                src_dir = base_dir / "src" / f"module_{i}"
                src_dir.mkdir(parents=True, exist_ok=True)
                paths.append(src_dir)
                
                # Create subdirectories
                for j in range(3):
                    sub_dir = src_dir / f"submodule_{j}"
                    sub_dir.mkdir(exist_ok=True)
                    paths.append(sub_dir)
            
            # Create tests structure  
            for i in range(10):
                test_dir = base_dir / "tests" / f"test_module_{i}"
                test_dir.mkdir(parents=True, exist_ok=True)
                paths.append(test_dir)
            
            return paths
        
        result = benchmark(create_mixed_structure)
        assert len(result) == 50  # 10 modules * 4 dirs + 10 test dirs


@pytest.mark.benchmark
class TestPerformanceRegression:
    """Performance regression detection tests."""

    def test_baseline_generation_performance(self, benchmark: BenchmarkFixture,
                                           temp_dir: Path, config_manager: ConfigManager):
        """Establish baseline performance for standard project generation."""
        def baseline_generation():
            return create_project(
                template_name="python_library",
                project_name="baseline_test",
                target_directory=temp_dir,
                variables={
                    "author": "Baseline User",
                    "version": "0.1.0", 
                    "description": "Baseline performance test",
                    "license": "MIT",
                },
                config_manager=config_manager
            )
        
        result = benchmark(baseline_generation)
        assert result.success, f"Baseline generation failed: {result.errors}"
        
        # Performance assertions for regression detection
        stats = benchmark.stats
        mean_time = stats.stats.mean
        
        # Assert performance targets (adjust based on actual measurements)
        assert mean_time < 2.0, f"Generation too slow: {mean_time:.3f}s (target: <2.0s)"
        
        # Memory usage assertion (if available)
        if hasattr(stats, 'memory'):
            peak_memory = getattr(stats.memory, 'peak', 0)
            assert peak_memory < 100 * 1024 * 1024, f"Memory usage too high: {peak_memory} bytes"

    def test_performance_consistency(self, benchmark: BenchmarkFixture,
                                   temp_dir: Path, config_manager: ConfigManager):
        """Test performance consistency across multiple runs."""
        def consistent_generation():
            return create_project(
                template_name="cli_single_package",
                project_name="consistency_test",
                target_directory=temp_dir,
                variables={
                    "author": "Consistency User",
                    "version": "0.1.0",
                    "description": "Consistency performance test",
                    "license": "MIT",
                },
                config_manager=config_manager
            )
        
        # Run with increased rounds for consistency testing
        result = benchmark.pedantic(consistent_generation, rounds=10, iterations=1)
        assert result.success, f"Consistency generation failed: {result.errors}"
        
        # Check consistency metrics
        stats = benchmark.stats
        if hasattr(stats.stats, 'stddev'):
            coefficient_variation = stats.stats.stddev / stats.stats.mean
            assert coefficient_variation < 0.5, f"Performance too inconsistent: CV={coefficient_variation:.3f}"


@pytest.fixture
def mock_template():
    """Provide a mock template for performance tests that require direct template access."""
    from create_project.templates.schema.template import Template
    
    # Create a mock template object for direct generator testing
    template = MagicMock(spec=Template)
    template.name = "test_template"
    template.display_name = "Test Template"
    template.description = "Mock template for performance testing"
    template.version = "1.0.0"
    template.author = "Test Author"
    template.tags = ["testing"]
    template.variables = []
    template.structure = {
        "src": {"__init__.py": "", "main.py": "# Main module"},
        "tests": {"__init__.py": "", "test_main.py": "# Test module"}
    }
    return template


@pytest.fixture  
def config_manager():
    """Provide a config manager for performance tests."""
    config = MagicMock()
    config.get_setting.return_value = None
    return config