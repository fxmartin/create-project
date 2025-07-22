# ABOUTME: Basic information wizard step for project details
# ABOUTME: Collects project name, author, version, and description with validation

"""
Basic information wizard step module.

This module implements the second wizard step that collects basic project
information including:
- Project name (with Python package name validation)
- Author name
- Version (with semantic versioning validation)
- Description
"""

import re
from typing import Optional, Any, Dict, cast

from PyQt6.QtWidgets import (
    QFormLayout, QLineEdit, QTextEdit, QLabel, QVBoxLayout
)
from PyQt6.QtCore import Qt, QRegularExpression
from PyQt6.QtGui import QRegularExpressionValidator

from create_project.gui.wizard.base_step import WizardStep
from create_project.utils.logger import get_logger

logger = get_logger(__name__)


class BasicInfoStep(WizardStep):
    """Second wizard step for collecting basic project information."""

    def __init__(self, parent: Optional[Any] = None) -> None:
        """Initialize the basic information step."""
        # Initialize UI elements - will be set in _setup_ui
        self.name_edit: QLineEdit
        self.author_edit: QLineEdit
        self.version_edit: QLineEdit
        self.description_edit: QTextEdit
        
        # Validation error labels
        self.name_error_label: QLabel
        self.version_error_label: QLabel

        super().__init__(
            "Basic Information",
            "Enter basic information about your project",
            parent
        )

    def _setup_ui(self) -> None:
        """Set up the user interface for this step."""
        # Create form layout
        form_layout = QFormLayout()
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        
        # Project Name field
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., my_awesome_project")
        self.name_edit.textChanged.connect(self._validate_project_name)
        
        # Name error label
        self.name_error_label = QLabel()
        self.name_error_label.setObjectName("fieldErrorLabel")
        self.name_error_label.setStyleSheet("color: red; font-size: 12px;")
        self.name_error_label.setWordWrap(True)
        self.name_error_label.hide()
        
        name_container = QVBoxLayout()
        name_container.addWidget(self.name_edit)
        name_container.addWidget(self.name_error_label)
        name_container.setContentsMargins(0, 0, 0, 0)
        
        # Author field
        self.author_edit = QLineEdit()
        self.author_edit.setPlaceholderText("e.g., John Doe")
        
        # Version field with semantic versioning
        self.version_edit = QLineEdit()
        self.version_edit.setText("0.1.0")  # Default version
        self.version_edit.setPlaceholderText("e.g., 0.1.0")
        self.version_edit.textChanged.connect(self._validate_version)
        
        # Version error label
        self.version_error_label = QLabel()
        self.version_error_label.setObjectName("fieldErrorLabel")
        self.version_error_label.setStyleSheet("color: red; font-size: 12px;")
        self.version_error_label.setWordWrap(True)
        self.version_error_label.hide()
        
        version_container = QVBoxLayout()
        version_container.addWidget(self.version_edit)
        version_container.addWidget(self.version_error_label)
        version_container.setContentsMargins(0, 0, 0, 0)
        
        # Description field
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("A brief description of your project...")
        self.description_edit.setMaximumHeight(100)
        
        # Add fields to form
        form_layout.addRow("Project Name*:", name_container)
        form_layout.addRow("Author*:", self.author_edit)
        form_layout.addRow("Version*:", version_container)
        form_layout.addRow("Description:", self.description_edit)
        
        # Register required fields with the wizard
        self.registerField("projectName*", self.name_edit)
        self.registerField("author*", self.author_edit)
        self.registerField("version*", self.version_edit)
        self.registerField("description", self.description_edit, "plainText")
        
        # Add form to main layout
        main_layout = cast(QVBoxLayout, self.layout)
        main_layout.addLayout(form_layout)
        main_layout.addStretch()
        
        logger.debug("Basic info step UI setup complete")

    def _connect_signals(self) -> None:
        """Connect signals for this step."""
        # Field validation is connected in _setup_ui
        pass

    def _validate_project_name(self, text: str) -> None:
        """Validate project name in real-time."""
        if not text:
            self.name_error_label.hide()
            self.completeChanged.emit()
            return
            
        # Python package name validation regex
        # Must start with letter/underscore, contain only letters/numbers/underscores
        pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*$'
        
        if not re.match(pattern, text):
            self.name_error_label.setText(
                "Project name must be a valid Python identifier: "
                "start with letter/underscore, contain only letters/numbers/underscores"
            )
            self.name_error_label.show()
            logger.debug(f"Project name '{text}' is invalid - showing error label")
        else:
            self.name_error_label.hide()
            logger.debug(f"Project name '{text}' is valid - hiding error label")
            
        # Update completion state
        self.completeChanged.emit()

    def _validate_version(self, text: str) -> None:
        """Validate version string in real-time."""
        if not text:
            self.version_error_label.hide()
            return
            
        # Semantic versioning regex
        # Matches X.Y.Z where X, Y, Z are non-negative integers
        pattern = r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$'
        
        if not re.match(pattern, text):
            self.version_error_label.setText(
                "Version must follow semantic versioning (e.g., 1.0.0, 0.1.0-alpha)"
            )
            self.version_error_label.show()
        else:
            self.version_error_label.hide()
            
        # Update completion state
        self.completeChanged.emit()

    def validate(self) -> Optional[str]:
        """Perform final validation before moving to next step."""
        # Check project name
        project_name = self.name_edit.text().strip()
        if not project_name:
            return "Project name is required"
            
        pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*$'
        if not re.match(pattern, project_name):
            return "Project name must be a valid Python identifier"
            
        # Check author
        author = self.author_edit.text().strip()
        if not author:
            return "Author name is required"
            
        # Check version
        version = self.version_edit.text().strip()
        if not version:
            return "Version is required"
            
        # Semantic versioning check
        version_pattern = r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$'
        if not re.match(version_pattern, version):
            return "Version must follow semantic versioning format"
            
        return None

    def isComplete(self) -> bool:
        """Check if the page is complete and ready to proceed."""
        # Check all required fields
        if not self.name_edit.text().strip():
            return False
            
        if not self.author_edit.text().strip():
            return False
            
        if not self.version_edit.text().strip():
            return False
            
        # Check for validation errors
        if self.name_error_label.isVisible():
            return False
            
        if self.version_error_label.isVisible():
            return False
            
        return True

    def initializePage(self) -> None:
        """Initialize the page when it becomes visible."""
        super().initializePage()
        
        # Get wizard data
        wizard = self.wizard()
        if wizard and hasattr(wizard, "data"):
            # Pre-fill author from config if available
            if hasattr(wizard, "config_manager"):
                default_author = wizard.config_manager.get_setting("defaults.author", "")
                if default_author and not self.author_edit.text():
                    self.author_edit.setText(default_author)
                    
            # Update wizard data with current values
            self._update_wizard_data()
            
        logger.debug("Basic info step initialized")

    def cleanupPage(self) -> None:
        """Clean up when leaving the page."""
        super().cleanupPage()
        self._update_wizard_data()

    def _update_wizard_data(self) -> None:
        """Update wizard data with current field values."""
        wizard = self.wizard()
        if wizard and hasattr(wizard, "data"):
            wizard.data.project_name = self.name_edit.text().strip()
            wizard.data.author = self.author_edit.text().strip()
            wizard.data.version = self.version_edit.text().strip()
            wizard.data.description = self.description_edit.toPlainText().strip()
            
            logger.debug(f"Updated wizard data: project_name={wizard.data.project_name}")