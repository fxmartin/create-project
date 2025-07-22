# ABOUTME: Location selection wizard step for choosing project directory
# ABOUTME: Provides directory browser with path validation and write permission checks

"""
Location selection wizard step module.

This module implements the third wizard step that allows users to select
where their project should be created. It provides:
- Directory browser with QFileDialog
- Path validation for write permissions
- Display of final project path
- Warning if directory already exists
"""

import os
from pathlib import Path
from typing import Optional, Any, cast

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QFileDialog, QGroupBox
)
from PyQt6.QtCore import Qt

from create_project.gui.wizard.base_step import WizardStep
from create_project.utils.logger import get_logger

logger = get_logger(__name__)


class LocationStep(WizardStep):
    """Third wizard step for selecting project location."""

    def __init__(self, parent: Optional[Any] = None) -> None:
        """Initialize the location selection step."""
        # Initialize UI elements - will be set in _setup_ui
        self.location_edit: QLineEdit
        self.browse_button: QPushButton
        self.path_preview_label: QLabel
        self.warning_label: QLabel
        
        super().__init__(
            "Project Location",
            "Choose where to create your project",
            parent
        )
        
    def _setup_ui(self) -> None:
        """Set up the user interface for this step."""
        # Location input group
        location_group = QGroupBox("Project Location")
        location_layout = QVBoxLayout()
        
        # Location input with browse button
        input_layout = QHBoxLayout()
        
        self.location_edit = QLineEdit()
        self.location_edit.setPlaceholderText("Select a directory...")
        self.location_edit.textChanged.connect(self._on_location_changed)
        
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self._browse_directory)
        
        input_layout.addWidget(self.location_edit)
        input_layout.addWidget(self.browse_button)
        
        # Path preview
        self.path_preview_label = QLabel()
        self.path_preview_label.setObjectName("pathPreview")
        self.path_preview_label.setStyleSheet("""
            QLabel#pathPreview {
                padding: 10px;
                background-color: #f0f0f0;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                font-family: monospace;
            }
        """)
        self.path_preview_label.setWordWrap(True)
        self.path_preview_label.hide()
        
        # Warning label for existing directories
        self.warning_label = QLabel()
        self.warning_label.setObjectName("warningLabel")
        self.warning_label.setStyleSheet("""
            QLabel#warningLabel {
                color: #ff8800;
                padding: 5px;
                background-color: #fff8e0;
                border: 1px solid #ffcc00;
                border-radius: 4px;
            }
        """)
        self.warning_label.setWordWrap(True)
        self.warning_label.hide()
        
        # Add widgets to group
        location_layout.addLayout(input_layout)
        location_layout.addWidget(self.path_preview_label)
        location_layout.addWidget(self.warning_label)
        location_group.setLayout(location_layout)
        
        # Register field with wizard
        self.registerField("location*", self.location_edit)
        
        # Add to main layout
        main_layout = cast(QVBoxLayout, self.layout)
        main_layout.addWidget(location_group)
        main_layout.addStretch()
        
        # Add help text
        help_label = QLabel(
            "Select the directory where your new project will be created. "
            "The project will be created in a new subdirectory with the project name."
        )
        help_label.setWordWrap(True)
        help_label.setObjectName("helpText")
        help_label.setStyleSheet("QLabel#helpText { color: #666; margin-top: 10px; }")
        main_layout.addWidget(help_label)
        
        logger.debug("Location step UI setup complete")
        
    def _connect_signals(self) -> None:
        """Connect signals for this step."""
        # Signals are connected in _setup_ui
        pass
        
    def _browse_directory(self) -> None:
        """Open directory browser dialog."""
        # Get default directory
        default_dir = self.location_edit.text() or os.path.expanduser("~")
        
        # Open directory dialog
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Project Location",
            default_dir,
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
        )
        
        if directory:
            self.location_edit.setText(directory)
            logger.debug(f"Directory selected: {directory}")
            
    def _on_location_changed(self, text: str) -> None:
        """Handle location text changes."""
        if not text:
            self.path_preview_label.hide()
            self.warning_label.hide()
            self.completeChanged.emit()
            return
            
        # Get project name from wizard
        wizard = self.wizard()
        project_name = ""
        if wizard and hasattr(wizard, "data") and wizard.data.project_name:
            project_name = wizard.data.project_name
        elif wizard:
            # Try to get from registered field
            try:
                project_name = str(wizard.field("projectName") or "")
            except Exception:
                project_name = ""
            
        if project_name:
            # Show full path preview
            full_path = Path(text) / project_name
            self.path_preview_label.setText(f"Project will be created at:\n{full_path}")
            self.path_preview_label.show()
            
            # Check if directory already exists
            if full_path.exists():
                self.warning_label.setText(
                    f"⚠️ Warning: Directory '{project_name}' already exists at this location. "
                    "Existing files may be overwritten."
                )
                self.warning_label.show()
            else:
                self.warning_label.hide()
        else:
            self.path_preview_label.setText(f"Project will be created in:\n{text}")
            self.path_preview_label.show()
            self.warning_label.hide()
            
        # Update completion state
        self.completeChanged.emit()
        
    def validate(self) -> Optional[str]:
        """Perform validation before moving to next step."""
        location = self.location_edit.text().strip()
        
        if not location:
            return "Please select a project location"
            
        try:
            path = Path(location)
            
            # Check if path exists
            if not path.exists():
                return f"Directory does not exist: {location}"
                
            # Check if it's a directory
            if not path.is_dir():
                return f"Path is not a directory: {location}"
                
            # Check write permissions
            if not os.access(path, os.W_OK):
                return f"No write permission for directory: {location}"
                
            # Validate it's not a system directory
            restricted_paths = [
                Path("/"),
                Path("/usr"),
                Path("/etc"),
                Path("/bin"),
                Path("/sbin"),
                Path("C:\\"),
                Path("C:\\Windows"),
                Path("C:\\Program Files"),
                Path("C:\\Program Files (x86)")
            ]
            
            # Resolve to absolute path for comparison
            abs_path = path.resolve()
            for restricted in restricted_paths:
                try:
                    if abs_path == restricted.resolve():
                        return f"Cannot create projects in system directory: {location}"
                except Exception:
                    # Skip if path doesn't exist on this OS
                    pass
                    
        except Exception as e:
            logger.error(f"Path validation error: {e}")
            return f"Invalid path: {str(e)}"
            
        return None
        
    def isComplete(self) -> bool:
        """Check if the page is complete and ready to proceed."""
        location = self.location_edit.text().strip()
        
        if not location:
            return False
            
        # Basic path validation
        try:
            path = Path(location)
            return path.exists() and path.is_dir()
        except Exception:
            return False
            
    def initializePage(self) -> None:
        """Initialize the page when it becomes visible."""
        super().initializePage()
        
        # Get wizard data
        wizard = self.wizard()
        if wizard and hasattr(wizard, "data"):
            # Set default location from config if available
            if not self.location_edit.text() and hasattr(wizard, "config_manager"):
                default_location = wizard.config_manager.get_setting("defaults.location", "")
                if not default_location:
                    # Use user's home directory as default
                    default_location = os.path.expanduser("~")
                self.location_edit.setText(default_location)
                
            # Update preview if project name is available
            if wizard.data.project_name:
                self._on_location_changed(self.location_edit.text())
                
        logger.debug("Location step initialized")
        
    def cleanupPage(self) -> None:
        """Clean up when leaving the page."""
        super().cleanupPage()
        self._update_wizard_data()
        
    def _update_wizard_data(self) -> None:
        """Update wizard data with current field values."""
        wizard = self.wizard()
        if wizard and hasattr(wizard, "data"):
            location_text = self.location_edit.text().strip()
            if location_text:
                wizard.data.location = Path(location_text)
                logger.debug(f"Updated wizard data: location={wizard.data.location}")