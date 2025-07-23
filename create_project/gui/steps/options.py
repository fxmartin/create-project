# ABOUTME: Options configuration step for project creation wizard
# ABOUTME: Allows users to customize project settings and options

"""
Options configuration step for the project creation wizard.

This module implements the options step where users can:
- Select license type
- Configure Git initialization
- Choose virtual environment tool
- Set template-specific options
"""

from typing import Optional, Dict, Any

from PyQt6.QtWidgets import (
    QVBoxLayout, QFormLayout, QComboBox, QCheckBox,
    QGroupBox, QLabel
)
from PyQt6.QtCore import Qt

from create_project.utils.logger import get_logger
from ..wizard.base_step import WizardStep

logger = get_logger(__name__)


class OptionsStep(WizardStep):
    """
    Options configuration step for the project wizard.
    
    This step allows users to:
    - Select project license
    - Enable/disable Git initialization
    - Choose virtual environment tool
    - Configure template-specific options
    """
    
    def __init__(self, wizard):
        """Initialize the options step."""
        super().__init__(
            title="Configure Options",
            subtitle="Customize project settings",
            parent=wizard
        )
        
        self.help_text = (
            "Configure additional options for your project.\n\n"
            "You can select a license, enable Git repository initialization, "
            "and choose whether to create a virtual environment."
        )
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the UI elements."""
        layout = QVBoxLayout()
        
        # Universal options group
        universal_group = QGroupBox("Universal Options")
        universal_layout = QFormLayout()
        
        # License selection
        self.license_combo = QComboBox()
        self.license_combo.setObjectName("licenseCombo")
        self.license_combo.addItems([
            "MIT",
            "Apache-2.0",
            "GPL-3.0",
            "BSD-3-Clause",
            "Unlicense",
            "None"
        ])
        universal_layout.addRow("License:", self.license_combo)
        
        # Git initialization
        self.git_check = QCheckBox("Initialize Git repository")
        self.git_check.setObjectName("gitCheck")
        self.git_check.setChecked(True)
        universal_layout.addRow(self.git_check)
        
        # Virtual environment
        self.venv_check = QCheckBox("Create virtual environment")
        self.venv_check.setObjectName("venvCheck")
        self.venv_check.setChecked(True)
        self.venv_check.stateChanged.connect(self._on_venv_changed)
        universal_layout.addRow(self.venv_check)
        
        # Virtual environment tool
        self.venv_tool_combo = QComboBox()
        self.venv_tool_combo.setObjectName("venvToolCombo")
        self.venv_tool_combo.addItems(["uv", "virtualenv", "venv"])
        universal_layout.addRow("Venv Tool:", self.venv_tool_combo)
        
        universal_group.setLayout(universal_layout)
        layout.addWidget(universal_group)
        
        # Placeholder for template-specific options
        self.template_options_label = QLabel(
            "Additional template-specific options will appear here "
            "based on the selected project type."
        )
        self.template_options_label.setWordWrap(True)
        self.template_options_label.setStyleSheet("color: gray;")
        layout.addWidget(self.template_options_label)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def _register_fields(self) -> None:
        """Register wizard fields."""
        # These fields will be accessible throughout the wizard
        self.wizard().registerField("license", self.license_combo, "currentText")
        self.wizard().registerField("initGit", self.git_check)
        self.wizard().registerField("createVenv", self.venv_check)
        self.wizard().registerField("venvTool", self.venv_tool_combo, "currentText")
    
    def _on_venv_changed(self, state: int) -> None:
        """Handle virtual environment checkbox state change."""
        enabled = state == Qt.CheckState.Checked.value
        self.venv_tool_combo.setEnabled(enabled)
    
    def initializePage(self) -> None:
        """Initialize the page when shown."""
        super().initializePage()
        
        # Register fields when page is shown (wizard is available)
        if hasattr(self, '_fields_registered'):
            return
        self._register_fields()
        self._fields_registered = True
        
        # Update wizard data with current selections
        data = self.wizard().data
        data.license = self.license_combo.currentText()
        data.init_git = self.git_check.isChecked()
        data.create_venv = self.venv_check.isChecked()
        data.venv_tool = self.venv_tool_combo.currentText()
    
    def cleanupPage(self) -> None:
        """Clean up when leaving the page."""
        super().cleanupPage()
        
        # Save current selections to wizard data
        data = self.wizard().data
        data.license = self.license_combo.currentText()
        data.init_git = self.git_check.isChecked()
        data.create_venv = self.venv_check.isChecked()
        data.venv_tool = self.venv_tool_combo.currentText() if data.create_venv else None
    
    def validate_step(self) -> bool:
        """Validate the step."""
        # Options are always valid - all have defaults
        return True