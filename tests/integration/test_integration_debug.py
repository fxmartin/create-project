# ABOUTME: Debug logging utilities for integration tests
# ABOUTME: Provides enhanced logging and debugging capabilities for test analysis

"""
Debug logging utilities for integration tests.

This module provides:
- Enhanced debug logging for integration test analysis
- Performance measurement utilities
- Component interaction tracing
- Error context collection for test failures
"""

import functools
import time
from typing import Any, Callable, Dict
import logging

# Set up debug logger
debug_logger = logging.getLogger("integration_test_debug")
debug_logger.setLevel(logging.DEBUG)

if not debug_logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    debug_logger.addHandler(handler)


def log_test_execution(test_name: str = None):
    """
    Decorator to log test execution with timing and context.
    
    Args:
        test_name: Optional custom test name for logging
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            actual_test_name = test_name or func.__name__
            debug_logger.info(f"Starting integration test: {actual_test_name}")
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                end_time = time.time()
                execution_time = end_time - start_time
                
                debug_logger.info(
                    f"Integration test completed successfully: {actual_test_name} "
                    f"(Duration: {execution_time:.3f}s)"
                )
                return result
                
            except Exception as e:
                end_time = time.time()
                execution_time = end_time - start_time
                
                debug_logger.error(
                    f"Integration test failed: {actual_test_name} "
                    f"(Duration: {execution_time:.3f}s) - Error: {str(e)}"
                )
                raise
                
        return wrapper
    return decorator


def log_component_interaction(component_name: str, operation: str):
    """
    Log component interactions for debugging integration issues.
    
    Args:
        component_name: Name of the component being tested
        operation: Description of the operation being performed
    """
    debug_logger.debug(f"Component interaction: {component_name} - {operation}")


def log_performance_metric(metric_name: str, value: float, unit: str = ""):
    """
    Log performance metrics for integration test analysis.
    
    Args:
        metric_name: Name of the performance metric
        value: Measured value
        unit: Unit of measurement (optional)
    """
    unit_str = f" {unit}" if unit else ""
    debug_logger.info(f"Performance metric: {metric_name} = {value:.3f}{unit_str}")


def log_test_context(context: Dict[str, Any]):
    """
    Log test context information for debugging.
    
    Args:
        context: Dictionary containing test context information
    """
    debug_logger.debug(f"Test context: {context}")


class IntegrationTestProfiler:
    """
    Context manager for profiling integration test performance.
    """
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        debug_logger.debug(f"Starting profiled operation: {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        
        if exc_type is None:
            debug_logger.info(
                f"Profiled operation completed: {self.operation_name} "
                f"(Duration: {duration:.3f}s)"
            )
        else:
            debug_logger.error(
                f"Profiled operation failed: {self.operation_name} "
                f"(Duration: {duration:.3f}s) - Error: {exc_val}"
            )
    
    @property
    def duration(self) -> float:
        """Get the duration of the profiled operation."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0


def create_test_summary(test_results: Dict[str, Any]) -> str:
    """
    Create a summary of integration test results.
    
    Args:
        test_results: Dictionary containing test results and metrics
        
    Returns:
        Formatted summary string
    """
    summary_lines = ["Integration Test Summary", "=" * 30]
    
    for test_name, result in test_results.items():
        status = "PASS" if result.get("success", False) else "FAIL"
        duration = result.get("duration", 0.0)
        summary_lines.append(f"{test_name}: {status} ({duration:.3f}s)")
    
    total_tests = len(test_results)
    passed_tests = sum(1 for r in test_results.values() if r.get("success", False))
    
    summary_lines.extend([
        "=" * 30,
        f"Total tests: {total_tests}",
        f"Passed: {passed_tests}",
        f"Failed: {total_tests - passed_tests}",
        f"Success rate: {(passed_tests / total_tests * 100):.1f}%"
    ])
    
    return "\n".join(summary_lines)


# Example usage for debugging integration tests
def debug_template_loading(template_loader, template_name: str):
    """Debug template loading process."""
    with IntegrationTestProfiler(f"Template loading: {template_name}"):
        log_component_interaction("TemplateLoader", f"Loading template: {template_name}")
        template = template_loader.load_template(template_name)
        
        if template:
            log_test_context({
                "template_name": template.metadata.name,
                "template_version": template.metadata.version,
                "variable_count": len(template.variables),
                "structure_items": len(template.structure)
            })
        else:
            debug_logger.warning(f"Template not found: {template_name}")
        
        return template


def debug_project_generation(generator, options):
    """Debug project generation process."""
    with IntegrationTestProfiler(f"Project generation: {options.project_name}"):
        log_component_interaction("ProjectGenerator", f"Creating project: {options.project_name}")
        log_test_context({
            "template_name": options.template_name,
            "project_name": options.project_name,
            "target_directory": options.target_directory,
            "init_git": options.init_git,
            "create_venv": options.create_venv
        })
        
        result = generator.create_project(options)
        
        if result.success:
            debug_logger.info(f"Project generation successful: {options.project_name}")
        else:
            debug_logger.error(f"Project generation failed: {options.project_name} - {result.errors}")
        
        return result