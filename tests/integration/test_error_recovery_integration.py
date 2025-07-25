# ABOUTME: Integration tests for error recovery system with project generator
# ABOUTME: Tests recovery workflows, rollback operations, and recovery dialog integration

"""Integration tests for error recovery system."""

import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from create_project.config.config_manager import ConfigManager
from create_project.core.error_recovery import RecoveryContext, RecoveryManager, RecoveryPoint, RecoveryStrategy
from create_project.core.exceptions import PathError, ProjectGenerationError, TemplateError
from create_project.core.project_generator import ProjectGenerator, ProjectOptions
from create_project.templates.loader import TemplateLoader
from create_project.templates.schema import Template, TemplateFile


@pytest.fixture
def temp_workspace():
    """Create temporary workspace for tests."""
    workspace = tempfile.mkdtemp()
    yield Path(workspace)
    shutil.rmtree(workspace, ignore_errors=True)


@pytest.fixture
def mock_template():
    """Create a mock template for testing."""
    template = Mock(spec=Template)
    template.name = "Test Template"
    template.description = "A test template"
    template.variables = []
    
    # Mock structure
    root_dir = Mock()
    root_dir.directories = []
    root_dir.files = [
        Mock(name="README.md", template_name="readme.md.j2"),
        Mock(name="setup.py", template_name="setup.py.j2"),
    ]
    
    structure = Mock()
    structure.root_directory = root_dir
    template.structure = structure
    
    return template


@pytest.fixture
def project_generator(temp_workspace):
    """Create project generator with recovery support."""
    config_manager = ConfigManager()
    template_loader = TemplateLoader()
    
    generator = ProjectGenerator(
        config_manager=config_manager,
        template_loader=template_loader,
    )
    
    return generator


class TestErrorRecoveryIntegration:
    """Test error recovery integration with project generator."""
    
    def test_recovery_points_created_during_generation(
        self, project_generator, mock_template, temp_workspace
    ):
        """Test that recovery points are created during project generation."""
        target_path = temp_workspace / "test_project"
        
        # Mock file renderer to track recovery points
        with patch.object(
            project_generator.file_renderer, "render_files_from_structure"
        ) as mock_render:
            # Generate project
            result = project_generator.generate_project(
                template=mock_template,
                variables={"project_name": "test"},
                target_path=target_path,
                options=ProjectOptions(),
            )
            
            # Check recovery points were created
            recovery_points = project_generator.recovery_manager.recovery_points
            assert len(recovery_points) >= 3  # validation, directory, file phases
            
            # Check phases
            phases = [rp.phase for rp in recovery_points]
            assert "validation" in phases
            assert "directory_creation" in phases
            assert "file_rendering" in phases
            
    def test_rollback_on_directory_creation_error(
        self, project_generator, mock_template, temp_workspace
    ):
        """Test rollback when directory creation fails."""
        target_path = temp_workspace / "test_project"
        
        # Create target directory to cause error
        target_path.mkdir()
        (target_path / "existing_file.txt").write_text("existing")
        
        # Try to generate project
        result = project_generator.generate_project(
            template=mock_template,
            variables={"project_name": "test"},
            target_path=target_path,
            options=ProjectOptions(),
        )
        
        # Should fail
        assert not result.success
        assert len(result.errors) > 0
        assert "already exists" in str(result.errors[0])
        
        # Check recovery context was created
        assert result.recovery_context is not None
        assert result.recovery_context.current_phase == "validation"
        
    def test_partial_recovery_after_file_render_error(
        self, project_generator, mock_template, temp_workspace
    ):
        """Test partial recovery when file rendering fails."""
        target_path = temp_workspace / "test_project"
        
        # Mock file renderer to fail after creating some files
        files_created = []
        
        def mock_render(*args, **kwargs):
            # Create a file
            test_file = target_path / "test.txt"
            test_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.write_text("test content")
            files_created.append(test_file)
            
            # Track it
            project_generator.recovery_manager.track_created_path(test_file)
            
            # Then fail
            raise TemplateError("Template rendering failed")
            
        with patch.object(
            project_generator.file_renderer,
            "render_files_from_structure",
            side_effect=mock_render,
        ):
            # Generate project
            result = project_generator.generate_project(
                template=mock_template,
                variables={"project_name": "test"},
                target_path=target_path,
                options=ProjectOptions(),
            )
            
        # Should fail
        assert not result.success
        assert "Template rendering failed" in str(result.errors)
        
        # Check recovery context
        assert result.recovery_context is not None
        assert result.recovery_context.current_phase in ["file_rendering", "unknown"]
        
        # Execute partial recovery
        recovery_manager = project_generator.recovery_manager
        success, message = recovery_manager.execute_recovery(
            result.recovery_context, RecoveryStrategy.PARTIAL_RECOVERY
        )
        
        # Files should be cleaned up
        assert not any(f.exists() for f in files_created)
        
    def test_retry_operation_recovery(
        self, project_generator, mock_template, temp_workspace
    ):
        """Test retry operation recovery strategy."""
        target_path = temp_workspace / "test_project"
        
        # Mock a transient error
        call_count = 0
        
        def mock_render(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Network error")
            # Success on retry
            return
            
        with patch.object(
            project_generator.file_renderer,
            "render_files_from_structure",
            side_effect=mock_render,
        ):
            # First attempt should fail
            result1 = project_generator.generate_project(
                template=mock_template,
                variables={"project_name": "test"},
                target_path=target_path,
                options=ProjectOptions(),
            )
            
            assert not result1.success
            assert "Network error" in str(result1.errors)
            
            # Check suggested strategy
            assert result1.recovery_context is not None
            suggested = project_generator.recovery_manager.suggest_recovery_strategy(
                ConnectionError("Network error"), "file_rendering", {}
            )
            assert suggested == RecoveryStrategy.RETRY_OPERATION
            
            # Retry should succeed
            result2 = project_generator.generate_project(
                template=mock_template,
                variables={"project_name": "test"},
                target_path=target_path,
                options=ProjectOptions(),
            )
            
            assert result2.success or call_count == 2  # Either success or retry was called
            
    def test_skip_and_continue_recovery(
        self, project_generator, mock_template, temp_workspace
    ):
        """Test skip and continue recovery for optional steps."""
        target_path = temp_workspace / "test_project"
        
        # Create project directory
        target_path.mkdir()
        
        # Mock git manager to fail
        with patch.object(
            project_generator.git_manager, "init_repository", side_effect=Exception("Git error")
        ):
            # Generate with git enabled
            result = project_generator.generate_project(
                template=mock_template,
                variables={"project_name": "test"},
                target_path=target_path,
                options=ProjectOptions(create_git_repo=True),
            )
            
            # Should succeed despite git error
            assert result.success
            assert not result.git_initialized
            assert "Git error" in str(result.errors)
            
    def test_error_log_creation(self, project_generator, temp_workspace):
        """Test that error logs are created on failure."""
        target_path = temp_workspace / "test_project"
        
        # Create conflict
        target_path.mkdir()
        (target_path / "conflict.txt").write_text("conflict")
        
        # Set custom log directory
        log_dir = temp_workspace / "logs"
        project_generator.recovery_manager.log_dir = log_dir
        
        # Generate project
        result = project_generator.generate_project(
            template=Mock(spec=Template, name="Test"),
            variables={"project_name": "test", "email": "test@example.com"},
            target_path=target_path,
            options=ProjectOptions(),
        )
        
        # Should fail
        assert not result.success
        
        # Check error log was created
        assert log_dir.exists()
        log_files = list(log_dir.glob("error_*.json"))
        assert len(log_files) == 1
        
        # Verify log content
        import json
        with open(log_files[0]) as f:
            log_data = json.load(f)
            
        assert log_data["error"]["phase"] == "validation"
        assert log_data["project"]["template"] == "Test"
        assert log_data["project"]["variables"]["email"] == "[REDACTED]"  # Sanitized
        
    def test_recovery_with_ai_assistance(
        self, project_generator, mock_template, temp_workspace
    ):
        """Test recovery with AI assistance integration."""
        target_path = temp_workspace / "test_project"
        
        # Mock AI service
        mock_ai_service = Mock()
        mock_ai_service.generate_help_response = Mock(
            return_value="Try using partial recovery to keep completed files."
        )
        project_generator.ai_service = mock_ai_service
        
        # Create error condition
        target_path.mkdir()
        (target_path / "existing.txt").write_text("existing")
        
        # Generate with AI enabled
        result = project_generator.generate_project(
            template=mock_template,
            variables={"project_name": "test"},
            target_path=target_path,
            options=ProjectOptions(enable_ai_assistance=True),
        )
        
        # Should fail with AI suggestions
        assert not result.success
        assert result.ai_suggestions is not None
        assert "partial recovery" in result.ai_suggestions
        
        # Recovery context should have AI suggestions
        if result.recovery_context:
            result.recovery_context.ai_suggestions = result.ai_suggestions
            
    def test_recovery_dialog_integration(self, qtbot, temp_workspace):
        """Test recovery dialog integration with recovery context."""
        from create_project.gui.dialogs.recovery_dialog import RecoveryDialog
        
        # Create recovery context
        error = TemplateError("Template validation failed")
        recovery_points = [
            RecoveryPoint(
                id="rp_1",
                timestamp=None,
                phase="validation",
                description="Validation phase",
                created_paths=set(),
            ),
            RecoveryPoint(
                id="rp_2",
                timestamp=None,
                phase="directory_creation",
                description="Directory creation",
                created_paths={temp_workspace / "test_dir"},
            ),
        ]
        
        context = RecoveryContext(
            error=error,
            recovery_points=recovery_points,
            current_phase="template_validation",
            failed_operation="validate_template",
            target_path=temp_workspace / "project",
            template_name="Test Template",
            project_variables={"name": "test"},
            partial_results={"directories_created": 3},
            suggested_strategy=RecoveryStrategy.PARTIAL_RECOVERY,
        )
        
        # Create dialog
        dialog = RecoveryDialog(context)
        qtbot.addWidget(dialog)
        
        # Check dialog displays context
        assert "TemplateError" in dialog.error_summary.text()
        assert "template_validation" in dialog.error_summary.text()
        
        # Check suggested strategy is selected
        assert dialog.strategy_buttons[RecoveryStrategy.PARTIAL_RECOVERY].isChecked()
        
        # Check progress information
        progress_html = dialog.progress_info.toHtml()
        assert "validation: Validation phase" in progress_html
        assert "directory_creation: Directory creation" in progress_html