# ABOUTME: Performance benchmark definitions and baseline metrics
# ABOUTME: Defines acceptable performance thresholds for critical operations

"""Performance benchmarks and baseline metrics for create-project."""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class PerformanceMetric:
    """Define a performance metric with acceptable thresholds."""

    operation: str
    max_duration_ms: float
    max_memory_mb: float
    description: str
    critical: bool = True

    def check_duration(self, duration_ms: float) -> bool:
        """Check if duration is within acceptable limits."""
        return duration_ms <= self.max_duration_ms

    def check_memory(self, memory_mb: float) -> bool:
        """Check if memory usage is within acceptable limits."""
        return memory_mb <= self.max_memory_mb


# Baseline performance metrics for critical operations
PERFORMANCE_BASELINES: Dict[str, PerformanceMetric] = {
    # Template loading operations
    "template_load_single": PerformanceMetric(
        operation="Load single template",
        max_duration_ms=50,
        max_memory_mb=10,
        description="Loading a single template should be fast",
    ),
    "template_load_all": PerformanceMetric(
        operation="Load all built-in templates",
        max_duration_ms=200,
        max_memory_mb=50,
        description="Loading all templates should complete quickly",
    ),
    "template_validate": PerformanceMetric(
        operation="Validate template schema",
        max_duration_ms=20,
        max_memory_mb=5,
        description="Template validation should be lightweight",
    ),

    # File operations
    "create_small_project": PerformanceMetric(
        operation="Create small project (10 files)",
        max_duration_ms=500,
        max_memory_mb=50,
        description="Small project generation should be fast",
    ),
    "create_medium_project": PerformanceMetric(
        operation="Create medium project (50 files)",
        max_duration_ms=2000,
        max_memory_mb=100,
        description="Medium project generation should scale well",
    ),
    "create_large_project": PerformanceMetric(
        operation="Create large project (100+ files)",
        max_duration_ms=5000,
        max_memory_mb=200,
        description="Large project generation should remain responsive",
        critical=False,
    ),

    # Configuration operations
    "config_load": PerformanceMetric(
        operation="Load configuration",
        max_duration_ms=20,
        max_memory_mb=5,
        description="Configuration loading should be instant",
    ),
    "config_save": PerformanceMetric(
        operation="Save configuration",
        max_duration_ms=50,
        max_memory_mb=5,
        description="Configuration saving should be quick",
    ),

    # Path operations
    "path_validation": PerformanceMetric(
        operation="Validate file path",
        max_duration_ms=1,
        max_memory_mb=1,
        description="Path validation should be extremely fast",
    ),
    "path_expansion": PerformanceMetric(
        operation="Expand path with variables",
        max_duration_ms=5,
        max_memory_mb=1,
        description="Path expansion should be quick",
    ),

    # Rendering operations
    "render_template_small": PerformanceMetric(
        operation="Render small template",
        max_duration_ms=10,
        max_memory_mb=5,
        description="Small template rendering should be instant",
    ),
    "render_template_large": PerformanceMetric(
        operation="Render large template",
        max_duration_ms=100,
        max_memory_mb=20,
        description="Large template rendering should be efficient",
    ),

    # GUI operations (when applicable)
    "wizard_step_transition": PerformanceMetric(
        operation="Wizard step transition",
        max_duration_ms=100,
        max_memory_mb=10,
        description="UI transitions should feel instant",
    ),
    "dialog_open": PerformanceMetric(
        operation="Open dialog",
        max_duration_ms=200,
        max_memory_mb=20,
        description="Dialog opening should be responsive",
    ),

    # AI operations (non-critical)
    "ai_model_detection": PerformanceMetric(
        operation="Detect AI models",
        max_duration_ms=1000,
        max_memory_mb=50,
        description="AI model detection can be slower",
        critical=False,
    ),
    "ai_cache_lookup": PerformanceMetric(
        operation="AI cache lookup",
        max_duration_ms=5,
        max_memory_mb=5,
        description="Cache lookups should be instant",
    ),
}


def get_baseline(operation: str) -> Optional[PerformanceMetric]:
    """Get performance baseline for an operation."""
    return PERFORMANCE_BASELINES.get(operation)


def check_performance(
    operation: str,
    duration_ms: float,
    memory_mb: float,
) -> tuple[bool, str]:
    """
    Check if performance meets baseline requirements.
    
    Returns:
        Tuple of (passes, message)
    """
    baseline = get_baseline(operation)
    if not baseline:
        return True, f"No baseline defined for {operation}"

    duration_ok = baseline.check_duration(duration_ms)
    memory_ok = baseline.check_memory(memory_mb)

    if duration_ok and memory_ok:
        return True, "Performance within acceptable limits"

    issues = []
    if not duration_ok:
        issues.append(
            f"Duration {duration_ms:.1f}ms exceeds limit {baseline.max_duration_ms}ms"
        )
    if not memory_ok:
        issues.append(
            f"Memory {memory_mb:.1f}MB exceeds limit {baseline.max_memory_mb}MB"
        )

    return False, "; ".join(issues)


# Performance test categories
CATEGORIES = {
    "fast": ["path_validation", "path_expansion", "render_template_small", "ai_cache_lookup"],
    "medium": ["template_load_single", "config_load", "config_save", "wizard_step_transition"],
    "slow": ["create_small_project", "create_medium_project", "template_load_all"],
    "stress": ["create_large_project", "render_template_large"],
}
