# ABOUTME: Background threading model for project generation operations
# ABOUTME: Provides thread-safe progress reporting, cancellation, and resource management

"""
Threading model for background project generation operations.

This module provides the ThreadingModel class which manages background
project generation with thread-safe progress reporting, cancellation support,
error propagation, and proper resource cleanup.
"""

import threading
import time
import queue
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from typing import Callable, Optional, Any, Dict, List, Union
from enum import Enum
from dataclasses import dataclass
from pathlib import Path
from structlog import get_logger

from .exceptions import ThreadingError, ProjectGenerationError
from .project_generator import ProjectGenerator, GenerationResult
from ..templates.schema.template import Template


class OperationStatus(Enum):
    """Status of background operation."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ProgressUpdate:
    """Progress update from background operation.
    
    Attributes:
        operation_id: Unique operation identifier
        message: Progress message
        current_step: Current step number (0-based)
        total_steps: Total number of steps
        percentage: Progress percentage (0-100)
        timestamp: Update timestamp
        details: Optional additional details
    """
    operation_id: str
    message: str
    current_step: int
    total_steps: int
    percentage: float
    timestamp: float
    details: Optional[Dict[str, Any]] = None


@dataclass
class OperationResult:
    """Result of background operation.
    
    Attributes:
        operation_id: Unique operation identifier
        status: Final operation status
        result: Operation result (if successful)
        error: Error information (if failed)
        duration: Operation duration in seconds
        progress_updates: List of all progress updates
    """
    operation_id: str
    status: OperationStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    duration: Optional[float] = None
    progress_updates: Optional[List[ProgressUpdate]] = None


class BackgroundOperation:
    """Background operation with progress tracking and cancellation."""
    
    def __init__(
        self,
        operation_id: str,
        operation_func: Callable,
        operation_args: tuple,
        operation_kwargs: dict,
        progress_callback: Optional[Callable[[ProgressUpdate], None]] = None
    ) -> None:
        """Initialize background operation.
        
        Args:
            operation_id: Unique operation identifier
            operation_func: Function to execute in background
            operation_args: Function arguments
            operation_kwargs: Function keyword arguments
            progress_callback: Optional progress callback
        """
        self.operation_id = operation_id
        self.operation_func = operation_func
        self.operation_args = operation_args
        self.operation_kwargs = operation_kwargs
        self.progress_callback = progress_callback
        
        self.status = OperationStatus.PENDING
        self.future: Optional[Future] = None
        self.result: Optional[Any] = None
        self.error: Optional[Exception] = None
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.progress_updates: List[ProgressUpdate] = []
        self.cancellation_event = threading.Event()
        
        # Thread-safe lock for status updates
        self._lock = threading.Lock()
        
        self.logger = get_logger(__name__)
    
    def start(self, executor: ThreadPoolExecutor) -> None:
        """Start the operation in background thread.
        
        Args:
            executor: Thread pool executor
        """
        with self._lock:
            if self.status != OperationStatus.PENDING:
                raise ThreadingError(
                    f"Cannot start operation in {self.status.value} state",
                    details={"operation_id": self.operation_id}
                )
            
            self.status = OperationStatus.RUNNING
            self.start_time = time.time()
            
            # Submit to thread pool
            self.future = executor.submit(self._run_operation)
            
            self.logger.info(
                "Background operation started",
                operation_id=self.operation_id
            )
    
    def cancel(self) -> bool:
        """Cancel the operation.
        
        Returns:
            True if cancellation was successful
        """
        with self._lock:
            if self.status in [OperationStatus.COMPLETED, OperationStatus.FAILED, OperationStatus.CANCELLED]:
                return False
            
            # Set cancellation event
            self.cancellation_event.set()
            
            # Try to cancel future
            if self.future:
                cancelled = self.future.cancel()
                
                if cancelled or self.cancellation_event.is_set():
                    self.status = OperationStatus.CANCELLED
                    self.end_time = time.time()
                    
                    self.logger.info(
                        "Background operation cancelled",
                        operation_id=self.operation_id
                    )
                    
                    return True
            
            return False
    
    def is_cancelled(self) -> bool:
        """Check if operation is cancelled."""
        return self.cancellation_event.is_set()
    
    def get_result(self, timeout: Optional[float] = None) -> OperationResult:
        """Get operation result (blocks until completion).
        
        Args:
            timeout: Optional timeout in seconds
            
        Returns:
            OperationResult with final status and result
        """
        if not self.future:
            raise ThreadingError(
                "Operation not started",
                details={"operation_id": self.operation_id}
            )
        
        try:
            # Wait for completion
            result = self.future.result(timeout=timeout)
            
            with self._lock:
                return OperationResult(
                    operation_id=self.operation_id,
                    status=self.status,
                    result=result,
                    error=str(self.error) if self.error else None,
                    duration=self.end_time - self.start_time if self.start_time and self.end_time else None,
                    progress_updates=self.progress_updates.copy()
                )
                
        except Exception as e:
            with self._lock:
                return OperationResult(
                    operation_id=self.operation_id,
                    status=OperationStatus.FAILED,
                    result=None,
                    error=str(e),
                    duration=self.end_time - self.start_time if self.start_time and self.end_time else None,
                    progress_updates=self.progress_updates.copy()
                )
    
    def add_progress_update(
        self,
        message: str,
        current_step: int,
        total_steps: int,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add progress update.
        
        Args:
            message: Progress message
            current_step: Current step number
            total_steps: Total number of steps
            details: Optional additional details
        """
        percentage = (current_step / max(total_steps, 1)) * 100.0
        
        update = ProgressUpdate(
            operation_id=self.operation_id,
            message=message,
            current_step=current_step,
            total_steps=total_steps,
            percentage=percentage,
            timestamp=time.time(),
            details=details
        )
        
        with self._lock:
            self.progress_updates.append(update)
        
        # Call progress callback if provided
        if self.progress_callback:
            try:
                self.progress_callback(update)
            except Exception as e:
                self.logger.warning(
                    "Progress callback failed",
                    operation_id=self.operation_id,
                    error=str(e)
                )
        
        self.logger.debug(
            "Progress update",
            operation_id=self.operation_id,
            message=message,
            percentage=percentage
        )
    
    def _run_operation(self) -> Any:
        """Run the actual operation with error handling."""
        try:
            # Create progress callback that checks for cancellation
            def progress_wrapper(message: str) -> None:
                if self.is_cancelled():
                    raise ThreadingError("Operation was cancelled")
                
                # Extract step info from message if available
                # This is a simple heuristic - in practice, operations would
                # provide more structured progress information
                current_step = len(self.progress_updates)
                total_steps = 10  # Default estimate
                
                self.add_progress_update(message, current_step, total_steps)
            
            # Add progress callback to kwargs if the operation supports it
            if 'progress_callback' in self.operation_kwargs:
                original_callback = self.operation_kwargs.get('progress_callback')
                
                def combined_callback(message: str) -> None:
                    progress_wrapper(message)
                    if original_callback:
                        original_callback(message)
                
                self.operation_kwargs['progress_callback'] = combined_callback
            
            # Execute the operation
            result = self.operation_func(*self.operation_args, **self.operation_kwargs)
            
            # Update final status
            with self._lock:
                if not self.is_cancelled():
                    self.status = OperationStatus.COMPLETED
                    self.result = result
                    self.end_time = time.time()
                    
                    self.logger.info(
                        "Background operation completed successfully",
                        operation_id=self.operation_id,
                        duration=self.end_time - self.start_time if self.start_time else None
                    )
            
            return result
            
        except Exception as e:
            with self._lock:
                if not self.is_cancelled():
                    self.status = OperationStatus.FAILED
                    self.error = e
                    self.end_time = time.time()
                    
                    self.logger.error(
                        "Background operation failed",
                        operation_id=self.operation_id,
                        error=str(e),
                        duration=self.end_time - self.start_time if self.start_time else None
                    )
            
            raise


class ThreadingModel:
    """Threading model for background project generation.
    
    This class manages background project generation operations with
    thread-safe progress reporting, cancellation support, error propagation,
    and proper resource cleanup.
    
    Attributes:
        logger: Structured logger for operations
        executor: Thread pool executor for background operations
        operations: Dictionary of active operations
        max_workers: Maximum number of worker threads
    """
    
    def __init__(self, max_workers: Optional[int] = None) -> None:
        """Initialize the ThreadingModel.
        
        Args:
            max_workers: Maximum number of worker threads (defaults to CPU count)
        """
        self.logger = get_logger(__name__)
        
        # Use CPU count if not specified, with reasonable bounds
        if max_workers is None:
            import os
            max_workers = max(2, min(os.cpu_count() or 2, 8))
        
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.operations: Dict[str, BackgroundOperation] = {}
        
        # Thread-safe lock for operations dictionary
        self._operations_lock = threading.Lock()
        
        self.logger.info(
            "ThreadingModel initialized",
            max_workers=max_workers
        )
    
    def start_project_generation(
        self,
        operation_id: str,
        project_generator: ProjectGenerator,
        template: Template,
        variables: Dict[str, Any],
        target_path: Union[str, Path],
        dry_run: bool = False,
        progress_callback: Optional[Callable[[ProgressUpdate], None]] = None
    ) -> str:
        """Start project generation in background.
        
        Args:
            operation_id: Unique operation identifier
            project_generator: ProjectGenerator instance
            template: Template to use
            variables: Template variables
            target_path: Target directory path
            dry_run: Whether to run in dry-run mode
            progress_callback: Optional progress callback
            
        Returns:
            Operation ID for tracking
            
        Raises:
            ThreadingError: If operation cannot be started
        """
        with self._operations_lock:
            if operation_id in self.operations:
                raise ThreadingError(
                    f"Operation with ID '{operation_id}' already exists",
                    details={"operation_id": operation_id}
                )
        
        # Create background operation
        operation = BackgroundOperation(
            operation_id=operation_id,
            operation_func=project_generator.generate_project,
            operation_args=(template, variables, target_path),
            operation_kwargs={'dry_run': dry_run, 'progress_callback': None},  # We'll handle progress internally
            progress_callback=progress_callback
        )
        
        # Add to operations dictionary
        with self._operations_lock:
            self.operations[operation_id] = operation
        
        # Start the operation
        try:
            operation.start(self.executor)
            
            self.logger.info(
                "Project generation started in background",
                operation_id=operation_id,
                template_name=template.name,
                target_path=str(target_path),
                dry_run=dry_run
            )
            
            return operation_id
            
        except Exception as e:
            # Remove from operations if start failed
            with self._operations_lock:
                self.operations.pop(operation_id, None)
            
            raise ThreadingError(
                f"Failed to start project generation: {e}",
                details={
                    "operation_id": operation_id,
                    "template_name": template.name,
                    "target_path": str(target_path)
                },
                original_error=e
            ) from e
    
    def cancel_operation(self, operation_id: str) -> bool:
        """Cancel a background operation.
        
        Args:
            operation_id: Operation to cancel
            
        Returns:
            True if operation was successfully cancelled
        """
        with self._operations_lock:
            operation = self.operations.get(operation_id)
        
        if not operation:
            self.logger.warning(
                "Attempted to cancel non-existent operation",
                operation_id=operation_id
            )
            return False
        
        return operation.cancel()
    
    def get_operation_result(
        self,
        operation_id: str,
        timeout: Optional[float] = None,
        remove_completed: bool = True
    ) -> OperationResult:
        """Get result of background operation.
        
        Args:
            operation_id: Operation to get result for
            timeout: Optional timeout in seconds
            remove_completed: Whether to remove completed operations
            
        Returns:
            OperationResult with final status and result
            
        Raises:
            ThreadingError: If operation doesn't exist
        """
        with self._operations_lock:
            operation = self.operations.get(operation_id)
        
        if not operation:
            raise ThreadingError(
                f"Operation '{operation_id}' not found",
                details={"operation_id": operation_id}
            )
        
        try:
            result = operation.get_result(timeout=timeout)
            
            # Remove completed operation if requested
            if remove_completed and result.status in [
                OperationStatus.COMPLETED,
                OperationStatus.FAILED,
                OperationStatus.CANCELLED
            ]:
                with self._operations_lock:
                    self.operations.pop(operation_id, None)
                
                self.logger.debug(
                    "Removed completed operation",
                    operation_id=operation_id,
                    status=result.status.value
                )
            
            return result
            
        except Exception as e:
            raise ThreadingError(
                f"Failed to get operation result: {e}",
                details={"operation_id": operation_id},
                original_error=e
            ) from e
    
    def get_operation_status(self, operation_id: str) -> Optional[OperationStatus]:
        """Get current status of operation.
        
        Args:
            operation_id: Operation to check
            
        Returns:
            Current operation status or None if not found
        """
        with self._operations_lock:
            operation = self.operations.get(operation_id)
        
        return operation.status if operation else None
    
    def list_active_operations(self) -> Dict[str, OperationStatus]:
        """Get list of active operations and their statuses.
        
        Returns:
            Dictionary mapping operation IDs to their current status
        """
        with self._operations_lock:
            return {
                op_id: operation.status
                for op_id, operation in self.operations.items()
            }
    
    def cleanup_completed_operations(self) -> int:
        """Remove completed operations from memory.
        
        Returns:
            Number of operations removed
        """
        removed_count = 0
        
        with self._operations_lock:
            completed_ops = [
                op_id for op_id, operation in self.operations.items()
                if operation.status in [
                    OperationStatus.COMPLETED,
                    OperationStatus.FAILED,
                    OperationStatus.CANCELLED
                ]
            ]
            
            for op_id in completed_ops:
                self.operations.pop(op_id, None)
                removed_count += 1
        
        if removed_count > 0:
            self.logger.info(
                "Cleaned up completed operations",
                removed_count=removed_count
            )
        
        return removed_count
    
    def shutdown(self, wait: bool = True, timeout: Optional[float] = None) -> None:
        """Shutdown the threading model and cleanup resources.
        
        Args:
            wait: Whether to wait for active operations to complete
            timeout: Optional timeout for shutdown
        """
        self.logger.info(
            "Shutting down ThreadingModel",
            wait=wait,
            timeout=timeout,
            active_operations=len(self.operations)
        )
        
        # Cancel all active operations if not waiting
        if not wait:
            with self._operations_lock:
                operation_ids = list(self.operations.keys())
            
            for op_id in operation_ids:
                self.cancel_operation(op_id)
        
        # Shutdown executor
        self.executor.shutdown(wait=wait)
        
        # Clear operations
        with self._operations_lock:
            self.operations.clear()
        
        self.logger.info("ThreadingModel shutdown complete")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.shutdown(wait=True, timeout=30.0)