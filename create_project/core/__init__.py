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
from .project_generator import ProjectGenerator, ProjectOptions, GenerationResult
from .path_utils import PathHandler
from .directory_creator import DirectoryCreator
from .file_renderer import FileRenderer
from .git_manager import GitManager, GitConfig
from .venv_manager import VenvManager
from .command_executor import CommandExecutor, ExecutionResult
from .threading_model import ThreadingModel, BackgroundOperation, ProgressUpdate, OperationResult

# Public API functions
from .api import (
    create_project,
    create_project_async,
    get_async_result,
    cancel_async_operation,
    validate_template,
    list_available_templates,
    get_template_info,
)

__all__ = [
    # Exceptions
    "ProjectGenerationError",
    "GitError", 
    "VirtualEnvError",
    "PathError",
    "TemplateError",
    "SecurityError",
    "ThreadingError",
    # Core classes
    "ProjectGenerator",
    "ProjectOptions",
    "GenerationResult",
    "PathHandler",
    "DirectoryCreator", 
    "FileRenderer",
    "GitManager",
    "GitConfig",
    "VenvManager",
    "CommandExecutor",
    "ExecutionResult",
    "ThreadingModel",
    "BackgroundOperation",
    "ProgressUpdate",
    "OperationResult",
    # Public API functions
    "create_project",
    "create_project_async",
    "get_async_result",
    "cancel_async_operation",
    "validate_template",
    "list_available_templates",
    "get_template_info",
]
