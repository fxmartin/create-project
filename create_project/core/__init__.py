# ABOUTME: Core module initialization for project generation logic
# ABOUTME: Exposes main business logic classes and exceptions

"""
Core project generation module.

This module provides the main business logic for generating Python projects
from templates, including directory creation, file rendering, Git integration,
virtual environment setup, and post-creation commands.
"""

# Core exceptions - available immediately
# Public API functions
from .api import (
    cancel_async_operation,
    create_project,
    create_project_async,
    get_async_result,
    get_template_info,
    list_available_templates,
    validate_template,
)
from .command_executor import CommandExecutor, ExecutionResult
from .directory_creator import DirectoryCreator
from .exceptions import (
    GitError,
    PathError,
    ProjectGenerationError,
    SecurityError,
    TemplateError,
    ThreadingError,
    VirtualEnvError,
)
from .file_renderer import FileRenderer
from .git_manager import GitConfig, GitManager
from .path_utils import PathHandler

# Main classes - import as they are created
from .project_generator import GenerationResult, ProjectGenerator, ProjectOptions
from .threading_model import (
    BackgroundOperation,
    OperationResult,
    ProgressUpdate,
    ThreadingModel,
)
from .venv_manager import VenvManager

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
