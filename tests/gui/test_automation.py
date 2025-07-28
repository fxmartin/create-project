# ABOUTME: Automated GUI interaction tests for the create-project wizard
# ABOUTME: Tests button clicks, form fills, navigation, and dialog interactions

"""Automated GUI interaction tests for the create-project wizard."""

import pytest

pytestmark = [pytest.mark.gui, pytest.mark.automation]
from unittest.mock import patch

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog, QPushButton

from create_project.gui.dialogs.error import ErrorDialog
from create_project.gui.dialogs.settings import SettingsDialog
from create_project.gui.widgets.progress_dialog import ProgressDialog
from create_project.gui.wizard.wizard import ProjectWizard


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

        # Click again to toggle back
        qtbot.mouseClick(git_checkbox, Qt.MouseButton.LeftButton)
        assert git_checkbox.isChecked() == initial_state

    def test_combo_box_selection(self, qtbot, mock_config_manager, mock_template_engine):
        """Test combo box selection with keyboard and mouse."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine)
        qtbot.addWidget(wizard)

        # Navigate to options page
        wizard.setCurrentId(3)
        options_step = wizard.currentPage()

        # Test license combo box
        license_combo = options_step.license_combo
        initial_index = license_combo.currentIndex()

        # Change selection with mouse
        license_combo.setCurrentIndex(2)
        assert license_combo.currentIndex() == 2

        # Change with keyboard
        license_combo.setFocus()
        qtbot.keyClick(license_combo, Qt.Key.Key_Down)
        assert license_combo.currentIndex() == 3

    def test_file_dialog_interactions(self, qtbot, mock_config_manager, mock_template_engine):
        """Test file dialog interactions."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine)
        qtbot.addWidget(wizard)

        # Navigate to location page
        wizard.setCurrentId(2)
        location_step = wizard.currentPage()

        # Mock file dialog to return a path
        test_path = "/test/location"
        with patch.object(QFileDialog, "getExistingDirectory", return_value=test_path):
            # Click browse button
            browse_button = location_step.browse_button
            qtbot.mouseClick(browse_button, Qt.MouseButton.LeftButton)

            # Path should be updated
            assert location_step.location_edit.text() == test_path

    def test_multi_page_workflow(self, qtbot, mock_config_manager, mock_template_engine):
        """Test complete multi-page workflow."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine)
        qtbot.addWidget(wizard)
        wizard.show()

        # Page 0: Select project type
        project_type_step = wizard.currentPage()
        project_type_step.template_list.setCurrentRow(0)
        wizard.next()

        # Page 1: Fill basic info
        basic_info_step = wizard.currentPage()
        basic_info_step.name_edit.setText("automated_project")
        basic_info_step.author_edit.setText("Auto Tester")
        basic_info_step.version_edit.setText("0.1.0")
        basic_info_step.description_edit.setPlainText("Automated test project")
        wizard.next()

        # Page 2: Set location
        location_step = wizard.currentPage()
        location_step.location_edit.setText("/tmp")
        wizard.next()

        # Page 3: Configure options
        options_step = wizard.currentPage()
        options_step.git_checkbox.setChecked(True)
        options_step.venv_combo.setCurrentIndex(1)
        options_step.license_combo.setCurrentIndex(2)
        wizard.next()

        # Page 4: Review
        assert wizard.currentId() == 4
        review_step = wizard.currentPage()
        
        # Verify data propagated
        assert "automated_project" in review_step.review_text.toPlainText()
        assert "Auto Tester" in review_step.review_text.toPlainText()

    def test_keyboard_navigation(self, qtbot, mock_config_manager, mock_template_engine):
        """Test keyboard navigation through wizard."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine)
        qtbot.addWidget(wizard)
        wizard.show()

        # Select template with keyboard
        project_type_step = wizard.currentPage()
        template_list = project_type_step.template_list
        template_list.setFocus()
        
        qtbot.keyClick(template_list, Qt.Key.Key_Down)
        qtbot.keyClick(template_list, Qt.Key.Key_Space)
        
        # Navigate with Alt+N (Next)
        qtbot.keyClick(wizard, Qt.Key.Key_N, modifier=Qt.KeyboardModifier.AltModifier)
        assert wizard.currentId() == 1

        # Navigate with Alt+B (Back)
        qtbot.keyClick(wizard, Qt.Key.Key_B, modifier=Qt.KeyboardModifier.AltModifier)
        assert wizard.currentId() == 0

    def test_progress_dialog_lifecycle(self, qtbot):
        """Test progress dialog lifecycle."""
        dialog = ProgressDialog()
        qtbot.addWidget(dialog)
        dialog.show()

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
        with patch("PyQt6.QtWidgets.QMessageBox.question", return_value=True):
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


class TestComplexInteractions:
    """Test complex interaction scenarios."""

    def test_validation_feedback_loop(self, qtbot, mock_config_manager, mock_template_engine):
        """Test validation feedback loop with user corrections."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine)
        qtbot.addWidget(wizard)

        # Navigate to basic info
        wizard.setCurrentId(1)
        basic_info = wizard.currentPage()

        # Enter invalid project name
        basic_info.name_edit.setText("123-invalid!")
        
        # Try to navigate forward
        next_button = wizard.button(wizard.NextButton)
        qtbot.mouseClick(next_button, Qt.MouseButton.LeftButton)
        
        # Should still be on same page due to validation
        assert wizard.currentId() == 1
        
        # Correct the name
        basic_info.name_edit.setText("valid_project_name")
        
        # Try again
        qtbot.mouseClick(next_button, Qt.MouseButton.LeftButton)
        
        # Should advance now
        assert wizard.currentId() == 2

    def test_concurrent_dialog_handling(self, qtbot, mock_config_manager):
        """Test handling multiple dialogs."""
        # Create progress dialog
        progress_dialog = ProgressDialog()
        qtbot.addWidget(progress_dialog)
        progress_dialog.show()

        # Create settings dialog
        settings_dialog = SettingsDialog(mock_config_manager)
        qtbot.addWidget(settings_dialog)
        settings_dialog.show()

        # Both should be visible
        assert progress_dialog.isVisible()
        assert settings_dialog.isVisible()

        # Close in order
        settings_dialog.close()
        progress_dialog.close()

        qtbot.waitUntil(lambda: not settings_dialog.isVisible(), timeout=1000)
        qtbot.waitUntil(lambda: not progress_dialog.isVisible(), timeout=1000)

    def test_data_consistency_across_steps(self, qtbot, mock_config_manager, mock_template_engine):
        """Test data consistency across all wizard steps."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine)
        qtbot.addWidget(wizard)

        test_data = {
            "project_name": "consistency_test",
            "author": "Test Author",
            "version": "1.2.3",
            "description": "Testing data consistency",
            "location": "/tmp/test",
            "license": "MIT"
        }

        # Fill all fields
        wizard.setCurrentId(1)
        basic_info = wizard.currentPage()
        basic_info.name_edit.setText(test_data["project_name"])
        basic_info.author_edit.setText(test_data["author"])
        basic_info.version_edit.setText(test_data["version"])
        basic_info.description_edit.setPlainText(test_data["description"])

        wizard.setCurrentId(2)
        location_step = wizard.currentPage()
        location_step.location_edit.setText(test_data["location"])

        wizard.setCurrentId(3)
        options_step = wizard.currentPage()
        license_index = options_step.license_combo.findText(test_data["license"])
        if license_index >= 0:
            options_step.license_combo.setCurrentIndex(license_index)

        # Navigate to review
        wizard.setCurrentId(4)
        review_step = wizard.currentPage()

        # Verify all data appears in review
        review_text = review_step.review_text.toPlainText()
        for value in test_data.values():
            assert value in review_text

    def test_stress_rapid_clicks(self, qtbot, mock_config_manager, mock_template_engine):
        """Test handling rapid button clicks."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine)
        qtbot.addWidget(wizard)
        wizard.show()

        next_button = wizard.button(wizard.NextButton)
        
        # Rapid clicks without selection
        for _ in range(10):
            qtbot.mouseClick(next_button, Qt.MouseButton.LeftButton)
            qtbot.wait(10)

        # Should still be on first page
        assert wizard.currentId() == 0

    def test_focus_chain_navigation(self, qtbot, mock_config_manager, mock_template_engine):
        """Test tab key navigation through focus chain."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine)
        qtbot.addWidget(wizard)
        wizard.show()

        # Navigate to basic info page
        wizard.setCurrentId(1)
        basic_info = wizard.currentPage()

        # Set focus to first field
        basic_info.name_edit.setFocus()
        assert basic_info.name_edit.hasFocus()

        # Tab through fields
        qtbot.keyClick(basic_info.name_edit, Qt.Key.Key_Tab)
        assert basic_info.author_edit.hasFocus()

        qtbot.keyClick(basic_info.author_edit, Qt.Key.Key_Tab)
        assert basic_info.version_edit.hasFocus()

        qtbot.keyClick(basic_info.version_edit, Qt.Key.Key_Tab)
        assert basic_info.description_edit.hasFocus()

    def test_partial_completion_recovery(self, qtbot, mock_config_manager, mock_template_engine):
        """Test recovery from partial completion states."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine)
        qtbot.addWidget(wizard)

        # Fill some data
        wizard.setCurrentId(1)
        basic_info = wizard.currentPage()
        basic_info.name_edit.setText("partial_project")
        
        # Navigate forward
        wizard.setCurrentId(2)
        
        # Navigate back
        wizard.setCurrentId(1)
        
        # Data should still be there
        assert basic_info.name_edit.text() == "partial_project"
        
        # Clear and refill
        basic_info.name_edit.clear()
        qtbot.keyClicks(basic_info.name_edit, "complete_project")
        
        # Verify new data
        assert basic_info.name_edit.text() == "complete_project"

    def test_edge_case_inputs(self, qtbot, mock_config_manager, mock_template_engine):
        """Test edge case inputs in forms."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine)
        qtbot.addWidget(wizard)

        wizard.setCurrentId(1)
        basic_info = wizard.currentPage()

        # Test very long input
        long_name = "a" * 100
        basic_info.name_edit.setText(long_name)
        assert len(basic_info.name_edit.text()) <= basic_info.name_edit.maxLength()

        # Test unicode characters
        unicode_author = "Test 作者 🎉"
        basic_info.author_edit.setText(unicode_author)
        assert basic_info.author_edit.text() == unicode_author

        # Test special characters in description
        special_desc = "Test\nproject\twith\r\nspecial chars & symbols <>"
        basic_info.description_edit.setPlainText(special_desc)
        assert basic_info.description_edit.toPlainText() == special_desc

    def test_complete_user_journey(self, qtbot, mock_config_manager, mock_template_engine):
        """Test complete user journey from start to finish."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine)
        qtbot.addWidget(wizard)
        wizard.show()
        qtbot.waitForWindowShown(wizard)

        # Select template
        project_type = wizard.currentPage()
        project_type.template_list.setCurrentRow(0)
        wizard.next()

        # Fill basic info
        basic_info = wizard.currentPage()
        qtbot.keyClicks(basic_info.name_edit, "complete_test_project")
        qtbot.keyClicks(basic_info.author_edit, "Complete Tester")
        qtbot.keyClicks(basic_info.version_edit, "1.0.0")
        qtbot.keyClicks(basic_info.description_edit, "A complete test project")
        wizard.next()

        # Set location
        location_step = wizard.currentPage()
        qtbot.keyClicks(location_step.location_edit, "/tmp/test_projects")
        wizard.next()

        # Configure options
        options_step = wizard.currentPage()
        options_step.git_checkbox.setChecked(True)
        options_step.venv_combo.setCurrentIndex(1)
        options_step.license_combo.setCurrentText("MIT")
        wizard.next()

        # Review
        review_step = wizard.currentPage()
        assert wizard.currentId() == 4
        
        # Verify review contains all entered data
        review_text = review_step.review_text.toPlainText()
        assert "complete_test_project" in review_text
        assert "Complete Tester" in review_text
        assert "1.0.0" in review_text
        assert "/tmp/test_projects" in review_text
        assert "MIT" in review_text

        # The actual project creation would happen here
        # but we're just testing the UI flow
        assert wizard.currentId() in range(5)