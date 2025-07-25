# ABOUTME: Memory usage profiling and leak detection tests
# ABOUTME: Monitors memory consumption during project generation and UI operations

"""
Memory usage profiling test suite.

This module provides comprehensive memory profiling for project generation including:
- Memory growth tracking during project generation
- Peak memory usage measurements
- Memory leak detection across repeated operations
- Template caching memory impact analysis
- Garbage collection performance monitoring
- Concurrent operation memory usage
"""

import gc
import os
import time
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock

import psutil
import pytest
from pytest_benchmark.fixture import BenchmarkFixture

from create_project.config.config_manager import ConfigManager
from create_project.core.project_generator import ProjectGenerator, ProjectOptions
from create_project.templates.engine import TemplateEngine


@pytest.mark.memory
class TestMemoryGrowthTracking:
    """Track memory growth during project generation operations."""

    def test_memory_growth_single_project(self, temp_dir: Path, template_engine: TemplateEngine,
                                        config_manager: ConfigManager):
        """Track memory growth during single project generation."""
        process = psutil.Process(os.getpid())

        # Take baseline memory measurement
        gc.collect()  # Force garbage collection
        baseline_memory = process.memory_info().rss

        memory_snapshots = [baseline_memory]

        # Generate project and track memory
        options = ProjectOptions(
            template_name="python_library",
            project_name="memory_test",
            target_directory=temp_dir,
            variables={
                "author": "Memory User",
                "version": "0.1.0",
                "description": "Memory tracking test",
                "license": "MIT",
            }
        )

        generator = ProjectGenerator(config_manager, template_engine)

        # Take memory snapshot before generation
        pre_generation = process.memory_info().rss
        memory_snapshots.append(pre_generation)

        # Generate project
        result = generator.create_project(options)

        # Take memory snapshot after generation
        post_generation = process.memory_info().rss
        memory_snapshots.append(post_generation)

        # Force cleanup
        del generator, result
        gc.collect()

        # Take final memory snapshot
        final_memory = process.memory_info().rss
        memory_snapshots.append(final_memory)

        # Analysis
        peak_growth = max(memory_snapshots) - baseline_memory
        final_growth = final_memory - baseline_memory

        # Assertions for memory usage
        assert peak_growth < 50 * 1024 * 1024, f"Peak memory growth too high: {peak_growth / 1024 / 1024:.1f}MB"
        assert final_growth < 10 * 1024 * 1024, f"Memory leak detected: {final_growth / 1024 / 1024:.1f}MB not cleaned up"

        # Log memory progression for analysis
        print("\nMemory progression (MB):")
        print(f"Baseline: {baseline_memory / 1024 / 1024:.1f}")
        print(f"Pre-generation: {pre_generation / 1024 / 1024:.1f}")
        print(f"Post-generation: {post_generation / 1024 / 1024:.1f}")
        print(f"Final: {final_memory / 1024 / 1024:.1f}")

    def test_memory_growth_multiple_projects(self, temp_dir: Path, template_engine: TemplateEngine,
                                           config_manager: ConfigManager):
        """Track memory growth across multiple project generations."""
        process = psutil.Process(os.getpid())

        # Baseline measurement
        gc.collect()
        baseline_memory = process.memory_info().rss

        memory_readings = []
        project_count = 5

        for i in range(project_count):
            # Generate project
            options = ProjectOptions(
                template_name="cli_single_package",
                project_name=f"memory_multi_{i}",
                target_directory=temp_dir / f"project_{i}",
                variables={
                    "author": "Multi User",
                    "version": "0.1.0",
                    "description": f"Multi project {i}",
                    "license": "MIT",
                }
            )

            generator = ProjectGenerator(config_manager, template_engine)
            result = generator.create_project(options)

            # Take memory reading
            current_memory = process.memory_info().rss
            memory_readings.append(current_memory)

            # Cleanup
            del generator, result
            gc.collect()

        # Analysis
        memory_deltas = [reading - baseline_memory for reading in memory_readings]
        max_growth = max(memory_deltas)
        final_growth = memory_deltas[-1]

        # Check for linear memory growth (potential leak)
        if len(memory_deltas) > 2:
            growth_trend = memory_deltas[-1] - memory_deltas[0]
            per_project_growth = growth_trend / project_count
        else:
            per_project_growth = 0

        # Assertions
        assert max_growth < 100 * 1024 * 1024, f"Peak memory too high: {max_growth / 1024 / 1024:.1f}MB"
        assert per_project_growth < 5 * 1024 * 1024, f"Memory leak per project: {per_project_growth / 1024 / 1024:.1f}MB"

        print(f"\nMemory growth across {project_count} projects:")
        for i, delta in enumerate(memory_deltas):
            print(f"Project {i}: +{delta / 1024 / 1024:.1f}MB")

    def test_memory_growth_template_switching(self, temp_dir: Path, template_engine: TemplateEngine,
                                            config_manager: ConfigManager):
        """Track memory when switching between different templates."""
        process = psutil.Process(os.getpid())
        templates = ["python_library", "cli_single_package", "flask_web_app"]

        gc.collect()
        baseline_memory = process.memory_info().rss
        template_memories = {}

        for template_name in templates:
            # Generate project with this template
            options = ProjectOptions(
                template_name=template_name,
                project_name=f"switch_{template_name}",
                target_directory=temp_dir / template_name,
                variables={
                    "author": "Switch User",
                    "version": "0.1.0",
                    "description": f"Template switch test {template_name}",
                    "license": "MIT",
                }
            )

            generator = ProjectGenerator(config_manager, template_engine)
            result = generator.create_project(options)

            # Record memory for this template
            current_memory = process.memory_info().rss
            template_memories[template_name] = current_memory - baseline_memory

            del generator, result
            gc.collect()

        # Analysis
        max_template_memory = max(template_memories.values())
        memory_variance = max(template_memories.values()) - min(template_memories.values())

        assert max_template_memory < 75 * 1024 * 1024, f"Template memory too high: {max_template_memory / 1024 / 1024:.1f}MB"

        print("\nMemory usage by template:")
        for template, memory in template_memories.items():
            print(f"{template}: +{memory / 1024 / 1024:.1f}MB")


@pytest.mark.memory
class TestPeakMemoryUsage:
    """Measure peak memory consumption during operations."""

    def test_peak_memory_large_project(self, temp_dir: Path, config_manager: ConfigManager):
        """Measure peak memory during large project generation."""
        process = psutil.Process(os.getpid())

        # Create large template structure
        large_template = self._create_large_template(100)  # 100 files

        template_engine = MagicMock()
        template_engine.get_template.return_value = large_template
        template_engine.render_template.return_value = self._create_large_rendered_files(100)

        # Monitor peak memory during generation
        memory_monitor = MemoryMonitor()
        memory_monitor.start()

        try:
            options = ProjectOptions(
                template_name="large_project",
                project_name="peak_memory_test",
                target_directory=temp_dir,
                variables={"author": "Peak User", "file_count": 100}
            )

            generator = ProjectGenerator(config_manager, template_engine)
            result = generator.create_project(options)

        finally:
            memory_monitor.stop()

        peak_memory = memory_monitor.get_peak_memory()
        baseline_memory = memory_monitor.get_baseline_memory()
        peak_growth = peak_memory - baseline_memory

        # Assertions
        assert result.success, "Large project generation failed"
        assert peak_growth < 150 * 1024 * 1024, f"Peak memory too high: {peak_growth / 1024 / 1024:.1f}MB"

        print("\nPeak memory analysis:")
        print(f"Baseline: {baseline_memory / 1024 / 1024:.1f}MB")
        print(f"Peak: {peak_memory / 1024 / 1024:.1f}MB")
        print(f"Growth: {peak_growth / 1024 / 1024:.1f}MB")

    def test_peak_memory_concurrent_operations(self, temp_dir: Path, template_engine: TemplateEngine,
                                             config_manager: ConfigManager):
        """Measure peak memory with concurrent-like operations."""
        import threading

        memory_monitor = MemoryMonitor()
        memory_monitor.start()

        results = []
        threads = []

        def generate_project(project_id: int):
            options = ProjectOptions(
                template_name="python_library",
                project_name=f"concurrent_{project_id}",
                target_directory=temp_dir / f"concurrent_{project_id}",
                variables={
                    "author": f"Concurrent User {project_id}",
                    "version": "0.1.0",
                    "description": f"Concurrent project {project_id}",
                    "license": "MIT",
                }
            )
            generator = ProjectGenerator(config_manager, template_engine)
            result = generator.create_project(options)
            results.append(result)

        try:
            # Create multiple threads (simulating concurrent operations)
            for i in range(3):
                thread = threading.Thread(target=generate_project, args=(i,))
                threads.append(thread)
                thread.start()

            # Wait for all threads
            for thread in threads:
                thread.join()

        finally:
            memory_monitor.stop()

        peak_memory = memory_monitor.get_peak_memory()
        baseline_memory = memory_monitor.get_baseline_memory()
        peak_growth = peak_memory - baseline_memory

        # Assertions
        assert all(r.success for r in results), "Some concurrent generations failed"
        assert peak_growth < 200 * 1024 * 1024, f"Concurrent peak memory too high: {peak_growth / 1024 / 1024:.1f}MB"

    def _create_large_template(self, file_count: int) -> Dict[str, Any]:
        """Create template structure with many files."""
        structure = {"src": {}, "tests": {}}

        for i in range(file_count // 2):
            structure["src"][f"module_{i}.py"] = f"# Module {i}"
            structure["tests"][f"test_module_{i}.py"] = f"# Test {i}"

        return {
            "name": "large_template",
            "structure": structure,
            "variables": ["author", "file_count"]
        }

    def _create_large_rendered_files(self, file_count: int) -> Dict[str, str]:
        """Create rendered file content for large template."""
        files = {}

        for i in range(file_count // 2):
            # Create realistic Python file content
            module_content = f"""# Module {i}
'''Module {i} documentation.'''

class Module{i}:
    '''Class for module {i}.'''
    
    def __init__(self):
        self.value = {i}
    
    def get_value(self):
        return self.value
    
    def process(self, data):
        return f"Module {i} processed: {{data}}"
"""
            files[f"src/module_{i}.py"] = module_content

            test_content = f"""# Test module {i}
import pytest
from src.module_{i} import Module{i}

class TestModule{i}:
    def test_init(self):
        module = Module{i}()
        assert module.value == {i}
    
    def test_get_value(self):
        module = Module{i}()
        assert module.get_value() == {i}
    
    def test_process(self):
        module = Module{i}()
        result = module.process("test")
        assert "Module {i} processed: test" in result
"""
            files[f"tests/test_module_{i}.py"] = test_content

        return files


@pytest.mark.memory
class TestMemoryLeakDetection:
    """Detect memory leaks in repeated operations."""

    def test_repeated_generation_leak_detection(self, temp_dir: Path, template_engine: TemplateEngine,
                                              config_manager: ConfigManager):
        """Detect memory leaks through repeated project generation."""
        process = psutil.Process(os.getpid())
        iterations = 10
        memory_readings = []

        # Warm up (first generation may allocate caches)
        self._generate_test_project(temp_dir / "warmup", template_engine, config_manager)
        gc.collect()

        # Take baseline after warmup
        baseline_memory = process.memory_info().rss

        for i in range(iterations):
            # Generate project
            project_dir = temp_dir / f"leak_test_{i}"
            self._generate_test_project(project_dir, template_engine, config_manager)

            # Force cleanup
            gc.collect()

            # Record memory
            current_memory = process.memory_info().rss
            memory_readings.append(current_memory)

            # Clean up project directory to avoid disk space issues
            if project_dir.exists():
                import shutil
                shutil.rmtree(project_dir)

        # Analyze for leaks
        memory_deltas = [reading - baseline_memory for reading in memory_readings]

        # Calculate trend (positive slope indicates leak)
        if len(memory_deltas) > 1:
            trend = (memory_deltas[-1] - memory_deltas[0]) / len(memory_deltas)
        else:
            trend = 0

        # Check for consistent growth
        growing_count = sum(1 for i in range(1, len(memory_deltas))
                          if memory_deltas[i] > memory_deltas[i-1])
        growth_ratio = growing_count / (len(memory_deltas) - 1) if len(memory_deltas) > 1 else 0

        # Assertions for leak detection
        assert trend < 1 * 1024 * 1024, f"Memory leak detected: {trend / 1024 / 1024:.1f}MB/iteration trend"
        assert growth_ratio < 0.7, f"Suspicious memory growth pattern: {growth_ratio:.1%} iterations growing"

        print("\nLeak detection results:")
        print(f"Iterations: {iterations}")
        print(f"Memory trend: {trend / 1024:.1f}KB/iteration")
        print(f"Growth ratio: {growth_ratio:.1%}")
        print(f"Final delta: {memory_deltas[-1] / 1024 / 1024:.1f}MB")

    def test_template_caching_memory_leak(self, temp_dir: Path, config_manager: ConfigManager):
        """Test for memory leaks in template caching."""
        process = psutil.Process(os.getpid())

        # Create multiple templates to stress caching
        templates = [f"template_{i}" for i in range(20)]
        memory_readings = []

        for i, template_name in enumerate(templates):
            # Create mock template
            template_engine = MagicMock()
            template_engine.get_template.return_value = {
                "name": template_name,
                "structure": {"main.py": f"# Template {i}"},
                "variables": ["author"]
            }
            template_engine.render_template.return_value = {
                "main.py": f"# Generated from {template_name}"
            }

            # Generate project
            options = ProjectOptions(
                template_name=template_name,
                project_name=f"cache_test_{i}",
                target_directory=temp_dir / f"cache_{i}",
                variables={"author": "Cache User"}
            )

            generator = ProjectGenerator(config_manager, template_engine)
            result = generator.create_project(options)

            # Record memory
            gc.collect()
            current_memory = process.memory_info().rss
            memory_readings.append(current_memory)

            del generator, result, template_engine

        # Analyze caching impact
        if memory_readings:
            memory_growth = memory_readings[-1] - memory_readings[0]
            avg_per_template = memory_growth / len(templates)

            assert memory_growth < 100 * 1024 * 1024, f"Template caching uses too much memory: {memory_growth / 1024 / 1024:.1f}MB"
            assert avg_per_template < 5 * 1024 * 1024, f"Per-template memory too high: {avg_per_template / 1024 / 1024:.1f}MB"

    def _generate_test_project(self, project_dir: Path, template_engine: TemplateEngine,
                             config_manager: ConfigManager):
        """Helper to generate a test project."""
        options = ProjectOptions(
            template_name="python_library",
            project_name="leak_test",
            target_directory=project_dir,
            variables={
                "author": "Leak Test User",
                "version": "0.1.0",
                "description": "Memory leak test project",
                "license": "MIT",
            }
        )
        generator = ProjectGenerator(config_manager, template_engine)
        return generator.create_project(options)


@pytest.mark.memory
class TestGarbageCollectionPerformance:
    """Monitor garbage collection performance and impact."""

    def test_gc_performance_during_generation(self, temp_dir: Path, template_engine: TemplateEngine,
                                            config_manager: ConfigManager):
        """Monitor garbage collection during project generation."""
        # Enable GC stats
        gc.collect()
        gc_stats_before = gc.get_stats()
        gc_counts_before = gc.get_count()

        # Generate multiple projects to trigger GC
        for i in range(5):
            options = ProjectOptions(
                template_name="django_web_app",
                project_name=f"gc_test_{i}",
                target_directory=temp_dir / f"gc_{i}",
                variables={
                    "author": "GC User",
                    "version": "0.1.0",
                    "description": f"GC test project {i}",
                    "license": "MIT",
                }
            )
            generator = ProjectGenerator(config_manager, template_engine)
            result = generator.create_project(options)
            del generator, result

        # Check GC stats after
        gc.collect()
        gc_stats_after = gc.get_stats()
        gc_counts_after = gc.get_count()

        # Calculate GC activity
        total_collections_before = sum(stat["collections"] for stat in gc_stats_before)
        total_collections_after = sum(stat["collections"] for stat in gc_stats_after)
        gc_activity = total_collections_after - total_collections_before

        # Analysis
        print("\nGC Performance Analysis:")
        print(f"GC collections triggered: {gc_activity}")
        print(f"Objects before: {gc_counts_before}")
        print(f"Objects after: {gc_counts_after}")

        # Reasonable GC activity assertions
        assert gc_activity < 50, f"Too much GC activity: {gc_activity} collections"

    def test_gc_impact_on_performance(self, benchmark: BenchmarkFixture, temp_dir: Path,
                                    template_engine: TemplateEngine, config_manager: ConfigManager):
        """Measure GC impact on generation performance."""
        def generation_with_gc_monitoring():
            gc_start = time.perf_counter()
            gc.collect()  # Force GC
            gc_time = time.perf_counter() - gc_start

            options = ProjectOptions(
                template_name="flask_web_app",
                project_name="gc_impact_test",
                target_directory=temp_dir,
                variables={
                    "author": "GC Impact User",
                    "version": "0.1.0",
                    "description": "GC impact test",
                    "license": "MIT",
                }
            )

            generator = ProjectGenerator(config_manager, template_engine)
            result = generator.create_project(options)

            return {"result": result, "gc_time": gc_time}

        outcome = benchmark(generation_with_gc_monitoring)
        assert outcome["result"].success, "Generation failed during GC test"
        assert outcome["gc_time"] < 0.1, f"GC taking too long: {outcome['gc_time']:.3f}s"


class MemoryMonitor:
    """Utility class for monitoring memory usage during operations."""

    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.baseline_memory = None
        self.peak_memory = None
        self.readings = []
        self.monitoring = False

    def start(self):
        """Start memory monitoring."""
        gc.collect()
        self.baseline_memory = self.process.memory_info().rss
        self.peak_memory = self.baseline_memory
        self.readings = [self.baseline_memory]
        self.monitoring = True

    def stop(self):
        """Stop memory monitoring."""
        self.monitoring = False
        if self.readings:
            self.peak_memory = max(self.readings)

    def record(self):
        """Record current memory usage."""
        if self.monitoring:
            current = self.process.memory_info().rss
            self.readings.append(current)
            if current > self.peak_memory:
                self.peak_memory = current

    def get_baseline_memory(self) -> int:
        """Get baseline memory usage."""
        return self.baseline_memory or 0

    def get_peak_memory(self) -> int:
        """Get peak memory usage."""
        return self.peak_memory or 0

    def get_current_memory(self) -> int:
        """Get current memory usage."""
        return self.process.memory_info().rss


@pytest.fixture
def template_engine():
    """Provide a template engine for memory tests."""
    engine = MagicMock()
    engine.get_template.return_value = {
        "name": "memory_test_template",
        "structure": {
            "src": {"__init__.py": "", "main.py": "# Main module"},
            "tests": {"__init__.py": "", "test_main.py": "# Test module"}
        },
        "variables": ["author", "version", "description", "license"]
    }
    engine.render_template.return_value = {
        "src/__init__.py": "",
        "src/main.py": "# Generated main module",
        "tests/__init__.py": "",
        "tests/test_main.py": "# Generated test module"
    }
    return engine


@pytest.fixture
def config_manager():
    """Provide a config manager for memory tests."""
    config = MagicMock()
    config.get_setting.return_value = None
    return config
