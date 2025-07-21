# ABOUTME: Main wizard implementation for project creation workflow
# ABOUTME: Manages step navigation, data collection, and project generation

"""
Project creation wizard module.

This module implements the main wizard interface that guides users through
the project creation process. It manages:
- Step navigation and validation
- Data collection from each step
- Integration with backend services
- Progress tracking during generation
- Error handling with AI assistance
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtWidgets import (
    QWizard, QWizardPage, QMessageBox, QProgressDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot

from create_project.config.config_manager import ConfigManager
from create_project.templates.engine import TemplateEngine
from create_project.core.api import create_project_async
from create_project.core.project_generator import ProjectOptions
from create_project.ai.ai_service import AIService
from create_project.utils.logger import get_logger
from .base_step import WizardStep
from ..steps.project_type import ProjectTypeStep

logger = get_logger(__name__)


@dataclass
class WizardData:
    """Container for data collected through the wizard."""
    
    # Template selection
    template_id: Optional[str] = None
    template_name: Optional[str] = None
    
    # Basic information
    project_name: Optional[str] = None
    author: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    
    # Location
    location: Optional[Path] = None
    
    # Options
    license: Optional[str] = None
    init_git: bool = True
    create_venv: bool = True
    venv_tool: Optional[str] = None
    additional_options: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.additional_options is None:
            self.additional_options = {}
    
    @property
    def target_path(self) -> Optional[Path]:
        """Get the full target path for the project."""
        if self.location and self.project_name:
            return self.location / self.project_name
        return None
    
    def to_variables(self) -> Dict[str, Any]:
        """Convert to template variables dictionary."""
        return {
            "project_name": self.project_name,
            "author": self.author,
            "version": self.version,
            "description": self.description,
            "license": self.license,
            **self.additional_options
        }


class ProjectGenerationThread(QThread):
    """Thread for running project generation without blocking UI."""
    
    progress = pyqtSignal(int, str)  # Progress percentage and message
    finished = pyqtSignal(bool, str)  # Success and message/error
    
    def __init__(
        self,
        template_engine: TemplateEngine,
        wizard_data: WizardData,
        ai_service: Optional[AIService] = None
    ):
        super().__init__()
        self.template_engine = template_engine
        self.wizard_data = wizard_data
        self.ai_service = ai_service
        self._cancelled = False
    
    def run(self):
        """Run project generation in background."""
        try:
            self.progress.emit(0, "Starting project generation...")
            
            # Get template
            template = self.template_engine.get_template(self.wizard_data.template_id)
            if not template:
                self.finished.emit(False, f"Template '{self.wizard_data.template_id}' not found")
                return
            
            if self._cancelled:
                return
            
            self.progress.emit(20, "Creating project structure...")
            
            # Create project options
            options = ProjectOptions(
                dry_run=False,
                create_git_repo=self.wizard_data.init_git,
                create_venv=self.wizard_data.create_venv,
                venv_tool=self.wizard_data.venv_tool,
                execute_post_commands=True,
                enable_ai_assistance=self.ai_service is not None
            )
            
            # Use the async API
            result = create_project_async(
                template=template,
                variables=self.wizard_data.to_variables(),
                target_path=self.wizard_data.target_path,
                options=options,
                ai_service=self.ai_service,
                progress_callback=self._progress_callback
            )
            
            if result.success:
                message = f"Project created successfully at {result.target_path}"
                self.finished.emit(True, message)
            else:
                error_msg = "\n".join(result.errors)
                self.finished.emit(False, error_msg)
                
        except Exception as e:
            logger.exception("Project generation failed")
            self.finished.emit(False, str(e))
    
    def _progress_callback(self, message: str, percentage: Optional[int] = None):
        """Handle progress updates from generator."""
        if percentage is not None:
            self.progress.emit(percentage, message)
    
    def cancel(self):
        """Cancel the generation process."""
        self._cancelled = True


class ProjectWizard(QWizard):
    """
    Main wizard for creating Python projects.
    
    Guides users through project configuration with the following steps:
    1. Project type selection
    2. Basic information
    3. Location selection
    4. Options configuration
    5. Review and create
    """
    
    # Page IDs
    PAGE_PROJECT_TYPE = 0
    PAGE_BASIC_INFO = 1
    PAGE_LOCATION = 2
    PAGE_OPTIONS = 3
    PAGE_REVIEW = 4
    
    # Signals
    project_created = pyqtSignal(Path)  # Emitted when project is successfully created
    
    def __init__(
        self,
        config_manager: ConfigManager,
        template_engine: TemplateEngine,
        template_loader=None,  # Add template_loader parameter
        ai_service: Optional[AIService] = None,
        parent=None
    ):
        """
        Initialize the project wizard.
        
        Args:
            config_manager: Configuration manager instance
            template_engine: Template engine instance
            template_loader: Template loader instance
            ai_service: Optional AI service for assistance
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.config_manager = config_manager
        self.template_engine = template_engine
        self.template_loader = template_loader
        self.ai_service = ai_service
        
        # Wizard data
        self.wizard_data = WizardData()
        
        # Generation thread
        self.generation_thread: Optional[ProjectGenerationThread] = None
        self.progress_dialog: Optional[QProgressDialog] = None
        
        # Set up wizard
        self._setup_wizard()
        self._add_pages()
        self._connect_signals()
        
        logger.info("Project wizard initialized")
    
    @property
    def data(self) -> WizardData:
        """Access wizard data for child pages."""
        return self.wizard_data
    
    def _setup_wizard(self) -> None:
        """Configure wizard appearance and behavior."""
        self.setWindowTitle("Create Python Project")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        
        # Enable help button
        self.setOption(QWizard.WizardOption.HaveHelpButton, True)
        self.setOption(QWizard.WizardOption.HelpButtonOnRight, False)
        
        # Set button text
        self.setButtonText(QWizard.WizardButton.BackButton, "< Back")
        self.setButtonText(QWizard.WizardButton.NextButton, "Next >")
        self.setButtonText(QWizard.WizardButton.FinishButton, "Create Project")
        self.setButtonText(QWizard.WizardButton.CancelButton, "Cancel")
        
        # Set minimum size
        self.setMinimumSize(800, 600)
    
    def _add_pages(self) -> None:
        """Add wizard pages."""
        logger.info("Adding wizard pages")
        
        # Add actual step implementations
        # Project Type Selection (implemented)
        self.addPage(ProjectTypeStep(self))
        
        # Placeholder pages for remaining steps
        for i, (title, subtitle) in enumerate([
            ("Basic Information", "Enter project details"),
            ("Select Location", "Choose where to create your project"),
            ("Configure Options", "Customize project settings"),
            ("Review and Create", "Review your choices and create the project")
        ]):
            page = QWizardPage()
            page.setTitle(title)
            page.setSubTitle(subtitle)
            self.addPage(page)
    
    def _connect_signals(self) -> None:
        """Connect signals and slots."""
        self.helpRequested.connect(self._on_help_requested)
        self.finished.connect(self._on_finished)
    
    @pyqtSlot()
    def _on_help_requested(self) -> None:
        """Handle help button click."""
        current_page = self.currentPage()
        if isinstance(current_page, WizardStep):
            current_page.request_help()
        else:
            # Show general help
            QMessageBox.information(
                self,
                "Help",
                "This wizard helps you create a new Python project.\n\n"
                "Follow the steps to configure your project, then click "
                "'Create Project' to generate the project structure."
            )
    
    @pyqtSlot(int)
    def _on_finished(self, result: int) -> None:
        """Handle wizard finish."""
        if result == QWizard.DialogCode.Accepted:
            logger.info("Wizard completed, starting project generation")
            self._start_generation()
        else:
            logger.info("Wizard cancelled")
    
    def validateCurrentPage(self) -> bool:
        """
        Validate the current page.
        
        Overrides QWizard method to ensure proper validation.
        """
        return super().validateCurrentPage()
    
    def _start_generation(self) -> None:
        """Start project generation process."""
        # Create progress dialog
        self.progress_dialog = QProgressDialog(
            "Creating project...",
            "Cancel",
            0,
            100,
            self
        )
        self.progress_dialog.setWindowTitle("Project Generation")
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setValue(0)
        
        # Create and start generation thread
        self.generation_thread = ProjectGenerationThread(
            self.template_engine,
            self.wizard_data,
            self.ai_service
        )
        
        # Connect signals
        self.generation_thread.progress.connect(self._on_generation_progress)
        self.generation_thread.finished.connect(self._on_generation_finished)
        self.progress_dialog.canceled.connect(self._on_generation_cancelled)
        
        # Start generation
        self.generation_thread.start()
    
    @pyqtSlot(int, str)
    def _on_generation_progress(self, percentage: int, message: str) -> None:
        """Handle generation progress updates."""
        if self.progress_dialog:
            self.progress_dialog.setValue(percentage)
            self.progress_dialog.setLabelText(message)
    
    @pyqtSlot(bool, str)
    def _on_generation_finished(self, success: bool, message: str) -> None:
        """Handle generation completion."""
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        
        if success:
            QMessageBox.information(
                self,
                "Success",
                message
            )
            if self.wizard_data.target_path:
                self.project_created.emit(self.wizard_data.target_path)
        else:
            # Show error with AI help if available
            if self.ai_service and self.ai_service.is_available():
                from ..dialogs.error import ErrorDialog
                error_dialog = ErrorDialog(
                    message,
                    details=None,
                    ai_service=self.ai_service,
                    parent=self
                )
                error_dialog.exec()
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to create project:\n\n{message}"
                )
        
        # Clean up thread
        if self.generation_thread:
            self.generation_thread.wait()
            self.generation_thread = None
    
    @pyqtSlot()
    def _on_generation_cancelled(self) -> None:
        """Handle generation cancellation."""
        if self.generation_thread:
            self.generation_thread.cancel()
            logger.info("Project generation cancelled by user")
    
    def collect_data(self) -> WizardData:
        """
        Collect data from all wizard pages.
        
        Returns:
            WizardData object with all collected information
        """
        # This will be implemented once we have the actual step pages
        # For now, return the existing wizard_data
        return self.wizard_data
    
    def done(self, result: int) -> None:
        """
        Handle wizard completion.
        
        Overrides QWizard.done() to add confirmation for cancel.
        """
        if result == QWizard.DialogCode.Rejected:
            # Confirm cancellation
            reply = QMessageBox.question(
                self,
                "Confirm Cancel",
                "Are you sure you want to cancel project creation?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        super().done(result)