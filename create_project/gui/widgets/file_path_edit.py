# ABOUTME: File path input widget with browse button and validation
# ABOUTME: Supports file/directory selection with customizable filters and validation

"""FilePathEdit widget for file/directory selection.

This widget combines a line edit with a browse button for selecting
files or directories, with built-in validation support.
"""

from enum import Enum
from pathlib import Path
from typing import Optional, Callable, List

from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QWidget,
)
from PyQt6.QtCore import Qt, pyqtSignal


class SelectionMode(Enum):
    """File selection mode."""
    FILE = "file"
    DIRECTORY = "directory"
    SAVE_FILE = "save_file"


class FilePathEdit(QWidget):
    """A file/directory path input with browse button.
    
    This widget provides a line edit for entering paths manually
    and a browse button for selecting via file dialog.
    
    Signals:
        pathChanged: Emitted when the path changes (str)
        validationChanged: Emitted when validation state changes (bool)
    """
    
    pathChanged = pyqtSignal(str)
    validationChanged = pyqtSignal(bool)
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        mode: SelectionMode = SelectionMode.DIRECTORY,
        caption: str = "Select",
        filter: str = "All Files (*)",
        start_dir: Optional[str] = None,
        placeholder: str = "Click browse or enter path...",
        validator: Optional[Callable[[str], bool]] = None
    ) -> None:
        """Initialize the FilePathEdit.
        
        Args:
            parent: Parent widget
            mode: Selection mode (file, directory, or save file)
            caption: Dialog caption
            filter: File filter for file selection modes
            start_dir: Starting directory for dialog
            placeholder: Placeholder text for line edit
            validator: Optional validation function
        """
        super().__init__(parent)
        
        self.mode = mode
        self.caption = caption
        self.filter = filter
        self.start_dir = start_dir or str(Path.home())
        self.validator = validator
        self._is_valid = True
        
        # Create layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Path input
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText(placeholder)
        self._path_edit.textChanged.connect(self._on_path_changed)
        layout.addWidget(self._path_edit, 1)
        
        # Browse button
        self._browse_button = QPushButton("Browse...")
        self._browse_button.clicked.connect(self._browse)
        layout.addWidget(self._browse_button)
        
    def get_path(self) -> str:
        """Get the current path.
        
        Returns:
            The current path as a string
        """
        return self._path_edit.text()
        
    def set_path(self, path: str) -> None:
        """Set the path.
        
        Args:
            path: Path to set
        """
        self._path_edit.setText(path)
        
    def is_valid(self) -> bool:
        """Check if the current path is valid.
        
        Returns:
            True if path is valid or no validator is set
        """
        return self._is_valid
        
    def set_enabled(self, enabled: bool) -> None:
        """Enable/disable the widget.
        
        Args:
            enabled: Whether to enable the widget
        """
        self._path_edit.setEnabled(enabled)
        self._browse_button.setEnabled(enabled)
        
    def set_read_only(self, read_only: bool) -> None:
        """Set read-only mode.
        
        Args:
            read_only: Whether to make the path edit read-only
        """
        self._path_edit.setReadOnly(read_only)
        self._browse_button.setEnabled(not read_only)
        
    def set_filter(self, filter: str) -> None:
        """Update the file filter.
        
        Args:
            filter: New file filter string
        """
        self.filter = filter
        
    def set_start_dir(self, start_dir: str) -> None:
        """Update the starting directory.
        
        Args:
            start_dir: New starting directory path
        """
        self.start_dir = start_dir
        
    def set_validator(self, validator: Optional[Callable[[str], bool]]) -> None:
        """Set a custom validation function.
        
        Args:
            validator: Function that takes a path and returns True if valid
        """
        self.validator = validator
        self._validate_current_path()
        
    def _browse(self) -> None:
        """Open file dialog for path selection."""
        current_path = self._path_edit.text()
        start_dir = current_path if current_path and Path(current_path).exists() else self.start_dir
        
        if self.mode == SelectionMode.DIRECTORY:
            path = QFileDialog.getExistingDirectory(
                self,
                self.caption,
                start_dir,
                QFileDialog.Option.ShowDirsOnly
            )
        elif self.mode == SelectionMode.FILE:
            path, _ = QFileDialog.getOpenFileName(
                self,
                self.caption,
                start_dir,
                self.filter
            )
        else:  # SAVE_FILE
            path, _ = QFileDialog.getSaveFileName(
                self,
                self.caption,
                start_dir,
                self.filter
            )
            
        if path:
            self.set_path(path)
            
    def _on_path_changed(self, text: str) -> None:
        """Handle path text changes.
        
        Args:
            text: New path text
        """
        self._validate_current_path()
        self.pathChanged.emit(text)
        
    def _validate_current_path(self) -> None:
        """Validate the current path."""
        old_state = self._is_valid
        path = self._path_edit.text()
        
        if not path:
            # Empty path - consider valid if no validator
            self._is_valid = self.validator is None
        elif self.validator:
            # Use custom validator
            self._is_valid = self.validator(path)
        else:
            # Default validation based on mode
            path_obj = Path(path)
            if self.mode == SelectionMode.DIRECTORY:
                self._is_valid = path_obj.is_dir()
            elif self.mode == SelectionMode.FILE:
                self._is_valid = path_obj.is_file()
            else:  # SAVE_FILE
                # For save mode, parent directory must exist
                self._is_valid = path_obj.parent.is_dir()
                
        # Update styling
        self._update_style()
        
        # Emit signal if state changed
        if old_state != self._is_valid:
            self.validationChanged.emit(self._is_valid)
            
    def _update_style(self) -> None:
        """Update the widget style based on validation state."""
        if self._is_valid or not self._path_edit.text():
            # Valid or empty - use default style
            self._path_edit.setStyleSheet("")
        else:
            # Invalid - use error style
            self._path_edit.setStyleSheet("""
                QLineEdit {
                    border: 1px solid #dc3545;
                    background-color: #fff5f5;
                }
                QLineEdit:focus {
                    border: 2px solid #dc3545;
                    outline: none;
                }
            """)