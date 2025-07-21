# ABOUTME: Core project generator orchestrating the entire project creation process
# ABOUTME: Integrates template system, file rendering, directory creation with atomic operations

"""
Core project generator for orchestrating the entire project creation process.

This module provides the ProjectGenerator class which coordinates all aspects
of project creation including template processing, directory structure creation,
file rendering, and error handling with atomic rollback capabilities.
"""

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from structlog import get_logger

from ..config.config_manager import ConfigManager
from ..templates.loader import TemplateLoader
from ..templates.schema.template import Template
from .command_executor import CommandExecutor
from .directory_creator import DirectoryCreator
from .exceptions import (
    GitError,
    PathError,
    ProjectGenerationError,
    TemplateError,
    VirtualEnvError,
)
from .file_renderer import FileRenderer
from .git_manager import GitConfig, GitManager
from .path_utils import PathHandler
from .venv_manager import VenvManager


@dataclass
class ProjectOptions:
    """Options for project generation.
    
    Attributes:
        create_git_repo: Whether to initialize git repository
        create_venv: Whether to create virtual environment
        venv_name: Name of virtual environment directory
        python_version: Specific Python version for virtual environment
        execute_post_commands: Whether to execute post-creation commands
        git_config: Git configuration for repository setup
        enable_ai_assistance: Whether to enable AI assistance on errors
    """
    create_git_repo: bool = True
    create_venv: bool = True
    venv_name: str = ".venv"
    python_version: Optional[str] = None
    execute_post_commands: bool = True
    git_config: Optional[GitConfig] = None
    enable_ai_assistance: bool = True


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
        git_initialized: Whether git repository was initialized
        venv_created: Whether virtual environment was created
        commands_executed: Number of post-creation commands executed
        ai_suggestions: AI-generated suggestions for fixing errors (if any)
    """
    success: bool
    target_path: Path
    template_name: str
    files_created: List[str]
    errors: List[str]
    duration: Optional[float] = None
    git_initialized: bool = False
    venv_created: bool = False
    commands_executed: int = 0
    ai_suggestions: Optional[str] = None


class ProjectGenerator:
    """Core project generator that orchestrates the entire creation process.
    
    This class coordinates all aspects of project creation including:
    - Template validation and processing
    - Directory structure creation
    - File rendering with template variables
    - Git repository initialization
    - Virtual environment creation
    - Post-creation command execution
    - Error handling with atomic rollback
    - Progress reporting through callbacks
    - AI assistance for error resolution
    
    The generator supports both normal and dry-run modes, with comprehensive
    logging and error reporting throughout the process.
    
    Attributes:
        config_manager: Configuration management
        template_loader: Template loading and validation
        path_handler: Cross-platform path operations
        directory_creator: Directory structure creation
        file_renderer: Template file rendering
        git_manager: Git repository management
        venv_manager: Virtual environment management
        command_executor: Post-creation command execution
        ai_service: AI service for error assistance (optional)
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
        file_renderer: Optional[FileRenderer] = None,
        git_manager: Optional[GitManager] = None,
        venv_manager: Optional[VenvManager] = None,
        command_executor: Optional[CommandExecutor] = None,
        ai_service: Optional["AIService"] = None  # Forward reference
    ) -> None:
        """Initialize the ProjectGenerator.
        
        Args:
            config_manager: Optional ConfigManager (creates new if None)
            template_loader: Optional TemplateLoader (creates new if None)
            path_handler: Optional PathHandler (creates new if None)
            directory_creator: Optional DirectoryCreator (creates new if None)
            file_renderer: Optional FileRenderer (creates new if None)
            git_manager: Optional GitManager (creates new if None)
            venv_manager: Optional VenvManager (creates new if None)
            command_executor: Optional CommandExecutor (creates new if None)
            ai_service: Optional AI service for error assistance
        """
        self.config_manager = config_manager or ConfigManager()
        self.template_loader = template_loader or TemplateLoader()
        self.path_handler = path_handler or PathHandler()
        # DirectoryCreator needs a base_path - we'll initialize it per project
        self.directory_creator = directory_creator
        self.file_renderer = file_renderer or FileRenderer()
        self.git_manager = git_manager or GitManager()
        self.venv_manager = venv_manager or VenvManager()
        self.command_executor = command_executor or CommandExecutor()
        self.ai_service = ai_service

        self.generation_errors: List[str] = []
        self.rollback_handlers: List[Callable[[], None]] = []
        self.logger = get_logger(__name__)

        # Initialize AI service if not provided and enabled in config
        if self.ai_service is None:
            try:
                from ..ai.ai_service import AIService, AIServiceConfig
                ai_config = AIServiceConfig(
                    enabled=self.config_manager.get_setting("ai.enabled", True),
                    ollama_url=self.config_manager.get_setting("ai.ollama_url", "http://localhost:11434"),
                    ollama_timeout=self.config_manager.get_setting("ai.ollama_timeout", 30),
                    cache_enabled=self.config_manager.get_setting("ai.cache_enabled", True),
                    cache_ttl_hours=self.config_manager.get_setting("ai.cache_ttl_hours", 24),
                    max_cache_entries=self.config_manager.get_setting("ai.max_cache_entries", 100),
                    preferred_models=self.config_manager.get_setting("ai.preferred_models"),
                    context_collection_enabled=self.config_manager.get_setting("ai.context_collection_enabled", True),
                    max_context_size_kb=self.config_manager.get_setting("ai.max_context_size_kb", 4)
                )
                if ai_config.enabled:
                    self.ai_service = AIService(
                        config_manager=self.config_manager,
                        ai_config=ai_config
                    )
                    self.logger.info("AI service initialized for error assistance")
            except ImportError:
                self.logger.warning("AI service not available - error assistance disabled")
            except Exception as e:
                self.logger.warning(
                    "Failed to initialize AI service",
                    error=str(e)
                )

        self.logger.info(
            "ProjectGenerator initialized",
            has_config_manager=self.config_manager is not None,
            has_template_loader=self.template_loader is not None,
            git_available=self.git_manager._git_available,
            venv_tools=len([t for t, p in self.venv_manager.available_tools.items() if p]),
            ai_service_available=self.ai_service is not None
        )

    def generate_project(
        self,
        template: Template,
        variables: Dict[str, Any],
        target_path: Union[str, Path],
        options: Optional[ProjectOptions] = None,
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
            options: Project generation options (git, venv, commands)
            dry_run: If True, validate but don't create files
            progress_callback: Optional progress reporting callback
            
        Returns:
            GenerationResult with success status and details
            
        Raises:
            ProjectGenerationError: For validation errors that prevent generation
        """
        import time
        start_time = time.time()

        # Set default options if not provided
        options = options or ProjectOptions()

        # Reset state for new generation
        self.generation_errors.clear()
        self.rollback_handlers.clear()

        target_path = self.path_handler.normalize_path(target_path)

        # Initialize result tracking
        git_initialized = False
        venv_created = False
        commands_executed = 0

        self.logger.info(
            "Starting project generation",
            template_name=template.name,
            target_path=str(target_path),
            dry_run=dry_run,
            create_git_repo=options.create_git_repo,
            create_venv=options.create_venv,
            execute_post_commands=options.execute_post_commands
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

                # Post-creation steps
                if options.create_git_repo:
                    report_progress("Initializing git repository...")
                    git_initialized = self._initialize_git_repository(target_path, options.git_config, report_progress)

                if options.create_venv:
                    report_progress("Creating virtual environment...")
                    venv_created = self._create_virtual_environment(target_path, options, report_progress)

                if options.execute_post_commands and hasattr(template, "hooks") and hasattr(template.hooks, "post_generation"):
                    report_progress("Executing post-creation commands...")
                    commands_executed = self._execute_post_commands(template, target_path, report_progress)

                # Create initial git commit if git was initialized
                if git_initialized:
                    report_progress("Creating initial git commit...")
                    self._create_initial_commit(target_path, options.git_config)
            else:
                self.logger.info("Dry-run mode: Skipping actual file creation and post-creation steps")

            report_progress("Project generation completed successfully")

            # Collect files created (for reporting)
            files_created = []
            if hasattr(self.file_renderer, "rendered_files"):
                files_created = [str(f) for f in self.file_renderer.rendered_files]

            duration = time.time() - start_time

            result = GenerationResult(
                success=True,
                target_path=target_path,
                template_name=template.name,
                files_created=files_created,
                errors=[],
                duration=duration,
                git_initialized=git_initialized,
                venv_created=venv_created,
                commands_executed=commands_executed
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

            # Get AI assistance if enabled
            ai_suggestions = None
            if options.enable_ai_assistance:
                partial_results = {
                    "git_initialized": git_initialized,
                    "venv_created": venv_created,
                    "commands_executed": commands_executed,
                    "files_created": len(files_created) if "files_created" in locals() else 0
                }
                ai_suggestions = self._get_ai_assistance(
                    error=e,
                    template=template,
                    variables=variables,
                    target_path=target_path,
                    options=options,
                    partial_results=partial_results
                )

            return GenerationResult(
                success=False,
                target_path=target_path,
                template_name=template.name,
                files_created=[],
                errors=[str(e)] + self.generation_errors,
                duration=duration,
                git_initialized=git_initialized,
                venv_created=venv_created,
                commands_executed=commands_executed,
                ai_suggestions=ai_suggestions
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
                "current_year": datetime.datetime.now().year,
                "current_date": datetime.datetime.now().strftime("%Y-%m-%d"),
                "generator_name": "create-project",
                "generator_version": "1.0.0"
            })

            # Validate required variables
            if hasattr(template, "variables"):
                for var_def in template.variables:
                    if var_def.required and var_def.name not in prepared_vars:
                        raise ProjectGenerationError(
                            f"Required variable '{var_def.name}' is missing"
                        )

                    # Apply defaults if not provided
                    if var_def.name not in prepared_vars and hasattr(var_def, "default"):
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
            if hasattr(template, "structure") and hasattr(template.structure, "directories"):
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
            if hasattr(template, "structure") and hasattr(template.structure, "files"):
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

    def _get_ai_assistance(
        self,
        error: Exception,
        template: Template,
        variables: Dict[str, Any],
        target_path: Path,
        options: ProjectOptions,
        partial_results: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Get AI assistance for generation errors.
        
        Args:
            error: The error that occurred
            template: Template being processed
            variables: Template variables used
            target_path: Target path for project
            options: Generation options
            partial_results: Any partial results before failure
            
        Returns:
            AI-generated help text or None if unavailable
        """
        if not options.enable_ai_assistance or self.ai_service is None:
            return None

        try:
            # Run async method in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                ai_help = loop.run_until_complete(
                    self.ai_service.generate_help_response(
                        error=error,
                        template=template,
                        project_variables=variables,
                        target_path=target_path,
                        options={
                            "create_git_repo": options.create_git_repo,
                            "create_venv": options.create_venv,
                            "venv_name": options.venv_name,
                            "python_version": options.python_version
                        },
                        attempted_operations=self.generation_errors,
                        partial_results=partial_results
                    )
                )

                self.logger.info(
                    "AI assistance generated",
                    error_type=type(error).__name__,
                    help_length=len(ai_help) if ai_help else 0
                )

                return ai_help

            finally:
                loop.close()

        except Exception as e:
            self.logger.warning(
                "Failed to get AI assistance",
                error=str(e),
                original_error=type(error).__name__
            )
            return None

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

    def _initialize_git_repository(
        self,
        target_path: Path,
        git_config: Optional[GitConfig],
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """Initialize git repository in project directory.
        
        Args:
            target_path: Project directory path
            git_config: Optional git configuration
            progress_callback: Optional progress callback
            
        Returns:
            True if git repository was initialized successfully
        """
        try:
            self.git_manager.init_repository(target_path, git_config)

            self.logger.info(
                "Git repository initialized",
                target_path=str(target_path)
            )

            return True

        except GitError as e:
            # Git errors are not fatal - log and continue
            error_msg = f"Git initialization failed: {e}"
            self.generation_errors.append(error_msg)
            self.logger.warning(
                "Git repository initialization failed",
                target_path=str(target_path),
                error=str(e)
            )

            return False

        except Exception as e:
            # Unexpected errors - log but don't fail generation
            error_msg = f"Unexpected git error: {e}"
            self.generation_errors.append(error_msg)
            self.logger.error(
                "Unexpected error during git initialization",
                target_path=str(target_path),
                error=str(e)
            )

            return False

    def _create_virtual_environment(
        self,
        target_path: Path,
        options: ProjectOptions,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """Create virtual environment in project directory.
        
        Args:
            target_path: Project directory path
            options: Project options with venv settings
            progress_callback: Optional progress callback
            
        Returns:
            True if virtual environment was created successfully
        """
        try:
            # Look for requirements file
            requirements_file = None
            for req_name in ["requirements.txt", "pyproject.toml", "Pipfile"]:
                req_path = target_path / req_name
                if req_path.exists():
                    requirements_file = req_path
                    break

            result = self.venv_manager.create_venv(
                project_path=target_path,
                venv_name=options.venv_name,
                python_version=options.python_version,
                requirements_file=requirements_file
            )

            if result["success"]:
                self.logger.info(
                    "Virtual environment created",
                    target_path=str(target_path),
                    venv_name=options.venv_name,
                    tool=result.get("tool"),
                    requirements_file=str(requirements_file) if requirements_file else None
                )

                return True
            else:
                error_msg = f"Virtual environment creation failed: {result.get('error', 'Unknown error')}"
                self.generation_errors.append(error_msg)
                self.logger.warning(
                    "Virtual environment creation failed",
                    target_path=str(target_path),
                    error=result.get("error")
                )

                return False

        except VirtualEnvError as e:
            # VEnv errors are not fatal - log and continue
            error_msg = f"Virtual environment creation failed: {e}"
            self.generation_errors.append(error_msg)
            self.logger.warning(
                "Virtual environment creation failed",
                target_path=str(target_path),
                error=str(e)
            )

            return False

        except Exception as e:
            # Unexpected errors - log but don't fail generation
            error_msg = f"Unexpected virtual environment error: {e}"
            self.generation_errors.append(error_msg)
            self.logger.error(
                "Unexpected error during virtual environment creation",
                target_path=str(target_path),
                error=str(e)
            )

            return False

    def _execute_post_commands(
        self,
        template: Template,
        target_path: Path,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> int:
        """Execute post-creation commands from template.
        
        Args:
            template: Template with post-creation commands
            target_path: Project directory path
            progress_callback: Optional progress callback
            
        Returns:
            Number of commands executed successfully
        """
        commands_executed = 0

        try:
            if not hasattr(template, "hooks") or not hasattr(template.hooks, "post_generation"):
                self.logger.debug("No post-generation commands in template")
                return 0

            post_commands = template.hooks.post_generation
            if not post_commands or not hasattr(post_commands, "commands"):
                self.logger.debug("No post-generation commands to execute")
                return 0

            commands = post_commands.commands if hasattr(post_commands, "commands") else []

            if not commands:
                self.logger.debug("Empty post-generation commands list")
                return 0

            self.logger.info(
                "Executing post-creation commands",
                target_path=str(target_path),
                command_count=len(commands)
            )

            def command_progress(message: str, current: int, total: int) -> None:
                if progress_callback:
                    progress_callback(f"Command {current + 1}/{total}: {message}")

            results = self.command_executor.execute_commands(
                commands=commands,
                cwd=target_path,
                timeout_per_command=120,  # 2 minutes per command
                progress_callback=command_progress,
                stop_on_failure=False  # Continue with remaining commands even if one fails
            )

            # Count successful commands
            commands_executed = sum(1 for result in results if result.success)

            # Log failures
            failed_commands = [result for result in results if not result.success]
            if failed_commands:
                for failed in failed_commands:
                    error_msg = f"Post-creation command failed: {failed.command} - {failed.stderr}"
                    self.generation_errors.append(error_msg)
                    self.logger.warning(
                        "Post-creation command failed",
                        command=failed.command,
                        error=failed.stderr,
                        returncode=failed.returncode
                    )

            self.logger.info(
                "Post-creation commands completed",
                target_path=str(target_path),
                commands_executed=commands_executed,
                total_commands=len(commands),
                failed_commands=len(failed_commands)
            )

            return commands_executed

        except Exception as e:
            # Command execution errors are not fatal - log and continue
            error_msg = f"Post-creation command execution failed: {e}"
            self.generation_errors.append(error_msg)
            self.logger.error(
                "Unexpected error during post-creation command execution",
                target_path=str(target_path),
                error=str(e)
            )

            return commands_executed

    def _create_initial_commit(
        self,
        target_path: Path,
        git_config: Optional[GitConfig]
    ) -> None:
        """Create initial git commit with generated files.
        
        Args:
            target_path: Project directory path
            git_config: Optional git configuration
        """
        try:
            commit_message = "Initial commit"
            if git_config and git_config.initial_commit_message:
                commit_message = git_config.initial_commit_message

            self.git_manager.create_initial_commit(
                target_path,
                message=commit_message,
                git_config=git_config
            )

            self.logger.info(
                "Initial git commit created",
                target_path=str(target_path),
                message=commit_message
            )

        except GitError as e:
            # Git commit errors are not fatal - log and continue
            error_msg = f"Initial git commit failed: {e}"
            self.generation_errors.append(error_msg)
            self.logger.warning(
                "Initial git commit failed",
                target_path=str(target_path),
                error=str(e)
            )

        except Exception as e:
            # Unexpected errors - log but don't fail generation
            error_msg = f"Unexpected git commit error: {e}"
            self.generation_errors.append(error_msg)
            self.logger.error(
                "Unexpected error during initial git commit",
                target_path=str(target_path),
                error=str(e)
            )
