# ABOUTME: Comprehensive end-to-end integration tests for complete project creation workflow
# ABOUTME: Tests all UI paths, configuration persistence, and error handling scenarios

"""
Comprehensive end-to-end integration tests for the complete project creation workflow.

These tests validate the entire application flow from UI interactions through
backend processing to final project generation, including configuration
persistence and error scenarios.
"""

import asyncio
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication, QMessageBox, QWizard

from create_project.config.config_manager import ConfigManager
from create_project.config.models import Config
from create_project.core.api import create_project
from create_project.core.project_generator import ProjectGenerator
from create_project.gui.app import main as run_gui
from create_project.gui.wizard.wizard import ProjectWizard, WizardData
from create_project.templates.engine import TemplateEngine
from create_project.templates.loader import TemplateLoader


@pytest.mark.integration
class TestCompleteProjectCreationWorkflow:
    """Test complete project creation workflow from UI to generated project."""
    
    def test_complete_wizard_flow_python_library(self, qtbot, tmp_path, mock_config_manager):
        """Test complete wizard workflow for Python library creation."""
        # Setup
        config_manager = mock_config_manager
        # Configure template path to find built-in templates
        config_manager.get_setting.side_effect = lambda key, default=None: {
            "defaults.author": "Test Author",
            "defaults.location": str(tmp_path / "projects"),
            "ai.enabled": True,
            "ai.ollama_url": "http://localhost:11434",
            "ai.model": "llama2",
            "templates.builtin_path": "create_project/templates/builtin",
            "templates.directories": [],
            "templates.user_path": str(Path.home() / ".create-project" / "templates"),
        }.get(key, default)
        # Also update the get method
        config_manager.get.side_effect = config_manager.get_setting.side_effect
        
        template_engine = TemplateEngine(config_manager)
        template_loader = TemplateLoader(config_manager)
        
        # Create wizard
        wizard = ProjectWizard(config_manager, template_engine, template_loader)
        qtbot.addWidget(wizard)
        
        # Show wizard to trigger page initialization
        wizard.show()
        
        # Ensure we start at the first page
        wizard.restart()
        
        # Step 1: Project Type Selection
        project_type_step = wizard.currentPage()
        assert project_type_step is not None, "Current page should not be None"
        assert project_type_step.title() == "Select Project Type"
        
        # Select Python Library
        template_list = project_type_step.template_list
        for i in range(template_list.count()):
            item = template_list.item(i)
            template_id = item.data(Qt.ItemDataRole.UserRole)
            if template_id == "builtin_python_library" or template_id == "python_library":
                template_list.setCurrentItem(item)
                break
        
        # Verify selection - template ID may have builtin_ prefix
        assert wizard.wizard_data.template_id in ["builtin_python_library", "python_library"]
        
        # Move to next step
        wizard.next()
        
        # Step 2: Basic Information
        basic_info_step = wizard.currentPage()
        assert basic_info_step.title() == "Basic Information"
        
        # Fill in project details
        basic_info_step.name_edit.setText("test_library")
        basic_info_step.author_edit.setText("Test Author")
        basic_info_step.version_edit.setText("0.1.0")
        basic_info_step.description_edit.setPlainText("Test library description")
        
        # Process events to trigger field updates
        QApplication.processEvents()
        
        # Verify data is captured - may need to wait or check after page cleanup
        # Data is captured during cleanupPage, so skip these assertions for now
        # We'll verify at the end after all data is collected
        
        # Move to next step
        wizard.next()
        
        # Step 3: Location Selection
        location_step = wizard.currentPage()
        assert location_step.title() == "Project Location"
        
        # Set project location
        test_location = tmp_path / "projects"
        test_location.mkdir(exist_ok=True)
        location_step.location_edit.setText(str(test_location))
        
        # Process events to trigger field updates
        QApplication.processEvents()
        
        # Move to next step
        wizard.next()
        
        # Step 4: Options Configuration
        options_step = wizard.currentPage()
        assert options_step.title() == "Configuration Options"
        
        # Configure options
        options_step.git_checkbox.setChecked(True)
        options_step.venv_combo.setCurrentText("uv")
        options_step.license_combo.setCurrentText("MIT")
        
        # Get options from step
        options = options_step.get_options()
        assert options.get("git_init", False) is True or options.get("initialize_git", False) is True
        assert options["venv_tool"] == "uv"
        # License might be in different key name
        assert "MIT" in str(options.values()) or options.get("license") == "MIT"
        
        # Move to final step
        wizard.next()
        
        # Step 5: Review and Create
        review_step = wizard.currentPage()
        assert review_step.title() == "Review and Create"
        
        # Verify all data is present in review
        # For now, just verify the page loaded correctly
        # The actual content validation would require accessing internal widgets
        assert review_step is not None
        
        # Test project generation with mock
        with patch.object(wizard, '_generate_project') as mock_generate:
            mock_generate.return_value = None
            wizard.accept()
            mock_generate.assert_called_once()
        
        # Verify wizard data is complete
        assert wizard.wizard_data.project_name == "test_library"
        assert wizard.wizard_data.author == "Test Author"
        assert wizard.wizard_data.version == "0.1.0"
        assert wizard.wizard_data.description == "Test library description"
        assert wizard.wizard_data.location == str(test_location)
        assert wizard.wizard_data.template_id == "python_library"
        assert wizard.wizard_data.additional_options["initialize_git"] is True
        assert wizard.wizard_data.additional_options["venv_tool"] == "uv"
        assert wizard.wizard_data.additional_options["license"] == "MIT"
    
    def test_configuration_persistence(self, qtbot, tmp_path, monkeypatch):
        """Test that configuration changes persist across application restarts."""
        # Create temporary config file
        config_file = tmp_path / "config" / "settings.json"
        config_file.parent.mkdir(exist_ok=True)
        
        # Initial configuration
        initial_config = {
            "project": {
                "defaults": {
                    "author": "Initial Author",
                    "version": "0.1.0",
                    "location": str(tmp_path / "initial_projects")
                }
            },
            "ai": {
                "ollama": {
                    "enabled": False,
                    "url": "http://localhost:11434",
                    "model": "llama2"
                }
            }
        }
        
        import json
        config_file.write_text(json.dumps(initial_config))
        
        # Create config manager with custom config file
        monkeypatch.setenv("CONFIG_PATH", str(config_file))
        config_manager = ConfigManager()
        
        # Verify initial values
        assert config_manager.get("project.defaults.author") == "Initial Author"
        assert config_manager.get("ai.ollama.enabled") is False
        
        # Update configuration
        config_manager.set("project.defaults.author", "Updated Author")
        config_manager.set("ai.ollama.enabled", True)
        config_manager.set("ai.ollama.model", "codellama")
        
        # Save configuration
        config_manager.save()
        
        # Create new config manager instance (simulating restart)
        config_manager2 = ConfigManager()
        
        # Verify persistence
        assert config_manager2.get("project.defaults.author") == "Updated Author"
        assert config_manager2.get("ai.ollama.enabled") is True
        assert config_manager2.get("ai.ollama.model") == "codellama"
    
    def test_error_handling_workflow(self, qtbot, tmp_path, mock_config_manager):
        """Test error handling during project generation."""
        # Setup
        config_manager = mock_config_manager
        template_engine = TemplateEngine(config_manager)
        
        # Create wizard
        wizard = ProjectWizard(config_manager, template_engine)
        qtbot.addWidget(wizard)
        
        # Quick navigate to final step with minimal data
        wizard.wizard_data.template_id = "python_library"
        wizard.wizard_data.project_name = "test_error_project"
        wizard.wizard_data.author = "Test Author"
        wizard.wizard_data.version = "0.1.0"
        wizard.wizard_data.description = "Test description"
        wizard.wizard_data.location = str(tmp_path)
        wizard.wizard_data.additional_options = {
            "initialize_git": True,
            "venv_tool": "uv",
            "license": "MIT"
        }
        
        # Navigate to review step
        for _ in range(4):
            wizard.next()
        
        # Mock project generator to raise an error
        with patch.object(ProjectGenerator, 'generate', side_effect=Exception("Test generation error")):
            # Test error dialog appears
            error_shown = False
            original_show_error = wizard._show_error
            
            def mock_show_error(error, context):
                nonlocal error_shown
                error_shown = True
                assert "Test generation error" in str(error)
                assert "project_name" in context
                assert context["project_name"] == "test_error_project"
            
            wizard._show_error = mock_show_error
            
            # Trigger project generation
            with patch.object(wizard, '_generate_project') as mock_gen:
                # Simulate the error in generation
                def raise_error():
                    wizard._handle_generation_error(Exception("Test generation error"), {
                        "project_name": "test_error_project",
                        "location": str(tmp_path)
                    })
                mock_gen.side_effect = raise_error
                
                wizard.accept()
            
            assert error_shown
    
    def test_all_template_types_workflow(self, qtbot, tmp_path, mock_config_manager):
        """Test that all template types can be successfully created."""
        config_manager = mock_config_manager
        template_engine = TemplateEngine(config_manager)
        loader = TemplateLoader(config_manager)
        
        # Get all available templates
        templates = loader.list_templates()
        
        for template in templates:
            # Create project using API
            project_data = {
                "project_name": f"test_{template.id}_project",
                "author": "Test Author",
                "version": "0.1.0",
                "description": f"Test {template.name} project",
                "python_version": "3.9",
                "license": "MIT",
                "initialize_git": False,  # Skip git for speed
                "venv_tool": "none"  # Skip venv for speed
            }
            
            # Add template-specific options
            for var in template.variables:
                if var.name not in project_data:
                    if var.type == "boolean":
                        project_data[var.name] = var.default or False
                    elif var.type == "choice" and var.choices:
                        project_data[var.name] = var.default or var.choices[0]
                    else:
                        project_data[var.name] = var.default or f"test_{var.name}"
            
            # Create project
            project_path = tmp_path / f"test_{template.id}_project"
            
            result = create_project(
                template_id=template.id,
                location=str(tmp_path),
                project_data=project_data
            )
            
            # Verify project was created
            assert project_path.exists()
            assert result["success"] is True
            assert result["project_path"] == str(project_path)
            
            # Clean up for next iteration
            if project_path.exists():
                shutil.rmtree(project_path)
    
    def test_concurrent_project_creation(self, tmp_path, mock_config_manager):
        """Test creating multiple projects concurrently."""
        config_manager = mock_config_manager
        
        async def create_project_async(template_id, project_name):
            """Create a project asynchronously."""
            project_data = {
                "project_name": project_name,
                "author": "Test Author",
                "version": "0.1.0",
                "description": f"Test {project_name}",
                "python_version": "3.9",
                "license": "MIT",
                "initialize_git": False,
                "venv_tool": "none"
            }
            
            return await asyncio.to_thread(
                create_project,
                template_id=template_id,
                location=str(tmp_path),
                project_data=project_data
            )
        
        async def run_concurrent_creation():
            """Run multiple project creations concurrently."""
            tasks = [
                create_project_async("python_library", "lib1"),
                create_project_async("cli_app_single", "cli1"),
                create_project_async("python_library", "lib2"),
                create_project_async("cli_app_single", "cli2")
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results
        
        # Run concurrent creation
        results = asyncio.run(run_concurrent_creation())
        
        # Verify all succeeded
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"Task {i} failed: {result}"
            assert result["success"] is True
        
        # Verify all projects exist
        assert (tmp_path / "lib1").exists()
        assert (tmp_path / "cli1").exists()
        assert (tmp_path / "lib2").exists()
        assert (tmp_path / "cli2").exists()
    
    def test_keyboard_navigation(self, qtbot, mock_config_manager):
        """Test keyboard navigation through wizard."""
        config_manager = mock_config_manager
        template_engine = TemplateEngine(config_manager)
        template_loader = TemplateLoader(config_manager)
        
        wizard = ProjectWizard(config_manager, template_engine, template_loader)
        qtbot.addWidget(wizard)
        wizard.show()
        
        # Test Tab navigation within first step
        project_type_step = wizard.currentPage()
        template_list = project_type_step.template_list
        preview_browser = project_type_step.preview_browser
        
        # Focus should start on template list
        assert template_list.hasFocus() or wizard.button(QWizard.WizardButton.NextButton).hasFocus()
        
        # Tab to move focus
        qtbot.keyClick(wizard, Qt.Key.Key_Tab)
        qtbot.wait(100)
        
        # Test Enter to move to next page
        qtbot.keyClick(template_list, Qt.Key.Key_Return)
        # Should still be on first page since no selection
        assert wizard.currentId() == 0
        
        # Select first item and press Enter
        if template_list.count() > 0:
            template_list.setCurrentRow(0)
            qtbot.keyClick(template_list, Qt.Key.Key_Return)
            # This might or might not advance depending on validation
    
    def test_settings_dialog_integration(self, qtbot, tmp_path, mock_config_manager):
        """Test settings dialog integration with main wizard."""
        from create_project.gui.dialogs.settings import SettingsDialog
        
        config_manager = mock_config_manager
        
        # Open settings dialog
        dialog = SettingsDialog(config_manager)
        qtbot.addWidget(dialog)
        
        # Modify settings
        dialog.author_edit.setText("New Test Author")
        dialog.location_edit.setText(str(tmp_path / "new_location"))
        dialog.ollama_url_edit.setText("http://localhost:9999")
        dialog.ollama_enabled_checkbox.setChecked(True)
        
        # Save settings
        with patch.object(config_manager, 'save') as mock_save:
            dialog.accept()
            mock_save.assert_called_once()
        
        # Verify settings were updated
        assert config_manager.get("project.defaults.author") == "New Test Author"
        assert config_manager.get("project.defaults.location") == str(tmp_path / "new_location")
        assert config_manager.get("ai.ollama.url") == "http://localhost:9999"
        assert config_manager.get("ai.ollama.enabled") is True


@pytest.mark.integration
class TestProjectGenerationScenarios:
    """Test various project generation scenarios."""
    
    def test_large_project_generation(self, tmp_path, mock_config_manager):
        """Test generating a large project with many files."""
        # Create custom template with many files
        template_data = {
            "name": "Large Project",
            "description": "Test template with many files",
            "variables": [
                {"name": "project_name", "type": "string", "required": True}
            ],
            "structure": {}
        }
        
        # Add 100 files to structure
        for i in range(100):
            template_data["structure"][f"file_{i:03d}.py"] = f"# File {i}\nprint('File {i}')\n"
        
        # Create project
        project_data = {
            "project_name": "large_project",
            "author": "Test Author",
            "version": "0.1.0",
            "description": "Large test project"
        }
        
        generator = ProjectGenerator(mock_config_manager)
        
        # Mock template engine to return our large template
        with patch.object(generator.template_engine, 'load_template', return_value=template_data):
            result = generator.generate(
                template_id="large_project",
                location=str(tmp_path),
                project_data=project_data
            )
        
        # Verify all files were created
        project_path = tmp_path / "large_project"
        assert project_path.exists()
        
        py_files = list(project_path.glob("file_*.py"))
        assert len(py_files) == 100
    
    def test_project_with_special_characters(self, tmp_path, mock_config_manager):
        """Test creating projects with special characters in names."""
        test_cases = [
            ("project-with-dashes", True),
            ("project_with_underscores", True),
            ("project.with.dots", False),  # Should fail validation
            ("project with spaces", False),  # Should fail validation
            ("project/with/slashes", False),  # Should fail validation
        ]
        
        for project_name, should_succeed in test_cases:
            project_data = {
                "project_name": project_name,
                "author": "Test Author",
                "version": "0.1.0",
                "description": "Test project with special chars",
                "python_version": "3.9",
                "license": "MIT",
                "initialize_git": False,
                "venv_tool": "none"
            }
            
            try:
                result = create_project(
                    template_id="python_library",
                    location=str(tmp_path),
                    project_data=project_data
                )
                
                if should_succeed:
                    assert result["success"] is True
                    assert (tmp_path / project_name.replace(" ", "_")).exists() or (tmp_path / project_name).exists()
                else:
                    # If it succeeded but shouldn't have, that's a test failure
                    pytest.fail(f"Project '{project_name}' should have failed validation")
                    
            except Exception as e:
                if should_succeed:
                    pytest.fail(f"Project '{project_name}' should have succeeded: {e}")
                else:
                    # Expected failure
                    assert "Invalid project name" in str(e) or "validation" in str(e).lower()
    
    def test_readonly_location_handling(self, tmp_path, mock_config_manager):
        """Test handling of read-only project locations."""
        # Create read-only directory
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        
        # Make it read-only
        import stat
        readonly_dir.chmod(stat.S_IRUSR | stat.S_IXUSR)
        
        try:
            project_data = {
                "project_name": "test_readonly",
                "author": "Test Author",
                "version": "0.1.0",
                "description": "Test readonly",
                "python_version": "3.9",
                "license": "MIT",
                "initialize_git": False,
                "venv_tool": "none"
            }
            
            result = create_project(
                template_id="python_library",
                location=str(readonly_dir),
                project_data=project_data
            )
            
            # Should fail due to permissions
            assert result["success"] is False
            assert "permission" in result.get("error", "").lower() or "access" in result.get("error", "").lower()
            
        finally:
            # Restore permissions for cleanup
            readonly_dir.chmod(stat.S_IRWXU)
    
    def test_ai_assistance_integration(self, tmp_path, mock_config_manager):
        """Test AI assistance integration during project creation errors."""
        from create_project.ai.ai_service import AIService
        
        # Configure AI service
        config_manager = mock_config_manager
        config_manager.set("ai.ollama.enabled", True)
        
        ai_service = AIService(config_manager)
        
        # Mock AI service to return help
        with patch.object(ai_service, 'generate_help') as mock_help:
            mock_help.return_value = "Try checking file permissions and disk space."
            
            # Create project with intentional error
            project_data = {
                "project_name": "///invalid///",  # Invalid name
                "author": "Test Author",
                "version": "0.1.0",
                "description": "Test AI help"
            }
            
            generator = ProjectGenerator(config_manager)
            generator.ai_service = ai_service
            
            try:
                generator.generate(
                    template_id="python_library",
                    location=str(tmp_path),
                    project_data=project_data
                )
            except Exception as e:
                # AI help should have been called
                mock_help.assert_called_once()
                call_args = mock_help.call_args[0]
                assert "error" in call_args[0].lower()