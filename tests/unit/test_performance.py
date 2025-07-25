# ABOUTME: Unit tests for performance monitoring utilities
# ABOUTME: Tests memory tracking, operation measurement, and performance reporting

"""
Unit tests for performance monitoring system.

Tests the PerformanceMonitor class, memory snapshots, operation metrics,
and performance reporting functionality.
"""

import gc
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from create_project.utils.performance import (
    PerformanceMonitor,
    MemorySnapshot,
    OperationMetrics,
    PerformanceReport,
    get_monitor,
    enable_monitoring,
    disable_monitoring,
    measure_operation,
    take_snapshot,
    log_performance_summary,
    reset_monitoring,
)


class TestMemorySnapshot:
    """Test MemorySnapshot dataclass."""

    def test_memory_snapshot_creation(self):
        """Test creating a memory snapshot."""
        snapshot = MemorySnapshot(
            timestamp=time.time(),
            rss_mb=100.5,
            vms_mb=200.0,
            percent=50.0,
            available_mb=1000.0,
            objects_count=10000,
            gc_stats={'generation_0': 100, 'generation_1': 50, 'generation_2': 10}
        )
        
        assert snapshot.rss_mb == 100.5
        assert snapshot.vms_mb == 200.0
        assert snapshot.percent == 50.0
        assert snapshot.available_mb == 1000.0
        assert snapshot.objects_count == 10000
        assert 'generation_0' in snapshot.gc_stats


class TestOperationMetrics:
    """Test OperationMetrics dataclass."""

    def test_operation_metrics_creation(self):
        """Test creating operation metrics."""
        before_snapshot = MemorySnapshot(
            timestamp=time.time(),
            rss_mb=100.0,
            vms_mb=200.0,
            percent=50.0,
            available_mb=1000.0,
            objects_count=10000,
            gc_stats={}
        )
        
        after_snapshot = MemorySnapshot(
            timestamp=time.time() + 1,
            rss_mb=110.0,
            vms_mb=210.0,
            percent=52.0,
            available_mb=990.0,
            objects_count=10100,
            gc_stats={}
        )
        
        metrics = OperationMetrics(
            operation_name="test_operation",
            start_time=time.time(),
            end_time=time.time() + 1,
            duration=1.0,
            memory_before=before_snapshot,
            memory_after=after_snapshot,
            memory_delta=10.0,
            cpu_percent=25.0,
            success=True,
            metadata={'test': 'data'}
        )
        
        assert metrics.operation_name == "test_operation"
        assert metrics.duration == 1.0
        assert metrics.memory_delta == 10.0
        assert metrics.cpu_percent == 25.0
        assert metrics.success is True
        assert metrics.metadata['test'] == 'data'


class TestPerformanceMonitor:
    """Test PerformanceMonitor class."""

    def setUp(self):
        """Set up test fixtures."""
        self.monitor = PerformanceMonitor(enabled=True)

    def test_monitor_initialization(self):
        """Test monitor initialization."""
        monitor = PerformanceMonitor(enabled=True)
        assert monitor.enabled is True
        assert len(monitor.operations) == 0
        assert monitor.system_info is not None
        assert 'python_version' in monitor.system_info

    def test_monitor_disabled(self):
        """Test monitor when disabled."""
        monitor = PerformanceMonitor(enabled=False)
        snapshot = monitor.take_memory_snapshot()
        
        # Should return empty snapshot when disabled
        assert snapshot.rss_mb == 0
        assert snapshot.vms_mb == 0
        assert snapshot.objects_count == 0

    @patch('psutil.Process')
    @patch('psutil.virtual_memory')
    def test_take_memory_snapshot(self, mock_virtual_memory, mock_process):
        """Test taking memory snapshot."""
        # Mock psutil objects
        mock_memory_info = MagicMock()
        mock_memory_info.rss = 100 * 1024 * 1024  # 100MB
        mock_memory_info.vms = 200 * 1024 * 1024  # 200MB
        
        mock_process_instance = MagicMock()
        mock_process_instance.memory_info.return_value = mock_memory_info
        mock_process.return_value = mock_process_instance
        
        mock_system_memory = MagicMock()
        mock_system_memory.percent = 60.0
        mock_system_memory.available = 1000 * 1024 * 1024  # 1000MB
        mock_virtual_memory.return_value = mock_system_memory
        
        monitor = PerformanceMonitor(enabled=True)
        snapshot = monitor.take_memory_snapshot()
        
        assert snapshot.rss_mb == 100.0
        assert snapshot.vms_mb == 200.0
        assert snapshot.percent == 60.0
        assert snapshot.available_mb == 1000.0
        assert snapshot.objects_count > 0

    def test_measure_operation_context_manager(self):
        """Test measuring operation with context manager."""
        monitor = PerformanceMonitor(enabled=True)
        
        with monitor.measure_operation("test_operation", {"test": "metadata"}):
            time.sleep(0.01)  # Small sleep to ensure duration > 0
        
        assert len(monitor.operations) == 1
        operation = monitor.operations[0]
        assert operation.operation_name == "test_operation"
        assert operation.duration > 0
        assert operation.success is True
        assert operation.metadata['test'] == "metadata"

    def test_measure_operation_with_exception(self):
        """Test measuring operation that raises exception."""
        monitor = PerformanceMonitor(enabled=True)
        
        with pytest.raises(ValueError):
            with monitor.measure_operation("failing_operation"):
                raise ValueError("Test error")
        
        assert len(monitor.operations) == 1
        operation = monitor.operations[0]
        assert operation.operation_name == "failing_operation"
        assert operation.success is False
        assert operation.error_message == "Test error"

    def test_get_peak_memory(self):
        """Test getting peak memory usage."""
        monitor = PerformanceMonitor(enabled=True)
        
        # Add some mock operations
        monitor.operations = [
            MagicMock(memory_before=MagicMock(rss_mb=100.0), memory_after=MagicMock(rss_mb=110.0)),
            MagicMock(memory_before=MagicMock(rss_mb=120.0), memory_after=MagicMock(rss_mb=125.0)),
            MagicMock(memory_before=MagicMock(rss_mb=90.0), memory_after=MagicMock(rss_mb=95.0)),
        ]
        
        peak = monitor.get_peak_memory()
        assert peak == 125.0

    def test_get_total_memory_delta(self):
        """Test getting total memory delta."""
        monitor = PerformanceMonitor(enabled=True)
        
        # Add some mock operations
        monitor.operations = [
            MagicMock(memory_delta=10.0),
            MagicMock(memory_delta=-5.0),
            MagicMock(memory_delta=15.0),
        ]
        
        total_delta = monitor.get_total_memory_delta()
        assert total_delta == 20.0

    def test_get_average_cpu(self):
        """Test getting average CPU usage."""
        monitor = PerformanceMonitor(enabled=True)
        
        # Add some mock operations
        monitor.operations = [
            MagicMock(cpu_percent=25.0),
            MagicMock(cpu_percent=35.0),
            MagicMock(cpu_percent=30.0),
        ]
        
        avg_cpu = monitor.get_average_cpu()
        assert avg_cpu == 30.0

    def test_get_slowest_operations(self):
        """Test getting slowest operations."""
        monitor = PerformanceMonitor(enabled=True)
        
        # Add some mock operations
        op1 = MagicMock(duration=1.0, operation_name="fast")
        op2 = MagicMock(duration=3.0, operation_name="slow")
        op3 = MagicMock(duration=2.0, operation_name="medium")
        
        monitor.operations = [op1, op2, op3]
        
        slowest = monitor.get_slowest_operations(2)
        assert len(slowest) == 2
        assert slowest[0].operation_name == "slow"
        assert slowest[1].operation_name == "medium"

    def test_get_memory_intensive_operations(self):
        """Test getting memory intensive operations."""
        monitor = PerformanceMonitor(enabled=True)
        
        # Add some mock operations
        op1 = MagicMock(memory_delta=5.0, operation_name="small")
        op2 = MagicMock(memory_delta=-20.0, operation_name="negative")
        op3 = MagicMock(memory_delta=15.0, operation_name="medium")
        
        monitor.operations = [op1, op2, op3]
        
        intensive = monitor.get_memory_intensive_operations(2)
        assert len(intensive) == 2
        # Should be sorted by absolute memory delta
        assert abs(intensive[0].memory_delta) >= abs(intensive[1].memory_delta)

    def test_generate_report(self):
        """Test generating performance report."""
        monitor = PerformanceMonitor(enabled=True)
        
        # Add a mock operation
        monitor.operations = [
            MagicMock(duration=1.0, memory_delta=10.0, cpu_percent=25.0)
        ]
        
        report = monitor.generate_report()
        
        assert isinstance(report, PerformanceReport)
        assert report.report_id.startswith("perf_")
        assert report.total_duration > 0
        assert len(report.operations) == 1
        assert report.system_info is not None

    def test_reset(self):
        """Test resetting monitor data."""
        monitor = PerformanceMonitor(enabled=True)
        
        # Add some data
        monitor.operations = [MagicMock()]
        
        monitor.reset()
        
        assert len(monitor.operations) == 0
        assert monitor.start_time > 0

    def test_log_summary(self):
        """Test logging performance summary."""
        monitor = PerformanceMonitor(enabled=True)
        
        # Add some mock operations
        monitor.operations = [
            MagicMock(duration=1.0, operation_name="test1"),
            MagicMock(duration=2.0, operation_name="test2"),
        ]
        
        with patch('create_project.utils.performance.logger') as mock_logger:
            monitor.log_summary()
            
            # Should have logged several info messages
            assert mock_logger.info.call_count >= 2


class TestGlobalFunctions:
    """Test global performance monitoring functions."""

    def test_get_monitor(self):
        """Test getting global monitor."""
        monitor = get_monitor()
        assert isinstance(monitor, PerformanceMonitor)
        
        # Should return same instance on subsequent calls
        monitor2 = get_monitor()
        assert monitor is monitor2

    def test_enable_disable_monitoring(self):
        """Test enabling and disabling monitoring."""
        monitor = get_monitor()
        
        enable_monitoring()
        assert monitor.enabled is True
        
        disable_monitoring()
        assert monitor.enabled is False

    def test_measure_operation_decorator(self):
        """Test measure_operation as decorator/context manager."""
        reset_monitoring()  # Clear any existing data
        
        with measure_operation("test_global_operation", {"key": "value"}):
            time.sleep(0.01)
        
        monitor = get_monitor()
        assert len(monitor.operations) == 1
        operation = monitor.operations[0]
        assert operation.operation_name == "test_global_operation"
        assert operation.metadata["key"] == "value"

    def test_take_snapshot_global(self):
        """Test taking snapshot using global function."""
        snapshot = take_snapshot()
        assert isinstance(snapshot, MemorySnapshot)
        assert snapshot.rss_mb >= 0

    def test_log_performance_summary_global(self):
        """Test global performance summary logging."""
        reset_monitoring()
        
        # Add some operations
        with measure_operation("test_operation"):
            time.sleep(0.01)
        
        with patch('create_project.utils.performance.logger') as mock_logger:
            log_performance_summary()
            mock_logger.info.assert_called()

    def test_reset_monitoring_global(self):
        """Test global monitoring reset."""
        # Add some operations
        with measure_operation("test_operation"):
            pass
        
        monitor = get_monitor()
        assert len(monitor.operations) == 1
        
        reset_monitoring()
        assert len(monitor.operations) == 0


class TestPerformanceReport:
    """Test PerformanceReport dataclass."""

    def test_performance_report_creation(self):
        """Test creating performance report."""
        operations = [
            MagicMock(duration=1.0, operation_name="op1"),
            MagicMock(duration=2.0, operation_name="op2"),
        ]
        
        report = PerformanceReport(
            report_id="test_report",
            start_time=time.time(),
            end_time=time.time() + 10,
            total_duration=10.0,
            operations=operations,
            peak_memory_mb=150.0,
            total_memory_delta=25.0,
            avg_cpu_percent=35.0,
            gc_collections=5,
            system_info={'platform': 'test'}
        )
        
        assert report.report_id == "test_report"
        assert report.total_duration == 10.0
        assert len(report.operations) == 2
        assert report.peak_memory_mb == 150.0
        assert report.total_memory_delta == 25.0
        assert report.avg_cpu_percent == 35.0
        assert report.gc_collections == 5
        assert report.system_info['platform'] == 'test'


class TestIntegrationScenarios:
    """Test integration scenarios for performance monitoring."""

    def test_nested_operations(self):
        """Test measuring nested operations."""
        reset_monitoring()
        
        with measure_operation("outer_operation"):
            time.sleep(0.01)
            with measure_operation("inner_operation"):
                time.sleep(0.01)
        
        monitor = get_monitor()
        assert len(monitor.operations) == 2
        
        operation_names = [op.operation_name for op in monitor.operations]
        assert "outer_operation" in operation_names
        assert "inner_operation" in operation_names

    def test_concurrent_operations_simulation(self):
        """Test simulation of concurrent operations."""
        reset_monitoring()
        
        # Simulate multiple operations
        operations = []
        for i in range(5):
            with measure_operation(f"operation_{i}", {"index": i}):
                time.sleep(0.001)  # Very small sleep
        
        monitor = get_monitor()
        assert len(monitor.operations) == 5
        
        # Check all operations recorded
        for i in range(5):
            operation_found = any(
                op.operation_name == f"operation_{i}" and op.metadata.get("index") == i
                for op in monitor.operations
            )
            assert operation_found

    def test_memory_tracking_accuracy(self):
        """Test memory tracking accuracy."""
        reset_monitoring()
        
        # Take initial snapshot
        initial_snapshot = take_snapshot()
        
        # Perform operation that should use memory
        with measure_operation("memory_test"):
            # Create some objects to use memory
            test_data = [i for i in range(10000)]
            test_dict = {i: str(i) for i in range(1000)}
        
        # Take final snapshot
        final_snapshot = take_snapshot()
        
        # Memory usage should have changed
        monitor = get_monitor()
        assert len(monitor.operations) == 1
        
        operation = monitor.operations[0]
        assert operation.operation_name == "memory_test"
        # Memory delta should be recorded (could be positive or negative due to GC)
        assert isinstance(operation.memory_delta, float)

    def test_error_handling_in_monitoring(self):
        """Test error handling during monitoring."""
        reset_monitoring()
        
        # Test with psutil errors
        with patch('psutil.Process') as mock_process:
            mock_process.side_effect = Exception("psutil error")
            
            monitor = PerformanceMonitor(enabled=True)
            snapshot = monitor.take_memory_snapshot()
            
            # Should handle error gracefully
            assert snapshot.rss_mb == 0
            assert 'error' in snapshot.gc_stats

    def test_performance_overhead(self):
        """Test that performance monitoring has minimal overhead."""
        reset_monitoring()
        
        # Test overhead of monitoring vs no monitoring
        iterations = 100
        
        # With monitoring disabled
        disable_monitoring()
        start_time = time.time()
        for i in range(iterations):
            with measure_operation("test_overhead"):
                pass
        disabled_duration = time.time() - start_time
        
        # With monitoring enabled
        enable_monitoring()
        start_time = time.time()
        for i in range(iterations):
            with measure_operation("test_overhead"):
                pass
        enabled_duration = time.time() - start_time
        
        # Monitoring should not add significant overhead
        # Allow up to 10x overhead (very generous for testing)
        assert enabled_duration < disabled_duration * 10