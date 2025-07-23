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

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QMessageBox, QWizard, QWizardPage

from create_project.ai.ai_service import AIService
from create_project.config.config_manager import ConfigManager
from create_project.core.api import create_project_async
from create_project.core.project_generator import ProjectOptions, ProjectGenerator
from create_project.templates.engine import TemplateEngine
from create_project.utils.logger import get_logger

from ..steps.basic_info import BasicInfoStep
from ..steps.location import LocationStep
from ..steps.options import OptionsStep
from ..steps.project_type import ProjectTypeStep
from ..steps.review import ReviewStep
from ..widgets.progress_dialog import ProgressDialog
from .base_step import WizardStep

logger = get_logger(__name__)


@dataclass
class WizardData:
    """Container for data collected through the wizard."""

    # Template selection
    template_id: Optional[str] = None
    template_name: Optional[str] = None
    template_path: Optional[str] = None

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
            **self.additional_options,
        }


class ProjectGenerationThread(QThread):
    """Thread for running project generation without blocking UI."""

    progress = pyqtSignal(int, str)  # Progress percentage and message
    finished = pyqtSignal(bool, str)  # Success and message/error

    def __init__(
        self,
        project_path: Path,
        options: ProjectOptions,
        template_engine: TemplateEngine,
        template_loader,
        wizard_data: WizardData,
        ai_service: Optional[AIService] = None,
    ):
        super().__init__()
        self.project_path = project_path
        self.options = options
        self.template_engine = template_engine
        self.template_loader = template_loader
        self.wizard_data = wizard_data
        self.ai_service = ai_service
        self._cancelled = False

    def run(self):
        """Run project generation in background."""
        try:
            self.progress.emit(0, "Starting project generation...")

            if self._cancelled:
                return

            self.progress.emit(10, "Loading template configuration...")
            
            if self._cancelled:
                return

            # Use the async API directly with required parameters
            from create_project.core.project_generator import ProjectGenerator
            
            # Create generator
            generator = ProjectGenerator(
                template_loader=self.template_engine.template_loader if hasattr(self.template_engine, 'template_loader') else None,
                ai_service=self.ai_service
            )
            
            # Find template file path first
            template_path = None
            templates = self.template_loader.list_templates()
            for template_info in templates:
                if template_info.get('template_id') == self.wizard_data.template_id:
                    template_path = template_info.get('file_path')
                    break
            
            if not template_path:
                self.finished.emit(False, f"Template '{self.wizard_data.template_id}' not found")
                return
            
            # Load the template
            try:
                template = self.template_engine.load_template(template_path)
            except Exception as e:
                self.finished.emit(False, f"Failed to load template: {str(e)}")
                return
            
            if self._cancelled:
                return
            
            self.progress.emit(30, "Preparing project variables...")
            # Collect variables
            variables = {
                "project_name": self.wizard_data.project_name,
                "author": self.wizard_data.author,
                "version": self.wizard_data.version,
                "description": self.wizard_data.description,
                "license": self.wizard_data.license,
            }
            # Add any additional template variables
            if self.wizard_data.additional_options:
                variables.update(self.wizard_data.additional_options)
            
            if self._cancelled:
                return
            
            # Create project options
            options = ProjectOptions(
                create_git_repo=self.wizard_data.init_git,
                create_venv=self.wizard_data.create_venv,
                execute_post_commands=True,
                enable_ai_assistance=self.ai_service is not None
            )
            
            self.progress.emit(40, "Starting project generation...")
            # Generate project
            result = generator.generate_project(
                template=template,
                variables=variables,
                target_path=self.project_path,
                options=options,
                progress_callback=self._progress_callback,
            )

            if result.success:
                message = f"Project created successfully at {result.project_path}"
                self.finished.emit(True, message)
            else:
                error_msg = "\n".join(result.errors) if result.errors else "Unknown error occurred"
                self.finished.emit(False, error_msg)

        except Exception as e:
            logger.exception("Project generation failed")
            self.finished.emit(False, str(e))

    def _progress_callback(self, message: str, percentage: Optional[int] = None):
        """Handle progress updates from generator."""
        # Map internal progress to 40-90% range since we use 0-40% for setup
        if percentage is not None:
            scaled_percentage = 40 + int((percentage / 100.0) * 50)
            self.progress.emit(scaled_percentage, message)
        else:
            # If no percentage, just emit the message with current progress
            self.progress.emit(50, message)

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
        parent=None,
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

        # Basic Information (implemented)
        self.addPage(BasicInfoStep(self))

        # Location Selection (implemented)
        self.addPage(LocationStep(self))

        # Options Configuration (implemented)
        options_step = OptionsStep(self)
        options_step.license_preview_requested.connect(self._show_license_preview)
        self.addPage(options_step)

        # Review and Create (implemented)
        review_step = ReviewStep(self.config_manager, self.template_engine, self)
        review_step.create_requested.connect(self._on_create_project)
        self.addPage(review_step)
    def _connect_signals(self) -> None:
        """Connect signals and slots."""
        self.helpRequested.connect(self._on_help_requested)
        self.finished.connect(self._on_finished)
        self.currentIdChanged.connect(self._on_page_changed)

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
                "'Create Project' to generate the project structure.",
            )

    @pyqtSlot(int)
    def _on_finished(self, result: int) -> None:
        """Handle wizard finish."""
        if result == QWizard.DialogCode.Accepted:
            logger.info("Wizard completed successfully")
            # Generation is triggered by the Create button in ReviewStep
        else:
            logger.info("Wizard cancelled")

    @pyqtSlot(str)
    def _show_license_preview(self, license_id: str) -> None:
        """
        Show license preview dialog.

        Args:
            license_id: License identifier to preview
        """
        from ..widgets.license_preview import LicensePreviewDialog

        dialog = LicensePreviewDialog(license_id, self)
        dialog.exec()

    def validateCurrentPage(self) -> bool:
        """
        Validate the current page.

        Overrides QWizard method to ensure proper validation.
        """
        return super().validateCurrentPage()

    def _start_generation(self, project_path: Path, options: ProjectOptions) -> None:
        """Start project generation process.
        
        Args:
            project_path: Path where project will be created
            options: Project generation options
        """
        # Create custom progress dialog
        self.progress_dialog = ProgressDialog(self)
        self.progress_dialog.show()

        # Create and start generation thread
        self.generation_thread = ProjectGenerationThread(
            project_path, options, self.template_engine, self.template_loader, self.wizard_data, self.ai_service
        )

        # Connect signals
        self.generation_thread.progress.connect(self._on_generation_progress)
        self.generation_thread.finished.connect(self._on_generation_finished)
        self.progress_dialog.cancelled.connect(self._on_generation_cancelled)

        # Start generation
        self.generation_thread.start()

    @pyqtSlot(int, str)
    def _on_generation_progress(self, percentage: int, message: str) -> None:
        """Handle generation progress updates."""
        if self.progress_dialog:
            self.progress_dialog.update_progress(percentage, message)

    @pyqtSlot(bool, str)
    def _on_generation_finished(self, success: bool, message: str) -> None:
        """Handle generation completion."""
        if self.progress_dialog:
            self.progress_dialog.set_finished(success, message)
            
            if success and self.wizard_data.target_path:
                self.project_created.emit(self.wizard_data.target_path)
        
        if not success:
            # Show error with AI help if available
            if self.ai_service and self.ai_service.is_available():
                from ..dialogs.error import ErrorDialog

                error_dialog = ErrorDialog(
                    message, details=None, ai_service=self.ai_service, parent=self
                )
                error_dialog.exec()
            else:
                QMessageBox.critical(
                    self, "Error", f"Failed to create project:\n\n{message}"
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
            
            # Update progress dialog to show cancelled state
            if self.progress_dialog:
                self.progress_dialog.set_cancelled()

    def collect_data(self) -> Dict[str, Any]:
        """
        Collect data from all wizard pages.

        Returns:
            Dictionary with all collected information
        """
        data = {}
        
        # Get fields from wizard
        data["project_name"] = self.field("projectName")
        data["author"] = self.field("author")
        data["version"] = self.field("version")
        data["description"] = self.field("description")
        data["base_path"] = self.field("location")
        
        # Get template from wizard data 
        data["template_type"] = self.wizard_data.template_path
        
        # Get additional options from options step
        options_page = self.page(3)  # Options is the 4th page (0-indexed)
        if hasattr(options_page, 'get_options'):
            data["additional_options"] = options_page.get_options()
        else:
            data["additional_options"] = {}
            
        return data

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
                QMessageBox.StandardButton.No,
            )

            if reply != QMessageBox.StandardButton.Yes:
                return

        super().done(result)

    @pyqtSlot(int)
    def _on_page_changed(self, page_id: int) -> None:
        """Handle page change events.
        
        Args:
            page_id: ID of the new current page
        """
        # If we're on the review page, update it with collected data
        if page_id == 4:  # Review is the 5th page (0-indexed)
            review_page = self.page(4)
            if isinstance(review_page, ReviewStep):
                data = self.collect_data()
                review_page.set_wizard_data(data)

    @pyqtSlot()
    def _on_create_project(self) -> None:
        """Handle project creation request from review step."""
        logger.info("Project creation requested")
        
        # Collect all data
        data = self.collect_data()
        
        # Create project options
        project_path = Path(data["base_path"]) / data["project_name"]
        
        # Get additional options
        additional = data.get("additional_options", {})
        
        # Create ProjectOptions
        options = ProjectOptions(
            create_git_repo=additional.get("git_init", True),
            create_venv=additional.get("venv_tool") != "none",
            venv_name=".venv",
            python_version=additional.get("python_version"),
            execute_post_commands=True,
            enable_ai_assistance=self.ai_service is not None,
        )
        
        # Start generation in thread
        self._start_generation(project_path, options)
