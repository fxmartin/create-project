# ABOUTME: GUI module for PyQt6 wizard interface
# ABOUTME: Provides step-based project creation wizard

"""
GUI module for the Create Project application.

This module provides a PyQt6-based graphical user interface for creating
Python projects. It includes:

- A step-by-step wizard interface
- Project template selection
- Configuration options
- Progress tracking
- Error handling with AI assistance

The GUI is designed to be intuitive and guide users through the project
creation process with validation and helpful feedback at each step.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .dialogs import AIHelpDialog, ErrorDialog, SettingsDialog
    from .widgets import (
        CollapsibleSection,
        FilePathEdit,
        LicensePreviewWidget,
        ProgressDialog,
        ValidatedLineEdit,
    )
    from .wizard import ProjectWizard

# Import main function for easy access
from .app import main

__all__ = [
    # Main entry point
    "main",
    # Main wizard
    "ProjectWizard",
    # Dialogs
    "SettingsDialog",
    "ErrorDialog",
    "AIHelpDialog",
    # Custom widgets
    "ValidatedLineEdit",
    "CollapsibleSection",
    "ProgressDialog",
    "FilePathEdit",
    "LicensePreviewWidget",
]
