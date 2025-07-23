# ABOUTME: Settings dialog for application preferences
# ABOUTME: Provides tabbed interface for general, AI, and template settings

"""Settings dialog for application preferences.

This module provides a comprehensive settings dialog with tabs for:
- General settings (default author, project location)
- AI settings (Ollama configuration, model selection)
- Template paths (custom template directories)
"""

from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from create_project.ai.ai_service import AIService
from create_project.config import ConfigManager
from create_project.gui.widgets import FilePathEdit, SelectionMode, ValidatedLineEdit
from create_project.utils.logger import get_logger

logger = get_logger(__name__)


class SettingsDialog(QDialog):
    """Settings dialog with tabbed interface for application preferences."""

    # Signal emitted when settings are saved
    settings_saved = pyqtSignal()

    def __init__(
        self, config_manager: ConfigManager, ai_service: AIService, parent=None
    ):
        """Initialize the settings dialog.

        Args:
            config_manager: Configuration manager instance
            ai_service: AI service instance for connection testing
            parent: Parent widget
        """
        super().__init__(parent)
        self.config_manager = config_manager
        self.ai_service = ai_service

        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(600, 500)

        self._create_ui()
        self._load_settings()

    def _create_ui(self) -> None:
        """Create the user interface."""
        layout = QVBoxLayout(self)

        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Create tabs
        self._create_general_tab()
        self._create_ai_tab()
        self._create_templates_tab()

        # Create button box
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self._save_settings)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def _create_general_tab(self) -> None:
        """Create the general settings tab."""
        widget = QWidget()
        layout = QFormLayout(widget)

        # Default author
        self.author_edit = QLineEdit()
        self.author_edit.setPlaceholderText("Your name")
        layout.addRow("Default Author:", self.author_edit)

        # Default project location
        self.location_edit = FilePathEdit(
            mode=SelectionMode.DIRECTORY,
            placeholder="Default directory for new projects"
        )
        layout.addRow("Default Location:", self.location_edit)

        # Add spacing
        layout.setVerticalSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        self.tab_widget.addTab(widget, "General")

    def _create_ai_tab(self) -> None:
        """Create the AI settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)

        # AI enabled checkbox
        self.ai_enabled_checkbox = QCheckBox("Enable AI Assistance")
        self.ai_enabled_checkbox.setToolTip(
            "Enable AI-powered error help and suggestions"
        )
        layout.addWidget(self.ai_enabled_checkbox)

        # AI settings group
        self.ai_settings_group = QGroupBox("Ollama Configuration")
        ai_layout = QFormLayout(self.ai_settings_group)

        # Ollama URL
        self.ollama_url_edit = ValidatedLineEdit(
            r"^https?://[^\s]+$",
            "Enter a valid URL (e.g., http://localhost:11434)"
        )
        self.ollama_url_edit.setPlaceholderText("http://localhost:11434")
        ai_layout.addRow("Ollama URL:", self.ollama_url_edit)

        # Model selection
        model_layout = QHBoxLayout()
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.setPlaceholderText("Select or enter model name")
        model_layout.addWidget(self.model_combo, 1)

        self.refresh_models_button = QPushButton("Refresh")
        self.refresh_models_button.clicked.connect(self._refresh_models)
        model_layout.addWidget(self.refresh_models_button)

        ai_layout.addRow("Model:", model_layout)

        # Test connection button
        self.test_connection_button = QPushButton("Test Connection")
        self.test_connection_button.clicked.connect(self._test_connection)
        ai_layout.addRow("", self.test_connection_button)

        layout.addWidget(self.ai_settings_group)

        # Connect checkbox to group enable/disable
        self.ai_enabled_checkbox.toggled.connect(
            self.ai_settings_group.setEnabled
        )

        layout.addStretch()

        self.tab_widget.addTab(widget, "AI Settings")

    def _create_templates_tab(self) -> None:
        """Create the template paths tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)

        # Built-in templates path (read-only)
        builtin_layout = QFormLayout()
        self.builtin_path_label = QLabel()
        self.builtin_path_label.setWordWrap(True)
        builtin_layout.addRow("Built-in Templates:", self.builtin_path_label)
        layout.addLayout(builtin_layout)

        # Custom template directories
        layout.addWidget(QLabel("Custom Template Directories:"))

        # List widget for template directories
        self.template_list = QListWidget()
        layout.addWidget(self.template_list)

        # Buttons for managing directories
        button_layout = QHBoxLayout()

        self.add_template_button = QPushButton("Add Directory...")
        self.add_template_button.clicked.connect(self._add_template_directory)
        button_layout.addWidget(self.add_template_button)

        self.remove_template_button = QPushButton("Remove")
        self.remove_template_button.clicked.connect(self._remove_template_directory)
        self.remove_template_button.setEnabled(False)
        button_layout.addWidget(self.remove_template_button)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        # Connect selection change
        self.template_list.itemSelectionChanged.connect(
            lambda: self.remove_template_button.setEnabled(
                bool(self.template_list.selectedItems())
            )
        )

        self.tab_widget.addTab(widget, "Template Paths")

    def _load_settings(self) -> None:
        """Load current settings from ConfigManager."""
        try:
            # General settings
            author = self.config_manager.get_setting("user.default_author", "")
            self.author_edit.setText(author)

            location = self.config_manager.get_setting("project.default_location", "")
            if location:
                self.location_edit.set_path(location)

            # AI settings
            ai_enabled = self.config_manager.get_setting("ai.enabled", default=True)
            self.ai_enabled_checkbox.setChecked(ai_enabled)
            self.ai_settings_group.setEnabled(ai_enabled)

            ollama_url = self.config_manager.get_setting("ai.ollama_url", "http://localhost:11434")
            self.ollama_url_edit.setText(ollama_url)

            model = self.config_manager.get_setting("ai.model", "llama2")
            self.model_combo.setCurrentText(model)

            # Template paths
            builtin_path = self.config_manager.get_setting("templates.builtin_path", "")
            self.builtin_path_label.setText(str(Path(builtin_path).resolve()))

            custom_dirs = self.config_manager.get_setting("templates.directories", [])
            self.template_list.clear()
            for directory in custom_dirs:
                self.template_list.addItem(directory)

            # Try to refresh models
            self._refresh_models()

        except Exception as e:
            logger.error(f"Error loading settings: {e}")

    def _save_settings(self) -> None:
        """Save settings to ConfigManager."""
        try:
            # Validate inputs
            if not self._validate_inputs():
                return

            # General settings
            self.config_manager.set_setting(
                "user.default_author", self.author_edit.text()
            )

            location = self.location_edit.get_path()
            if location:
                self.config_manager.set_setting("project.default_location", location)

            # AI settings
            self.config_manager.set_setting(
                "ai.enabled", self.ai_enabled_checkbox.isChecked()
            )

            if self.ai_enabled_checkbox.isChecked():
                self.config_manager.set_setting(
                    "ai.ollama_url", self.ollama_url_edit.text()
                )
                self.config_manager.set_setting(
                    "ai.model", self.model_combo.currentText()
                )

            # Template paths
            custom_dirs = []
            for i in range(self.template_list.count()):
                custom_dirs.append(self.template_list.item(i).text())
            self.config_manager.set_setting("templates.directories", custom_dirs)

            # Save configuration
            self.config_manager.save_config()

            # Emit signal and close
            self.settings_saved.emit()
            self.accept()

        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save settings: {str(e)}"
            )

    def _validate_inputs(self) -> bool:
        """Validate all input fields.

        Returns:
            True if all inputs are valid
        """
        # Validate location if provided
        location = self.location_edit.get_path()
        if location and not Path(location).exists():
            QMessageBox.warning(
                self,
                "Invalid Location",
                "The default location directory does not exist."
            )
            self.tab_widget.setCurrentIndex(0)  # Switch to General tab
            return False

        # Validate AI settings if enabled
        if self.ai_enabled_checkbox.isChecked():
            if not self.ollama_url_edit.is_valid():
                QMessageBox.warning(
                    self,
                    "Invalid URL",
                    "Please enter a valid Ollama URL."
                )
                self.tab_widget.setCurrentIndex(1)  # Switch to AI tab
                return False

            if not self.model_combo.currentText():
                QMessageBox.warning(
                    self,
                    "No Model Selected",
                    "Please select or enter an AI model name."
                )
                self.tab_widget.setCurrentIndex(1)  # Switch to AI tab
                return False

        # Validate template directories
        for i in range(self.template_list.count()):
            path = self.template_list.item(i).text()
            if not Path(path).exists():
                QMessageBox.warning(
                    self,
                    "Invalid Template Directory",
                    f"Template directory does not exist:\n{path}"
                )
                self.tab_widget.setCurrentIndex(2)  # Switch to Templates tab
                return False

        return True

    def _refresh_models(self) -> None:
        """Refresh the list of available models from Ollama."""
        try:
            self.model_combo.clear()

            # For now, just add some common models
            # TODO: Make this async or use a worker thread for actual model discovery
            common_models = ["llama2", "codellama", "mistral", "phi", "neural-chat"]
            self.model_combo.addItems(common_models)

            # Restore previously selected model if available
            current_model = self.config_manager.get_setting("ai.model", "")
            if current_model:
                index = self.model_combo.findText(current_model)
                if index >= 0:
                    self.model_combo.setCurrentIndex(index)
                else:
                    self.model_combo.setCurrentText(current_model)

        except Exception as e:
            logger.error(f"Error refreshing models: {e}")

    def _test_connection(self) -> None:
        """Test the Ollama connection."""
        try:
            # Update AI service with current URL
            url = self.ollama_url_edit.text()

            # Simple HTTP check for Ollama availability
            import requests
            try:
                response = requests.get(f"{url}/api/tags", timeout=5)
                if response.status_code == 200:
                    QMessageBox.information(
                        self,
                        "Connection Successful",
                        "Successfully connected to Ollama service."
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Connection Failed",
                        f"Ollama returned status code: {response.status_code}\n"
                        "Please check the URL and ensure Ollama is running."
                    )
            except requests.exceptions.ConnectionError:
                QMessageBox.warning(
                    self,
                    "Connection Failed",
                    "Could not connect to Ollama service.\n"
                    "Please check the URL and ensure Ollama is running."
                )
            except requests.exceptions.Timeout:
                QMessageBox.warning(
                    self,
                    "Connection Timeout",
                    "Connection to Ollama timed out.\n"
                    "Please check the URL and network connection."
                )

        except Exception as e:
            logger.error(f"Error testing connection: {e}")
            QMessageBox.critical(
                self,
                "Connection Error",
                f"Error testing connection:\n{str(e)}"
            )

    def _add_template_directory(self) -> None:
        """Add a new template directory."""
        from PyQt6.QtWidgets import QFileDialog

        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Template Directory",
            "",
            QFileDialog.Option.ShowDirsOnly
        )

        if directory:
            # Check if already in list
            for i in range(self.template_list.count()):
                if self.template_list.item(i).text() == directory:
                    QMessageBox.information(
                        self,
                        "Directory Exists",
                        "This directory is already in the list."
                    )
                    return

            self.template_list.addItem(directory)

    def _remove_template_directory(self) -> None:
        """Remove the selected template directory."""
        current_item = self.template_list.currentItem()
        if current_item:
            row = self.template_list.row(current_item)
            self.template_list.takeItem(row)

