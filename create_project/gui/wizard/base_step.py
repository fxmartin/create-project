# ABOUTME: Base class for wizard steps providing common functionality
# ABOUTME: Handles validation, navigation control, and data persistence

"""
Base wizard step module.

This module provides the base class for all wizard steps, implementing
common functionality such as:
- Validation hooks
- Navigation control
- Field registration
- Error display
- Help integration
"""

from typing import Optional, Dict, Any, List, Callable
from abc import abstractmethod

from PyQt6.QtWidgets import QWizardPage, QVBoxLayout, QLabel, QMessageBox
from PyQt6.QtCore import pyqtSignal

from create_project.utils.logger import get_logger

logger = get_logger(__name__)


class WizardStep(QWizardPage):
    """
    Base class for wizard steps.
    
    Provides common functionality for all wizard steps including
    validation, error handling, and navigation control.
    """
    
    # Signals
    validation_error = pyqtSignal(str)  # Emitted when validation fails
    help_requested = pyqtSignal(str)    # Emitted when help is requested
    
    def __init__(self, title: str, subtitle: str = "", parent=None):
        """
        Initialize the wizard step.
        
        Args:
            title: The step title
            subtitle: Optional subtitle/description
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.setTitle(title)
        if subtitle:
            self.setSubTitle(subtitle)
        
        # Main layout
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
        # Error label (hidden by default)
        self.error_label = QLabel()
        self.error_label.setObjectName("errorLabel")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        self.layout.addWidget(self.error_label)
        
        # Validation functions
        self._validators: List[Callable[[], Optional[str]]] = []
        
        # Initialize UI
        self._setup_ui()
        self._connect_signals()
        
        logger.debug(f"Initialized wizard step: {title}")
    
    @abstractmethod
    def _setup_ui(self) -> None:
        """
        Set up the step's user interface.
        
        This method should be implemented by subclasses to create
        the specific UI elements for the step.
        """
        pass
    
    def _connect_signals(self) -> None:
        """
        Connect signals and slots.
        
        Can be overridden by subclasses to add additional connections.
        """
        pass
    
    def add_validator(self, validator: Callable[[], Optional[str]]) -> None:
        """
        Add a validation function.
        
        Args:
            validator: Function that returns None if valid, error message if invalid
        """
        self._validators.append(validator)
    
    def validatePage(self) -> bool:
        """
        Validate the page when moving forward.
        
        This is called by QWizard when the user clicks Next.
        
        Returns:
            True if validation passes, False otherwise
        """
        logger.debug(f"Validating page: {self.title()}")
        
        # Clear any previous errors
        self.clear_error()
        
        # Run all validators
        for validator in self._validators:
            error = validator()
            if error:
                self.show_error(error)
                self.validation_error.emit(error)
                logger.warning(f"Validation failed: {error}")
                return False
        
        # Run custom validation
        error = self.validate()
        if error:
            self.show_error(error)
            self.validation_error.emit(error)
            logger.warning(f"Custom validation failed: {error}")
            return False
        
        logger.debug("Validation passed")
        return True
    
    def validate(self) -> Optional[str]:
        """
        Perform custom validation.
        
        Can be overridden by subclasses to add step-specific validation.
        
        Returns:
            None if valid, error message if invalid
        """
        return None
    
    def show_error(self, message: str) -> None:
        """
        Display an error message.
        
        Args:
            message: The error message to display
        """
        self.error_label.setText(f"❌ {message}")
        self.error_label.show()
    
    def clear_error(self) -> None:
        """Clear any displayed error message."""
        self.error_label.hide()
        self.error_label.clear()
    
    def get_data(self) -> Dict[str, Any]:
        """
        Get the data entered in this step.
        
        Can be overridden by subclasses to return step-specific data.
        
        Returns:
            Dictionary of field names to values
        """
        return {}
    
    def set_data(self, data: Dict[str, Any]) -> None:
        """
        Set data in this step's fields.
        
        Can be overridden by subclasses to populate fields with data.
        
        Args:
            data: Dictionary of field names to values
        """
        pass
    
    def initializePage(self) -> None:
        """
        Initialize the page when it becomes visible.
        
        Called by QWizard when the page is shown.
        Can be overridden to perform step-specific initialization.
        """
        logger.debug(f"Initializing page: {self.title()}")
        self.clear_error()
    
    def cleanupPage(self) -> None:
        """
        Clean up when leaving the page.
        
        Called by QWizard when navigating away from the page.
        Can be overridden to perform step-specific cleanup.
        """
        logger.debug(f"Cleaning up page: {self.title()}")
        self.clear_error()
    
    def isComplete(self) -> bool:
        """
        Check if the page is complete.
        
        This determines whether the Next/Finish button is enabled.
        Can be overridden for dynamic completion checking.
        
        Returns:
            True if the page is complete
        """
        return True
    
    def request_help(self) -> None:
        """
        Request context-sensitive help.
        
        Emits the help_requested signal with context information.
        """
        context = self._get_help_context()
        self.help_requested.emit(context)
        logger.info(f"Help requested for: {self.title()}")
    
    def _get_help_context(self) -> str:
        """
        Get context information for help.
        
        Can be overridden to provide step-specific context.
        
        Returns:
            Help context string
        """
        return f"Help for: {self.title()}"
    
    def show_info(self, title: str, message: str) -> None:
        """
        Show an information dialog.
        
        Args:
            title: Dialog title
            message: Information message
        """
        QMessageBox.information(self, title, message)
    
    def show_warning(self, title: str, message: str) -> None:
        """
        Show a warning dialog.
        
        Args:
            title: Dialog title
            message: Warning message
        """
        QMessageBox.warning(self, title, message)
    
    def confirm_action(self, title: str, message: str) -> bool:
        """
        Show a confirmation dialog.
        
        Args:
            title: Dialog title
            message: Confirmation message
            
        Returns:
            True if user confirms, False otherwise
        """
        result = QMessageBox.question(
            self,
            title,
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        return result == QMessageBox.StandardButton.Yes