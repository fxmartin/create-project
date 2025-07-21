# ABOUTME: Core module initialization for project generation logic
# ABOUTME: Exposes main business logic classes and exceptions

"""
Core project generation module.

This module provides the main business logic for generating Python projects
from templates, including directory creation, file rendering, Git integration,
virtual environment setup, and post-creation commands.
"""

# Core exceptions - available immediately
from .exceptions import (
    ProjectGenerationError,
    GitError,
    VirtualEnvError,
    PathError,
    TemplateError,
    SecurityError,
    ThreadingError,
)

# Main classes - import as they are created
# from .project_generator import ProjectGenerator
from .path_utils import PathHandler
from .directory_creator import DirectoryCreator
# from .file_renderer import FileRenderer
# from .git_manager import GitManager
# from .venv_manager import VenvManager
# from .command_executor import CommandExecutor
# from .threading_model import ThreadingModel

__all__ = [
    # Exceptions
    "ProjectGenerationError",
    "GitError", 
    "VirtualEnvError",
    "PathError",
    "TemplateError",
    "SecurityError",
    "ThreadingError",
    # Classes (to be added as implemented)
    # "ProjectGenerator",
    "PathHandler",
    "DirectoryCreator", 
    # "FileRenderer",
    # "GitManager",
    # "VenvManager",
    # "CommandExecutor",
    # "ThreadingModel",
]
