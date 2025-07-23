# ABOUTME: Tests for the settings dialog
# ABOUTME: Verifies tabbed interface, configuration loading/saving, and validation

"""Tests for the settings dialog."""

from unittest.mock import Mock, patch

import pytest
import requests
from PyQt6.QtWidgets import QMessageBox

from create_project.ai.ai_service import AIService
from create_project.config import ConfigManager
from create_project.gui.dialogs.settings import SettingsDialog


@pytest.fixture
def mock_config_manager():
    """Create a mock ConfigManager."""
    config = Mock(spec=ConfigManager)

    # Set up default return values
    config.get_setting.side_effect = lambda key, default=None: {
        "user.default_author": "Test Author",
        "project.default_location": "/tmp/projects",
        "ai.enabled": True,
        "ai.ollama_url": "http://localhost:11434",
        "ai.model": "llama2",
        "templates.builtin_path": "/app/templates/builtin",
        "templates.directories": ["/custom/templates1", "/custom/templates2"]
    }.get(key, default)

    config.set_setting = Mock()
    config.save_config = Mock()

    return config


@pytest.fixture
def mock_ai_service():
    """Create a mock AIService."""
    ai_service = Mock(spec=AIService)
    # Mock async methods
    ai_service.is_available = Mock(return_value=True)
    ai_service.get_available_models = Mock(return_value=[])
    return ai_service


@pytest.fixture
def settings_dialog(qtbot, mock_config_manager, mock_ai_service):
    """Create a SettingsDialog instance."""
    dialog = SettingsDialog(mock_config_manager, mock_ai_service)
    qtbot.addWidget(dialog)
    return dialog


class TestSettingsDialog:
    """Tests for SettingsDialog."""

    def test_dialog_creation(self, settings_dialog):
        """Test dialog is created with correct structure."""
        assert settings_dialog.windowTitle() == "Settings"
        assert settings_dialog.isModal()

        # Check tabs exist
        assert settings_dialog.tab_widget.count() == 3
        assert settings_dialog.tab_widget.tabText(0) == "General"
        assert settings_dialog.tab_widget.tabText(1) == "AI Settings"
        assert settings_dialog.tab_widget.tabText(2) == "Template Paths"

    def test_general_tab_widgets(self, settings_dialog):
        """Test general tab contains expected widgets."""
        # Check author edit
        assert hasattr(settings_dialog, "author_edit")
        assert settings_dialog.author_edit.text() == "Test Author"

        # Check location edit
        assert hasattr(settings_dialog, "location_edit")
        assert settings_dialog.location_edit.get_path() == "/tmp/projects"

    def test_ai_tab_widgets(self, settings_dialog):
        """Test AI tab contains expected widgets."""
        # Check AI enabled checkbox
        assert hasattr(settings_dialog, "ai_enabled_checkbox")
        assert settings_dialog.ai_enabled_checkbox.isChecked()

        # Check AI settings group
        assert hasattr(settings_dialog, "ai_settings_group")
        assert settings_dialog.ai_settings_group.isEnabled()

        # Check Ollama URL
        assert hasattr(settings_dialog, "ollama_url_edit")
        assert settings_dialog.ollama_url_edit.text() == "http://localhost:11434"

        # Check model combo
        assert hasattr(settings_dialog, "model_combo")
        assert settings_dialog.model_combo.currentText() == "llama2"

    def test_templates_tab_widgets(self, settings_dialog):
        """Test templates tab contains expected widgets."""
        # Check builtin path label
        assert hasattr(settings_dialog, "builtin_path_label")
        assert "/app/templates/builtin" in settings_dialog.builtin_path_label.text()

        # Check template list
        assert hasattr(settings_dialog, "template_list")
        assert settings_dialog.template_list.count() == 2
        assert settings_dialog.template_list.item(0).text() == "/custom/templates1"
        assert settings_dialog.template_list.item(1).text() == "/custom/templates2"

    def test_ai_enabled_toggle(self, settings_dialog, qtbot):
        """Test AI settings group is enabled/disabled based on checkbox."""
        # Initially checked and enabled
        assert settings_dialog.ai_enabled_checkbox.isChecked()
        assert settings_dialog.ai_settings_group.isEnabled()

        # Uncheck - should disable group
        settings_dialog.ai_enabled_checkbox.setChecked(False)
        assert not settings_dialog.ai_settings_group.isEnabled()

        # Check again - should enable group
        settings_dialog.ai_enabled_checkbox.setChecked(True)
        assert settings_dialog.ai_settings_group.isEnabled()

    def test_save_settings(self, settings_dialog, mock_config_manager, qtbot):
        """Test saving settings updates ConfigManager."""
        # Modify some values
        settings_dialog.author_edit.setText("New Author")
        settings_dialog.ai_enabled_checkbox.setChecked(False)

        # Mock the validation
        settings_dialog._validate_inputs = Mock(return_value=True)

        # Save settings
        settings_dialog._save_settings()

        # Check ConfigManager was updated
        mock_config_manager.set_setting.assert_any_call("user.default_author", "New Author")
        mock_config_manager.set_setting.assert_any_call("ai.enabled", False)
        mock_config_manager.save_config.assert_called_once()

    def test_validation_invalid_location(self, settings_dialog, qtbot):
        """Test validation fails for non-existent location."""
        # Set invalid location
        settings_dialog.location_edit.set_path("/nonexistent/path")

        # Mock message box
        with patch.object(QMessageBox, "warning") as mock_warning:
            result = settings_dialog._validate_inputs()

            assert not result
            mock_warning.assert_called_once()
            assert "does not exist" in str(mock_warning.call_args)

    def test_validation_invalid_url(self, settings_dialog, qtbot):
        """Test validation fails for invalid Ollama URL."""
        # Clear location to avoid that validation error
        settings_dialog.location_edit.set_path("")

        # Clear template directories to avoid that validation error
        settings_dialog.template_list.clear()

        # Set invalid URL
        settings_dialog.ollama_url_edit.setText("not-a-url")

        # Mock message box
        with patch.object(QMessageBox, "warning") as mock_warning:
            result = settings_dialog._validate_inputs()

            assert not result
            mock_warning.assert_called_once()
            assert "valid Ollama URL" in str(mock_warning.call_args)

    def test_validation_no_model(self, settings_dialog, qtbot):
        """Test validation fails when no model selected."""
        # Clear location to avoid that validation error
        settings_dialog.location_edit.set_path("")

        # Clear template directories to avoid that validation error
        settings_dialog.template_list.clear()

        # Clear model selection
        settings_dialog.model_combo.setCurrentText("")

        # Mock message box
        with patch.object(QMessageBox, "warning") as mock_warning:
            result = settings_dialog._validate_inputs()

            assert not result
            mock_warning.assert_called_once()
            assert "model name" in str(mock_warning.call_args)

    def test_refresh_models(self, settings_dialog, mock_ai_service, qtbot):
        """Test refreshing models from AI service."""
        # Clear combo first
        settings_dialog.model_combo.clear()
        assert settings_dialog.model_combo.count() == 0

        # Refresh models
        settings_dialog._refresh_models()

        # Check models were added (we're using hardcoded list now)
        assert settings_dialog.model_combo.count() == 5
        assert settings_dialog.model_combo.itemText(0) == "llama2"
        assert settings_dialog.model_combo.itemText(1) == "codellama"
        assert settings_dialog.model_combo.itemText(2) == "mistral"
        assert settings_dialog.model_combo.itemText(3) == "phi"
        assert settings_dialog.model_combo.itemText(4) == "neural-chat"

    def test_test_connection_success(self, settings_dialog, qtbot):
        """Test successful connection test."""
        # Mock requests
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            # Mock message box
            with patch.object(QMessageBox, "information") as mock_info:
                settings_dialog._test_connection()

                mock_info.assert_called_once()
                assert "Successfully connected" in str(mock_info.call_args)

    def test_test_connection_failure(self, settings_dialog, qtbot):
        """Test failed connection test."""
        # Mock requests with connection error
        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError()

            # Mock message box
            with patch.object(QMessageBox, "warning") as mock_warning:
                settings_dialog._test_connection()

                mock_warning.assert_called_once()
                assert "Could not connect" in str(mock_warning.call_args)

    def test_add_template_directory(self, settings_dialog, qtbot):
        """Test adding a template directory."""
        # Mock file dialog
        with patch("PyQt6.QtWidgets.QFileDialog.getExistingDirectory") as mock_dialog:
            mock_dialog.return_value = "/new/template/dir"

            # Initial count
            initial_count = settings_dialog.template_list.count()

            # Add directory
            settings_dialog._add_template_directory()

            # Check it was added
            assert settings_dialog.template_list.count() == initial_count + 1
            assert (
                settings_dialog.template_list.item(initial_count).text()
                == "/new/template/dir"
            )

    def test_add_duplicate_template_directory(self, settings_dialog, qtbot):
        """Test adding a duplicate template directory shows warning."""
        # Mock file dialog to return existing directory
        with patch("PyQt6.QtWidgets.QFileDialog.getExistingDirectory") as mock_dialog:
            mock_dialog.return_value = "/custom/templates1"  # Already in list

            # Mock message box
            with patch.object(QMessageBox, "information") as mock_info:
                settings_dialog._add_template_directory()

                mock_info.assert_called_once()
                assert "already in the list" in str(mock_info.call_args)

    def test_remove_template_directory(self, settings_dialog, qtbot):
        """Test removing a template directory."""
        # Select first item
        settings_dialog.template_list.setCurrentRow(0)

        # Initial count
        initial_count = settings_dialog.template_list.count()
        removed_text = settings_dialog.template_list.item(0).text()

        # Remove it
        settings_dialog._remove_template_directory()

        # Check it was removed
        assert settings_dialog.template_list.count() == initial_count - 1

        # Check the removed item is not in the list
        for i in range(settings_dialog.template_list.count()):
            assert settings_dialog.template_list.item(i).text() != removed_text

    def test_remove_button_enabled_state(self, settings_dialog, qtbot):
        """Test remove button is enabled only when item selected."""
        # Initially no selection
        settings_dialog.template_list.clearSelection()
        assert not settings_dialog.remove_template_button.isEnabled()

        # Select an item
        settings_dialog.template_list.setCurrentRow(0)
        assert settings_dialog.remove_template_button.isEnabled()

        # Clear selection
        settings_dialog.template_list.clearSelection()
        assert not settings_dialog.remove_template_button.isEnabled()

    def test_settings_saved_signal(self, settings_dialog, qtbot):
        """Test settings_saved signal is emitted."""
        # Mock validation and accept
        settings_dialog._validate_inputs = Mock(return_value=True)
        settings_dialog.accept = Mock()

        # Connect signal spy
        with qtbot.waitSignal(settings_dialog.settings_saved, timeout=1000):
            settings_dialog._save_settings()

        settings_dialog.accept.assert_called_once()

    def test_cancel_button(self, settings_dialog, qtbot):
        """Test cancel button exists."""
        # Check cancel button exists
        cancel_button = settings_dialog.button_box.button(
            settings_dialog.button_box.StandardButton.Cancel
        )
        assert cancel_button is not None
        assert cancel_button.text() == "Cancel"

