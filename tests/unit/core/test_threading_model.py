# ABOUTME: Unit tests for threading model module
# ABOUTME: Tests background operations, progress tracking, and cancellation

"""Unit tests for threading model module."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, call

import pytest

from create_project.core.threading_model import (
    ThreadingModel,
    BackgroundOperation,
    OperationStatus,
    ProgressUpdate,
    OperationResult,
)
from create_project.core.exceptions import ThreadingError
from create_project.templates.schema.template import Template


class TestBackgroundOperation:
    """Test BackgroundOperation class."""

    def test_init(self):
        """Test BackgroundOperation initialization."""
        def dummy_func():
            return "result"
        
        operation = BackgroundOperation(
            operation_id="test-123",
            operation_func=dummy_func,
            operation_args=(),
            operation_kwargs={},
            progress_callback=None,
        )
        
        assert operation.operation_id == "test-123"
        assert operation.status == OperationStatus.PENDING
        assert operation.result is None
        assert operation.error is None
        assert operation.cancellation_event.is_set() is False

    def test_start_success(self):
        """Test starting an operation successfully."""
        def dummy_func():
            return "result"
        
        operation = BackgroundOperation(
            operation_id="test-123",
            operation_func=dummy_func,
            operation_args=(),
            operation_kwargs={},
        )
        
        with ThreadPoolExecutor(max_workers=1) as executor:
            operation.start(executor)
            
            assert operation.status == OperationStatus.RUNNING
            assert operation.start_time is not None
            assert operation.future is not None

    def test_start_invalid_state(self):
        """Test starting an operation in invalid state."""
        def dummy_func():
            return "result"
        
        operation = BackgroundOperation(
            operation_id="test-123",
            operation_func=dummy_func,
            operation_args=(),
            operation_kwargs={},
        )
        
        # Set to non-pending state
        operation.status = OperationStatus.RUNNING
        
        with ThreadPoolExecutor(max_workers=1) as executor:
            with pytest.raises(ThreadingError) as exc_info:
                operation.start(executor)
            
            assert "Cannot start operation" in str(exc_info.value)

    def test_cancel_running_operation(self):
        """Test cancelling a running operation."""
        cancel_event = threading.Event()
        
        def long_running_func():
            # Wait for cancel or timeout
            cancel_event.wait(timeout=10)
            return "result"
        
        operation = BackgroundOperation(
            operation_id="test-123",
            operation_func=long_running_func,
            operation_args=(),
            operation_kwargs={},
        )
        
        with ThreadPoolExecutor(max_workers=1) as executor:
            operation.start(executor)
            
            # Give it time to start
            time.sleep(0.1)
            
            # Cancel the operation
            cancelled = operation.cancel()
            cancel_event.set()  # Release the function
            
            assert cancelled is True
            assert operation.is_cancelled() is True

    def test_cancel_completed_operation(self):
        """Test cancelling an already completed operation."""
        operation = BackgroundOperation(
            operation_id="test-123",
            operation_func=lambda: "result",
            operation_args=(),
            operation_kwargs={},
        )
        
        operation.status = OperationStatus.COMPLETED
        
        cancelled = operation.cancel()
        assert cancelled is False

    def test_get_result_success(self):
        """Test getting result of successful operation."""
        def dummy_func():
            return "success_result"
        
        operation = BackgroundOperation(
            operation_id="test-123",
            operation_func=dummy_func,
            operation_args=(),
            operation_kwargs={},
        )
        
        with ThreadPoolExecutor(max_workers=1) as executor:
            operation.start(executor)
            result = operation.get_result(timeout=5.0)
            
            assert result.operation_id == "test-123"
            assert result.status == OperationStatus.COMPLETED
            assert result.result == "success_result"
            assert result.error is None
            assert result.duration is not None

    def test_get_result_failure(self):
        """Test getting result of failed operation."""
        def failing_func():
            raise ValueError("Test error")
        
        operation = BackgroundOperation(
            operation_id="test-123",
            operation_func=failing_func,
            operation_args=(),
            operation_kwargs={},
        )
        
        with ThreadPoolExecutor(max_workers=1) as executor:
            operation.start(executor)
            result = operation.get_result(timeout=5.0)
            
            assert result.operation_id == "test-123"
            assert result.status == OperationStatus.FAILED
            assert result.result is None
            assert "Test error" in result.error

    def test_get_result_not_started(self):
        """Test getting result of operation that wasn't started."""
        operation = BackgroundOperation(
            operation_id="test-123",
            operation_func=lambda: "result",
            operation_args=(),
            operation_kwargs={},
        )
        
        with pytest.raises(ThreadingError) as exc_info:
            operation.get_result()
        
        assert "Operation not started" in str(exc_info.value)

    def test_add_progress_update(self):
        """Test adding progress updates."""
        progress_updates = []
        
        def progress_callback(update):
            progress_updates.append(update)
        
        operation = BackgroundOperation(
            operation_id="test-123",
            operation_func=lambda: "result",
            operation_args=(),
            operation_kwargs={},
            progress_callback=progress_callback,
        )
        
        operation.add_progress_update("Step 1", 1, 10, {"key": "value"})
        
        assert len(operation.progress_updates) == 1
        assert len(progress_updates) == 1
        
        update = progress_updates[0]
        assert update.operation_id == "test-123"
        assert update.message == "Step 1"
        assert update.current_step == 1
        assert update.total_steps == 10
        assert update.percentage == 10.0
        assert update.details == {"key": "value"}

    def test_progress_callback_exception(self):
        """Test that progress callback exceptions don't break operation."""
        def bad_callback(update):
            raise ValueError("Callback error")
        
        operation = BackgroundOperation(
            operation_id="test-123",
            operation_func=lambda: "result",
            operation_args=(),
            operation_kwargs={},
            progress_callback=bad_callback,
        )
        
        # Should not raise
        operation.add_progress_update("Step 1", 1, 10)
        assert len(operation.progress_updates) == 1

    def test_run_operation_with_progress_callback(self):
        """Test running operation with progress callback integration."""
        progress_messages = []
        
        def operation_func(progress_callback=None):
            if progress_callback:
                progress_callback("Starting")
                progress_callback("Processing")
                progress_callback("Finishing")
            return "done"
        
        operation = BackgroundOperation(
            operation_id="test-123",
            operation_func=operation_func,
            operation_args=(),
            operation_kwargs={"progress_callback": lambda msg: progress_messages.append(msg)},
        )
        
        with ThreadPoolExecutor(max_workers=1) as executor:
            operation.start(executor)
            result = operation.get_result(timeout=5.0)
            
            assert result.status == OperationStatus.COMPLETED
            assert result.result == "done"
            assert len(progress_messages) == 3
            assert len(operation.progress_updates) == 3

    def test_run_operation_checks_cancellation(self):
        """Test that operation checks for cancellation during progress updates."""
        def operation_func(progress_callback=None):
            if progress_callback:
                progress_callback("Step 1")
                time.sleep(0.1)
                progress_callback("Step 2")  # This should raise if cancelled
            return "done"
        
        operation = BackgroundOperation(
            operation_id="test-123",
            operation_func=operation_func,
            operation_args=(),
            operation_kwargs={"progress_callback": None},
        )
        
        with ThreadPoolExecutor(max_workers=1) as executor:
            operation.start(executor)
            
            # Cancel after a short delay
            time.sleep(0.05)
            operation.cancel()
            
            result = operation.get_result(timeout=5.0)
            
            # When cancelled via progress callback, it raises ThreadingError
            # which causes FAILED status with "Operation was cancelled" message
            assert result.status == OperationStatus.FAILED
            assert "Operation was cancelled" in result.error


class TestThreadingModel:
    """Test ThreadingModel class."""

    @pytest.fixture
    def threading_model(self):
        """Create a ThreadingModel instance."""
        model = ThreadingModel(max_workers=2)
        yield model
        model.shutdown(wait=False)

    @pytest.fixture
    def mock_project_generator(self):
        """Create a mock project generator."""
        generator = MagicMock()
        generator.generate_project.return_value = {"success": True}
        return generator

    @pytest.fixture
    def mock_template(self):
        """Create a mock template."""
        template = MagicMock(spec=Template)
        template.name = "test_template"
        return template

    def test_init_default_workers(self):
        """Test ThreadingModel initialization with default workers."""
        with patch("os.cpu_count", return_value=4):
            model = ThreadingModel()
            assert model.max_workers == 4
            model.shutdown(wait=False)

    def test_init_custom_workers(self):
        """Test ThreadingModel initialization with custom workers."""
        model = ThreadingModel(max_workers=8)
        assert model.max_workers == 8
        model.shutdown(wait=False)

    def test_init_cpu_count_none(self):
        """Test ThreadingModel initialization when cpu_count returns None."""
        with patch("os.cpu_count", return_value=None):
            model = ThreadingModel()
            assert model.max_workers == 2  # Should default to 2
            model.shutdown(wait=False)

    def test_start_project_generation_success(
        self,
        threading_model,
        mock_project_generator,
        mock_template,
        tmp_path,
    ):
        """Test starting project generation successfully."""
        operation_id = threading_model.start_project_generation(
            operation_id="gen-123",
            project_generator=mock_project_generator,
            template=mock_template,
            variables={"name": "test_project"},
            target_path=tmp_path,
            dry_run=False,
        )
        
        assert operation_id == "gen-123"
        assert "gen-123" in threading_model.operations
        
        # Status could be RUNNING or already COMPLETED depending on timing
        status = threading_model.get_operation_status("gen-123")
        assert status in [OperationStatus.RUNNING, OperationStatus.COMPLETED]

    def test_start_project_generation_duplicate_id(
        self,
        threading_model,
        mock_project_generator,
        mock_template,
        tmp_path,
    ):
        """Test starting project generation with duplicate ID."""
        # Start first operation
        threading_model.start_project_generation(
            operation_id="gen-123",
            project_generator=mock_project_generator,
            template=mock_template,
            variables={},
            target_path=tmp_path,
        )
        
        # Try to start with same ID
        with pytest.raises(ThreadingError) as exc_info:
            threading_model.start_project_generation(
                operation_id="gen-123",
                project_generator=mock_project_generator,
                template=mock_template,
                variables={},
                target_path=tmp_path,
            )
        
        assert "already exists" in str(exc_info.value)

    def test_start_project_generation_with_progress_callback(
        self,
        threading_model,
        mock_project_generator,
        mock_template,
        tmp_path,
    ):
        """Test starting project generation with progress callback."""
        progress_updates = []
        
        def progress_callback(update):
            progress_updates.append(update)
        
        operation_id = threading_model.start_project_generation(
            operation_id="gen-123",
            project_generator=mock_project_generator,
            template=mock_template,
            variables={},
            target_path=tmp_path,
            progress_callback=progress_callback,
        )
        
        # Wait for completion
        result = threading_model.get_operation_result(operation_id, timeout=5.0)
        
        assert result.status == OperationStatus.COMPLETED

    def test_cancel_operation_success(
        self,
        threading_model,
        mock_template,
        tmp_path,
    ):
        """Test cancelling an operation successfully."""
        # Create a slow generator
        generator = MagicMock()
        
        def slow_generate(*args, **kwargs):
            time.sleep(10)  # Long enough to cancel
            return {"success": True}
        
        generator.generate_project.side_effect = slow_generate
        
        operation_id = threading_model.start_project_generation(
            operation_id="gen-123",
            project_generator=generator,
            template=mock_template,
            variables={},
            target_path=tmp_path,
        )
        
        # Give it time to start
        time.sleep(0.1)
        
        # Cancel the operation
        cancelled = threading_model.cancel_operation(operation_id)
        assert cancelled is True

    def test_cancel_operation_not_found(self, threading_model):
        """Test cancelling a non-existent operation."""
        cancelled = threading_model.cancel_operation("non-existent")
        assert cancelled is False

    def test_get_operation_result_success(
        self,
        threading_model,
        mock_project_generator,
        mock_template,
        tmp_path,
    ):
        """Test getting result of successful operation."""
        mock_project_generator.generate_project.return_value = {"success": True, "files": 10}
        
        operation_id = threading_model.start_project_generation(
            operation_id="gen-123",
            project_generator=mock_project_generator,
            template=mock_template,
            variables={},
            target_path=tmp_path,
        )
        
        result = threading_model.get_operation_result(operation_id, timeout=5.0)
        
        assert result.operation_id == "gen-123"
        assert result.status == OperationStatus.COMPLETED
        assert result.result == {"success": True, "files": 10}
        assert result.error is None

    def test_get_operation_result_failure(
        self,
        threading_model,
        mock_project_generator,
        mock_template,
        tmp_path,
    ):
        """Test getting result of failed operation."""
        mock_project_generator.generate_project.side_effect = ValueError("Generation failed")
        
        operation_id = threading_model.start_project_generation(
            operation_id="gen-123",
            project_generator=mock_project_generator,
            template=mock_template,
            variables={},
            target_path=tmp_path,
        )
        
        result = threading_model.get_operation_result(operation_id, timeout=5.0)
        
        assert result.operation_id == "gen-123"
        assert result.status == OperationStatus.FAILED
        assert result.result is None
        assert "Generation failed" in result.error

    def test_get_operation_result_not_found(self, threading_model):
        """Test getting result of non-existent operation."""
        with pytest.raises(ThreadingError) as exc_info:
            threading_model.get_operation_result("non-existent")
        
        assert "not found" in str(exc_info.value)

    def test_get_operation_result_remove_completed(
        self,
        threading_model,
        mock_project_generator,
        mock_template,
        tmp_path,
    ):
        """Test that completed operations are removed when requested."""
        operation_id = threading_model.start_project_generation(
            operation_id="gen-123",
            project_generator=mock_project_generator,
            template=mock_template,
            variables={},
            target_path=tmp_path,
        )
        
        # Get result with remove_completed=True (default)
        result = threading_model.get_operation_result(operation_id, timeout=5.0)
        
        assert result.status == OperationStatus.COMPLETED
        assert operation_id not in threading_model.operations

    def test_get_operation_status(
        self,
        threading_model,
        mock_project_generator,
        mock_template,
        tmp_path,
    ):
        """Test getting operation status."""
        operation_id = threading_model.start_project_generation(
            operation_id="gen-123",
            project_generator=mock_project_generator,
            template=mock_template,
            variables={},
            target_path=tmp_path,
        )
        
        status = threading_model.get_operation_status(operation_id)
        # Could be PENDING, RUNNING, or already COMPLETED
        assert status in [OperationStatus.PENDING, OperationStatus.RUNNING, OperationStatus.COMPLETED]
        
        # Wait for completion
        threading_model.get_operation_result(operation_id, timeout=5.0)
        
        # Should be None after removal
        status = threading_model.get_operation_status(operation_id)
        assert status is None

    def test_list_active_operations(
        self,
        threading_model,
        mock_project_generator,
        mock_template,
        tmp_path,
    ):
        """Test listing active operations."""
        # Start multiple operations
        for i in range(3):
            threading_model.start_project_generation(
                operation_id=f"gen-{i}",
                project_generator=mock_project_generator,
                template=mock_template,
                variables={},
                target_path=tmp_path / f"project_{i}",
            )
        
        active_ops = threading_model.list_active_operations()
        
        assert len(active_ops) == 3
        assert all(op_id in active_ops for op_id in ["gen-0", "gen-1", "gen-2"])

    def test_cleanup_completed_operations(
        self,
        threading_model,
        mock_project_generator,
        mock_template,
        tmp_path,
    ):
        """Test cleaning up completed operations."""
        # Start and complete some operations
        for i in range(3):
            operation_id = threading_model.start_project_generation(
                operation_id=f"gen-{i}",
                project_generator=mock_project_generator,
                template=mock_template,
                variables={},
                target_path=tmp_path / f"project_{i}",
            )
            
            # Get result but don't remove
            threading_model.get_operation_result(
                operation_id,
                timeout=5.0,
                remove_completed=False,
            )
        
        # All should still be in memory
        assert len(threading_model.operations) == 3
        
        # Cleanup
        removed = threading_model.cleanup_completed_operations()
        
        assert removed == 3
        assert len(threading_model.operations) == 0

    def test_shutdown_wait(
        self,
        threading_model,
        mock_project_generator,
        mock_template,
        tmp_path,
    ):
        """Test shutdown with wait for operations."""
        # Start an operation
        threading_model.start_project_generation(
            operation_id="gen-123",
            project_generator=mock_project_generator,
            template=mock_template,
            variables={},
            target_path=tmp_path,
        )
        
        # Shutdown with wait
        threading_model.shutdown(wait=True, timeout=5.0)
        
        assert len(threading_model.operations) == 0

    def test_shutdown_no_wait(
        self,
        threading_model,
        mock_template,
        tmp_path,
    ):
        """Test shutdown without waiting."""
        # Create a slow generator
        generator = MagicMock()
        generator.generate_project.side_effect = lambda *args, **kwargs: time.sleep(10)
        
        # Start an operation
        threading_model.start_project_generation(
            operation_id="gen-123",
            project_generator=generator,
            template=mock_template,
            variables={},
            target_path=tmp_path,
        )
        
        # Shutdown without wait
        threading_model.shutdown(wait=False)
        
        assert len(threading_model.operations) == 0

    def test_context_manager(self, mock_project_generator, mock_template, tmp_path):
        """Test using ThreadingModel as context manager."""
        with ThreadingModel(max_workers=2) as model:
            operation_id = model.start_project_generation(
                operation_id="gen-123",
                project_generator=mock_project_generator,
                template=mock_template,
                variables={},
                target_path=tmp_path,
            )
            
            result = model.get_operation_result(operation_id, timeout=5.0)
            assert result.status == OperationStatus.COMPLETED
        
        # Model should be shut down after context exit

    def test_concurrent_operations(
        self,
        threading_model,
        mock_project_generator,
        mock_template,
        tmp_path,
    ):
        """Test running multiple operations concurrently."""
        operation_ids = []
        
        # Start multiple operations
        for i in range(5):
            op_id = f"gen-{i}"
            threading_model.start_project_generation(
                operation_id=op_id,
                project_generator=mock_project_generator,
                template=mock_template,
                variables={"index": i},
                target_path=tmp_path / f"project_{i}",
            )
            operation_ids.append(op_id)
        
        # Get all results
        results = []
        for op_id in operation_ids:
            result = threading_model.get_operation_result(op_id, timeout=5.0)
            results.append(result)
        
        # All should complete successfully
        assert all(r.status == OperationStatus.COMPLETED for r in results)
        assert len(results) == 5