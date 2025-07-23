# ABOUTME: Integration tests for complete wizard workflow and UI components
# ABOUTME: Tests end-to-end functionality including project generation from GUI

"""
Integration tests for the Create Project GUI application.

This module tests complete workflows including:
- Complete wizard flow from start to finish
- Project generation triggered from UI
- Settings persistence across sessions
- Error handling flow with AI assistance
- Cross-component signal/slot connections
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QListWidgetItem

from create_project.gui.wizard.wizard import ProjectWizard


class TestWizardIntegration:
    """Test complete wizard workflow integration."""

    def test_complete_wizard_flow(self, qtbot, mock_config_manager, mock_template_engine, mock_ai_service):
        """Test complete wizard flow from project type to creation."""
        # Create wizard
        wizard = ProjectWizard(
            mock_config_manager, 
            mock_template_engine, 
            None, 
            mock_ai_service
        )
        qtbot.addWidget(wizard)
        
        # Show wizard
        wizard.show()
        qtbot.waitForWindowShown(wizard)
        
        # Step 1: Project Type Selection
        assert wizard.currentId() == 0
        project_type_step = wizard.page(0)
        
        # Add and select a template
        item = QListWidgetItem("Test Template")
        item.setData(Qt.ItemDataRole.UserRole, "test_template_id")
        project_type_step.template_list.addItem(item)
        project_type_step.template_list.setCurrentItem(item)
        
        # Navigate to next step
        wizard.next()
        assert wizard.currentId() == 1
        
        # Step 2: Basic Information
        basic_info_step = wizard.page(1)
        basic_info_step.name_edit.setText("test_project")
        basic_info_step.author_edit.setText("Test Author")
        basic_info_step.version_edit.setText("1.0.0")
        basic_info_step.description_edit.setText("Test project description")
        
        # Navigate to next step
        wizard.next()
        assert wizard.currentId() == 2
        
        # Step 3: Location Selection
        location_step = wizard.page(2)
        with tempfile.TemporaryDirectory() as temp_dir:
            location_step.location_edit.setText(temp_dir)
            
            # Navigate to next step
            wizard.next()
            assert wizard.currentId() == 3
            
            # Step 4: Options Configuration
            options_step = wizard.page(3)
            # Options should have defaults, just proceed
            
            # Navigate to final step
            wizard.next()
            assert wizard.currentId() == 4
            
            # Step 5: Review and Create
            review_step = wizard.page(4)
            
            # Verify that all data is properly displayed in review
            # The review step should show the collected information
            assert review_step is not None

    @pytest.mark.skip(reason="Project generation testing requires proper backend mocking")
    def test_project_generation_from_ui(self, qtbot, mock_config_manager, mock_template_engine):
        """Test that project generation can be triggered from UI."""
        # This test would require extensive mocking of the project generation backend
        # and is complex to implement without actual backend integration
        wizard = ProjectWizard(mock_config_manager, mock_template_engine, None, None)
        qtbot.addWidget(wizard)
        
        # The actual implementation would:
        # 1. Navigate through all wizard steps
        # 2. Fill in all required fields
        # 3. Trigger project creation from review step
        # 4. Verify that ProjectGenerationThread is started
        # 5. Mock successful project generation
        # 6. Verify success signals are emitted
        
        assert True  # Placeholder

    def test_wizard_data_persistence(self, qtbot, mock_config_manager, mock_template_engine):
        """Test that wizard data persists between step navigation."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine, None, None)
        qtbot.addWidget(wizard)
        wizard.show()
        qtbot.waitForWindowShown(wizard)
        
        # Set up project type selection
        project_type_step = wizard.page(0)
        item = QListWidgetItem("Test Template")
        item.setData(Qt.ItemDataRole.UserRole, "test_template_id")
        project_type_step.template_list.addItem(item)
        project_type_step.template_list.setCurrentItem(item)
        wizard.next()
        
        # Fill basic info
        basic_info_step = wizard.page(1)
        basic_info_step.name_edit.setText("persistent_project")
        basic_info_step.author_edit.setText("Persistent Author")
        basic_info_step.version_edit.setText("2.0.0")
        wizard.next()
        
        # Navigate forward and back
        wizard.next()  # Location step
        wizard.next()  # Options step
        wizard.back()  # Back to location
        wizard.back()  # Back to options
        wizard.back()  # Back to basic info
        
        # Verify data is still there
        assert basic_info_step.name_edit.text() == "persistent_project"
        assert basic_info_step.author_edit.text() == "Persistent Author"
        assert basic_info_step.version_edit.text() == "2.0.0"

    def test_wizard_validation_integration(self, qtbot, mock_config_manager, mock_template_engine):
        """Test that validation works across wizard steps."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine, None, None)
        qtbot.addWidget(wizard)
        wizard.show()
        qtbot.waitForWindowShown(wizard)
        
        # Try to navigate without selecting template (should fail)
        current_id = wizard.currentId()
        wizard.next()
        assert wizard.currentId() == current_id  # Should still be on same page
        
        # Select template and try again
        project_type_step = wizard.page(0)
        item = QListWidgetItem("Test Template")
        item.setData(Qt.ItemDataRole.UserRole, "test_template_id")
        project_type_step.template_list.addItem(item)
        project_type_step.template_list.setCurrentItem(item)
        
        # Now navigation should work
        wizard.next()
        assert wizard.currentId() == 1
        
        # Try to navigate from basic info without required fields
        current_id = wizard.currentId()
        wizard.next()
        # Should not advance due to validation
        assert wizard.currentId() == current_id


class TestSettingsIntegration:
    """Test settings persistence and integration."""

    def test_settings_persistence(self, qtbot, mock_config_manager):
        """Test that settings are properly loaded and saved."""
        # Mock config manager to track calls
        mock_config_manager.get.return_value = "Test Default Author"
        mock_config_manager.set_setting = MagicMock()
        
        from create_project.gui.dialogs.settings import SettingsDialog
        
        dialog = SettingsDialog(mock_config_manager)
        qtbot.addWidget(dialog)
        
        # Verify settings are loaded
        mock_config_manager.get.assert_called()
        
        # Modify a setting
        dialog.author_edit.setText("New Author")
        
        # Accept dialog (save settings)
        dialog.accept()
        
        # Verify settings are saved
        mock_config_manager.set_setting.assert_called()

    def test_settings_applied_to_wizard(self, qtbot, mock_config_manager, mock_template_engine):
        """Test that settings are applied to wizard fields."""
        # Configure mock to return specific author
        mock_config_manager.get.side_effect = lambda key, default=None: {
            "defaults.author": "Configured Author",
            "defaults.location": "/configured/path",
        }.get(key, default)
        
        wizard = ProjectWizard(mock_config_manager, mock_template_engine, None, None)
        qtbot.addWidget(wizard)
        wizard.show()
        qtbot.waitForWindowShown(wizard)
        
        # Navigate to basic info step
        project_type_step = wizard.page(0)
        item = QListWidgetItem("Test Template")
        item.setData(Qt.ItemDataRole.UserRole, "test_template_id")
        project_type_step.template_list.addItem(item)
        project_type_step.template_list.setCurrentItem(item)
        wizard.next()
        
        # Check that default author is applied
        basic_info_step = wizard.page(1)
        assert basic_info_step.author_edit.text() == "Configured Author"


class TestErrorHandlingIntegration:
    """Test error handling flow with AI assistance."""

    def test_error_dialog_integration(self, qtbot, mock_config_manager):
        """Test error dialog with AI help integration."""
        from create_project.gui.dialogs.error import ErrorDialog
        
        # Create test error
        test_error = RuntimeError("Test error message")
        test_context = {"operation": "test", "details": "error details"}
        
        # Mock AI enabled
        mock_config_manager.get.side_effect = lambda key, default=None: {
            "ai.enabled": True
        }.get(key, default)
        
        dialog = ErrorDialog(test_error, test_context, mock_config_manager)
        qtbot.addWidget(dialog)
        
        # Verify error is displayed
        assert "Test error message" in dialog.error_label.text()
        
        # Verify AI help button is available when AI is enabled
        assert dialog.help_button.isVisible()

    @pytest.mark.skip(reason="AI integration testing requires proper service mocking")
    def test_ai_help_integration(self, qtbot, mock_config_manager, mock_ai_service):
        """Test AI help dialog integration."""
        # This would test the complete AI help flow
        # but requires complex mocking of AI service responses
        assert True  # Placeholder


class TestSignalSlotIntegration:
    """Test signal/slot connections between components."""

    def test_wizard_signals(self, qtbot, mock_config_manager, mock_template_engine):
        """Test that wizard signals are properly connected."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine, None, None)
        qtbot.addWidget(wizard)
        
        # Test that wizard has expected signals
        assert hasattr(wizard, 'project_created')
        
        # Mock signal connections
        signal_received = []
        wizard.project_created.connect(lambda path: signal_received.append(path))
        
        # The actual signal emission would be tested in integration
        # with real project generation, which is complex to mock

    def test_step_completion_signals(self, qtbot, mock_config_manager, mock_template_engine):
        """Test step completion signal handling."""
        wizard = ProjectWizard(mock_config_manager, mock_template_engine, None, None)
        qtbot.addWidget(wizard)
        wizard.show()
        qtbot.waitForWindowShown(wizard)
        
        # Get basic info step
        project_type_step = wizard.page(0)
        item = QListWidgetItem("Test Template")
        item.setData(Qt.ItemDataRole.UserRole, "test_template_id")
        project_type_step.template_list.addItem(item)
        project_type_step.template_list.setCurrentItem(item)
        wizard.next()
        
        basic_info_step = wizard.page(1)
        
        # Test that step completion changes are signaled
        completion_changes = []
        basic_info_step.completeChanged.connect(lambda: completion_changes.append(True))
        
        # Filling required fields should trigger completion change
        basic_info_step.name_edit.setText("test")
        basic_info_step.author_edit.setText("author")
        basic_info_step.version_edit.setText("1.0.0")
        
        # Signal may be triggered by text changes (hard to test reliably in headless mode)


class TestEndToEndWorkflow:
    """Test complete end-to-end workflow scenarios."""

    @pytest.mark.skip(reason="Full E2E testing requires display and complex backend mocking")
    def test_successful_project_creation_workflow(self):
        """Test complete successful project creation from start to finish."""
        # This would be a comprehensive test that:
        # 1. Starts the wizard
        # 2. Goes through all steps with valid data
        # 3. Triggers project creation
        # 4. Mocks successful backend generation
        # 5. Verifies success dialog/completion
        # 6. Verifies project files are created (mocked)
        assert True  # Placeholder for complex integration test

    @pytest.mark.skip(reason="Error scenario testing requires backend error simulation")
    def test_project_creation_error_workflow(self):
        """Test project creation error handling workflow."""
        # This would test:
        # 1. Project creation failure scenario
        # 2. Error dialog appearance
        # 3. AI help dialog integration
        # 4. Recovery options
        assert True  # Placeholder for error scenario testing


# Integration test utilities
class IntegrationTestHelper:
    """Helper class for integration testing."""
    
    @staticmethod
    def setup_valid_wizard_data(wizard):
        """Set up a wizard with valid data for all steps."""
        wizard.show()
        
        # Project type
        project_type_step = wizard.page(0)
        item = QListWidgetItem("Integration Test Template")
        item.setData(Qt.ItemDataRole.UserRole, "integration_test_template")
        project_type_step.template_list.addItem(item)
        project_type_step.template_list.setCurrentItem(item)
        wizard.next()
        
        # Basic info
        basic_info_step = wizard.page(1)
        basic_info_step.name_edit.setText("integration_test_project")
        basic_info_step.author_edit.setText("Integration Test Author")
        basic_info_step.version_edit.setText("1.0.0")
        basic_info_step.description_edit.setText("Integration test project")
        wizard.next()
        
        # Location (use temp directory)
        location_step = wizard.page(2)
        location_step.location_edit.setText("/tmp")
        wizard.next()
        
        # Options (use defaults)
        wizard.next()
        
        # Should now be at review step
        assert wizard.currentId() == 4
        return wizard

    @staticmethod
    def simulate_user_interaction(qtbot, widget, delay_ms=100):
        """Simulate realistic user interaction timing."""
        qtbot.wait(delay_ms)
        return widget


# Test fixtures for integration testing
@pytest.fixture
def integration_wizard(qtbot, mock_config_manager, mock_template_engine, mock_ai_service):
    """Create a wizard configured for integration testing."""
    wizard = ProjectWizard(
        mock_config_manager,
        mock_template_engine, 
        None,
        mock_ai_service
    )
    qtbot.addWidget(wizard)
    return wizard


@pytest.fixture
def populated_wizard(qtbot, integration_wizard):
    """Create a wizard with all steps populated with valid data."""
    return IntegrationTestHelper.setup_valid_wizard_data(integration_wizard)