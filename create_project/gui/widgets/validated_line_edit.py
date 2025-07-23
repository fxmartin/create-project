# ABOUTME: Custom QLineEdit widget with regex validation support
# ABOUTME: Provides real-time validation feedback with visual indicators and error messages

"""ValidatedLineEdit widget with regex validation."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QRegularExpression, pyqtSignal
from PyQt6.QtGui import QRegularExpressionValidator
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QWidget

from create_project.utils.logger import get_logger

logger = get_logger(__name__)


class ValidatedLineEdit(QWidget):
    """A QLineEdit with built-in regex validation and error display.
    
    This widget provides:
    - Real-time regex validation
    - Visual feedback (red border for invalid input)
    - Error message display
    - Validation state signals
    """

    # Signals
    validationChanged = pyqtSignal(bool)  # Emitted when validation state changes
    textChanged = pyqtSignal(str)  # Re-emit line edit's textChanged

    def __init__(
        self,
        validator_regex: str = ".*",
        error_message: str = "Invalid input",
        placeholder: str = "",
        parent: Optional[QWidget] = None
    ) -> None:
        """Initialize the validated line edit.
            placeholder: Placeholder text for the input field
            parent: Parent widget
        """
        super().__init__(parent)

        self._validator_regex = validator_regex
        self._error_message = error_message
        self._is_valid = True

        self._setup_ui(placeholder)
        self._setup_validator()

    def _setup_ui(self, placeholder: str) -> None:
        """Set up the user interface."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Line edit
        self._line_edit = QLineEdit()
        self._line_edit.setPlaceholderText(placeholder)
        layout.addWidget(self._line_edit)

        # Error label (hidden by default)
        self._error_label = QLabel()
        self._error_label.setStyleSheet("QLabel { color: red; font-size: 11px; }")
        self._error_label.hide()
        layout.addWidget(self._error_label)

        # Connect signals
        self._line_edit.textChanged.connect(self._on_text_changed)

    def _setup_validator(self) -> None:
        """Set up the regex validator."""
        try:
            regex = QRegularExpression(self._validator_regex)
            if not regex.isValid():
                logger.error(f"Invalid regex pattern: {self._validator_regex}")
                return

            validator = QRegularExpressionValidator(regex)
            self._line_edit.setValidator(validator)
            logger.debug(f"Set validator with pattern: {self._validator_regex}")
        except Exception as e:
            logger.error(f"Failed to set validator: {e}")

    def _on_text_changed(self, text: str) -> None:
        """Handle text changes and validate input.
        
        Args:
            text: Current text in the line edit
        """
        # Re-emit signal
        self.textChanged.emit(text)

        # Validate text
        is_valid = self._validate_text(text)

        # Update UI based on validation state
        if is_valid:
            self._set_valid_state()
        else:
            self._set_invalid_state()

        # Emit validation change if state changed
        if is_valid != self._is_valid:
            self._is_valid = is_valid
            self.validationChanged.emit(is_valid)

    def _validate_text(self, text: str) -> bool:
        """Validate the text against the regex pattern.
        
        Args:
            text: Text to validate
            
        Returns:
            True if text is valid, False otherwise
        """
        if not text and self.isRequired():
            return False

        try:
            regex = QRegularExpression(self._validator_regex)
            match = regex.match(text)
            return match.hasMatch() and match.capturedStart() == 0 and match.capturedEnd() == len(text)
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False

    def _set_valid_state(self) -> None:
        """Set the UI to valid state."""
        self._line_edit.setStyleSheet("")
        self._error_label.hide()

    def _set_invalid_state(self) -> None:
        """Set the UI to invalid state."""
        self._line_edit.setStyleSheet("QLineEdit { border: 1px solid red; }")
        self._error_label.setText(self._error_message)
        self._error_label.show()

    # Public methods
    def text(self) -> str:
        """Get the current text.
        
        Returns:
            Current text in the line edit
        """
        return self._line_edit.text()

    def setText(self, text: str) -> None:
        """Set the text.
        
        Args:
            text: Text to set
        """
        self._line_edit.setText(text)

    def setPlaceholderText(self, text: str) -> None:
        """Set placeholder text.
        
        Args:
            text: Placeholder text
        """
        self._line_edit.setPlaceholderText(text)

    def isValid(self) -> bool:
        """Check if current input is valid.
        
        Returns:
            True if input is valid, False otherwise
        """
        return self._is_valid

    def setRequired(self, required: bool = True) -> None:
        """Set whether the field is required.
        
        Args:
            required: Whether field is required
        """
        self._required = required
        # Revalidate current text
        self._on_text_changed(self.text())

    def isRequired(self) -> bool:
        """Check if field is required.
        
        Returns:
            True if field is required
        """
        return getattr(self, "_required", False)

    def setValidatorRegex(self, pattern: str) -> None:
        """Update the validator regex pattern.
        
        Args:
            pattern: New regex pattern
        """
        self._validator_regex = pattern
        self._setup_validator()
        # Revalidate current text
        self._on_text_changed(self.text())

    def setErrorMessage(self, message: str) -> None:
        """Update the error message.
        
        Args:
            message: New error message
        """
        self._error_message = message
        if not self._is_valid:
            self._error_label.setText(message)

    def clear(self) -> None:
        """Clear the input field."""
        self._line_edit.clear()

    def setFocus(self) -> None:
        """Set focus to the input field."""
        self._line_edit.setFocus()

    def selectAll(self) -> None:
        """Select all text in the input field."""
        self._line_edit.selectAll()

    def setReadOnly(self, read_only: bool) -> None:
        """Set read-only state.
        
        Args:
            read_only: Whether field should be read-only
        """
        self._line_edit.setReadOnly(read_only)

    def hasAcceptableInput(self) -> bool:
        """Check if input is acceptable according to validator.
        
        Returns:
            True if input is acceptable
        """
        return self._line_edit.hasAcceptableInput() and self._is_valid
