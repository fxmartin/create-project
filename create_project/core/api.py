# ABOUTME: Public API interface for the core project generation module
# ABOUTME: Provides simplified functions for external consumers of the core functionality

"""
Public API interface for core project generation.

This module provides simplified API functions for external modules to use
the core project generation functionality without needing to manage
individual component instances directly.
"""

from pathlib import Path
from typing import Any, Callable, Dict, Optional, Union

from ..config.config_manager import ConfigManager
from ..templates.engine import TemplateEngine
from ..templates.loader import TemplateLoader
from .project_generator import (
    GenerationResult,
    ProjectGenerator,
    ProjectOptions,
)
from .threading_model import OperationResult, ThreadingModel


def create_project(
    template_name: str,
    project_name: str,
    target_directory: Union[str, Path],
    variables: Optional[Dict[str, Any]] = None,
    options: Optional[ProjectOptions] = None,
    dry_run: bool = False,
    progress_callback: Optional[Callable[[str], None]] = None,
    config_manager: Optional[ConfigManager] = None,
) -> GenerationResult:
    """Create a project from a template (synchronous).

    This is the main API entry point for project creation. It handles
    template loading, variable preparation, and project generation
    in a single call.

    Args:
        template_name: Name of template to use
        project_name: Name of the project to create
        target_directory: Directory where project should be created
        variables: Optional template variables (project_name is added automatically)
        options: Optional project generation options
        dry_run: If True, validate but don't create files
        progress_callback: Optional progress callback function
        config_manager: Optional config manager instance

    Returns:
        GenerationResult with success status and details

    Raises:
        ProjectGenerationError: If template loading or generation fails
    """
    # Initialize components
    config_manager = config_manager or ConfigManager()
    template_loader = TemplateLoader(config_manager=config_manager)
    template_engine = TemplateEngine(config_manager=config_manager)
    generator = ProjectGenerator(config_manager=config_manager)

    # Find template file
    template_path = template_loader.find_template_by_name(template_name)
    if not template_path:
        return GenerationResult(
            success=False,
            target_path=Path(target_directory) / project_name,
            template_name=template_name,
            files_created=[],
            errors=[f"Template '{template_name}' not found"],
        )

    # Load template
    template = template_engine.load_template(template_path)

    # Prepare variables
    final_variables = variables or {}
    final_variables["project_name"] = project_name

    # Set default options
    if options is None:
        options = ProjectOptions()

    # Ensure target directory includes project name
    target_path = Path(target_directory) / project_name

    # Generate project
    return generator.generate_project(
        template=template,
        variables=final_variables,
        target_path=target_path,
        options=options,
        dry_run=dry_run,
        progress_callback=progress_callback,
    )


def create_project_async(
    template_name: str,
    project_name: str,
    target_directory: Union[str, Path],
    variables: Optional[Dict[str, Any]] = None,
    options: Optional[ProjectOptions] = None,
    dry_run: bool = False,
    progress_callback: Optional[Callable[[str], None]] = None,
    config_manager: Optional[ConfigManager] = None,
    threading_model: Optional[ThreadingModel] = None,
) -> str:
    """Create a project from a template (asynchronous).

    This function starts project generation in the background and returns
    an operation ID that can be used to track progress and get results.

    Args:
        template_name: Name of template to use
        project_name: Name of the project to create
        target_directory: Directory where project should be created
        variables: Optional template variables (project_name is added automatically)
        options: Optional project generation options
        dry_run: If True, validate but don't create files
        progress_callback: Optional progress callback function
        config_manager: Optional config manager instance
        threading_model: Optional threading model instance

    Returns:
        Operation ID for tracking the background generation

    Raises:
        ProjectGenerationError: If template loading fails
        ThreadingError: If background operation cannot be started
    """
    # Initialize components
    config_manager = config_manager or ConfigManager()
    template_loader = TemplateLoader(config_manager=config_manager)
    template_engine = TemplateEngine(config_manager=config_manager)
    generator = ProjectGenerator(config_manager=config_manager)
    threading_model = threading_model or ThreadingModel()

    # Find template file
    template_path = template_loader.find_template_by_name(template_name)
    if not template_path:
        raise ValueError(f"Template '{template_name}' not found")

    # Load template
    template = template_engine.load_template(template_path)

    # Prepare variables
    final_variables = variables or {}
    final_variables["project_name"] = project_name

    # Set default options
    if options is None:
        options = ProjectOptions()

    # Ensure target directory includes project name
    target_path = Path(target_directory) / project_name

    # Generate operation ID
    operation_id = f"project_{project_name}_{hash(str(target_path)) & 0x7FFFFFFF:08x}"

    # Start background generation
    return threading_model.start_project_generation(
        operation_id=operation_id,
        project_generator=generator,
        template=template,
        variables=final_variables,
        target_path=target_path,
        dry_run=dry_run,
        progress_callback=progress_callback,
    )


def get_async_result(
    operation_id: str,
    threading_model: ThreadingModel,
    timeout: Optional[float] = None,
    remove_completed: bool = True,
) -> OperationResult:
    """Get result of asynchronous project generation.

    Args:
        operation_id: Operation ID returned by create_project_async
        threading_model: ThreadingModel instance used for async creation
        timeout: Optional timeout in seconds
        remove_completed: Whether to remove completed operation from memory

    Returns:
        OperationResult with final status and result

    Raises:
        ThreadingError: If operation doesn't exist or result retrieval fails
    """
    return threading_model.get_operation_result(
        operation_id=operation_id, timeout=timeout, remove_completed=remove_completed
    )


def cancel_async_operation(operation_id: str, threading_model: ThreadingModel) -> bool:
    """Cancel an asynchronous project generation operation.

    Args:
        operation_id: Operation ID to cancel
        threading_model: ThreadingModel instance managing the operation

    Returns:
        True if operation was successfully cancelled
    """
    return threading_model.cancel_operation(operation_id)


def validate_template(
    template_name: str, config_manager: Optional[ConfigManager] = None
) -> bool:
    """Validate that a template exists and is valid.

    Args:
        template_name: Name of template to validate
        config_manager: Optional config manager instance

    Returns:
        True if template is valid

    Raises:
        ProjectGenerationError: If template is invalid
    """
    try:
        template_loader = TemplateLoader()
        template = template_loader.load_template(template_name)
        return True
    except Exception:
        return False


def list_available_templates(
    config_manager: Optional[ConfigManager] = None,
) -> list[str]:
    """List all available templates.

    Args:
        config_manager: Optional config manager instance

    Returns:
        List of available template names
    """
    template_loader = TemplateLoader()
    return template_loader.list_available_templates()


def get_template_info(
    template_name: str, config_manager: Optional[ConfigManager] = None
) -> Dict[str, Any]:
    """Get information about a specific template.

    Args:
        template_name: Name of template to get info for
        config_manager: Optional config manager instance

    Returns:
        Dictionary with template information

    Raises:
        ProjectGenerationError: If template doesn't exist
    """
    template_loader = TemplateLoader()
    template = template_loader.load_template(template_name)

    return {
        "name": template.name,
        "display_name": template.display_name,
        "description": template.description,
        "version": template.version,
        "author": template.author,
        "tags": template.tags,
        "variables": [
            {
                "name": var.name,
                "display_name": var.display_name,
                "description": var.description,
                "type": var.type,
                "required": var.required,
                "default": getattr(var, "default", None),
            }
            for var in template.variables
        ]
        if hasattr(template, "variables")
        else [],
        "compatibility": {
            "min_python_version": template.compatibility.min_python_version,
            "max_python_version": template.compatibility.max_python_version,
            "supported_os": template.compatibility.supported_os,
            "dependencies": template.compatibility.dependencies,
        }
        if hasattr(template, "compatibility")
        else {},
    }
