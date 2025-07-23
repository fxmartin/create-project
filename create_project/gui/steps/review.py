# ABOUTME: Review and Create wizard step for project generation
# ABOUTME: Displays summary of all settings and triggers project creation

"""Review and Create wizard step."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    QWizardPage,
)

from create_project.gui.widgets.collapsible_section import CollapsibleSection
from create_project.utils.logger import get_logger

if TYPE_CHECKING:
    from create_project.config import ConfigManager
    from create_project.templates import TemplateEngine

logger = get_logger(__name__)


class ReviewStep(QWizardPage):
    """Review and Create wizard step."""

    # Signals
    data_changed = pyqtSignal()
    create_requested = pyqtSignal()

    def __init__(
        self,
        config_manager: ConfigManager,
        template_engine: TemplateEngine,
        parent: Optional[QWidget] = None,
    ) -> None:
        """Initialize the review step.

        Args:
            config_manager: Configuration manager instance
            template_engine: Template engine instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.config_manager = config_manager
        self.template_engine = template_engine
        self._wizard_data: Dict[str, Any] = {}
        self._template = None
        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize the user interface."""
        # Set wizard page properties
        self.setTitle("Review and Create")
        self.setSubTitle("Review your project settings. Click 'Create Project' when ready.")

        layout = QVBoxLayout(self)

        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        # Content widget
        content = QWidget()
        self._content_layout = QVBoxLayout(content)
        self._content_layout.setSpacing(10)

        # Sections
        self._create_sections()

        # Structure preview at bottom
        self._structure_tree = QTreeWidget()
        self._structure_tree.setHeaderLabel("Project Structure Preview")
        self._structure_tree.setMinimumHeight(200)
        self._content_layout.addWidget(self._structure_tree)

        scroll.setWidget(content)
        layout.addWidget(scroll)

        # Create button
        self._create_button = QPushButton("Create Project")
        self._create_button.setStyleSheet("""
            QPushButton {
                background-color: #0d6efd;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #0b5ed7;
            }
            QPushButton:pressed {
                background-color: #0a58ca;
            }
        """)
        self._create_button.clicked.connect(self.create_requested.emit)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self._create_button)
        layout.addLayout(button_layout)

    def _create_sections(self) -> None:
        """Create collapsible sections for different categories."""
        # Basic Information section
        self._basic_section = CollapsibleSection("Basic Information")
        self._basic_content = QTextEdit()
        self._basic_content.setReadOnly(True)
        self._basic_content.setMaximumHeight(100)
        self._basic_section.add_content(self._basic_content)
        self._content_layout.addWidget(self._basic_section)

        # Location section
        self._location_section = CollapsibleSection("Location")
        self._location_content = QTextEdit()
        self._location_content.setReadOnly(True)
        self._location_content.setMaximumHeight(60)
        self._location_section.add_content(self._location_content)
        self._content_layout.addWidget(self._location_section)

        # Options section
        self._options_section = CollapsibleSection("Configuration Options")
        self._options_content = QTextEdit()
        self._options_content.setReadOnly(True)
        self._options_content.setMaximumHeight(150)
        self._options_section.add_content(self._options_content)
        self._content_layout.addWidget(self._options_section)

    def set_wizard_data(self, data: Dict[str, Any]) -> None:
        """Set wizard data for display.

        Args:
            data: Complete wizard data
        """
        self._wizard_data = data
        self._update_display()

    def _update_display(self) -> None:
        """Update the display with current wizard data."""
        if not self._wizard_data:
            return

        # Update basic information
        basic_text = []
        if "project_name" in self._wizard_data:
            basic_text.append(f"<b>Project Name:</b> {self._wizard_data['project_name']}")
        if "author" in self._wizard_data:
            basic_text.append(f"<b>Author:</b> {self._wizard_data['author']}")
        if "version" in self._wizard_data:
            basic_text.append(f"<b>Version:</b> {self._wizard_data['version']}")
        if "description" in self._wizard_data:
            desc = self._wizard_data["description"] or "<i>No description</i>"
            basic_text.append(f"<b>Description:</b> {desc}")
        self._basic_content.setHtml("<br>".join(basic_text))

        # Update location
        location_text = []
        if "base_path" in self._wizard_data:
            base_path = Path(self._wizard_data["base_path"])
            project_name = self._wizard_data.get("project_name", "")
            full_path = base_path / project_name
            location_text.append(f"<b>Project Path:</b> {full_path}")
            if full_path.exists():
                location_text.append(
                    "<span style='color: #f0ad4e;'>⚠️ Directory already exists</span>"
                )
        self._location_content.setHtml("<br>".join(location_text))

        # Update options
        options_text = []

        # Template type
        if "template_type" in self._wizard_data:
            # Load template to get its name
            try:
                template = self.template_engine.load_template(self._wizard_data["template_type"])
                self._template = template
                options_text.append(f"<b>Project Type:</b> {template.metadata.name}")
            except Exception as e:
                logger.error(f"Failed to load template: {e}")
                options_text.append(f"<b>Project Type:</b> {self._wizard_data['template_type']}")

        # Additional options
        additional = self._wizard_data.get("additional_options", {})
        if "git_init" in additional:
            git_status = "Yes" if additional["git_init"] else "No"
            options_text.append(f"<b>Initialize Git:</b> {git_status}")
        if "venv_tool" in additional:
            venv_tool = additional["venv_tool"]
            if venv_tool == "none":
                venv_tool = "No virtual environment"
            options_text.append(f"<b>Virtual Environment:</b> {venv_tool}")
        if "license" in additional:
            options_text.append(f"<b>License:</b> {additional['license']}")

        # Template-specific options
        for key, value in additional.items():
            if key not in ["git_init", "venv_tool", "license"]:
                # Convert key to readable format
                readable_key = key.replace("_", " ").title()
                options_text.append(f"<b>{readable_key}:</b> {value}")

        self._options_content.setHtml("<br>".join(options_text))

        # Update structure preview
        self._update_structure_preview()

    def _update_structure_preview(self) -> None:
        """Update the project structure tree preview."""
        self._structure_tree.clear()

        if not self._template or not self._wizard_data.get("project_name"):
            return

        # Create root item
        project_name = self._wizard_data["project_name"]
        root = QTreeWidgetItem(self._structure_tree, [project_name])
        root.setExpanded(True)

        # Add structure from template
        structure = self._template.structure
        self._add_structure_items(root, structure)

    def _add_structure_items(
        self, parent: QTreeWidgetItem, structure: Dict[str, Any], level: int = 0
    ) -> None:
        """Recursively add structure items to tree.

        Args:
            parent: Parent tree item
            structure: Structure dictionary
            level: Current nesting level
        """
        # Limit depth to prevent excessive nesting
        if level > 5:
            return

        for name, content in structure.items():
            if isinstance(content, dict):
                # Directory
                dir_item = QTreeWidgetItem(parent, [name + "/"])
                dir_item.setExpanded(level < 2)  # Expand first two levels
                self._add_structure_items(dir_item, content, level + 1)
            elif isinstance(content, str):
                # File
                if content:
                    # File with template content
                    file_item = QTreeWidgetItem(parent, [name + " (template)"])
                else:
                    # Empty file
                    file_item = QTreeWidgetItem(parent, [name])

    def validate(self) -> bool:
        """Validate the step data.

        Returns:
            True if validation passes
        """
        # Review step is always valid if we have the required data
        required_fields = ["project_name", "author", "base_path", "template_type"]
        for field in required_fields:
            if field not in self._wizard_data:
                logger.error(f"Missing required field: {field}")
                return False
        return True

    def register_field(self, name: str, widget: QWidget) -> None:
        """Register a field (not used in review step).

        Args:
            name: Field name
            widget: Widget to register
        """
        # Review step doesn't have editable fields
        pass
