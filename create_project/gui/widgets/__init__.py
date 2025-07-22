# ABOUTME: Widgets module containing custom reusable PyQt6 components
# ABOUTME: Provides validated inputs, collapsible sections, and progress dialogs

"""
Custom widgets module for the Create Project application.

This module contains reusable custom widgets that provide enhanced functionality:
- ValidatedLineEdit for input validation
- CollapsibleSection for organized content
- ProgressDialog for operation feedback
- FilePathEdit for path selection
"""

from typing import TYPE_CHECKING

from .license_preview import LicensePreviewDialog

if TYPE_CHECKING:
    from .collapsible_section import CollapsibleSection
    from .custom_widgets import FilePathEdit
    from .progress_dialog import ProgressDialog
    from .validated_line_edit import ValidatedLineEdit

__all__ = [
    "FilePathEdit",
    "ValidatedLineEdit",
    "CollapsibleSection",
    "ProgressDialog",
    "LicensePreviewDialog",
]
