# ABOUTME: Review step implementation for project creation wizard
# ABOUTME: Shows summary of selections and triggers project generation

"""
Review step for the project creation wizard.

This module implements the final review step where users can:
- Review all selected options
- See a preview of the project structure
- Trigger project generation
- View progress during generation
"""

from typing import Optional, Dict, Any
from pathlib import Path

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QGroupBox,
    QTextEdit, QSplitter, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal

from create_project.templates.schema import DirectoryItem
from create_project.utils.logger import get_logger
from ..wizard.base_step import WizardStep

logger = get_logger(__name__)


class ReviewStep(WizardStep):
    """
    Review and create step for the project wizard.
    
    This step displays:
    - Summary of all selected options
    - Preview of the project structure
    - Create button to trigger generation
    """
    
    # Signals
    create_clicked = pyqtSignal()  # Emitted when create button is clicked
    
    def __init__(self, wizard):
        """Initialize the review step."""
        super().__init__(
            title="Review and Create",
            subtitle="Review your choices and create the project",
            parent=wizard
        )
        
        self.help_text = (
            "This is the final step before creating your project.\n\n"
            "Review all your selections and the project structure preview. "
            "If everything looks correct, click 'Create Project' to generate "
            "your new project.\n\n"
            "You can go back to any previous step to make changes."
        )
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Set up the UI elements."""
        layout = QVBoxLayout()
        
        # Create splitter for summary and preview
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side: Summary
        summary_widget = self._create_summary_widget()
        splitter.addWidget(summary_widget)
        
        # Right side: Structure preview
        preview_widget = self._create_preview_widget()
        splitter.addWidget(preview_widget)
        
        # Set initial splitter sizes (40% summary, 60% preview)
        splitter.setSizes([400, 600])
        
        layout.addWidget(splitter)
        
        # Create button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.create_button = QPushButton("Create Project")
        self.create_button.setObjectName("createButton")
        self.create_button.clicked.connect(self.create_clicked.emit)
        button_layout.addWidget(self.create_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _create_summary_widget(self) -> QWidget:
        """Create the summary widget showing all selections."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Summary text area
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setObjectName("summaryText")
        
        layout.addWidget(QLabel("Project Configuration:"))
        layout.addWidget(self.summary_text)
        
        widget.setLayout(layout)
        return widget
    
    def _create_preview_widget(self) -> QWidget:
        """Create the structure preview widget."""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Structure tree
        self.structure_tree = QTreeWidget()
        self.structure_tree.setHeaderLabel("Project Structure")
        self.structure_tree.setObjectName("structureTree")
        
        layout.addWidget(QLabel("Project Structure Preview:"))
        layout.addWidget(self.structure_tree)
        
        widget.setLayout(layout)
        return widget
    
    def _register_fields(self) -> None:
        """Register wizard fields."""
        # No fields to register - this is a review step
        pass
    
    def initializePage(self) -> None:
        """Initialize the page when shown."""
        super().initializePage()
        
        # Update summary
        self._update_summary()
        
        # Update structure preview
        self._update_structure_preview()
    
    def _update_summary(self) -> None:
        """Update the summary text with current selections."""
        data = self.wizard().data
        
        summary_parts = []
        
        # Project Type
        if data.template_name:
            summary_parts.append(f"<b>Project Type:</b> {data.template_name}")
        
        # Basic Information
        summary_parts.append("<br><b>Basic Information:</b>")
        if data.project_name:
            summary_parts.append(f"• Name: {data.project_name}")
        if data.author:
            summary_parts.append(f"• Author: {data.author}")
        if data.version:
            summary_parts.append(f"• Version: {data.version}")
        if data.description:
            summary_parts.append(f"• Description: {data.description}")
        
        # Location
        if data.target_path:
            summary_parts.append(f"<br><b>Location:</b> {data.target_path}")
        
        # Options
        summary_parts.append("<br><b>Options:</b>")
        if data.license:
            summary_parts.append(f"• License: {data.license}")
        summary_parts.append(f"• Initialize Git: {'Yes' if data.init_git else 'No'}")
        summary_parts.append(f"• Create Virtual Environment: {'Yes' if data.create_venv else 'No'}")
        if data.create_venv and data.venv_tool:
            summary_parts.append(f"• Virtual Environment Tool: {data.venv_tool}")
        
        # Additional options
        if data.additional_options:
            summary_parts.append("<br><b>Additional Options:</b>")
            for key, value in data.additional_options.items():
                summary_parts.append(f"• {key}: {value}")
        
        # Set the HTML content
        self.summary_text.setHtml("<br>".join(summary_parts))
    
    def _update_structure_preview(self) -> None:
        """Update the project structure preview."""
        self.structure_tree.clear()
        
        data = self.wizard().data
        if not data.template_id or not data.project_name:
            return
        
        # Get template from wizard
        template_loader = self.wizard().template_loader
        if not template_loader:
            return
        
        # Find template
        templates = template_loader.list_templates()
        template_info = None
        for tpl in templates:
            if tpl.get('template_id') == data.template_id:
                template_info = tpl
                break
        
        if not template_info:
            return
        
        # Load template to get structure
        try:
            template_path = template_info.get('file_path')
            if template_path:
                template = self.wizard().template_engine.load_template(template_path)
                if template and hasattr(template, 'structure'):
                    # Create root item
                    root_item = QTreeWidgetItem(self.structure_tree)
                    root_item.setText(0, data.project_name)
                    root_item.setExpanded(True)
                    
                    # Add structure items from root_directory
                    if hasattr(template.structure, 'root_directory'):
                        self._add_structure_items(root_item, template.structure.root_directory)
        except Exception as e:
            logger.error(f"Failed to load template structure: {e}")
    
    def _add_structure_items(
        self,
        parent_item: QTreeWidgetItem,
        directory: DirectoryItem
    ) -> None:
        """Recursively add directory items to the tree."""
        # Add subdirectories
        if directory.directories:
            for subdir in directory.directories:
                dir_item = QTreeWidgetItem(parent_item)
                dir_item.setText(0, f"📁 {subdir.name}")
                
                # Recursively add contents
                self._add_structure_items(dir_item, subdir)
        
        # Add files
        if directory.files:
            for file in directory.files:
                file_item = QTreeWidgetItem(parent_item)
                file_item.setText(0, f"📄 {file.name}")
    
    def validate_step(self) -> bool:
        """
        Validate the step.
        
        The review step is always valid since all validation
        happens in previous steps.
        """
        return True
    
    def isComplete(self) -> bool:
        """Check if the step is complete."""
        # Always complete - user can create project or go back
        return True