# ABOUTME: Error recovery system for project generation with rollback and partial recovery support
# ABOUTME: Tracks recovery points, manages rollback operations, and provides recovery strategies

"""Error recovery system for project generation.

This module provides comprehensive error recovery capabilities including:
- Recovery point tracking for rollback operations
- Automatic cleanup of partial project creation
- Multiple recovery strategies
- State restoration and partial recovery support
- Detailed error logging for debugging
"""

import json
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from structlog import get_logger

logger = get_logger(__name__)


class RecoveryStrategy(Enum):
    """Available recovery strategies."""

    FULL_ROLLBACK = "full_rollback"  # Remove everything and start fresh
    PARTIAL_RECOVERY = "partial_recovery"  # Keep completed parts, retry failed
    RETRY_OPERATION = "retry_operation"  # Retry the failed operation
    SKIP_AND_CONTINUE = "skip_and_continue"  # Skip failed step and continue
    ABORT = "abort"  # Clean abort with minimal cleanup


@dataclass
class RecoveryPoint:
    """Represents a point in the generation process that can be restored."""

    id: str
    timestamp: datetime
    phase: str
    description: str
    created_paths: Set[Path] = field(default_factory=set)
    modified_paths: Set[Path] = field(default_factory=set)
    state_data: Dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "phase": self.phase,
            "description": self.description,
            "created_paths": [str(p) for p in self.created_paths],
            "modified_paths": [str(p) for p in self.modified_paths],
            "state_data": self.state_data,
            "parent_id": self.parent_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RecoveryPoint":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            phase=data["phase"],
            description=data["description"],
            created_paths={Path(p) for p in data.get("created_paths", [])},
            modified_paths={Path(p) for p in data.get("modified_paths", [])},
            state_data=data.get("state_data", {}),
            parent_id=data.get("parent_id"),
        )


@dataclass
class RecoveryContext:
    """Context information for recovery operations."""

    error: Exception
    recovery_points: List[RecoveryPoint]
    current_phase: str
    failed_operation: str
    target_path: Path
    template_name: str
    project_variables: Dict[str, Any]
    partial_results: Dict[str, Any] = field(default_factory=dict)
    suggested_strategy: Optional[RecoveryStrategy] = None
    ai_suggestions: Optional[str] = None


class RecoveryManager:
    """Manages error recovery and rollback operations."""

    def __init__(self, log_dir: Optional[Path] = None) -> None:
        """Initialize recovery manager.
        
        Args:
            log_dir: Directory for error logs (defaults to temp directory)
        """
        self.logger = logger.bind(component="recovery_manager")
        self.recovery_points: List[RecoveryPoint] = []
        self.current_point_id: Optional[str] = None
        self.log_dir = log_dir or Path(tempfile.gettempdir()) / "create_project" / "recovery"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._point_counter = 0

    def create_recovery_point(
        self,
        phase: str,
        description: str,
        state_data: Optional[Dict[str, Any]] = None,
    ) -> RecoveryPoint:
        """Create a new recovery point.
        
        Args:
            phase: Current phase of generation
            description: Description of the recovery point
            state_data: Additional state data to store
            
        Returns:
            Created recovery point
        """
        self._point_counter += 1
        point_id = f"rp_{self._point_counter}_{phase}"

        point = RecoveryPoint(
            id=point_id,
            timestamp=datetime.now(),
            phase=phase,
            description=description,
            state_data=state_data or {},
            parent_id=self.current_point_id,
        )

        self.recovery_points.append(point)
        self.current_point_id = point_id

        self.logger.debug(
            "Created recovery point",
            point_id=point_id,
            phase=phase,
            description=description,
        )

        return point

    def track_created_path(self, path: Path) -> None:
        """Track a newly created path for potential rollback.
        
        Args:
            path: Path that was created
        """
        if self.current_point_id:
            current_point = self._get_point(self.current_point_id)
            if current_point:
                current_point.created_paths.add(path)
                self.logger.debug(
                    "Tracked created path",
                    path=str(path),
                    point_id=self.current_point_id,
                )

    def track_modified_path(self, path: Path) -> None:
        """Track a modified path for potential restoration.
        
        Args:
            path: Path that was modified
        """
        if self.current_point_id:
            current_point = self._get_point(self.current_point_id)
            if current_point:
                current_point.modified_paths.add(path)
                self.logger.debug(
                    "Tracked modified path",
                    path=str(path),
                    point_id=self.current_point_id,
                )

    def rollback_to_point(self, point_id: str) -> bool:
        """Rollback to a specific recovery point.
        
        Args:
            point_id: ID of the recovery point to rollback to
            
        Returns:
            True if rollback successful, False otherwise
        """
        self.logger.info("Starting rollback", target_point=point_id)

        target_point = self._get_point(point_id)
        if not target_point:
            self.logger.error("Recovery point not found", point_id=point_id)
            return False

        # Find all points after the target point
        target_index = self.recovery_points.index(target_point)
        points_to_rollback = self.recovery_points[target_index + 1:]

        # Rollback in reverse order
        success = True
        for point in reversed(points_to_rollback):
            if not self._rollback_point(point):
                success = False

        # Remove rolled back points
        self.recovery_points = self.recovery_points[:target_index + 1]
        self.current_point_id = point_id

        self.logger.info(
            "Rollback completed",
            success=success,
            rolled_back_count=len(points_to_rollback),
        )

        return success

    def rollback_all(self) -> bool:
        """Rollback all recovery points (full cleanup).
        
        Returns:
            True if rollback successful, False otherwise
        """
        self.logger.info("Starting full rollback")

        success = True
        for point in reversed(self.recovery_points):
            if not self._rollback_point(point):
                success = False

        self.recovery_points.clear()
        self.current_point_id = None

        self.logger.info("Full rollback completed", success=success)
        return success

    def suggest_recovery_strategy(
        self,
        error: Exception,
        phase: str,
        partial_results: Dict[str, Any],
    ) -> RecoveryStrategy:
        """Suggest an appropriate recovery strategy based on the error.
        
        Args:
            error: The error that occurred
            phase: Phase where error occurred
            partial_results: Any partial results available
            
        Returns:
            Suggested recovery strategy
        """
        error_type = type(error).__name__
        error_msg = str(error).lower()

        # Permission errors - usually need full rollback
        if error_type in ["PermissionError", "OSError"] and "permission" in error_msg:
            return RecoveryStrategy.FULL_ROLLBACK

        # Path already exists - might be able to continue
        if "exists" in error_msg or "already exists" in error_msg:
            return RecoveryStrategy.PARTIAL_RECOVERY

        # Network or temporary errors - retry might work
        if error_type in ["ConnectionError", "TimeoutError", "HTTPError"]:
            return RecoveryStrategy.RETRY_OPERATION

        # Git or venv errors - can often skip
        if phase in ["git_init", "venv_setup"] and partial_results.get("files_created"):
            return RecoveryStrategy.SKIP_AND_CONTINUE

        # Default to full rollback for safety
        return RecoveryStrategy.FULL_ROLLBACK

    def create_recovery_context(
        self,
        error: Exception,
        phase: str,
        failed_operation: str,
        target_path: Path,
        template_name: str,
        project_variables: Dict[str, Any],
        partial_results: Optional[Dict[str, Any]] = None,
    ) -> RecoveryContext:
        """Create a recovery context for error handling.
        
        Args:
            error: The error that occurred
            phase: Current phase of generation
            failed_operation: Operation that failed
            target_path: Target project path
            template_name: Template being used
            project_variables: Project variables
            partial_results: Any partial results
            
        Returns:
            Recovery context
        """
        suggested_strategy = self.suggest_recovery_strategy(
            error, phase, partial_results or {}
        )

        context = RecoveryContext(
            error=error,
            recovery_points=self.recovery_points.copy(),
            current_phase=phase,
            failed_operation=failed_operation,
            target_path=target_path,
            template_name=template_name,
            project_variables=project_variables,
            partial_results=partial_results or {},
            suggested_strategy=suggested_strategy,
        )

        # Save error log
        self._save_error_log(context)

        return context

    def execute_recovery(
        self,
        context: RecoveryContext,
        strategy: RecoveryStrategy,
    ) -> Tuple[bool, Optional[str]]:
        """Execute a recovery strategy.
        
        Args:
            context: Recovery context
            strategy: Strategy to execute
            
        Returns:
            Tuple of (success, message)
        """
        self.logger.info(
            "Executing recovery strategy",
            strategy=strategy.value,
            phase=context.current_phase,
        )

        try:
            if strategy == RecoveryStrategy.FULL_ROLLBACK:
                success = self.rollback_all()
                message = "All changes rolled back successfully" if success else "Rollback failed"

            elif strategy == RecoveryStrategy.PARTIAL_RECOVERY:
                # Find the last successful phase
                last_good_point = self._find_last_successful_point(context.current_phase)
                if last_good_point:
                    success = self.rollback_to_point(last_good_point.id)
                    message = f"Rolled back to: {last_good_point.description}"
                else:
                    success = False
                    message = "No valid recovery point found"

            elif strategy == RecoveryStrategy.RETRY_OPERATION:
                # Just return success, caller will retry
                success = True
                message = "Ready to retry operation"

            elif strategy == RecoveryStrategy.SKIP_AND_CONTINUE:
                # Mark current phase as skipped in state
                if self.current_point_id:
                    current_point = self._get_point(self.current_point_id)
                    if current_point:
                        current_point.state_data["skipped"] = True
                success = True
                message = f"Skipped {context.failed_operation}"

            elif strategy == RecoveryStrategy.ABORT:
                # Minimal cleanup, just clear tracking
                self.recovery_points.clear()
                self.current_point_id = None
                success = True
                message = "Aborted with minimal cleanup"

            else:
                success = False
                message = f"Unknown strategy: {strategy.value}"

            return success, message

        except Exception as e:
            self.logger.error(
                "Recovery execution failed",
                strategy=strategy.value,
                error=str(e),
            )
            return False, f"Recovery failed: {str(e)}"

    def _get_point(self, point_id: str) -> Optional[RecoveryPoint]:
        """Get a recovery point by ID."""
        for point in self.recovery_points:
            if point.id == point_id:
                return point
        return None

    def _rollback_point(self, point: RecoveryPoint) -> bool:
        """Rollback a single recovery point.
        
        Args:
            point: Recovery point to rollback
            
        Returns:
            True if successful, False otherwise
        """
        self.logger.debug("Rolling back point", point_id=point.id, phase=point.phase)

        success = True

        # Remove created paths
        for path in point.created_paths:
            try:
                if path.exists():
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink()
                    self.logger.debug("Removed path", path=str(path))
            except Exception as e:
                self.logger.warning(
                    "Failed to remove path",
                    path=str(path),
                    error=str(e),
                )
                success = False

        return success

    def _find_last_successful_point(self, failed_phase: str) -> Optional[RecoveryPoint]:
        """Find the last successful recovery point before a failed phase.
        
        Args:
            failed_phase: Phase that failed
            
        Returns:
            Last successful recovery point, or None
        """
        # Find points before the failed phase
        for point in reversed(self.recovery_points):
            if point.phase != failed_phase and not point.state_data.get("skipped"):
                return point
        return None

    def _save_error_log(self, context: RecoveryContext) -> None:
        """Save detailed error log for debugging.
        
        Args:
            context: Recovery context with error information
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_dir / f"error_{timestamp}_{context.current_phase}.json"

        log_data = {
            "timestamp": datetime.now().isoformat(),
            "error": {
                "type": type(context.error).__name__,
                "message": str(context.error),
                "phase": context.current_phase,
                "operation": context.failed_operation,
            },
            "project": {
                "template": context.template_name,
                "target_path": str(context.target_path),
                "variables": self._sanitize_variables(context.project_variables),
            },
            "recovery_points": [rp.to_dict() for rp in context.recovery_points],
            "partial_results": context.partial_results,
            "suggested_strategy": context.suggested_strategy.value if context.suggested_strategy else None,
        }

        try:
            with open(log_file, "w") as f:
                json.dump(log_data, f, indent=2)
            self.logger.info("Error log saved", log_file=str(log_file))
        except Exception as e:
            self.logger.error("Failed to save error log", error=str(e))

    def _sanitize_variables(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize sensitive information from variables.
        
        Args:
            variables: Variables to sanitize
            
        Returns:
            Sanitized variables
        """
        sensitive_keys = {"password", "token", "secret", "key", "email"}
        sanitized = {}

        for key, value in variables.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value

        return sanitized
