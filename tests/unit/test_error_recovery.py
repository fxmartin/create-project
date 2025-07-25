# ABOUTME: Unit tests for error recovery system including recovery points and rollback operations
# ABOUTME: Tests recovery manager, recovery strategies, and error context creation

"""Unit tests for error recovery system."""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from create_project.core.error_recovery import (
    RecoveryContext,
    RecoveryManager,
    RecoveryPoint,
    RecoveryStrategy,
)


class TestRecoveryPoint:
    """Test RecoveryPoint dataclass."""

    def test_recovery_point_creation(self):
        """Test creating a recovery point."""
        point = RecoveryPoint(
            id="test_point",
            timestamp=datetime.now(),
            phase="initialization",
            description="Test recovery point",
            created_paths={Path("/tmp/test")},
            modified_paths={Path("/tmp/modified")},
            state_data={"key": "value"},
            parent_id="parent_point",
        )

        assert point.id == "test_point"
        assert point.phase == "initialization"
        assert point.description == "Test recovery point"
        assert Path("/tmp/test") in point.created_paths
        assert Path("/tmp/modified") in point.modified_paths
        assert point.state_data["key"] == "value"
        assert point.parent_id == "parent_point"

    def test_recovery_point_serialization(self):
        """Test serializing recovery point to dict."""
        timestamp = datetime.now()
        point = RecoveryPoint(
            id="test_point",
            timestamp=timestamp,
            phase="test_phase",
            description="Test point",
            created_paths={Path("/tmp/file1"), Path("/tmp/file2")},
            modified_paths={Path("/tmp/mod1")},
            state_data={"test": True},
        )

        data = point.to_dict()

        assert data["id"] == "test_point"
        assert data["timestamp"] == timestamp.isoformat()
        assert data["phase"] == "test_phase"
        assert data["description"] == "Test point"
        assert "/tmp/file1" in data["created_paths"]
        assert "/tmp/file2" in data["created_paths"]
        assert "/tmp/mod1" in data["modified_paths"]
        assert data["state_data"]["test"] is True

    def test_recovery_point_deserialization(self):
        """Test deserializing recovery point from dict."""
        timestamp = datetime.now()
        data = {
            "id": "test_point",
            "timestamp": timestamp.isoformat(),
            "phase": "test_phase",
            "description": "Test point",
            "created_paths": ["/tmp/file1", "/tmp/file2"],
            "modified_paths": ["/tmp/mod1"],
            "state_data": {"test": True},
            "parent_id": "parent",
        }

        point = RecoveryPoint.from_dict(data)

        assert point.id == "test_point"
        assert point.phase == "test_phase"
        assert point.description == "Test point"
        assert Path("/tmp/file1") in point.created_paths
        assert Path("/tmp/file2") in point.created_paths
        assert Path("/tmp/mod1") in point.modified_paths
        assert point.state_data["test"] is True
        assert point.parent_id == "parent"


class TestRecoveryManager:
    """Test RecoveryManager class."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def recovery_manager(self, temp_dir):
        """Create RecoveryManager instance."""
        return RecoveryManager(log_dir=temp_dir / "logs")

    def test_create_recovery_point(self, recovery_manager):
        """Test creating recovery points."""
        # Create first point
        point1 = recovery_manager.create_recovery_point(
            phase="init",
            description="Initial setup",
            state_data={"step": 1},
        )

        assert point1.id == "rp_1_init"
        assert point1.phase == "init"
        assert point1.description == "Initial setup"
        assert point1.state_data["step"] == 1
        assert point1.parent_id is None
        assert recovery_manager.current_point_id == point1.id

        # Create second point
        point2 = recovery_manager.create_recovery_point(
            phase="files",
            description="File creation",
            state_data={"step": 2},
        )

        assert point2.id == "rp_2_files"
        assert point2.parent_id == point1.id
        assert recovery_manager.current_point_id == point2.id
        assert len(recovery_manager.recovery_points) == 2

    def test_track_paths(self, recovery_manager):
        """Test tracking created and modified paths."""
        # Create recovery point
        point = recovery_manager.create_recovery_point("test", "Test point")

        # Track paths
        created_path = Path("/tmp/created")
        modified_path = Path("/tmp/modified")

        recovery_manager.track_created_path(created_path)
        recovery_manager.track_modified_path(modified_path)

        # Verify paths are tracked
        assert created_path in point.created_paths
        assert modified_path in point.modified_paths

    def test_rollback_to_point(self, recovery_manager, temp_dir):
        """Test rolling back to a specific recovery point."""
        # Create test files
        file1 = temp_dir / "file1.txt"
        file2 = temp_dir / "file2.txt"
        file3 = temp_dir / "file3.txt"

        # Create recovery points
        point1 = recovery_manager.create_recovery_point("phase1", "First phase")
        file1.write_text("content1")
        recovery_manager.track_created_path(file1)

        point2 = recovery_manager.create_recovery_point("phase2", "Second phase")
        file2.write_text("content2")
        recovery_manager.track_created_path(file2)

        point3 = recovery_manager.create_recovery_point("phase3", "Third phase")
        file3.write_text("content3")
        recovery_manager.track_created_path(file3)

        # All files should exist
        assert file1.exists()
        assert file2.exists()
        assert file3.exists()

        # Rollback to point1
        success = recovery_manager.rollback_to_point(point1.id)

        assert success
        assert file1.exists()  # Should remain
        assert not file2.exists()  # Should be removed
        assert not file3.exists()  # Should be removed
        assert len(recovery_manager.recovery_points) == 1
        assert recovery_manager.current_point_id == point1.id

    def test_rollback_all(self, recovery_manager, temp_dir):
        """Test full rollback."""
        # Create test files
        file1 = temp_dir / "file1.txt"
        file2 = temp_dir / "file2.txt"
        dir1 = temp_dir / "dir1"

        # Create recovery points with files
        point1 = recovery_manager.create_recovery_point("phase1", "First phase")
        file1.write_text("content1")
        recovery_manager.track_created_path(file1)

        point2 = recovery_manager.create_recovery_point("phase2", "Second phase")
        file2.write_text("content2")
        dir1.mkdir()
        recovery_manager.track_created_path(file2)
        recovery_manager.track_created_path(dir1)

        # All should exist
        assert file1.exists()
        assert file2.exists()
        assert dir1.exists()

        # Full rollback
        success = recovery_manager.rollback_all()

        assert success
        assert not file1.exists()
        assert not file2.exists()
        assert not dir1.exists()
        assert len(recovery_manager.recovery_points) == 0
        assert recovery_manager.current_point_id is None

    def test_suggest_recovery_strategy(self, recovery_manager):
        """Test recovery strategy suggestions."""
        # Permission error -> full rollback
        error = PermissionError("Permission denied")
        strategy = recovery_manager.suggest_recovery_strategy(error, "files", {})
        assert strategy == RecoveryStrategy.FULL_ROLLBACK

        # Path exists -> partial recovery
        error = FileExistsError("Path already exists")
        strategy = recovery_manager.suggest_recovery_strategy(error, "files", {})
        assert strategy == RecoveryStrategy.PARTIAL_RECOVERY

        # Network error -> retry
        error = ConnectionError("Connection failed")
        strategy = recovery_manager.suggest_recovery_strategy(error, "download", {})
        assert strategy == RecoveryStrategy.RETRY_OPERATION

        # Git error with files created -> skip
        error = RuntimeError("Git init failed")
        strategy = recovery_manager.suggest_recovery_strategy(
            error, "git_init", {"files_created": True}
        )
        assert strategy == RecoveryStrategy.SKIP_AND_CONTINUE

        # Unknown error -> full rollback
        error = ValueError("Unknown error")
        strategy = recovery_manager.suggest_recovery_strategy(error, "unknown", {})
        assert strategy == RecoveryStrategy.FULL_ROLLBACK

    def test_create_recovery_context(self, recovery_manager, temp_dir):
        """Test creating recovery context."""
        # Create some recovery points
        point1 = recovery_manager.create_recovery_point("init", "Init")
        point2 = recovery_manager.create_recovery_point("files", "Files")

        # Create context
        error = ValueError("Test error")
        context = recovery_manager.create_recovery_context(
            error=error,
            phase="validation",
            failed_operation="validate_input",
            target_path=temp_dir / "project",
            template_name="test_template",
            project_variables={"name": "test", "email": "test@example.com"},
            partial_results={"files_created": 5},
        )

        assert context.error == error
        assert context.current_phase == "validation"
        assert context.failed_operation == "validate_input"
        assert context.target_path == temp_dir / "project"
        assert context.template_name == "test_template"
        assert context.project_variables["name"] == "test"
        assert context.partial_results["files_created"] == 5
        assert len(context.recovery_points) == 2
        assert context.suggested_strategy == RecoveryStrategy.FULL_ROLLBACK

        # Check error log was saved
        log_files = list((temp_dir / "logs").glob("error_*.json"))
        assert len(log_files) == 1

        # Verify log content
        with open(log_files[0]) as f:
            log_data = json.load(f)

        assert log_data["error"]["type"] == "ValueError"
        assert log_data["error"]["message"] == "Test error"
        assert log_data["project"]["template"] == "test_template"
        assert log_data["project"]["variables"]["email"] == "[REDACTED]"  # Sanitized

    def test_execute_recovery_full_rollback(self, recovery_manager, temp_dir):
        """Test executing full rollback recovery."""
        # Create test file
        test_file = temp_dir / "test.txt"
        point = recovery_manager.create_recovery_point("test", "Test")
        test_file.write_text("content")
        recovery_manager.track_created_path(test_file)

        # Create context
        context = RecoveryContext(
            error=ValueError("Test"),
            recovery_points=recovery_manager.recovery_points,
            current_phase="test",
            failed_operation="test_op",
            target_path=temp_dir,
            template_name="test",
            project_variables={},
        )

        # Execute full rollback
        success, message = recovery_manager.execute_recovery(
            context, RecoveryStrategy.FULL_ROLLBACK
        )

        assert success
        assert "rolled back successfully" in message.lower()
        assert not test_file.exists()
        assert len(recovery_manager.recovery_points) == 0

    def test_execute_recovery_partial(self, recovery_manager):
        """Test executing partial recovery."""
        # Create recovery points
        point1 = recovery_manager.create_recovery_point("phase1", "Phase 1")
        point2 = recovery_manager.create_recovery_point("phase2", "Phase 2")
        point3 = recovery_manager.create_recovery_point("phase3", "Phase 3")

        # Create context with current phase as phase3
        context = RecoveryContext(
            error=ValueError("Test"),
            recovery_points=recovery_manager.recovery_points,
            current_phase="phase3",
            failed_operation="test_op",
            target_path=Path("/tmp"),
            template_name="test",
            project_variables={},
        )

        # Execute partial recovery
        success, message = recovery_manager.execute_recovery(
            context, RecoveryStrategy.PARTIAL_RECOVERY
        )

        assert success
        assert "Rolled back to: Phase 2" in message
        assert len(recovery_manager.recovery_points) == 2

    def test_execute_recovery_skip(self, recovery_manager):
        """Test executing skip and continue recovery."""
        # Create recovery point
        point = recovery_manager.create_recovery_point("test", "Test")

        # Create context
        context = RecoveryContext(
            error=ValueError("Test"),
            recovery_points=recovery_manager.recovery_points,
            current_phase="test",
            failed_operation="optional_step",
            target_path=Path("/tmp"),
            template_name="test",
            project_variables={},
        )

        # Execute skip and continue
        success, message = recovery_manager.execute_recovery(
            context, RecoveryStrategy.SKIP_AND_CONTINUE
        )

        assert success
        assert "Skipped optional_step" in message
        assert point.state_data.get("skipped") is True

    def test_execute_recovery_retry(self, recovery_manager):
        """Test executing retry recovery."""
        # Create context
        context = RecoveryContext(
            error=ConnectionError("Network error"),
            recovery_points=[],
            current_phase="download",
            failed_operation="fetch_resource",
            target_path=Path("/tmp"),
            template_name="test",
            project_variables={},
        )

        # Execute retry
        success, message = recovery_manager.execute_recovery(
            context, RecoveryStrategy.RETRY_OPERATION
        )

        assert success
        assert "Ready to retry" in message

    def test_sanitize_variables(self, recovery_manager):
        """Test sanitizing sensitive variables."""
        variables = {
            "name": "test_project",
            "email": "user@example.com",
            "password": "secret123",
            "api_token": "token456",
            "secret_key": "key789",
            "description": "Normal description",
        }

        sanitized = recovery_manager._sanitize_variables(variables)

        assert sanitized["name"] == "test_project"
        assert sanitized["email"] == "[REDACTED]"
        assert sanitized["password"] == "[REDACTED]"
        assert sanitized["api_token"] == "[REDACTED]"
        assert sanitized["secret_key"] == "[REDACTED]"
        assert sanitized["description"] == "Normal description"
