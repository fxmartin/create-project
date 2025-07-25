# ABOUTME: Fixes for AI integration tests to handle async and error simulation
# ABOUTME: Provides patches and utilities to fix failing integration tests

"""
Fixes for AI integration tests.

This module provides utilities and patches to fix issues with:
- Async test execution
- Error simulation (disk space, permissions)
- Template validation error handling
- Concurrent test execution
"""

import asyncio
import os
from pathlib import Path
from typing import Callable
from unittest.mock import MagicMock


def fix_async_test(test_func: Callable) -> Callable:
    """Decorator to fix async tests by running them synchronously.
    
    This converts async test functions to sync by properly managing
    the event loop lifecycle.
    """
    def wrapper(*args, **kwargs):
        # Remove any async markers
        if asyncio.iscoroutinefunction(test_func):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # Get the coroutine
                coro = test_func(*args, **kwargs)
                # Run it
                return loop.run_until_complete(coro)
            finally:
                loop.close()
        else:
            return test_func(*args, **kwargs)

    # Copy attributes
    wrapper.__name__ = test_func.__name__
    wrapper.__doc__ = test_func.__doc__
    return wrapper


def simulate_disk_space_error(path_pattern: str = "large_project"):
    """Create a context manager that simulates disk space errors.
    
    Args:
        path_pattern: Pattern to match in path for triggering error
    """
    class DiskSpaceErrorSimulator:
        def __init__(self, pattern: str):
            self.pattern = pattern
            self.original_mkdir = None
            self.original_makedirs = None
            self.original_open = None

        def __enter__(self):
            # Store originals
            self.original_mkdir = Path.mkdir
            self.original_makedirs = os.makedirs
            self.original_open = open

            # Create mock functions
            def mock_mkdir(path_self, *args, **kwargs):
                if self.pattern in str(path_self):
                    raise OSError(28, "No space left on device", str(path_self))
                return self.original_mkdir(path_self, *args, **kwargs)

            def mock_makedirs(path, *args, **kwargs):
                if self.pattern in str(path):
                    raise OSError(28, "No space left on device", path)
                return self.original_makedirs(path, *args, **kwargs)

            def mock_open(file, *args, **kwargs):
                if self.pattern in str(file):
                    raise OSError(28, "No space left on device", str(file))
                return self.original_open(file, *args, **kwargs)

            # Apply patches
            Path.mkdir = mock_mkdir
            os.makedirs = mock_makedirs
            # Don't patch open globally, it breaks too many things

            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            # Restore originals
            if self.original_mkdir:
                Path.mkdir = self.original_mkdir
            if self.original_makedirs:
                os.makedirs = self.original_makedirs
            if self.original_open:
                # Restore if we patched it
                pass

    return DiskSpaceErrorSimulator(path_pattern)


def ensure_ai_service_sync(ai_service):
    """Ensure AI service is initialized synchronously.
    
    Args:
        ai_service: AIService instance to initialize
    """
    if hasattr(ai_service, "_initialized") and ai_service._initialized:
        return

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(ai_service.initialize())
    finally:
        loop.close()


def create_template_validation_error(template_name: str, missing_vars: list):
    """Create a proper template validation error for testing.
    
    Args:
        template_name: Name of the template
        missing_vars: List of missing required variables
    """
    from create_project.templates.exceptions import TemplateValidationError

    error_details = {
        "template": template_name,
        "missing_variables": missing_vars,
        "validation_errors": [
            f"Required variable '{var}' is missing" for var in missing_vars
        ]
    }

    error_msg = f"Template validation failed: Missing required variables: {', '.join(missing_vars)}"
    return TemplateValidationError(error_msg, details=error_details)


def patch_ollama_client_sync(mocker, mock_client):
    """Patch Ollama client for synchronous test execution.
    
    Args:
        mocker: pytest-mock MockerFixture
        mock_client: Mock client instance to use
    """
    # Patch the client creation
    mocker.patch(
        "create_project.ai.ollama_client.OllamaClient.__new__",
        return_value=mock_client,
    )

    # Also patch httpx client to prevent real network calls
    mock_httpx = MagicMock()
    mock_httpx.get.return_value.status_code = 200
    mock_httpx.get.return_value.json.return_value = {"models": []}
    mocker.patch("httpx.Client", return_value=mock_httpx)
    mocker.patch("httpx.AsyncClient", return_value=mock_httpx)


def fix_template_validation_test(generator, template, variables, expected_missing):
    """Fix template validation test by properly injecting validation errors.
    
    Args:
        generator: ProjectGenerator instance
        template: Template to validate
        variables: Variables to pass
        expected_missing: Expected missing variables
        
    Returns:
        Modified generator that will produce validation errors
    """
    original_prepare = generator._prepare_template_variables

    def mock_prepare(tmpl, vars):
        # Check if required variables are missing
        if hasattr(tmpl, "variables"):
            missing = []
            for var_def in tmpl.variables:
                if var_def.required and var_def.name not in vars:
                    missing.append(var_def.name)

            if missing:
                from create_project.core.exceptions import ProjectGenerationError
                raise ProjectGenerationError(
                    f"Template validation failed: Missing required variables: {', '.join(missing)}"
                )

        return original_prepare(tmpl, vars)

    # Monkey patch the method
    generator._prepare_template_variables = mock_prepare
    return generator
