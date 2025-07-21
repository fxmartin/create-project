# ABOUTME: Core exceptions for project generation operations
# ABOUTME: Defines hierarchical exception classes for error handling

"""
Core exceptions for the project generation system.

This module defines a hierarchy of exceptions that can be raised during
project generation operations. All exceptions inherit from ProjectGenerationError
to allow for unified error handling.
"""

from typing import Optional, Dict, Any


class ProjectGenerationError(Exception):
    """Base exception for all project generation errors.
    
    This is the root exception class for all errors that occur during
    project creation, template processing, or related operations.
    
    Args:
        message: Human-readable error description
        details: Optional dictionary with additional error context
        original_error: Optional original exception that caused this error
    """
    
    def __init__(
        self, 
        message: str, 
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ) -> None:
        self.message = message
        self.details = details or {}
        self.original_error = original_error
        super().__init__(message)
    
    def __str__(self) -> str:
        return self.message
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('{self.message}')"


class GitError(ProjectGenerationError):
    """Git operation errors.
    
    Raised when git operations fail during project generation,
    such as repository initialization or initial commit creation.
    """
    pass


class VirtualEnvError(ProjectGenerationError):
    """Virtual environment creation errors.
    
    Raised when virtual environment creation fails using any of the
    supported tools (venv, virtualenv, uv).
    """
    pass


class PathError(ProjectGenerationError):
    """Path-related errors.
    
    Raised when path operations fail, such as invalid paths,
    permission issues, or path traversal attempts.
    """
    pass


class TemplateError(ProjectGenerationError):
    """Template processing errors.
    
    Raised when template rendering or processing fails,
    including variable substitution and file generation.
    """
    pass


class SecurityError(ProjectGenerationError):
    """Security-related errors.
    
    Raised when security validations fail, such as command
    injection attempts or unauthorized file access.
    """
    pass


class ThreadingError(ProjectGenerationError):
    """Threading and concurrency errors.
    
    Raised when background operations fail or threading
    issues occur during project generation.
    """
    pass


class AIAssistanceError(ProjectGenerationError):
    """AI assistance errors.
    
    Raised when AI assistance features fail, but does not prevent
    project generation from continuing without AI help.
    """
    pass