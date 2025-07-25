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

from .collapsible_section import CollapsibleSection
from .config_aware_widget import ConfigAwareWidget, ConfigChangeNotifier
from .file_path_edit import FilePathEdit, SelectionMode
from .license_preview import LicensePreviewDialog
from .progress_dialog import ProgressDialog
from .validated_line_edit import ValidatedLineEdit

__all__ = [
    "CollapsibleSection",
    "ConfigAwareWidget",
    "ConfigChangeNotifier",
    "FilePathEdit",
    "LicensePreviewDialog",
    "ProgressDialog",
    "SelectionMode",
    "ValidatedLineEdit",
]
