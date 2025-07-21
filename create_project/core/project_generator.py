# ABOUTME: Core project generator orchestrating the entire project creation process
# ABOUTME: Integrates template system, file rendering, directory creation with atomic operations

"""
Core project generator for orchestrating the entire project creation process.

This module provides the ProjectGenerator class which coordinates all aspects
of project creation including template processing, directory structure creation,
file rendering, and error handling with atomic rollback capabilities.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass
from structlog import get_logger

from .exceptions import ProjectGenerationError, TemplateError, PathError
from .path_utils import PathHandler
from .directory_creator import DirectoryCreator
from .file_renderer import FileRenderer
from ..config.config_manager import ConfigManager
from ..templates.schema.template import Template
from ..templates.loader import TemplateLoader


@dataclass
class GenerationResult:
    """Result of project generation operation.
    
    Attributes:
        success: Whether generation was successful
        target_path: Path where project was generated
        template_name: Name of template used
        files_created: List of files that were created
        errors: List of error messages if any
        duration: Generation duration in seconds (optional)
    """
    success: bool
    target_path: Path
    template_name: str
    files_created: List[str]
    errors: List[str]
    duration: Optional[float] = None


class ProjectGenerator:
    """Core project generator that orchestrates the entire creation process.
    
    This class coordinates all aspects of project creation including:
    - Template validation and processing
    - Directory structure creation
    - File rendering with template variables
    - Error handling with atomic rollback
    - Progress reporting through callbacks
    
    The generator supports both normal and dry-run modes, with comprehensive
    logging and error reporting throughout the process.
    
    Attributes:
        config_manager: Configuration management
        template_loader: Template loading and validation
        path_handler: Cross-platform path operations
        directory_creator: Directory structure creation
        file_renderer: Template file rendering
        generation_errors: Accumulated errors during generation
        rollback_handlers: Cleanup functions for rollback
        logger: Structured logger for operations
    """
    
    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        template_loader: Optional[TemplateLoader] = None,
        path_handler: Optional[PathHandler] = None,
        directory_creator: Optional[DirectoryCreator] = None,
        file_renderer: Optional[FileRenderer] = None
    ) -> None:
        """Initialize the ProjectGenerator.
        
        Args:
            config_manager: Optional ConfigManager (creates new if None)
            template_loader: Optional TemplateLoader (creates new if None)
            path_handler: Optional PathHandler (creates new if None)
            directory_creator: Optional DirectoryCreator (creates new if None)
            file_renderer: Optional FileRenderer (creates new if None)
        """
        self.config_manager = config_manager or ConfigManager()
        self.template_loader = template_loader or TemplateLoader()
        self.path_handler = path_handler or PathHandler()
        # DirectoryCreator needs a base_path - we'll initialize it per project
        self.directory_creator = directory_creator
        self.file_renderer = file_renderer or FileRenderer()
        
        self.generation_errors: List[str] = []
        self.rollback_handlers: List[Callable[[], None]] = []
        self.logger = get_logger(__name__)
        
        self.logger.info(
            "ProjectGenerator initialized",
            has_config_manager=self.config_manager is not None,
            has_template_loader=self.template_loader is not None
        )
    
    def generate_project(
        self,
        template: Template,
        variables: Dict[str, Any],
        target_path: Union[str, Path],
        dry_run: bool = False,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> GenerationResult:
        """Generate a project from template.
        
        This is the main entry point for project generation. It orchestrates
        the entire process with proper error handling and rollback capabilities.
        
        Args:
            template: Template to use for generation
            variables: Template variables for substitution
            target_path: Where to create the project
            dry_run: If True, validate but don't create files
            progress_callback: Optional progress reporting callback
            
        Returns:
            GenerationResult with success status and details
            
        Raises:
            ProjectGenerationError: For validation errors that prevent generation
        """
        import time
        start_time = time.time()
        
        # Reset state for new generation
        self.generation_errors.clear()
        self.rollback_handlers.clear()
        
        target_path = self.path_handler.normalize_path(target_path)
        
        self.logger.info(
            "Starting project generation",
            template_name=template.name,
            target_path=str(target_path),
            dry_run=dry_run
        )
        
        try:
            # Progress reporting helper
            def report_progress(message: str) -> None:
                if progress_callback:
                    progress_callback(message)
                self.logger.debug("Generation progress", message=message)
            
            report_progress("Validating template and target path...")
            self._validate_target_path(target_path)
            
            report_progress("Preparing template variables...")
            prepared_variables = self._prepare_template_variables(template, variables)
            
            if not dry_run:
                report_progress("Creating directory structure...")
                self._create_directories(template, target_path, report_progress)
                
                report_progress("Rendering template files...")
                self._render_files(template, prepared_variables, target_path, report_progress)
            else:
                self.logger.info("Dry-run mode: Skipping actual file creation")
            
            report_progress("Project generation completed successfully")
            
            # Collect files created (for reporting)
            files_created = []
            if hasattr(self.file_renderer, 'rendered_files'):
                files_created = [str(f) for f in self.file_renderer.rendered_files]
            
            duration = time.time() - start_time
            
            result = GenerationResult(
                success=True,
                target_path=target_path,
                template_name=template.name,
                files_created=files_created,
                errors=[],
                duration=duration
            )
            
            self.logger.info(
                "Project generation completed successfully",
                template_name=template.name,
                target_path=str(target_path),
                files_created=len(files_created),
                duration=duration
            )
            
            return result
            
        except (TemplateError, PathError, ProjectGenerationError) as e:
            # Expected errors - execute rollback and return result
            self.logger.error(
                "Project generation failed",
                error=str(e),
                template_name=template.name,
                target_path=str(target_path)
            )
            
            if not dry_run:
                self._execute_rollback()
            
            duration = time.time() - start_time
            
            return GenerationResult(
                success=False,
                target_path=target_path,
                template_name=template.name,
                files_created=[],
                errors=[str(e)] + self.generation_errors,
                duration=duration
            )
            
        except Exception as e:
            # Unexpected errors - execute rollback and re-raise
            self.logger.error(
                "Unexpected error during project generation",
                error=str(e),
                template_name=template.name,
                target_path=str(target_path)
            )
            
            if not dry_run:
                self._execute_rollback()
            
            raise ProjectGenerationError(
                f"Unexpected error during project generation: {e}",
                details={
                    "template_name": template.name,
                    "target_path": str(target_path),
                    "generation_errors": self.generation_errors
                },
                original_error=e
            ) from e
    
    def _validate_target_path(self, target_path: Path) -> None:
        """Validate target path for project creation.
        
        Args:
            target_path: Path to validate
            
        Raises:
            ProjectGenerationError: If path is invalid
        """
        try:
            # Check if path exists
            if target_path.exists():
                if target_path.is_file():
                    raise ProjectGenerationError(
                        f"Target path '{target_path}' already exists and is not a directory"
                    )
                elif target_path.is_dir() and any(target_path.iterdir()):
                    raise ProjectGenerationError(
                        f"Target directory '{target_path}' already exists and is not empty"
                    )
            
            # Try to create parent directories if needed
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Test write permissions by attempting to create the directory
            if not target_path.exists():
                target_path.mkdir(exist_ok=True)
                # Remove it since we're just testing
                target_path.rmdir()
            
            self.logger.debug("Target path validation successful", target_path=str(target_path))
            
        except PermissionError as e:
            raise ProjectGenerationError(
                f"Permission denied when creating project at '{target_path}': {e}"
            ) from e
        except OSError as e:
            raise ProjectGenerationError(
                f"Cannot create project at '{target_path}': {e}"
            ) from e
        except Exception as e:
            raise ProjectGenerationError(
                f"Path validation failed for '{target_path}': {e}"
            ) from e
    
    def _prepare_template_variables(
        self, 
        template: Template, 
        variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare and validate template variables.
        
        Args:
            template: Template to prepare variables for
            variables: Input variables from user
            
        Returns:
            Prepared variables with defaults and computed values
            
        Raises:
            ProjectGenerationError: If required variables are missing
        """
        try:
            # Start with input variables
            prepared_vars = variables.copy()
            
            # Add system variables
            import datetime
            prepared_vars.update({
                'current_year': datetime.datetime.now().year,
                'current_date': datetime.datetime.now().strftime('%Y-%m-%d'),
                'generator_name': 'create-project',
                'generator_version': '1.0.0'  # TODO: Get from config
            })
            
            # Validate required variables
            if hasattr(template, 'variables'):
                for var_def in template.variables:
                    if var_def.required and var_def.name not in prepared_vars:
                        raise ProjectGenerationError(
                            f"Required variable '{var_def.name}' is missing"
                        )
                    
                    # Apply defaults if not provided
                    if var_def.name not in prepared_vars and hasattr(var_def, 'default'):
                        prepared_vars[var_def.name] = var_def.default
            
            self.logger.debug(
                "Template variables prepared",
                variables_count=len(prepared_vars),
                has_required_vars=True
            )
            
            return prepared_vars
            
        except Exception as e:
            raise ProjectGenerationError(
                f"Failed to prepare template variables: {e}"
            ) from e
    
    def _create_directories(
        self,
        template: Template,
        target_path: Path,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> None:
        """Create directory structure from template.
        
        Args:
            template: Template with directory structure
            target_path: Base path for creation
            progress_callback: Optional progress callback
        """
        try:
            if progress_callback:
                progress_callback("Creating directory structure...")
            
            # Initialize DirectoryCreator for this project if not provided
            if self.directory_creator is None:
                self.directory_creator = DirectoryCreator(base_path=target_path)
            
            # Extract directory structure from template
            structure = {}
            if hasattr(template, 'structure') and hasattr(template.structure, 'directories'):
                for directory in template.structure.directories:
                    # Convert flat directory list to nested structure
                    parts = Path(directory).parts
                    current = structure
                    for part in parts:
                        if part not in current:
                            current[part] = {}
                        current = current[part]
            
            # Create directories using DirectoryCreator
            self.directory_creator.create_structure(
                structure=structure,
                progress_callback=progress_callback
            )
            
            # Add rollback handler
            self._add_rollback_handler(
                lambda: self.directory_creator.rollback()
            )
            
            self.logger.debug(
                "Directory structure created",
                target_path=str(target_path),
                directories_created=len(self.directory_creator.created_directories)
            )
            
        except Exception as e:
            self.generation_errors.append(f"Directory creation failed: {e}")
            raise TemplateError(f"Failed to create directory structure: {e}") from e
    
    def _render_files(
        self,
        template: Template,
        variables: Dict[str, Any],
        target_path: Path,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> None:
        """Render template files.
        
        Args:
            template: Template with file definitions
            variables: Template variables
            target_path: Target directory
            progress_callback: Optional progress callback
        """
        try:
            if progress_callback:
                progress_callback("Rendering template files...")
            
            # Get template files structure
            file_structure = {}
            if hasattr(template, 'structure') and hasattr(template.structure, 'files'):
                file_structure = template.structure.files
            
            if not file_structure:
                self.logger.info("No files to render in template")
                return
            
            # Determine template base path
            # Built-in templates are in templates/builtin/template_files/{template_name}/
            from pathlib import Path
            import create_project
            package_root = Path(create_project.__file__).parent
            template_base_path = package_root / "templates" / "builtin" / "template_files"
            
            # Render files using FileRenderer
            self.file_renderer.render_files_from_structure(
                base_template_path=template_base_path,
                base_target_path=target_path,
                file_structure=file_structure,
                variables=variables,
                progress_callback=progress_callback
            )
            
            # Add rollback handler
            self._add_rollback_handler(
                lambda: self.file_renderer.rollback_rendered_files()
            )
            
            self.logger.debug(
                "Files rendered successfully",
                target_path=str(target_path),
                files_rendered=len(self.file_renderer.rendered_files)
            )
            
        except Exception as e:
            self.generation_errors.append(f"File rendering failed: {e}")
            raise TemplateError(f"Failed to render template files: {e}") from e
    
    def _add_rollback_handler(self, handler: Callable[[], None]) -> None:
        """Add a rollback handler.
        
        Args:
            handler: Function to call during rollback
        """
        self.rollback_handlers.append(handler)
        self.logger.debug("Rollback handler added", handlers_count=len(self.rollback_handlers))
    
    def _execute_rollback(self) -> None:
        """Execute all rollback handlers in reverse order."""
        if not self.rollback_handlers:
            self.logger.info("No rollback handlers to execute")
            return
        
        self.logger.info(
            "Executing rollback",
            handlers_count=len(self.rollback_handlers)
        )
        
        # Execute handlers in reverse order (LIFO)
        for handler in reversed(self.rollback_handlers):
            try:
                handler()
                self.logger.debug("Rollback handler executed successfully")
            except Exception as e:
                error_msg = f"Rollback handler failed: {e}"
                self.generation_errors.append(error_msg)
                self.logger.error(
                    "Rollback handler failed",
                    error=str(e)
                )
        
        self.rollback_handlers.clear()
        self.logger.info("Rollback execution completed")