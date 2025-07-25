# ABOUTME: Performance tests for configuration management
# ABOUTME: Benchmarks config loading, saving, and access patterns

"""Performance tests for configuration operations."""

import json
from pathlib import Path
from typing import Any

import pytest

from create_project.config.config_manager import ConfigManager
from tests.performance.benchmarks import check_performance


@pytest.mark.benchmark
def test_config_load(
    benchmark: Any,
    temp_dir: Path,
    memory_snapshot: Any,
) -> None:
    """Benchmark configuration loading."""
    config_dir = temp_dir / "config"
    config_dir.mkdir()

    # Create a test configuration file
    config_file = config_dir / "settings.json"
    config_data = {
        "app": {
            "version": "1.0.0",
            "debug": False,
            "data_dir": "./data",
        },
        "ui": {
            "theme": "dark",
            "window_size": [800, 600],
            "remember_window_state": True,
        },
        "ollama": {
            "api_url": "http://localhost:11434",
            "timeout": 30,
            "preferred_model": "codellama",
            "enable_cache": True,
        },
        "templates": {
            "builtin_path": "./templates/builtin",
            "directories": ["~/templates", "/usr/share/templates"],
        },
        "ai": {
            "enabled": True,
            "auto_detect": True,
            "preferred_model": "codellama",
        },
    }
    config_file.write_text(json.dumps(config_data, indent=2))

    initial_memory = memory_snapshot()

    def load_config() -> ConfigManager:
        return ConfigManager(config_path=config_dir)

    result = benchmark(load_config)

    final_memory = memory_snapshot()
    memory_used = final_memory["rss_mb"] - initial_memory["rss_mb"]

    duration_ms = benchmark.stats["mean"] * 1000
    passed, message = check_performance(
        "config_load",
        duration_ms,
        memory_used,
    )

    assert passed, f"Performance check failed: {message}"
    assert result is not None
    assert result.get_setting("ui.theme") == "dark"


@pytest.mark.benchmark
def test_config_save(
    benchmark: Any,
    config_manager: ConfigManager,
    memory_snapshot: Any,
) -> None:
    """Benchmark configuration saving."""
    # Modify configuration - use existing config sections
    config_manager.set_setting("app.debug", True)
    config_manager.set_setting("ui.theme", "light")
    config_manager.set_setting("ollama.timeout", 60)

    initial_memory = memory_snapshot()

    benchmark(config_manager.save_config)

    final_memory = memory_snapshot()
    memory_used = final_memory["rss_mb"] - initial_memory["rss_mb"]

    duration_ms = benchmark.stats["mean"] * 1000
    passed, message = check_performance(
        "config_save",
        duration_ms,
        memory_used,
    )

    assert passed, f"Performance check failed: {message}"

    # Verify save worked
    config_manager.reload_config()
    assert config_manager.get_setting("ui.theme") == "light"


@pytest.mark.benchmark
def test_config_access_patterns(
    benchmark: Any,
    config_manager: ConfigManager,
) -> None:
    """Benchmark various configuration access patterns."""
    # Set up test data using real config keys

    def access_patterns() -> None:
        # Simple gets of existing config keys
        for _ in range(10):
            config_manager.get_setting("app.version")
            config_manager.get_setting("ui.theme")
            config_manager.get_setting("ollama.api_url")

        # Nested gets
        for _ in range(10):
            config_manager.get_setting("ai.preferred_model")
            config_manager.get_setting("templates.builtin_path")

        # Gets with defaults (non-existent keys)
        for i in range(10):
            config_manager.get_setting(f"missing{i}", default="default")

        # Check existence of various keys
        for key in ["app", "ui", "ollama", "ai", "templates"]:
            config_manager.get_setting(key) is not None

    result = benchmark(access_patterns)

    # Access should be very fast
    duration_ms = benchmark.stats["mean"] * 1000
    assert duration_ms < 10, f"Config access too slow: {duration_ms:.1f}ms"


@pytest.mark.benchmark
@pytest.mark.stress
def test_config_concurrent_access(
    benchmark: Any,
    config_manager: ConfigManager,
    memory_snapshot: Any,
) -> None:
    """Stress test configuration with concurrent-like access patterns."""
    import time

    # Prepare large config
    for i in range(100):
        section = f"app{i}"
        config_manager.set_setting(f"{section}.name", f"Application {i}")
        config_manager.set_setting(f"{section}.version", f"1.0.{i}")
        config_manager.set_setting(f"{section}.features", list(range(10)))
        config_manager.set_setting(f"{section}.settings.debug", i % 2 == 0)

    initial_memory = memory_snapshot()
    results = []
    errors = []

    def concurrent_operations() -> None:
        # Simulate concurrent read/write patterns
        operations = []

        # Readers
        for i in range(50):
            val = config_manager.get_setting(f"app{i}.name")
            operations.append(("read", val))

        # Writers
        for i in range(50, 60):
            config_manager.set_setting(f"app{i}.last_access", time.time())
            operations.append(("write", i))

        # Mixed operations
        for i in range(10):
            if config_manager.get_setting(f"app{i}") is not None:
                val = config_manager.get_setting(f"app{i}.version")
                config_manager.set_setting(f"app{i}.access_count", i)
                operations.append(("mixed", val))

        results.extend(operations)

    # Run the stress test
    benchmark(concurrent_operations)

    final_memory = memory_snapshot()
    memory_used = final_memory["rss_mb"] - initial_memory["rss_mb"]

    duration_ms = benchmark.stats["mean"] * 1000

    # Verify operations completed successfully
    assert len(results) == 110
    assert len(errors) == 0
    assert memory_used < 50, f"Memory usage too high: {memory_used:.1f}MB"

    print(f"\nConcurrent operations completed in {duration_ms:.1f}ms")


@pytest.mark.benchmark
def test_config_large_values(
    benchmark: Any,
    config_manager: ConfigManager,
    memory_snapshot: Any,
) -> None:
    """Test performance with large configuration values."""
    # Create large configuration values
    large_list = list(range(10000))
    large_dict = {f"key_{i}": f"value_{i}" * 10 for i in range(1000)}
    large_string = "x" * 100000

    initial_memory = memory_snapshot()

    def large_value_operations() -> None:
        # Set large values
        config_manager.set_setting("large.list", large_list)
        config_manager.set_setting("large.dict", large_dict)
        config_manager.set_setting("large.string", large_string)

        # Get large values
        retrieved_list = config_manager.get_setting("large.list")
        retrieved_dict = config_manager.get_setting("large.dict")
        retrieved_string = config_manager.get_setting("large.string")

        # Verify
        assert len(retrieved_list) == 10000
        assert len(retrieved_dict) == 1000
        assert len(retrieved_string) == 100000

    benchmark(large_value_operations)

    final_memory = memory_snapshot()
    memory_used = final_memory["rss_mb"] - initial_memory["rss_mb"]

    duration_ms = benchmark.stats["mean"] * 1000

    # Large values will use more memory but should still be reasonable
    assert memory_used < 200, f"Memory usage too high: {memory_used:.1f}MB"
    print(f"\nLarge value operations: {duration_ms:.1f}ms, {memory_used:.1f}MB")
