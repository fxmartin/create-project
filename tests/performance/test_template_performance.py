# ABOUTME: Performance tests for template operations
# ABOUTME: Benchmarks template loading, validation, and rendering

"""Performance tests for template operations."""

import pytest
from pathlib import Path
from typing import Any, Dict

from create_project.templates.loader import TemplateLoader
from create_project.templates.engine import TemplateEngine
from create_project.config.manager import ConfigManager
from tests.performance.benchmarks import check_performance


@pytest.mark.benchmark
def test_template_load_single(
    benchmark: Any,
    template_loader: TemplateLoader,
    memory_snapshot: Any,
) -> None:
    """Benchmark loading a single template."""
    # Measure initial memory
    initial_memory = memory_snapshot()
    
    # Run benchmark
    result = benchmark(template_loader.load_template, "python_library")
    
    # Measure final memory
    final_memory = memory_snapshot()
    memory_used = final_memory["rss_mb"] - initial_memory["rss_mb"]
    
    # Check performance
    duration_ms = benchmark.stats["mean"] * 1000
    passed, message = check_performance(
        "template_load_single",
        duration_ms,
        memory_used,
    )
    
    assert passed, f"Performance check failed: {message}"
    assert result is not None
    assert result.metadata.name == "python_library"


@pytest.mark.benchmark
def test_template_load_all(
    benchmark: Any,
    template_loader: TemplateLoader,
    memory_snapshot: Any,
) -> None:
    """Benchmark loading all built-in templates."""
    initial_memory = memory_snapshot()
    
    def load_all_templates() -> list:
        templates = []
        for template_id in [
            "python_library",
            "python_package",
            "cli_single",
            "cli_multi",
            "flask_web",
            "django_web",
        ]:
            templates.append(template_loader.load_template(template_id))
        return templates
    
    result = benchmark(load_all_templates)
    
    final_memory = memory_snapshot()
    memory_used = final_memory["rss_mb"] - initial_memory["rss_mb"]
    
    duration_ms = benchmark.stats["mean"] * 1000
    passed, message = check_performance(
        "template_load_all",
        duration_ms,
        memory_used,
    )
    
    assert passed, f"Performance check failed: {message}"
    assert len(result) == 6


@pytest.mark.benchmark
def test_template_validation(
    benchmark: Any,
    template_loader: TemplateLoader,
    memory_snapshot: Any,
) -> None:
    """Benchmark template schema validation."""
    template = template_loader.load_template("python_library")
    initial_memory = memory_snapshot()
    
    def validate_template() -> bool:
        # Simulate validation by checking required fields
        required = ["metadata", "structure", "variables"]
        template_dict = template.dict()
        return all(field in template_dict for field in required)
    
    result = benchmark(validate_template)
    
    final_memory = memory_snapshot()
    memory_used = final_memory["rss_mb"] - initial_memory["rss_mb"]
    
    duration_ms = benchmark.stats["mean"] * 1000
    passed, message = check_performance(
        "template_validate",
        duration_ms,
        memory_used,
    )
    
    assert passed, f"Performance check failed: {message}"
    assert result is True


@pytest.mark.benchmark
def test_render_template_small(
    benchmark: Any,
    template_engine: TemplateEngine,
    sample_template_variables: Dict[str, Any],
    memory_snapshot: Any,
) -> None:
    """Benchmark rendering a small template."""
    template_content = "Hello {{ project_name }} by {{ author }}!"
    initial_memory = memory_snapshot()
    
    result = benchmark(
        template_engine.render_string,
        template_content,
        sample_template_variables,
    )
    
    final_memory = memory_snapshot()
    memory_used = final_memory["rss_mb"] - initial_memory["rss_mb"]
    
    duration_ms = benchmark.stats["mean"] * 1000
    passed, message = check_performance(
        "render_template_small",
        duration_ms,
        memory_used,
    )
    
    assert passed, f"Performance check failed: {message}"
    assert "test_project" in result
    assert "Test Author" in result


@pytest.mark.benchmark
def test_render_template_large(
    benchmark: Any,
    template_engine: TemplateEngine,
    sample_template_variables: Dict[str, Any],
    memory_snapshot: Any,
) -> None:
    """Benchmark rendering a large template."""
    # Create a large template with many variables and loops
    template_content = """
# {{ project_name }}

Author: {{ author }}
Email: {{ email }}
Version: {{ version }}
License: {{ license }}

## Description
{{ description }}

## Dependencies
{% for i in range(50) %}
- dependency_{{ i }}
{% endfor %}

## Modules
{% for i in range(20) %}
### Module {{ i }}
This is module {{ i }} for {{ project_name }}.
Author: {{ author }}
Year: {{ current_year }}
{% endfor %}

## Configuration
{% for key, value in variables.items() %}
- {{ key }}: {{ value }}
{% endfor %}
"""
    
    # Add extra variables for the template
    variables = sample_template_variables.copy()
    variables["variables"] = {f"config_{i}": f"value_{i}" for i in range(30)}
    
    initial_memory = memory_snapshot()
    
    result = benchmark(
        template_engine.render_string,
        template_content,
        variables,
    )
    
    final_memory = memory_snapshot()
    memory_used = final_memory["rss_mb"] - initial_memory["rss_mb"]
    
    duration_ms = benchmark.stats["mean"] * 1000
    passed, message = check_performance(
        "render_template_large",
        duration_ms,
        memory_used,
    )
    
    assert passed, f"Performance check failed: {message}"
    assert "test_project" in result
    assert "Module 19" in result
    assert "config_29" in result


@pytest.mark.benchmark
@pytest.mark.stress
def test_template_rendering_stress(
    benchmark: Any,
    template_engine: TemplateEngine,
    sample_template_variables: Dict[str, Any],
    memory_snapshot: Any,
) -> None:
    """Stress test template rendering with many concurrent operations."""
    templates = [
        f"Project: {{{{ project_name }}}}_v{i} by {{{{ author }}}}"
        for i in range(100)
    ]
    
    initial_memory = memory_snapshot()
    
    def render_many_templates() -> list:
        results = []
        for template in templates:
            results.append(
                template_engine.render_string(template, sample_template_variables)
            )
        return results
    
    result = benchmark(render_many_templates)
    
    final_memory = memory_snapshot()
    memory_used = final_memory["rss_mb"] - initial_memory["rss_mb"]
    
    # For stress tests, we're more interested in completion than strict limits
    assert len(result) == 100
    assert all("test_project" in r for r in result)
    
    # Log performance for analysis
    duration_ms = benchmark.stats["mean"] * 1000
    print(f"\nStress test completed in {duration_ms:.1f}ms using {memory_used:.1f}MB")