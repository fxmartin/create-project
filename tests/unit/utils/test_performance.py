# ABOUTME: Comprehensive unit tests for performance monitoring utilities
# ABOUTME: Tests memory snapshots, operation metrics, performance reports, and monitoring functionality

"""Unit tests for performance module."""

import gc
import os
import threading
import time
from unittest.mock import MagicMock, Mock, patch

import pytest

from create_project.utils.performance import (
    MemorySnapshot,
    OperationMetrics,
    PerformanceMonitor,
    PerformanceReport,
    disable_monitoring,
    enable_monitoring,
    get_monitor,
    log_performance_summary,
    measure_operation,
    reset_monitoring,
    take_snapshot,
)


class TestMemorySnapshot:
    """Test MemorySnapshot dataclass."""

    def test_memory_snapshot_creation(self):
        """Test creating MemorySnapshot instance."""
        timestamp = time.time()
        gc_stats = {"generation_0": 100, "generation_1": 50, "generation_2": 10}
        
        snapshot = MemorySnapshot(
            timestamp=timestamp,
            rss_mb=128.5,
            vms_mb=256.7,
            percent=45.2,
            available_mb=1024.0,
            objects_count=50000,
            gc_stats=gc_stats
        )
        
        assert snapshot.timestamp == timestamp
        assert snapshot.rss_mb == 128.5
        assert snapshot.vms_mb == 256.7
        assert snapshot.percent == 45.2
        assert snapshot.available_mb == 1024.0
        assert snapshot.objects_count == 50000
        assert snapshot.gc_stats == gc_stats

    def test_memory_snapshot_default_values(self):
        """Test MemorySnapshot with minimal values."""
        snapshot = MemorySnapshot(
            timestamp=0.0,
            rss_mb=0.0,
            vms_mb=0.0,
            percent=0.0,
            available_mb=0.0,
            objects_count=0,
            gc_stats={}
        )
        
        assert snapshot.timestamp == 0.0
        assert snapshot.rss_mb == 0.0
        assert snapshot.objects_count == 0
        assert snapshot.gc_stats == {}


class TestOperationMetrics:
    """Test OperationMetrics dataclass."""

    @pytest.fixture
    def sample_memory_snapshots(self):
        """Create sample memory snapshots for testing."""
        before = MemorySnapshot(
            timestamp=1000.0,
            rss_mb=100.0,
            vms_mb=200.0,
            percent=40.0,
            available_mb=500.0,
            objects_count=10000,
            gc_stats={"generation_0": 50}
        )
        
        after = MemorySnapshot(
            timestamp=1005.0,
            rss_mb=120.0,
            vms_mb=220.0,
            percent=42.0,
            available_mb=480.0,
            objects_count=11000,
            gc_stats={"generation_0": 55}
        )
        
        return before, after

    def test_operation_metrics_creation(self, sample_memory_snapshots):
        """Test creating OperationMetrics instance."""
        before, after = sample_memory_snapshots
        
        metrics = OperationMetrics(
            operation_name="test_operation",
            start_time=1000.0,
            end_time=1005.0,
            duration=5.0,
            memory_before=before,
            memory_after=after,
            memory_delta=20.0,
            cpu_percent=15.5,
            success=True,
            error_message=None,
            metadata={"file_count": 10}
        )
        
        assert metrics.operation_name == "test_operation"
        assert metrics.start_time == 1000.0
        assert metrics.end_time == 1005.0
        assert metrics.duration == 5.0
        assert metrics.memory_before == before
        assert metrics.memory_after == after
        assert metrics.memory_delta == 20.0
        assert metrics.cpu_percent == 15.5
        assert metrics.success is True
        assert metrics.error_message is None
        assert metrics.metadata == {"file_count": 10}

    def test_operation_metrics_with_error(self, sample_memory_snapshots):
        """Test OperationMetrics with error information."""
        before, after = sample_memory_snapshots
        
        metrics = OperationMetrics(
            operation_name="failed_operation",
            start_time=1000.0,
            end_time=1002.0,
            duration=2.0,
            memory_before=before,
            memory_after=after,
            memory_delta=5.0,
            cpu_percent=8.0,
            success=False,
            error_message="Operation failed due to invalid input"
        )
        
        assert metrics.success is False
        assert metrics.error_message == "Operation failed due to invalid input"

    def test_operation_metrics_default_values(self, sample_memory_snapshots):
        """Test OperationMetrics with default values."""
        before, after = sample_memory_snapshots
        
        metrics = OperationMetrics(
            operation_name="default_test",
            start_time=1000.0,
            end_time=1001.0,
            duration=1.0,
            memory_before=before,
            memory_after=after,
            memory_delta=0.0,
            cpu_percent=5.0
        )
        
        # Default values
        assert metrics.success is True
        assert metrics.error_message is None
        assert metrics.metadata == {}


class TestPerformanceReport:
    """Test PerformanceReport dataclass."""

    def test_performance_report_creation(self):
        """Test creating PerformanceReport instance."""
        operations = [Mock(spec=OperationMetrics)]
        system_info = {"platform": "test", "cpu_count": 4}
        
        report = PerformanceReport(
            report_id="test_report_123",
            start_time=1000.0,
            end_time=1100.0,
            total_duration=100.0,
            operations=operations,
            peak_memory_mb=256.0,
            total_memory_delta=10.5,
            avg_cpu_percent=25.3,
            gc_collections=150,
            system_info=system_info
        )
        
        assert report.report_id == "test_report_123"
        assert report.start_time == 1000.0
        assert report.end_time == 1100.0
        assert report.total_duration == 100.0
        assert report.operations == operations
        assert report.peak_memory_mb == 256.0
        assert report.total_memory_delta == 10.5
        assert report.avg_cpu_percent == 25.3
        assert report.gc_collections == 150
        assert report.system_info == system_info


class TestPerformanceMonitor:
    """Test PerformanceMonitor class."""

    @pytest.fixture
    def mock_psutil(self):
        """Mock psutil for testing."""
        with patch('create_project.utils.performance.psutil') as mock_psutil:
            # Mock process
            mock_process = Mock()
            mock_process.memory_info.return_value = Mock(rss=128 * 1024 * 1024, vms=256 * 1024 * 1024)
            mock_process.cpu_percent.return_value = 15.5
            mock_psutil.Process.return_value = mock_process
            
            # Mock system memory
            mock_memory = Mock()
            mock_memory.total = 8 * 1024 * 1024 * 1024  # 8GB
            mock_memory.available = 4 * 1024 * 1024 * 1024  # 4GB
            mock_memory.percent = 50.0
            mock_psutil.virtual_memory.return_value = mock_memory
            
            # Mock CPU info
            mock_psutil.cpu_count.return_value = 4
            mock_cpu_freq = Mock()
            mock_cpu_freq._asdict.return_value = {"current": 2400, "min": 1200, "max": 3600}
            mock_psutil.cpu_freq.return_value = mock_cpu_freq
            
            yield mock_psutil

    @pytest.fixture
    def monitor(self, mock_psutil):
        """Create performance monitor for testing."""
        return PerformanceMonitor(enabled=True)

    def test_initialization_enabled(self, mock_psutil):
        """Test PerformanceMonitor initialization when enabled."""
        monitor = PerformanceMonitor(enabled=True)
        
        assert monitor.enabled is True
        assert monitor.operations == []
        assert isinstance(monitor.start_time, float)
        assert isinstance(monitor._lock, type(threading.Lock()))
        assert monitor.process is not None
        assert isinstance(monitor.system_info, dict)

    def test_initialization_disabled(self, mock_psutil):
        """Test PerformanceMonitor initialization when disabled."""
        monitor = PerformanceMonitor(enabled=False)
        
        assert monitor.enabled is False
        assert monitor.operations == []

    def test_initialization_psutil_error(self):
        """Test PerformanceMonitor initialization with psutil error."""
        with patch('create_project.utils.performance.psutil.Process', side_effect=Exception("Process error")):
            with patch('create_project.utils.performance.logger') as mock_logger:
                monitor = PerformanceMonitor()
                
                assert monitor.process is None
                mock_logger.warning.assert_called_once()

    def test_get_system_info_success(self, mock_psutil):
        """Test _get_system_info with successful system calls."""
        monitor = PerformanceMonitor()
        
        system_info = monitor.system_info
        
        assert "platform" in system_info
        assert "python_version" in system_info
        assert "total_memory_mb" in system_info
        assert "available_memory_mb" in system_info
        assert "cpu_info" in system_info
        assert "process_id" in system_info
        
        assert system_info["cpu_info"]["cpu_count"] == 4
        assert system_info["total_memory_mb"] == 8192.0  # 8GB in MB

    def test_get_system_info_error(self):
        """Test _get_system_info with system call errors."""
        with patch('create_project.utils.performance.psutil.virtual_memory', side_effect=Exception("Memory error")):
            with patch('create_project.utils.performance.logger') as mock_logger:
                monitor = PerformanceMonitor()
                
                assert "error" in monitor.system_info
                mock_logger.warning.assert_called()

    def test_take_memory_snapshot_enabled(self, monitor, mock_psutil):
        """Test take_memory_snapshot when monitoring is enabled."""
        with patch('create_project.utils.performance.gc.get_objects', return_value=[Mock()] * 1000):
            with patch('create_project.utils.performance.gc.get_count', return_value=[50, 25, 10]):
                snapshot = monitor.take_memory_snapshot()
                
                assert isinstance(snapshot, MemorySnapshot)
                assert snapshot.rss_mb == 128.0  # 128MB
                assert snapshot.vms_mb == 256.0  # 256MB
                assert snapshot.objects_count == 1000
                assert snapshot.gc_stats == {"generation_0": 50, "generation_1": 25, "generation_2": 10}

    def test_take_memory_snapshot_disabled(self):
        """Test take_memory_snapshot when monitoring is disabled."""
        monitor = PerformanceMonitor(enabled=False)
        snapshot = monitor.take_memory_snapshot()
        
        assert isinstance(snapshot, MemorySnapshot)
        assert snapshot.rss_mb == 0
        assert snapshot.vms_mb == 0
        assert snapshot.objects_count == 0
        assert snapshot.gc_stats == {}

    def test_take_memory_snapshot_no_process(self, mock_psutil):
        """Test take_memory_snapshot when process is None."""
        monitor = PerformanceMonitor(enabled=True)
        monitor.process = None
        
        snapshot = monitor.take_memory_snapshot()
        
        assert isinstance(snapshot, MemorySnapshot)
        assert snapshot.rss_mb == 0
        assert snapshot.vms_mb == 0

    def test_take_memory_snapshot_error(self, monitor, mock_psutil):
        """Test take_memory_snapshot with system call error."""
        monitor.process.memory_info.side_effect = Exception("Memory info error")
        
        with patch('create_project.utils.performance.logger') as mock_logger:
            snapshot = monitor.take_memory_snapshot()
            
            assert isinstance(snapshot, MemorySnapshot)
            assert snapshot.rss_mb == 0
            assert "error" in snapshot.gc_stats
            mock_logger.error.assert_called_once()

    def test_measure_operation_success(self, monitor, mock_psutil):
        """Test measure_operation context manager with successful operation."""
        with patch.object(monitor, 'take_memory_snapshot') as mock_snapshot:
            # Mock memory snapshots
            before_snapshot = Mock(spec=MemorySnapshot)
            before_snapshot.rss_mb = 100.0
            after_snapshot = Mock(spec=MemorySnapshot)
            after_snapshot.rss_mb = 110.0
            
            mock_snapshot.side_effect = [before_snapshot, after_snapshot]
            
            # Mock CPU percentage
            monitor.process.cpu_percent.side_effect = [10.0, 20.0]
            
            with monitor.measure_operation("test_op", {"key": "value"}):
                time.sleep(0.01)  # Small delay to ensure duration > 0
            
            assert len(monitor.operations) == 1
            op = monitor.operations[0]
            assert op.operation_name == "test_op"
            assert op.success is True
            assert op.error_message is None
            assert op.memory_delta == 10.0
            assert op.cpu_percent == 15.0  # Average of 10 and 20
            assert op.metadata == {"key": "value"}

    def test_measure_operation_error(self, monitor, mock_psutil):
        """Test measure_operation context manager with operation error."""
        with patch.object(monitor, 'take_memory_snapshot') as mock_snapshot:
            mock_snapshot.return_value = Mock(spec=MemorySnapshot, rss_mb=100.0)
            monitor.process.cpu_percent.return_value = 10.0
            
            with pytest.raises(ValueError, match="Test error"):
                with monitor.measure_operation("failing_op"):
                    raise ValueError("Test error")
            
            assert len(monitor.operations) == 1
            op = monitor.operations[0]
            assert op.operation_name == "failing_op"
            assert op.success is False
            assert op.error_message == "Test error"

    def test_measure_operation_disabled(self):
        """Test measure_operation when monitoring is disabled."""
        monitor = PerformanceMonitor(enabled=False)
        
        with monitor.measure_operation("disabled_op"):
            pass
        
        assert len(monitor.operations) == 0

    def test_measure_operation_threading(self, monitor, mock_psutil):
        """Test measure_operation is thread-safe."""
        with patch.object(monitor, 'take_memory_snapshot') as mock_snapshot:
            mock_snapshot.return_value = Mock(spec=MemorySnapshot, rss_mb=100.0)
            monitor.process.cpu_percent.return_value = 10.0
            
            def operation(op_name):
                with monitor.measure_operation(op_name):
                    time.sleep(0.01)
            
            # Run operations in multiple threads
            threads = []
            for i in range(3):
                thread = threading.Thread(target=operation, args=(f"thread_op_{i}",))
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join()
            
            assert len(monitor.operations) == 3
            operation_names = [op.operation_name for op in monitor.operations]
            assert "thread_op_0" in operation_names
            assert "thread_op_1" in operation_names
            assert "thread_op_2" in operation_names

    def test_get_peak_memory_no_operations(self, monitor):
        """Test get_peak_memory with no operations."""
        assert monitor.get_peak_memory() == 0.0

    def test_get_peak_memory_with_operations(self, monitor):
        """Test get_peak_memory with operations."""
        # Create mock operations with different memory usage
        op1 = Mock(spec=OperationMetrics)
        op1.memory_before = Mock(rss_mb=100.0)
        op1.memory_after = Mock(rss_mb=120.0)
        
        op2 = Mock(spec=OperationMetrics)
        op2.memory_before = Mock(rss_mb=150.0)
        op2.memory_after = Mock(rss_mb=130.0)
        
        monitor.operations = [op1, op2]
        
        peak = monitor.get_peak_memory()
        assert peak == 150.0  # Highest value from before/after

    def test_get_total_memory_delta_no_operations(self, monitor):
        """Test get_total_memory_delta with no operations."""
        assert monitor.get_total_memory_delta() == 0.0

    def test_get_total_memory_delta_with_operations(self, monitor):
        """Test get_total_memory_delta with operations."""
        op1 = Mock(spec=OperationMetrics, memory_delta=10.0)
        op2 = Mock(spec=OperationMetrics, memory_delta=-5.0)
        op3 = Mock(spec=OperationMetrics, memory_delta=15.0)
        
        monitor.operations = [op1, op2, op3]
        
        total_delta = monitor.get_total_memory_delta()
        assert total_delta == 20.0  # 10 - 5 + 15

    def test_get_average_cpu_no_operations(self, monitor):
        """Test get_average_cpu with no operations."""
        assert monitor.get_average_cpu() == 0.0

    def test_get_average_cpu_with_operations(self, monitor):
        """Test get_average_cpu with operations."""
        op1 = Mock(spec=OperationMetrics, cpu_percent=10.0)
        op2 = Mock(spec=OperationMetrics, cpu_percent=20.0)
        op3 = Mock(spec=OperationMetrics, cpu_percent=30.0)
        
        monitor.operations = [op1, op2, op3]
        
        avg_cpu = monitor.get_average_cpu()
        assert avg_cpu == 20.0  # (10 + 20 + 30) / 3

    def test_get_slowest_operations(self, monitor):
        """Test get_slowest_operations."""
        op1 = Mock(spec=OperationMetrics, duration=1.0, operation_name="fast")
        op2 = Mock(spec=OperationMetrics, duration=5.0, operation_name="slow")
        op3 = Mock(spec=OperationMetrics, duration=3.0, operation_name="medium")
        
        monitor.operations = [op1, op2, op3]
        
        slowest = monitor.get_slowest_operations(2)
        assert len(slowest) == 2
        assert slowest[0].operation_name == "slow"
        assert slowest[1].operation_name == "medium"

    def test_get_memory_intensive_operations(self, monitor):
        """Test get_memory_intensive_operations."""
        op1 = Mock(spec=OperationMetrics, memory_delta=2.0, operation_name="small")
        op2 = Mock(spec=OperationMetrics, memory_delta=-10.0, operation_name="negative")
        op3 = Mock(spec=OperationMetrics, memory_delta=5.0, operation_name="medium")
        
        monitor.operations = [op1, op2, op3]
        
        intensive = monitor.get_memory_intensive_operations(2)
        assert len(intensive) == 2
        assert intensive[0].operation_name == "negative"  # abs(-10) = 10
        assert intensive[1].operation_name == "medium"   # abs(5) = 5

    def test_generate_report(self, monitor):
        """Test generate_report."""
        # Set up monitor with some operations
        op1 = Mock(spec=OperationMetrics)
        monitor.operations = [op1]
        
        with patch.object(monitor, 'get_peak_memory', return_value=200.0):
            with patch.object(monitor, 'get_total_memory_delta', return_value=15.0):
                with patch.object(monitor, 'get_average_cpu', return_value=25.0):
                    with patch('create_project.utils.performance.gc.get_count', return_value=[10, 5, 2]):
                        report = monitor.generate_report()
        
        assert isinstance(report, PerformanceReport)
        assert report.report_id.startswith("perf_")
        assert report.operations == [op1]
        assert report.peak_memory_mb == 200.0
        assert report.total_memory_delta == 15.0
        assert report.avg_cpu_percent == 25.0
        assert report.gc_collections == 17  # 10 + 5 + 2

    def test_reset(self, monitor):
        """Test reset functionality."""
        # Add some operations
        monitor.operations = [Mock(spec=OperationMetrics)]
        original_start_time = monitor.start_time
        
        time.sleep(0.01)  # Ensure time difference
        monitor.reset()
        
        assert len(monitor.operations) == 0
        assert monitor.start_time > original_start_time

    def test_log_summary_disabled(self, monitor):
        """Test log_summary when monitoring is disabled."""
        monitor.enabled = False
        
        with patch('create_project.utils.performance.logger') as mock_logger:
            monitor.log_summary()
            mock_logger.info.assert_not_called()

    def test_log_summary_no_operations(self, monitor):
        """Test log_summary with no operations."""
        with patch('create_project.utils.performance.logger') as mock_logger:
            monitor.log_summary()
            mock_logger.info.assert_not_called()

    def test_log_summary_with_operations(self, monitor):
        """Test log_summary with operations."""
        # Create mock operations
        op1 = Mock(spec=OperationMetrics)
        op1.operation_name = "operation_1"
        op1.duration = 2.5
        
        op2 = Mock(spec=OperationMetrics)
        op2.operation_name = "operation_2"
        op2.duration = 1.0
        
        monitor.operations = [op1, op2]
        
        with patch.object(monitor, 'generate_report') as mock_generate:
            mock_report = Mock(spec=PerformanceReport)
            mock_report.operations = [op1, op2]
            mock_report.total_duration = 10.0
            mock_report.peak_memory_mb = 150.0
            mock_report.total_memory_delta = 5.0
            mock_report.avg_cpu_percent = 20.0
            mock_generate.return_value = mock_report
            
            with patch.object(monitor, 'get_slowest_operations', return_value=[op1]):
                with patch('create_project.utils.performance.logger') as mock_logger:
                    monitor.log_summary()
                    
                    # Check that summary information was logged
                    mock_logger.info.assert_called()
                    call_args = [call[0][0] for call in mock_logger.info.call_args_list]
                    
                    # Check for specific log content
                    summary_logs = [log for log in call_args if "Performance Summary" in log]
                    assert len(summary_logs) == 1
                    
                    operation_logs = [log for log in call_args if "Total operations: 2" in log]
                    assert len(operation_logs) == 1


class TestGlobalFunctions:
    """Test global performance monitoring functions."""

    def test_get_monitor_singleton(self):
        """Test that get_monitor returns singleton instance."""
        # Clear global monitor first
        import create_project.utils.performance as perf_module
        perf_module._global_monitor = None
        
        monitor1 = get_monitor()
        monitor2 = get_monitor()
        
        assert monitor1 is monitor2
        assert isinstance(monitor1, PerformanceMonitor)

    def test_enable_monitoring(self):
        """Test enable_monitoring function."""
        with patch('create_project.utils.performance.get_monitor') as mock_get:
            mock_monitor = Mock()
            mock_get.return_value = mock_monitor
            
            with patch('create_project.utils.performance.logger') as mock_logger:
                enable_monitoring()
                
                assert mock_monitor.enabled is True
                mock_logger.info.assert_called_with("Performance monitoring enabled")

    def test_disable_monitoring(self):
        """Test disable_monitoring function."""
        with patch('create_project.utils.performance.get_monitor') as mock_get:
            mock_monitor = Mock()
            mock_get.return_value = mock_monitor
            
            with patch('create_project.utils.performance.logger') as mock_logger:
                disable_monitoring()
                
                assert mock_monitor.enabled is False
                mock_logger.info.assert_called_with("Performance monitoring disabled")

    def test_measure_operation_function(self):
        """Test measure_operation function (context manager)."""
        with patch('create_project.utils.performance.get_monitor') as mock_get:
            mock_monitor = Mock()
            mock_context = Mock()
            mock_monitor.measure_operation.return_value = mock_context
            mock_get.return_value = mock_monitor
            
            result = measure_operation("test_op", {"meta": "data"})
            
            assert result is mock_context
            mock_monitor.measure_operation.assert_called_once_with("test_op", {"meta": "data"})

    def test_take_snapshot_function(self):
        """Test take_snapshot function."""
        with patch('create_project.utils.performance.get_monitor') as mock_get:
            mock_monitor = Mock()
            mock_snapshot = Mock(spec=MemorySnapshot)
            mock_monitor.take_memory_snapshot.return_value = mock_snapshot
            mock_get.return_value = mock_monitor
            
            result = take_snapshot()
            
            assert result is mock_snapshot
            mock_monitor.take_memory_snapshot.assert_called_once()

    def test_log_performance_summary_function(self):
        """Test log_performance_summary function."""
        with patch('create_project.utils.performance.get_monitor') as mock_get:
            mock_monitor = Mock()
            mock_get.return_value = mock_monitor
            
            log_performance_summary()
            
            mock_monitor.log_summary.assert_called_once()

    def test_reset_monitoring_function(self):
        """Test reset_monitoring function."""
        with patch('create_project.utils.performance.get_monitor') as mock_get:
            mock_monitor = Mock()
            mock_get.return_value = mock_monitor
            
            reset_monitoring()
            
            mock_monitor.reset.assert_called_once()


class TestIntegrationScenarios:
    """Test integration scenarios and real-world usage."""

    def test_decorator_usage_simulation(self):
        """Test using measure_operation as a decorator simulation."""
        with patch('create_project.utils.performance.get_monitor') as mock_get:
            mock_monitor = Mock()
            mock_context = Mock()
            mock_monitor.measure_operation.return_value = mock_context
            mock_get.return_value = mock_monitor
            
            # Simulate decorator usage
            context_manager = measure_operation("simulated_function")
            
            assert context_manager is mock_context
            mock_monitor.measure_operation.assert_called_once_with("simulated_function", None)

    def test_performance_monitoring_workflow(self):
        """Test complete performance monitoring workflow."""
        # Clear global monitor
        import create_project.utils.performance as perf_module
        perf_module._global_monitor = None
        
        # Enable monitoring
        enable_monitoring()
        monitor = get_monitor()
        assert monitor.enabled is True
        
        # Perform some operations
        with measure_operation("workflow_step_1", {"step": 1}):
            time.sleep(0.01)
        
        with measure_operation("workflow_step_2", {"step": 2}):
            time.sleep(0.01)
        
        # Check that operations were recorded
        assert len(monitor.operations) == 2
        assert monitor.operations[0].operation_name == "workflow_step_1"
        assert monitor.operations[1].operation_name == "workflow_step_2"
        
        # Take snapshot
        snapshot = take_snapshot()
        assert isinstance(snapshot, MemorySnapshot)
        
        # Reset monitoring
        reset_monitoring()
        assert len(monitor.operations) == 0

    def test_concurrent_performance_monitoring(self):
        """Test performance monitoring under concurrent usage."""
        # Clear global monitor
        import create_project.utils.performance as perf_module
        perf_module._global_monitor = None
        
        enable_monitoring()
        
        def concurrent_operation(op_id):
            with measure_operation(f"concurrent_op_{op_id}"):
                time.sleep(0.01)
        
        # Run operations concurrently
        threads = []
        for i in range(5):
            thread = threading.Thread(target=concurrent_operation, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        monitor = get_monitor()
        assert len(monitor.operations) == 5
        
        # Check that all operations were recorded
        operation_names = {op.operation_name for op in monitor.operations}
        expected_names = {f"concurrent_op_{i}" for i in range(5)}
        assert operation_names == expected_names

    @patch('create_project.utils.performance.psutil')
    def test_memory_snapshot_consistency(self, mock_psutil):
        """Test memory snapshot consistency across operations."""
        # Set up proper mock
        mock_process = Mock()
        mock_process.cpu_percent.return_value = 15.0
        mock_process.memory_info.return_value = Mock(rss=128 * 1024 * 1024, vms=256 * 1024 * 1024)
        mock_psutil.Process.return_value = mock_process
        
        # Mock system memory
        mock_memory = Mock()
        mock_memory.total = 8 * 1024 * 1024 * 1024
        mock_memory.available = 4 * 1024 * 1024 * 1024
        mock_memory.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_memory
        
        monitor = PerformanceMonitor()
        
        # Take multiple snapshots
        snapshots = []
        for i in range(3):
            snapshot = monitor.take_memory_snapshot()
            snapshots.append(snapshot)
            time.sleep(0.01)
        
        # Check that timestamps are increasing
        for i in range(1, len(snapshots)):
            assert snapshots[i].timestamp > snapshots[i-1].timestamp
        
        # Check that snapshots have consistent structure
        for snapshot in snapshots:
            assert isinstance(snapshot.rss_mb, float)
            assert isinstance(snapshot.vms_mb, float)
            assert isinstance(snapshot.objects_count, int)
            assert isinstance(snapshot.gc_stats, dict)

    @patch('create_project.utils.performance.psutil')
    def test_performance_report_generation(self, mock_psutil):
        """Test performance report generation with real data."""
        # Set up proper mock
        mock_process = Mock()
        mock_process.cpu_percent.return_value = 15.5
        mock_psutil.Process.return_value = mock_process
        
        monitor = PerformanceMonitor()
        
        # Simulate operations
        with monitor.measure_operation("report_test_1"):
            pass
        
        with monitor.measure_operation("report_test_2"):
            pass
        
        # Generate report
        report = monitor.generate_report()
        
        assert isinstance(report, PerformanceReport)
        assert len(report.operations) == 2
        assert report.report_id.startswith("perf_")
        assert report.total_duration > 0
        assert isinstance(report.system_info, dict)
        assert "platform" in report.system_info

    @patch('create_project.utils.performance.psutil')
    def test_error_handling_in_monitoring(self, mock_psutil):
        """Test error handling during performance monitoring."""
        # Set up proper mock
        mock_process = Mock()
        mock_process.cpu_percent.return_value = 10.0
        mock_psutil.Process.return_value = mock_process
        
        monitor = PerformanceMonitor()
        
        # Test operation that raises exception
        with pytest.raises(ValueError):
            with monitor.measure_operation("error_operation"):
                raise ValueError("Intentional test error")
        
        # Check that operation was still recorded
        assert len(monitor.operations) == 1
        op = monitor.operations[0]
        assert op.operation_name == "error_operation"
        assert op.success is False
        assert "Intentional test error" in op.error_message

    @patch('create_project.utils.performance.psutil')
    def test_monitoring_with_metadata(self, mock_psutil):
        """Test performance monitoring with operation metadata."""
        # Set up proper mock
        mock_process = Mock()
        mock_process.cpu_percent.return_value = 12.5
        mock_psutil.Process.return_value = mock_process
        
        monitor = PerformanceMonitor()
        
        metadata = {
            "file_count": 100,
            "total_size_mb": 250.5,
            "operation_type": "file_processing"
        }
        
        with monitor.measure_operation("metadata_test", metadata):
            pass
        
        assert len(monitor.operations) == 1
        op = monitor.operations[0]
        assert op.metadata == metadata

    def test_performance_analysis_methods(self):
        """Test performance analysis methods with sample data."""
        monitor = PerformanceMonitor()
        
        # Create operations with different characteristics
        operations_data = [
            ("fast_op", 0.1, 5.0),
            ("slow_op", 2.0, 50.0),
            ("medium_op", 0.5, 20.0),
            ("memory_intensive", 0.3, 100.0),
        ]
        
        for op_name, duration, memory_delta in operations_data:
            op = Mock(spec=OperationMetrics)
            op.operation_name = op_name
            op.duration = duration
            op.memory_delta = memory_delta
            op.cpu_percent = 15.0
            op.memory_before = Mock(rss_mb=100.0)
            op.memory_after = Mock(rss_mb=100.0 + memory_delta)
            monitor.operations.append(op)
        
        # Test analysis methods
        slowest = monitor.get_slowest_operations(2)
        assert len(slowest) == 2
        assert slowest[0].operation_name == "slow_op"
        assert slowest[1].operation_name == "medium_op"
        
        memory_intensive = monitor.get_memory_intensive_operations(2)
        assert len(memory_intensive) == 2
        assert memory_intensive[0].operation_name == "memory_intensive"
        assert memory_intensive[1].operation_name == "slow_op"
        
        peak_memory = monitor.get_peak_memory()
        assert peak_memory == 200.0  # 100 + 100 (memory_intensive)
        
        total_delta = monitor.get_total_memory_delta()
        assert total_delta == 175.0  # Sum of all deltas
        
        avg_cpu = monitor.get_average_cpu()
        assert avg_cpu == 15.0  # All operations have 15.0% CPU