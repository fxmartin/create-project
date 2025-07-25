# ABOUTME: Performance monitoring utilities for tracking application metrics
# ABOUTME: Provides memory usage tracking, operation timing, and system performance data

"""
Performance monitoring module.

This module provides utilities for tracking application performance including:
- Memory usage monitoring with snapshots
- Operation timing and profiling
- System resource utilization
- Performance metrics collection and reporting
- Debug mode performance dashboard data
"""

import gc
import os
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import psutil

from create_project.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MemorySnapshot:
    """Memory usage snapshot at a point in time."""

    timestamp: float
    rss_mb: float  # Resident Set Size in MB
    vms_mb: float  # Virtual Memory Size in MB
    percent: float  # Memory percentage used
    available_mb: float  # Available system memory in MB
    objects_count: int  # Number of Python objects
    gc_stats: Dict[str, int]  # Garbage collection statistics


@dataclass
class OperationMetrics:
    """Metrics for a single operation."""

    operation_name: str
    start_time: float
    end_time: float
    duration: float
    memory_before: MemorySnapshot
    memory_after: MemorySnapshot
    memory_delta: float  # Memory change in MB
    cpu_percent: float  # CPU usage during operation
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceReport:
    """Complete performance report for analysis."""

    report_id: str
    start_time: float
    end_time: float
    total_duration: float
    operations: List[OperationMetrics]
    peak_memory_mb: float
    total_memory_delta: float
    avg_cpu_percent: float
    gc_collections: int
    system_info: Dict[str, Any]


class PerformanceMonitor:
    """
    Central performance monitoring system.
    
    Tracks memory usage, operation timing, and system metrics
    during application execution.
    """

    def __init__(self, enabled: bool = True):
        """
        Initialize performance monitor.
        
        Args:
            enabled: Whether to enable performance monitoring
        """
        self.enabled = enabled
        self.operations: List[OperationMetrics] = []
        self.start_time = time.time()
        self._lock = threading.Lock()

        # System info
        try:
            self.process = psutil.Process()
        except Exception as e:
            logger.warning(f"Failed to initialize process object: {e}")
            self.process = None

        self.system_info = self._get_system_info()

        logger.debug(f"Performance monitor initialized (enabled: {enabled})")

    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information for performance context."""
        try:
            memory = psutil.virtual_memory()
            cpu_info = {
                "cpu_count": psutil.cpu_count(),
                "cpu_count_logical": psutil.cpu_count(logical=True),
                "cpu_freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
            }

            return {
                "platform": os.name,
                "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
                "total_memory_mb": memory.total / (1024 * 1024),
                "available_memory_mb": memory.available / (1024 * 1024),
                "cpu_info": cpu_info,
                "process_id": os.getpid(),
            }
        except Exception as e:
            logger.warning(f"Failed to get system info: {e}")
            return {"error": str(e)}

    def take_memory_snapshot(self) -> MemorySnapshot:
        """Take a snapshot of current memory usage."""
        if not self.enabled:
            return MemorySnapshot(
                timestamp=time.time(),
                rss_mb=0,
                vms_mb=0,
                percent=0,
                available_mb=0,
                objects_count=0,
                gc_stats={}
            )

        try:
            # Process memory info
            if self.process is None:
                # Return empty snapshot if process is not available
                return MemorySnapshot(
                    timestamp=time.time(),
                    rss_mb=0,
                    vms_mb=0,
                    percent=0,
                    available_mb=0,
                    objects_count=0,
                    gc_stats={}
                )

            memory_info = self.process.memory_info()
            system_memory = psutil.virtual_memory()

            # Python objects count
            objects_count = len(gc.get_objects())

            # Garbage collection stats
            gc_stats = {
                f"generation_{i}": gc.get_count()[i] if i < len(gc.get_count()) else 0
                for i in range(gc.get_count().__len__())
            }

            return MemorySnapshot(
                timestamp=time.time(),
                rss_mb=memory_info.rss / (1024 * 1024),
                vms_mb=memory_info.vms / (1024 * 1024),
                percent=system_memory.percent,
                available_mb=system_memory.available / (1024 * 1024),
                objects_count=objects_count,
                gc_stats=gc_stats
            )
        except Exception as e:
            logger.error(f"Failed to take memory snapshot: {e}")
            return MemorySnapshot(time.time(), 0, 0, 0, 0, 0, {"error": str(e)})

    @contextmanager
    def measure_operation(self, operation_name: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Context manager to measure operation performance.
        
        Args:
            operation_name: Name of the operation being measured
            metadata: Additional metadata about the operation
            
        Usage:
            with monitor.measure_operation("template_loading"):
                # Your operation here
                pass
        """
        if not self.enabled:
            yield
            return

        metadata = metadata or {}
        start_time = time.time()
        memory_before = self.take_memory_snapshot()
        cpu_before = self.process.cpu_percent()

        error_message = None
        success = True

        try:
            yield
        except Exception as e:
            success = False
            error_message = str(e)
            logger.error(f"Operation '{operation_name}' failed: {e}")
            raise
        finally:
            end_time = time.time()
            memory_after = self.take_memory_snapshot()
            cpu_after = self.process.cpu_percent()

            # Calculate metrics
            duration = end_time - start_time
            memory_delta = memory_after.rss_mb - memory_before.rss_mb
            avg_cpu = (cpu_before + cpu_after) / 2

            # Create operation metrics
            metrics = OperationMetrics(
                operation_name=operation_name,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                memory_before=memory_before,
                memory_after=memory_after,
                memory_delta=memory_delta,
                cpu_percent=avg_cpu,
                success=success,
                error_message=error_message,
                metadata=metadata
            )

            # Store metrics thread-safely
            with self._lock:
                self.operations.append(metrics)

            logger.info(
                f"Operation '{operation_name}' completed in {duration:.3f}s "
                f"(memory: {memory_delta:+.2f}MB, CPU: {avg_cpu:.1f}%)"
            )

    def get_peak_memory(self) -> float:
        """Get peak memory usage across all operations."""
        if not self.operations:
            return 0.0

        peak_before = max(op.memory_before.rss_mb for op in self.operations)
        peak_after = max(op.memory_after.rss_mb for op in self.operations)
        return max(peak_before, peak_after)

    def get_total_memory_delta(self) -> float:
        """Get total memory change across all operations."""
        if not self.operations:
            return 0.0

        return sum(op.memory_delta for op in self.operations)

    def get_average_cpu(self) -> float:
        """Get average CPU usage across all operations."""
        if not self.operations:
            return 0.0

        return sum(op.cpu_percent for op in self.operations) / len(self.operations)

    def get_slowest_operations(self, limit: int = 5) -> List[OperationMetrics]:
        """Get the slowest operations by duration."""
        return sorted(self.operations, key=lambda op: op.duration, reverse=True)[:limit]

    def get_memory_intensive_operations(self, limit: int = 5) -> List[OperationMetrics]:
        """Get operations with highest memory usage."""
        return sorted(self.operations, key=lambda op: abs(op.memory_delta), reverse=True)[:limit]

    def generate_report(self) -> PerformanceReport:
        """Generate comprehensive performance report."""
        end_time = time.time()
        total_duration = end_time - self.start_time

        # Count garbage collections
        gc_collections = sum(gc.get_count())

        return PerformanceReport(
            report_id=f"perf_{int(self.start_time)}_{os.getpid()}",
            start_time=self.start_time,
            end_time=end_time,
            total_duration=total_duration,
            operations=self.operations.copy(),
            peak_memory_mb=self.get_peak_memory(),
            total_memory_delta=self.get_total_memory_delta(),
            avg_cpu_percent=self.get_average_cpu(),
            gc_collections=gc_collections,
            system_info=self.system_info
        )

    def reset(self):
        """Reset all performance data."""
        with self._lock:
            self.operations.clear()
            self.start_time = time.time()
        logger.debug("Performance monitor reset")

    def log_summary(self):
        """Log performance summary to logger."""
        if not self.enabled or not self.operations:
            return

        report = self.generate_report()

        logger.info("Performance Summary:")
        logger.info(f"  Total operations: {len(report.operations)}")
        logger.info(f"  Total duration: {report.total_duration:.3f}s")
        logger.info(f"  Peak memory: {report.peak_memory_mb:.2f}MB")
        logger.info(f"  Memory delta: {report.total_memory_delta:+.2f}MB")
        logger.info(f"  Average CPU: {report.avg_cpu_percent:.1f}%")

        # Log slowest operations
        slowest = self.get_slowest_operations(3)
        if slowest:
            logger.info("  Slowest operations:")
            for op in slowest:
                logger.info(f"    {op.operation_name}: {op.duration:.3f}s")


# Global performance monitor instance
_global_monitor: Optional[PerformanceMonitor] = None


def get_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor


def enable_monitoring():
    """Enable global performance monitoring."""
    monitor = get_monitor()
    monitor.enabled = True
    logger.info("Performance monitoring enabled")


def disable_monitoring():
    """Disable global performance monitoring."""
    monitor = get_monitor()
    monitor.enabled = False
    logger.info("Performance monitoring disabled")


def measure_operation(operation_name: str, metadata: Optional[Dict[str, Any]] = None):
    """
    Decorator/context manager for measuring operation performance.
    
    Args:
        operation_name: Name of the operation
        metadata: Additional metadata
        
    Usage:
        @measure_operation("template_loading")
        def load_template():
            pass
            
        # Or as context manager:
        with measure_operation("file_creation"):
            create_files()
    """
    monitor = get_monitor()
    return monitor.measure_operation(operation_name, metadata)


def take_snapshot() -> MemorySnapshot:
    """Take a memory snapshot using global monitor."""
    return get_monitor().take_memory_snapshot()


def log_performance_summary():
    """Log performance summary using global monitor."""
    get_monitor().log_summary()


def reset_monitoring():
    """Reset global performance monitoring data."""
    get_monitor().reset()
