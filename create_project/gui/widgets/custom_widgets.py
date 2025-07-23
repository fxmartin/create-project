# ABOUTME: Custom reusable widgets for the GUI interface
# ABOUTME: Provides validated inputs, collapsible sections, and file path selectors

"""Custom widgets for the Create Project GUI application.

This module provides reusable custom widgets that extend PyQt6 functionality
with additional features like validation, collapsibility, and file browsing.
"""

from .collapsible_section import CollapsibleSection
from .file_path_edit import FilePathEdit
from .validated_line_edit import ValidatedLineEdit

__all__ = [
    "ValidatedLineEdit",
    "CollapsibleSection",
    "FilePathEdit",
]
