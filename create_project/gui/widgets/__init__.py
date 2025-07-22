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

if TYPE_CHECKING:
    from .custom_widgets import FilePathEdit
    from .validated_line_edit import ValidatedLineEdit
    from .collapsible_section import CollapsibleSection
    from .progress_dialog import ProgressDialog
    from .license_preview import LicensePreviewWidget

__all__ = [
    "FilePathEdit",
    "ValidatedLineEdit",
    "CollapsibleSection",
    "ProgressDialog",
    "LicensePreviewWidget"
]