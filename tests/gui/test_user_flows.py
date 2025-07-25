# ABOUTME: Complete user workflow scenarios for the create-project wizard
# ABOUTME: Tests end-to-end flows for all template types and error scenarios

"""Complete user workflow scenarios for the create-project wizard."""

import pytest

pytestmark = [pytest.mark.gui, pytest.mark.workflow]
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from pathlib import Path
import tempfile

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication, QMessageBox, QFileDialog, QLabel
from PyQt6.QtTest import QTest

from create_project.gui.wizard.wizard import ProjectWizard
from create_project.gui.dialogs.settings import SettingsDialog
from create_project.gui.dialogs.error import ErrorDialog
from create_project.gui.dialogs.ai_help import AIHelpDialog
from create_project.gui.dialogs.recovery_dialog import RecoveryDialog
from create_project.gui.widgets.progress_dialog import ProgressDialog
from create_project.core.error_recovery import RecoveryStrategy
from create_project.templates.schema.template import Template
from create_project.templates.schema.variables import TemplateVariable
from create_project.core.exceptions import ProjectGenerationError


class WizardTestHelper:
    """Helper class for wizard workflow testing."""
    
    def __init__(self, wizard, qtbot):
        self.wizard = wizard
        self.qtbot = qtbot
    
    def select_template(self, index):
        """Select a template by index."""
        project_type = self.wizard.currentPage()
        project_type.template_list.setCurrentRow(index)
        self.wizard.next()
    
    def fill_basic_info(self, name, author, version="1.0.0", description="Test project"):
        """Fill in basic information."""
        basic_info = self.wizard.currentPage()
        basic_info.name_edit.setText(name)
        basic_info.author_edit.setText(author)
        basic_info.version_edit.setText(version)
        basic_info.description_edit.setPlainText(description)
        self.wizard.next()
    
    def set_location(self, path):
        """Set project location."""
        location = self.wizard.currentPage()
        location.location_edit.setText(path)
        self.wizard.next()
    
    def configure_options(self, git=True, venv_tool="uv", license_type="MIT"):
        """Configure project options."""
        options = self.wizard.currentPage()
        options.git_checkbox.setChecked(git)
        
        # Set venv tool
        for i in range(options.venv_combo.count()):
            if options.venv_combo.itemText(i) == venv_tool:
                options.venv_combo.setCurrentIndex(i)
                break
        
        # Set license
        for i in range(options.license_combo.count()):
            if options.license_combo.itemText(i) == license_type:
                options.license_combo.setCurrentIndex(i)
                break
        
        self.wizard.next()
    
    def complete_wizard(self):
        """Complete the wizard by clicking create."""
        review = self.wizard.currentPage()
        # The create button is the Finish button in the wizard
        finish_button = self.wizard.button(self.wizard.FinishButton)
        self.qtbot.mouseClick(finish_button, Qt.MouseButton.LeftButton)


class TestUserWorkflowScenarios:
    """Test complete user workflow scenarios."""

    def test_python_library_workflow(self, qtbot, mock_config_manager, mock_template_engine):
        """Test complete workflow for creating a Python library project."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine)
        qtbot.addWidget(wizard)
        wizard.show()
        qtbot.waitForWindowShown(wizard)
        
        helper = WizardTestHelper(wizard, qtbot)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Complete workflow
            helper.select_template(0)  # Python Library/Package
            helper.fill_basic_info("my_library", "Test Author", "0.1.0", "A test Python library")
            helper.set_location(temp_dir)
            helper.configure_options(git=True, venv_tool="uv", license_type="MIT")
            
            # Mock the project generation
            with patch.object(wizard, '_start_project_generation'):
                helper.complete_wizard()
            
            # Verify wizard data
            data = wizard.get_wizard_data()
            assert data.project_name == "my_library"
            assert data.author == "Test Author"
            assert data.version == "0.1.0"
            assert data.git_init is True

    def test_cli_app_workflow(self, qtbot, mock_config_manager, mock_template_engine):
        """Test complete workflow for creating a CLI application."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine)
        qtbot.addWidget(wizard)
        wizard.show()
        
        helper = WizardTestHelper(wizard, qtbot)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Complete workflow
            helper.select_template(1)  # CLI Application
            helper.fill_basic_info("my_cli_app", "CLI Developer", "1.0.0", "A command-line tool")
            helper.set_location(temp_dir)
            helper.configure_options(git=True, venv_tool="virtualenv", license_type="Apache-2.0")
            
            # Mock the project generation
            with patch.object(wizard, '_start_project_generation'):
                helper.complete_wizard()
            
            # Verify wizard data
            data = wizard.get_wizard_data()
            assert data.project_name == "my_cli_app"
            assert data.license_type == "Apache-2.0"

    def test_flask_web_app_workflow(self, qtbot, mock_config_manager, mock_template_engine):
        """Test complete workflow for creating a Flask web application."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine)
        qtbot.addWidget(wizard)
        wizard.show()
        
        helper = WizardTestHelper(wizard, qtbot)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Complete workflow for Flask app
            helper.select_template(3)  # Flask Web App
            helper.fill_basic_info("my_flask_app", "Web Developer", "1.0.0", "A Flask web application")
            helper.set_location(temp_dir)
            
            # Configure Flask-specific options
            options = wizard.currentPage()
            options.git_checkbox.setChecked(True)
            options.license_combo.setCurrentText("MIT")
            
            # Set Flask-specific template variables if they exist
            for widget_name, widget in options.template_widgets.items():
                if widget_name == "use_blueprints" and hasattr(widget, 'setChecked'):
                    widget.setChecked(True)
                elif widget_name == "use_sqlalchemy" and hasattr(widget, 'setChecked'):
                    widget.setChecked(True)
            
            wizard.next()
            
            # Mock the project generation
            with patch.object(wizard, '_start_project_generation'):
                helper.complete_wizard()
            
            # Verify wizard data
            data = wizard.get_wizard_data()
            assert data.project_name == "my_flask_app"

    def test_cancel_workflow(self, qtbot, mock_config_manager, mock_template_engine):
        """Test canceling the wizard at various stages."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine)
        qtbot.addWidget(wizard)
        wizard.show()
        
        helper = WizardTestHelper(wizard, qtbot)
        
        # Cancel at project type selection
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes):
            wizard.reject()
        
        assert wizard.result() == wizard.DialogCode.Rejected

    def test_validation_error_workflow(self, qtbot, mock_config_manager, mock_template_engine):
        """Test workflow with validation errors."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine)
        qtbot.addWidget(wizard)
        wizard.show()
        
        helper = WizardTestHelper(wizard, qtbot)
        
        # Select template
        helper.select_template(0)
        
        # Try to proceed with invalid data
        basic_info = wizard.currentPage()
        basic_info.name_edit.setText("invalid-project-name!")  # Invalid characters
        basic_info.author_edit.setText("")  # Empty author
        
        # Try to go next - should fail validation
        current_page = wizard.currentId()
        wizard.next()
        
        # Should still be on the same page
        assert wizard.currentId() == current_page
        
        # Fix the errors
        basic_info.name_edit.setText("valid_project_name")
        basic_info.author_edit.setText("Valid Author")
        
        # Now should be able to proceed
        wizard.next()
        assert wizard.currentId() == current_page + 1

    def test_settings_configuration_workflow(self, qtbot, mock_config_manager):
        """Test settings configuration workflow."""
        dialog = SettingsDialog(mock_config_manager)
        qtbot.addWidget(dialog)
        dialog.show()
        qtbot.waitForWindowShown(dialog)
        
        # Configure general settings
        dialog.author_edit.setText("New Default Author")
        dialog.location_edit.setText("/new/default/location")
        
        # Configure AI settings
        dialog.tab_widget.setCurrentIndex(1)
        dialog.ollama_url_edit.setText("http://localhost:11434")
        dialog.model_combo.setCurrentText("codellama")
        
        # Configure template paths
        dialog.tab_widget.setCurrentIndex(2)
        dialog.add_template_path("/custom/templates")
        
        # Save settings
        with patch.object(mock_config_manager, 'save'):
            dialog.accept()
        
        assert dialog.result() == dialog.DialogCode.Accepted

    def test_error_recovery_workflow(self, qtbot, mock_config_manager, mock_template_engine):
        """Test error handling and recovery workflow."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine)
        qtbot.addWidget(wizard)
        wizard.show()
        
        helper = WizardTestHelper(wizard, qtbot)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Complete workflow setup
            helper.select_template(0)
            helper.fill_basic_info("error_test_project", "Test Author")
            helper.set_location(temp_dir)
            helper.configure_options()
            
            # Mock project generation to fail
            error = ProjectGenerationError("Failed to create directory")
            
            with patch.object(wizard, '_start_project_generation') as mock_gen:
                # Simulate error during generation
                mock_gen.side_effect = lambda: wizard._on_generation_error(error, {"phase": "directory_creation"})
                
                # Click create
                helper.complete_wizard()
                
                # Error dialog should appear
                # In real scenario, ErrorDialog would be shown

    def test_progress_monitoring_workflow(self, qtbot):
        """Test progress monitoring during project generation."""
        progress_dialog = ProgressDialog("Creating Project", parent=None)
        qtbot.addWidget(progress_dialog)
        progress_dialog.show()
        qtbot.waitForWindowShown(progress_dialog)
        
        # Simulate progress updates
        updates = [
            (10, "Creating directory structure..."),
            (30, "Rendering template files..."),
            (50, "Initializing Git repository..."),
            (70, "Creating virtual environment..."),
            (90, "Running post-creation commands..."),
            (100, "Project created successfully!")
        ]
        
        for progress, message in updates:
            progress_dialog.update_progress(progress)
            progress_dialog.add_log_entry(message)
            qtbot.wait(100)  # Small delay to see updates
        
        # Dialog should show completion
        assert progress_dialog.progress_bar.value() == 100


class TestAccessibilityWorkflows:
    """Test accessibility and keyboard navigation workflows."""

    def test_keyboard_only_workflow(self, qtbot, mock_config_manager, mock_template_engine):
        """Test completing the wizard using only keyboard navigation."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine)
        qtbot.addWidget(wizard)
        wizard.show()
        qtbot.waitForWindowShown(wizard)
        
        # Tab to template list and select with Enter
        project_type = wizard.currentPage()
        project_type.template_list.setFocus()
        qtbot.keyClick(project_type.template_list, Qt.Key.Key_Down)
        qtbot.keyClick(project_type.template_list, Qt.Key.Key_Return)
        
        # Tab to Next button and press
        qtbot.keyClick(wizard, Qt.Key.Key_Tab, Qt.KeyboardModifier.ControlModifier)
        qtbot.keyClick(wizard, Qt.Key.Key_Return)
        
        # Should be on basic info page
        assert wizard.currentId() == 1

    def test_escape_key_handling(self, qtbot, mock_config_manager, mock_template_engine):
        """Test Escape key handling in wizard and dialogs."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine)
        qtbot.addWidget(wizard)
        wizard.show()
        
        # Press Escape
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes):
            qtbot.keyClick(wizard, Qt.Key.Key_Escape)
        
        # Wizard should close
        qtbot.waitUntil(lambda: not wizard.isVisible(), timeout=1000)

    def test_focus_management(self, qtbot, mock_config_manager, mock_template_engine):
        """Test focus management during navigation."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine)
        qtbot.addWidget(wizard)
        wizard.show()
        
        # Navigate through pages and check focus
        wizard.setCurrentId(1)  # Basic info
        basic_info = wizard.currentPage()
        
        # First field should have focus
        assert basic_info.name_edit.hasFocus() or basic_info.author_edit.hasFocus()
        
        # Tab through fields
        qtbot.keyClick(basic_info.name_edit, Qt.Key.Key_Tab)
        assert basic_info.author_edit.hasFocus()
        
        qtbot.keyClick(basic_info.author_edit, Qt.Key.Key_Tab)
        assert basic_info.version_edit.hasFocus()

    def test_screen_reader_compatibility(self, qtbot, mock_config_manager, mock_template_engine):
        """Test screen reader compatibility with proper labels and descriptions."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine)
        qtbot.addWidget(wizard)
        
        # Check accessibility properties
        wizard.setCurrentId(1)
        basic_info = wizard.currentPage()
        
        # Fields should have accessible names
        assert basic_info.name_edit.accessibleName() or basic_info.findChild(QLabel, "name_label")
        assert basic_info.author_edit.accessibleName() or basic_info.findChild(QLabel, "author_label")


class TestPerformanceWorkflows:
    """Test performance under various workflow conditions."""

    def test_rapid_navigation_performance(self, qtbot, mock_config_manager, mock_template_engine):
        """Test performance with rapid page navigation."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine)
        qtbot.addWidget(wizard)
        wizard.show()
        
        import time
        start_time = time.time()
        
        # Rapidly navigate through all pages 10 times
        for _ in range(10):
            for page_id in range(5):
                wizard.setCurrentId(page_id)
                qtbot.wait(10)
        
        elapsed = time.time() - start_time
        
        # Should complete in reasonable time (< 5 seconds)
        assert elapsed < 5.0

    def test_large_form_data_performance(self, qtbot, mock_config_manager, mock_template_engine):
        """Test performance with large amounts of form data."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine)
        qtbot.addWidget(wizard)
        
        # Fill forms with large data
        wizard.setCurrentId(1)
        basic_info = wizard.currentPage()
        
        # Large description
        large_text = "This is a test description. " * 100
        basic_info.description_edit.setPlainText(large_text)
        
        # Should handle large text without freezing
        assert len(basic_info.description_edit.toPlainText()) > 1000

    def test_memory_usage_workflow(self, qtbot, mock_config_manager, mock_template_engine):
        """Test memory usage during complete workflow."""
        import gc
        import sys
        
        initial_objects = len(gc.get_objects())
        
        # Create and destroy multiple wizards
        for _ in range(5):
            wizard = ProjectWizard(mock_config_manager, mock_template_engine)
            qtbot.addWidget(wizard)
            wizard.show()
            wizard.close()
            wizard.deleteLater()
        
        # Force garbage collection
        gc.collect()
        qtbot.wait(100)
        
        # Check object count didn't grow excessively
        final_objects = len(gc.get_objects())
        object_growth = final_objects - initial_objects
        
        # Allow some growth but not excessive (< 1000 objects)
        assert object_growth < 1000


class TestCompleteUserJourneys:
    """Test complete user journeys from start to finish."""

    def test_first_time_user_journey(self, qtbot, mock_config_manager, mock_template_engine):
        """Test journey of a first-time user creating their first project."""
        # First time user might configure settings first
        settings_dialog = SettingsDialog(mock_config_manager)
        qtbot.addWidget(settings_dialog)
        settings_dialog.show()
        
        # Set default author
        settings_dialog.author_edit.setText("New User")
        settings_dialog.location_edit.setText(str(Path.home() / "projects"))
        
        with patch.object(mock_config_manager, 'save'):
            settings_dialog.accept()
        
        # Now create first project
        wizard = ProjectWizard(mock_config_manager, mock_template_engine)
        qtbot.addWidget(wizard)
        wizard.show()
        
        helper = WizardTestHelper(wizard, qtbot)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Simple script project for first timer
            helper.select_template(4)  # One-off Script
            helper.fill_basic_info("my_first_script", "New User", "0.1.0", "My first Python script")
            helper.set_location(temp_dir)
            helper.configure_options(git=False, venv_tool="none", license_type="MIT")
            
            with patch.object(wizard, '_start_project_generation'):
                helper.complete_wizard()

    def test_experienced_user_journey(self, qtbot, mock_config_manager, mock_template_engine):
        """Test journey of an experienced user with specific requirements."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine)
        qtbot.addWidget(wizard)
        wizard.show()
        
        helper = WizardTestHelper(wizard, qtbot)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Experienced user creating a complex project
            helper.select_template(2)  # Django Web App
            helper.fill_basic_info(
                "enterprise_webapp",
                "Senior Developer",
                "2.0.0",
                "Enterprise-grade Django application with advanced features"
            )
            helper.set_location(temp_dir)
            
            # Configure advanced options
            options = wizard.currentPage()
            options.git_checkbox.setChecked(True)
            options.venv_combo.setCurrentText("uv")  # Fast modern tool
            options.license_combo.setCurrentText("GPL-3.0")  # Specific license
            
            # Set Django-specific options if available
            for widget_name, widget in options.template_widgets.items():
                if widget_name == "use_celery" and hasattr(widget, 'setChecked'):
                    widget.setChecked(True)
                elif widget_name == "use_docker" and hasattr(widget, 'setChecked'):
                    widget.setChecked(True)
            
            wizard.next()
            
            with patch.object(wizard, '_start_project_generation'):
                helper.complete_wizard()

    def test_team_lead_journey(self, qtbot, mock_config_manager, mock_template_engine):
        """Test journey of a team lead setting up a standardized project."""
        # Team lead configures organization settings
        settings_dialog = SettingsDialog(mock_config_manager)
        qtbot.addWidget(settings_dialog)
        settings_dialog.show()
        
        # Configure organization defaults
        settings_dialog.author_edit.setText("ACME Corp Development Team")
        settings_dialog.location_edit.setText("/opt/acme/projects")
        
        # Add custom template directory
        settings_dialog.tab_widget.setCurrentIndex(2)
        with patch.object(settings_dialog, 'add_template_path'):
            settings_dialog.add_template_path("/opt/acme/templates")
        
        with patch.object(mock_config_manager, 'save'):
            settings_dialog.accept()
        
        # Create standardized project
        wizard = ProjectWizard(mock_config_manager, mock_template_engine)
        qtbot.addWidget(wizard)
        wizard.show()
        
        helper = WizardTestHelper(wizard, qtbot)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            helper.select_template(0)  # Python Library
            helper.fill_basic_info(
                "acme_commons",
                "ACME Corp Development Team",
                "1.0.0",
                "ACME Corporation common utilities library"
            )
            helper.set_location(temp_dir)
            helper.configure_options(git=True, venv_tool="uv", license_type="Proprietary")
            
            with patch.object(wizard, '_start_project_generation'):
                helper.complete_wizard()