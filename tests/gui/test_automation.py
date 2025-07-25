# ABOUTME: Automated GUI interaction tests for the create-project wizard
# ABOUTME: Tests button clicks, form fills, navigation, and dialog interactions

"""Automated GUI interaction tests for the create-project wizard."""

import pytest

pytestmark = [pytest.mark.gui, pytest.mark.automation]
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QApplication, QPushButton, QLineEdit, QListWidget,
    QCheckBox, QComboBox, QTextEdit, QFileDialog
)
from PyQt6.QtTest import QTest

from create_project.gui.wizard.wizard import ProjectWizard
from create_project.gui.steps.project_type import ProjectTypeStep
from create_project.gui.steps.basic_info import BasicInfoStep
from create_project.gui.steps.location import LocationStep
from create_project.gui.steps.options import OptionsStep
from create_project.gui.steps.review import ReviewStep
from create_project.gui.dialogs.settings import SettingsDialog
from create_project.gui.dialogs.error import ErrorDialog
from create_project.gui.dialogs.ai_help import AIHelpDialog
from create_project.gui.widgets.progress_dialog import ProgressDialog
from create_project.templates.schema.template import Template
from create_project.templates.schema.variables import TemplateVariable


class TestAutomatedGUIInteractions:
    """Test automated GUI interactions using qtbot."""

    def test_wizard_button_navigation(self, qtbot, mock_config_manager, mock_template_engine):
        """Test navigation through wizard using button clicks."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine)
        qtbot.addWidget(wizard)
        wizard.show()
        qtbot.waitForWindowShown(wizard)
        
        # Start on project type page
        assert wizard.currentId() == 0
        
        # Click Next button
        next_button = wizard.button(wizard.NextButton)
        qtbot.mouseClick(next_button, Qt.MouseButton.LeftButton)
        
        # Should still be on page 0 (no selection made)
        assert wizard.currentId() == 0
        
        # Select a project type
        project_type_step = wizard.currentPage()
        project_type_step.template_list.setCurrentRow(0)
        
        # Click Next again
        qtbot.mouseClick(next_button, Qt.MouseButton.LeftButton)
        assert wizard.currentId() == 1  # Basic info page
        
        # Click Back button
        back_button = wizard.button(wizard.BackButton)
        qtbot.mouseClick(back_button, Qt.MouseButton.LeftButton)
        assert wizard.currentId() == 0  # Back to project type

    def test_form_field_interactions(self, qtbot, mock_config_manager, mock_template_engine):
        """Test form field interactions with automated input."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine)
        qtbot.addWidget(wizard)
        
        # Navigate to basic info page
        wizard.setCurrentId(1)
        basic_info_step = wizard.currentPage()
        
        # Type in project name field
        name_field = basic_info_step.name_edit
        name_field.clear()
        qtbot.keyClicks(name_field, "my_test_project")
        assert name_field.text() == "my_test_project"
        
        # Type in author field
        author_field = basic_info_step.author_edit
        author_field.clear()
        qtbot.keyClicks(author_field, "Test Author")
        assert author_field.text() == "Test Author"
        
        # Type in version field
        version_field = basic_info_step.version_edit
        version_field.clear()
        qtbot.keyClicks(version_field, "1.0.0")
        assert version_field.text() == "1.0.0"
        
        # Type in description field
        desc_field = basic_info_step.description_edit
        qtbot.keyClicks(desc_field, "This is a test project")
        assert desc_field.toPlainText() == "This is a test project"

    def test_checkbox_toggle(self, qtbot, mock_config_manager, mock_template_engine):
        """Test checkbox toggling with mouse clicks."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine)
        qtbot.addWidget(wizard)
        
        # Navigate to options page
        wizard.setCurrentId(3)
        options_step = wizard.currentPage()
        
        # Find git checkbox
        git_checkbox = options_step.git_checkbox
        initial_state = git_checkbox.isChecked()
        
        # Click checkbox
        qtbot.mouseClick(git_checkbox, Qt.MouseButton.LeftButton)
        assert git_checkbox.isChecked() != initial_state
        
        # Click again
        qtbot.mouseClick(git_checkbox, Qt.MouseButton.LeftButton)
        assert git_checkbox.isChecked() == initial_state

    def test_combobox_selection(self, qtbot, mock_config_manager, mock_template_engine):
        """Test combobox selection with automated interaction."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine)
        qtbot.addWidget(wizard)
        
        # Navigate to options page
        wizard.setCurrentId(3)
        options_step = wizard.currentPage()
        
        # Select venv tool
        venv_combo = options_step.venv_combo
        venv_combo.setCurrentIndex(1)  # Select virtualenv
        assert venv_combo.currentText() == "virtualenv"
        
        # Select another option
        venv_combo.setCurrentIndex(2)  # Select venv
        assert venv_combo.currentText() == "venv"

    def test_dialog_interactions(self, qtbot, mock_config_manager):
        """Test dialog button interactions."""
        # Create error dialog
        error = Exception("Test error")
        context = {"test": "context"}
        dialog = ErrorDialog(error, context, mock_config_manager)
        qtbot.addWidget(dialog)
        dialog.show()
        qtbot.waitForWindowShown(dialog)
        
        # Find and click copy button
        copy_button = dialog.findChild(QPushButton, "copy_button")
        if copy_button:
            qtbot.mouseClick(copy_button, Qt.MouseButton.LeftButton)
        
        # Click OK button to close
        ok_button = dialog.button_box.button(dialog.button_box.StandardButton.Ok)
        qtbot.mouseClick(ok_button, Qt.MouseButton.LeftButton)
        
        # Dialog should close
        qtbot.waitUntil(lambda: not dialog.isVisible(), timeout=1000)

    def test_list_widget_selection(self, qtbot, mock_config_manager, mock_template_engine):
        """Test list widget item selection."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine)
        qtbot.addWidget(wizard)
        wizard.show()
        
        # Get project type step
        project_type_step = wizard.currentPage()
        template_list = project_type_step.template_list
        
        # Select first item
        if template_list.count() > 0:
            template_list.setCurrentRow(0)
            assert template_list.currentRow() == 0
            
            # Select second item if available
            if template_list.count() > 1:
                template_list.setCurrentRow(1)
                assert template_list.currentRow() == 1

    def test_file_dialog_interaction(self, qtbot, mock_config_manager, mock_template_engine):
        """Test file dialog interaction (mocked)."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine)
        qtbot.addWidget(wizard)
        
        # Navigate to location page
        wizard.setCurrentId(2)
        location_step = wizard.currentPage()
        
        # Mock file dialog
        with patch.object(QFileDialog, 'getExistingDirectory', return_value='/test/path'):
            # Click browse button
            browse_button = location_step.browse_button
            qtbot.mouseClick(browse_button, Qt.MouseButton.LeftButton)
            
            # Check path was set
            assert location_step.location_edit.text() == '/test/path'

    def test_progress_dialog_updates(self, qtbot):
        """Test progress dialog automated updates."""
        dialog = ProgressDialog("Test Progress", parent=None)
        qtbot.addWidget(dialog)
        dialog.show()
        qtbot.waitForWindowShown(dialog)
        
        # Update progress
        dialog.update_progress(25)
        assert dialog.progress_bar.value() == 25
        
        # Add log entry
        dialog.add_log_entry("Test log entry")
        assert "Test log entry" in dialog.log_display.toPlainText()
        
        # Update to completion
        dialog.update_progress(100)
        assert dialog.progress_bar.value() == 100

    def test_settings_dialog_tab_switching(self, qtbot, mock_config_manager):
        """Test settings dialog tab switching."""
        dialog = SettingsDialog(mock_config_manager)
        qtbot.addWidget(dialog)
        dialog.show()
        qtbot.waitForWindowShown(dialog)
        
        # Switch tabs
        tab_widget = dialog.tab_widget
        tab_widget.setCurrentIndex(1)  # AI Settings
        assert tab_widget.currentIndex() == 1
        
        tab_widget.setCurrentIndex(2)  # Template Paths
        assert tab_widget.currentIndex() == 2
        
        tab_widget.setCurrentIndex(0)  # General
        assert tab_widget.currentIndex() == 0

    def test_cancel_button_workflow(self, qtbot, mock_config_manager, mock_template_engine):
        """Test cancel button workflow."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine)
        qtbot.addWidget(wizard)
        wizard.show()
        qtbot.waitForWindowShown(wizard)
        
        # Click cancel button
        cancel_button = wizard.button(wizard.CancelButton)
        
        # Mock the message box to automatically click "Yes"
        with patch('PyQt6.QtWidgets.QMessageBox.question', return_value=True):
            qtbot.mouseClick(cancel_button, Qt.MouseButton.LeftButton)
            
        # Wizard should close
        qtbot.waitUntil(lambda: not wizard.isVisible(), timeout=1000)

    def test_rapid_navigation(self, qtbot, mock_config_manager, mock_template_engine):
        """Test rapid navigation between pages."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine)
        qtbot.addWidget(wizard)
        wizard.show()
        
        # Rapidly switch between pages
        for _ in range(5):
            wizard.setCurrentId(1)
            qtbot.wait(50)
            wizard.setCurrentId(2)
            qtbot.wait(50)
            wizard.setCurrentId(3)
            qtbot.wait(50)
            wizard.setCurrentId(0)
            qtbot.wait(50)
        
        # Should end on page 0
        assert wizard.currentId() == 0

    def test_widget_state_persistence(self, qtbot, mock_config_manager, mock_template_engine):
        """Test widget state persistence during navigation."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine)
        qtbot.addWidget(wizard)
        
        # Set data on basic info page
        wizard.setCurrentId(1)
        basic_info = wizard.currentPage()
        basic_info.name_edit.setText("persistent_project")
        basic_info.author_edit.setText("Persistent Author")
        
        # Navigate away and back
        wizard.setCurrentId(2)
        wizard.setCurrentId(1)
        
        # Data should persist
        assert basic_info.name_edit.text() == "persistent_project"
        assert basic_info.author_edit.text() == "Persistent Author"

    def test_error_recovery_workflow(self, qtbot, mock_config_manager):
        """Test error dialog recovery workflow."""
        error = ValueError("Test validation error")
        context = {"field": "project_name", "value": "invalid-name!"}
        
        dialog = ErrorDialog(error, context, mock_config_manager)
        qtbot.addWidget(dialog)
        dialog.show()
        
        # Check if retry button exists (for retryable errors)
        retry_button = None
        for button in dialog.button_box.buttons():
            if button.text() == "Retry":
                retry_button = button
                break
        
        if retry_button:
            # Click retry
            qtbot.mouseClick(retry_button, Qt.MouseButton.LeftButton)
            assert dialog.result() == dialog.DialogCode.Retry


class TestAdvancedAutomation:
    """Test advanced automation scenarios."""

    def test_multi_step_workflow(self, qtbot, mock_config_manager, mock_template_engine):
        """Test complete multi-step workflow automation."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine)
        qtbot.addWidget(wizard)
        wizard.show()
        
        # Step 1: Select project type
        project_type = wizard.currentPage()
        project_type.template_list.setCurrentRow(0)
        wizard.next()
        
        # Step 2: Fill basic info
        basic_info = wizard.currentPage()
        basic_info.name_edit.setText("automated_project")
        basic_info.author_edit.setText("Automation Test")
        basic_info.version_edit.setText("1.0.0")
        basic_info.description_edit.setPlainText("Automated test project")
        wizard.next()
        
        # Step 3: Set location
        location = wizard.currentPage()
        location.location_edit.setText("/tmp/test_projects")
        wizard.next()
        
        # Step 4: Configure options
        options = wizard.currentPage()
        options.git_checkbox.setChecked(True)
        options.license_combo.setCurrentIndex(0)  # MIT
        wizard.next()
        
        # Step 5: Review
        review = wizard.currentPage()
        assert wizard.currentId() == 4
        
        # Verify all data is present
        wizard_data = wizard.get_wizard_data()
        assert wizard_data.project_name == "automated_project"
        assert wizard_data.author == "Automation Test"

    def test_concurrent_dialog_handling(self, qtbot, mock_config_manager):
        """Test handling multiple dialogs."""
        # Create multiple dialogs
        error1 = Exception("Error 1")
        error2 = Exception("Error 2")
        
        dialog1 = ErrorDialog(error1, {}, mock_config_manager)
        dialog2 = ErrorDialog(error2, {}, mock_config_manager)
        
        qtbot.addWidget(dialog1)
        qtbot.addWidget(dialog2)
        
        # Show both
        dialog1.show()
        dialog2.show()
        
        # Close in order
        ok_button1 = dialog1.button_box.button(dialog1.button_box.StandardButton.Ok)
        qtbot.mouseClick(ok_button1, Qt.MouseButton.LeftButton)
        
        ok_button2 = dialog2.button_box.button(dialog2.button_box.StandardButton.Ok)
        qtbot.mouseClick(ok_button2, Qt.MouseButton.LeftButton)
        
        # Both should be closed
        qtbot.waitUntil(lambda: not dialog1.isVisible() and not dialog2.isVisible(), timeout=1000)

    def test_stress_test_rapid_clicks(self, qtbot, mock_config_manager, mock_template_engine):
        """Stress test with rapid button clicks."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine)
        qtbot.addWidget(wizard)
        wizard.show()
        
        next_button = wizard.button(wizard.NextButton)
        back_button = wizard.button(wizard.BackButton)
        
        # Rapid clicking shouldn't break the wizard
        for _ in range(10):
            qtbot.mouseClick(next_button, Qt.MouseButton.LeftButton)
            qtbot.wait(10)
            qtbot.mouseClick(back_button, Qt.MouseButton.LeftButton)
            qtbot.wait(10)
        
        # Wizard should still be functional
        assert wizard.currentId() in range(5)


@pytest.mark.gui
@pytest.mark.automation
class TestGUIAutomationSuite:
    """Complete GUI automation test suite."""

    def test_complete_automation_suite(self, qtbot, mock_config_manager, mock_template_engine):
        """Run complete automation test suite."""
        results = {
            "navigation": False,
            "form_input": False,
            "dialog_handling": False,
            "state_persistence": False
        }
        
        wizard = ProjectWizard(mock_config_manager, mock_template_engine)
        qtbot.addWidget(wizard)
        wizard.show()
        
        # Test navigation
        wizard.setCurrentId(1)
        wizard.setCurrentId(0)
        results["navigation"] = wizard.currentId() == 0
        
        # Test form input
        wizard.setCurrentId(1)
        basic_info = wizard.currentPage()
        basic_info.name_edit.setText("test_project")
        results["form_input"] = basic_info.name_edit.text() == "test_project"
        
        # Test dialog handling
        try:
            error_dialog = ErrorDialog(Exception("Test"), {}, mock_config_manager)
            qtbot.addWidget(error_dialog)
            error_dialog.show()
            error_dialog.accept()
            results["dialog_handling"] = True
        except:
            results["dialog_handling"] = False
        
        # Test state persistence
        wizard.setCurrentId(2)
        wizard.setCurrentId(1)
        results["state_persistence"] = basic_info.name_edit.text() == "test_project"
        
        # All tests should pass
        assert all(results.values()), f"Failed tests: {[k for k,v in results.items() if not v]}"