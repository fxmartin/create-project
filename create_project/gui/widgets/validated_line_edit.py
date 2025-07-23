# ABOUTME: QLineEdit widget with built-in regex validation and error display
# ABOUTME: Shows real-time validation status with customizable error messages

"""ValidatedLineEdit widget with regex validation support.

This widget extends QLineEdit to provide built-in validation with visual
feedback and error messages.
"""

import re
from typing import Optional, Union, Pattern

from PyQt6.QtWidgets import QLineEdit, QVBoxLayout, QLabel, QWidget
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPalette


class ValidatedLineEdit(QLineEdit):
    """A QLineEdit with built-in regex validation and error display.
    
    This widget provides real-time validation feedback with visual
    indicators and optional error message display.
    
    Signals:
        validationChanged: Emitted when validation state changes (bool)
    """
    
    validationChanged = pyqtSignal(bool)  # True = valid, False = invalid
    
    def __init__(
        self,
        validator_regex: Union[str, Pattern[str]],
        error_message: str = "Invalid input",
        parent: Optional[QWidget] = None,
        required: bool = True,
        placeholder: Optional[str] = None
    ) -> None:
        """Initialize the ValidatedLineEdit.
        
        Args:
            validator_regex: Regular expression pattern for validation
            error_message: Message to display when validation fails
            parent: Parent widget
            required: Whether the field is required (empty = invalid)
            placeholder: Placeholder text for the input field
        """
        super().__init__(parent)
        
        # Store validation parameters
        self.error_message = error_message
        self.required = required
        
        # Compile regex pattern
        if isinstance(validator_regex, str):
            self.validator_pattern = re.compile(validator_regex)
        else:
            self.validator_pattern = validator_regex
            
        # Set placeholder if provided
        if placeholder:
            self.setPlaceholderText(placeholder)
            
        # Initialize validation state
        self._is_valid = not self.required  # Empty optional fields are valid
        self._error_label: Optional[QLabel] = None
        
        # Connect text change signal for real-time validation
        self.textChanged.connect(self._validate_text)
        
        # Apply initial styling
        self._update_style()
        
    def set_error_label(self, error_label: QLabel) -> None:
        """Set an external error label to display validation messages.
        
        Args:
            error_label: QLabel widget to display error messages
        """
        self._error_label = error_label
        self._update_error_display()
        
    def is_valid(self) -> bool:
        """Check if the current text is valid.
        
        Returns:
            True if the text matches the validation pattern
        """
        return self._is_valid
        
    def _validate_text(self, text: str) -> None:
        """Validate the text against the regex pattern.
        
        Args:
            text: The current text to validate
        """
        old_state = self._is_valid
        
        # Check if empty
        if not text:
            self._is_valid = not self.required
        else:
            # Check against regex pattern
            self._is_valid = bool(self.validator_pattern.match(text))
            
        # Update UI if state changed
        if old_state != self._is_valid:
            self._update_style()
            self._update_error_display()
            self.validationChanged.emit(self._is_valid)
            
    def _update_style(self) -> None:
        """Update the widget style based on validation state."""
        if self._is_valid or not self.text():
            # Valid or empty - use default style
            self.setStyleSheet("")
        else:
            # Invalid - use error style
            self.setStyleSheet("""
                QLineEdit {
                    border: 1px solid #dc3545;
                    background-color: #fff5f5;
                }
                QLineEdit:focus {
                    border: 2px solid #dc3545;
                    outline: none;
                }
            """)
            
    def _update_error_display(self) -> None:
        """Update the error label visibility and text."""
        if self._error_label:
            if self._is_valid or not self.text():
                self._error_label.hide()
            else:
                self._error_label.setText(self.error_message)
                self._error_label.show()
                
    def set_validator_regex(self, validator_regex: Union[str, Pattern[str]]) -> None:
        """Update the validation regex pattern.
        
        Args:
            validator_regex: New regular expression pattern
        """
        if isinstance(validator_regex, str):
            self.validator_pattern = re.compile(validator_regex)
        else:
            self.validator_pattern = validator_regex
            
        # Re-validate current text
        self._validate_text(self.text())
        
    def set_error_message(self, error_message: str) -> None:
        """Update the error message.
        
        Args:
            error_message: New error message to display
        """
        self.error_message = error_message
        self._update_error_display()
        
    def set_required(self, required: bool) -> None:
        """Update whether the field is required.
        
        Args:
            required: Whether the field should be required
        """
        self.required = required
        self._validate_text(self.text())
        
    def force_validation(self) -> bool:
        """Force validation and update display.
        
        Returns:
            True if the current text is valid
        """
        self._validate_text(self.text())
        return self._is_valid