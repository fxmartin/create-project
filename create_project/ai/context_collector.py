# ABOUTME: Error context collection system for AI assistance
# ABOUTME: Collects system info, project parameters, and traceback data with PII sanitization

"""
Error context collection system for AI assistance.

This module provides the ErrorContextCollector class which gathers comprehensive
context information when project generation failures occur. The collected context
is structured for optimal AI processing to provide targeted assistance.

Context includes:
- System information (OS, Python version, disk space)
- Project generation parameters from failed attempts
- Relevant error traceback information
- Template information and validation errors
- Sanitized information (paths, usernames removed)
"""

import os
import platform
import re
import shutil
import sys
import traceback
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from structlog import get_logger

from ..core.exceptions import ProjectGenerationError
from ..templates.schema.template import Template
from .exceptions import ContextCollectionError

logger = get_logger(__name__)


@dataclass
class SystemContext:
    """System information for error context.
    
    Attributes:
        os_name: Operating system name
        os_version: Operating system version
        python_version: Python interpreter version
        platform_machine: Platform machine type
        available_disk_space_gb: Available disk space in GB
        working_directory: Current working directory (sanitized)
        environment_variables: Relevant environment variables (sanitized)
    """
    os_name: str
    os_version: str
    python_version: str
    platform_machine: str
    available_disk_space_gb: float
    working_directory: str
    environment_variables: Dict[str, str]


@dataclass
class ProjectContext:
    """Project generation parameters from failed attempts.
    
    Attributes:
        template_name: Name of template being used
        target_path: Target path for project creation (sanitized)
        project_variables: Template variables used (sanitized)
        options: Project generation options
        attempted_operations: List of operations that were attempted
        partial_results: Partial results from failed generation
    """
    template_name: str
    target_path: str
    project_variables: Dict[str, Any]
    options: Dict[str, Any]
    attempted_operations: List[str]
    partial_results: Dict[str, Any]


@dataclass
class ErrorContext:
    """Error information from failed generation attempts.
    
    Attributes:
        error_type: Type of error that occurred
        error_message: Error message (sanitized)
        traceback_lines: Relevant traceback lines (sanitized)
        error_location: File and line where error occurred
        original_error: Original underlying error if available
        validation_errors: Template validation errors if any
    """
    error_type: str
    error_message: str
    traceback_lines: List[str]
    error_location: Optional[str]
    original_error: Optional[str]
    validation_errors: List[str]


@dataclass
class TemplateContext:
    """Template information for error context.
    
    Attributes:
        template_name: Template name
        template_version: Template version
        required_variables: List of required template variables
        available_variables: List of variables that were provided
        missing_variables: List of missing required variables
        template_files: List of template files being processed
        validation_status: Template validation status
    """
    template_name: str
    template_version: str
    required_variables: List[str]
    available_variables: List[str]
    missing_variables: List[str]
    template_files: List[str]
    validation_status: str


@dataclass
class CompleteErrorContext:
    """Complete error context for AI assistance.
    
    Attributes:
        timestamp: When context was collected
        context_version: Version of context collection format
        system: System information
        project: Project generation context
        error: Error information
        template: Template context
        context_size_bytes: Total size of context data
        collection_duration_ms: Time taken to collect context
    """
    timestamp: str
    context_version: str
    system: SystemContext
    project: ProjectContext
    error: ErrorContext
    template: TemplateContext
    context_size_bytes: int
    collection_duration_ms: float


class ErrorContextCollector:
    """Collects comprehensive error context for AI assistance.
    
    This class gathers system information, project parameters, error details,
    and template context when project generation failures occur. All sensitive
    information is sanitized before collection.
    
    The collected context is structured to be under 4KB for efficiency while
    providing all necessary information for AI-powered assistance.
    """

    # Context format version for compatibility
    CONTEXT_VERSION = "1.0.0"

    # Maximum context size in bytes (4KB target)
    MAX_CONTEXT_SIZE = 4096

    # PII sanitization patterns
    PII_PATTERNS = [
        (re.compile(r"/Users/[^/]+"), "/Users/[USER]"),
        (re.compile(r"/home/[^/]+"), "/home/[USER]"),
        (re.compile(r"C:\\Users\\[^\\]+"), r"C:\\Users\\[USER]"),
        (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[EMAIL]"),
        (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[IP_ADDRESS]"),
        (re.compile(r"/tmp/[a-zA-Z0-9_-]+"), "/tmp/[TEMP]"),
    ]

    def __init__(self) -> None:
        """Initialize the error context collector."""
        self.logger = logger.bind(component="context_collector")

    def collect_context(
        self,
        error: Exception,
        template: Optional[Template] = None,
        project_variables: Optional[Dict[str, Any]] = None,
        target_path: Optional[Path] = None,
        options: Optional[Dict[str, Any]] = None,
        attempted_operations: Optional[List[str]] = None,
        partial_results: Optional[Dict[str, Any]] = None
    ) -> CompleteErrorContext:
        """Collect complete error context for AI assistance.
        
        Args:
            error: The exception that occurred
            template: Template being processed (if available)
            project_variables: Variables used for project generation
            target_path: Target path for project creation
            options: Project generation options
            attempted_operations: List of operations attempted
            partial_results: Partial results from failed generation
            
        Returns:
            CompleteErrorContext with all collected information
            
        Raises:
            ContextCollectionError: If context collection fails
        """
        start_time = datetime.now()

        try:
            self.logger.info("Starting error context collection")

            # Collect all context components
            system_context = self._collect_system_context()
            project_context = self._collect_project_context(
                template, project_variables, target_path, options,
                attempted_operations, partial_results
            )
            error_context = self._collect_error_context(error)
            template_context = self._collect_template_context(template, project_variables)

            # Create complete context
            end_time = datetime.now()
            duration_ms = (end_time - start_time).total_seconds() * 1000

            complete_context = CompleteErrorContext(
                timestamp=start_time.isoformat(),
                context_version=self.CONTEXT_VERSION,
                system=system_context,
                project=project_context,
                error=error_context,
                template=template_context,
                context_size_bytes=0,  # Will be calculated below
                collection_duration_ms=duration_ms
            )

            # Calculate context size
            context_dict = asdict(complete_context)
            context_size = len(str(context_dict))
            complete_context.context_size_bytes = context_size

            # Warn if context is large
            if context_size > self.MAX_CONTEXT_SIZE:
                self.logger.warning(
                    "Context size exceeds target",
                    size_bytes=context_size,
                    target_bytes=self.MAX_CONTEXT_SIZE
                )

            self.logger.info(
                "Error context collection completed",
                duration_ms=duration_ms,
                size_bytes=context_size
            )

            return complete_context

        except Exception as e:
            self.logger.error(
                "Failed to collect error context",
                error=str(e)
            )
            raise ContextCollectionError(
                f"Context collection failed: {str(e)}",
                details={"original_error": str(error)},
                original_error=e
            ) from e

    def _collect_system_context(self) -> SystemContext:
        """Collect system information.
        
        Returns:
            SystemContext with sanitized system information
        """
        try:
            # Get disk space for current directory
            disk_usage = shutil.disk_usage(".")
            available_gb = disk_usage[2] / (1024 ** 3)  # disk_usage returns (total, used, free)

            # Get relevant environment variables (sanitized)
            env_vars = {}
            relevant_vars = ["PATH", "PYTHONPATH", "VIRTUAL_ENV", "UV_PYTHON"]
            for var in relevant_vars:
                if var in os.environ:
                    env_vars[var] = self._sanitize_text(os.environ[var])

            return SystemContext(
                os_name=platform.system(),
                os_version=platform.version(),
                python_version=sys.version,
                platform_machine=platform.machine(),
                available_disk_space_gb=round(available_gb, 2),
                working_directory=self._sanitize_text(str(Path.cwd())),
                environment_variables=env_vars
            )

        except Exception as e:
            self.logger.warning("Failed to collect system context", error=str(e))
            # Try to get individual components that might still work
            try:
                os_name = platform.system()
            except Exception:
                os_name = "unknown"

            try:
                os_version = platform.version()
            except Exception:
                os_version = "unknown"

            try:
                machine = platform.machine()
            except Exception:
                machine = "unknown"

            try:
                working_dir = self._sanitize_text(str(Path.cwd()))
            except Exception:
                working_dir = "unknown"

            return SystemContext(
                os_name=os_name,
                os_version=os_version,
                python_version=sys.version,
                platform_machine=machine,
                available_disk_space_gb=0.0,
                working_directory=working_dir,
                environment_variables={}
            )

    def _collect_project_context(
        self,
        template: Optional[Template],
        project_variables: Optional[Dict[str, Any]],
        target_path: Optional[Path],
        options: Optional[Dict[str, Any]],
        attempted_operations: Optional[List[str]],
        partial_results: Optional[Dict[str, Any]]
    ) -> ProjectContext:
        """Collect project generation context.
        
        Args:
            template: Template being processed
            project_variables: Variables used for generation
            target_path: Target path for project
            options: Generation options
            attempted_operations: Operations that were attempted
            partial_results: Partial results from generation
            
        Returns:
            ProjectContext with sanitized project information
        """
        # Sanitize project variables
        sanitized_variables = {}
        if project_variables:
            for key, value in project_variables.items():
                sanitized_variables[key] = self._sanitize_value(value)

        # Sanitize options
        sanitized_options = {}
        if options:
            for key, value in options.items():
                sanitized_options[key] = self._sanitize_value(value)

        # Sanitize partial results
        sanitized_results = {}
        if partial_results:
            for key, value in partial_results.items():
                sanitized_results[key] = self._sanitize_value(value)

        return ProjectContext(
            template_name=template.name if template else "unknown",
            target_path=self._sanitize_text(str(target_path)) if target_path else "unknown",
            project_variables=sanitized_variables,
            options=sanitized_options,
            attempted_operations=attempted_operations or [],
            partial_results=sanitized_results
        )

    def _collect_error_context(self, error: Exception) -> ErrorContext:
        """Collect error information.
        
        Args:
            error: The exception that occurred
            
        Returns:
            ErrorContext with sanitized error information
        """
        # Get traceback information
        tb_lines = []
        if hasattr(error, "__traceback__") and error.__traceback__:
            tb_lines = traceback.format_tb(error.__traceback__)
            tb_lines = [self._sanitize_text(line.strip()) for line in tb_lines[-5:]]  # Last 5 lines

        # Extract error location
        error_location = None
        if tb_lines:
            for line in reversed(tb_lines):
                if 'File "' in line and "line " in line:
                    error_location = self._sanitize_text(line)
                    break

        # Get original error if available
        original_error = None
        if isinstance(error, ProjectGenerationError) and error.original_error:
            original_error = self._sanitize_text(str(error.original_error))

        # Get validation errors if available
        validation_errors = []
        if hasattr(error, "details") and error.details and isinstance(error.details, dict):
            if "validation_errors" in error.details:
                validation_errors = [
                    self._sanitize_text(str(ve))
                    for ve in error.details["validation_errors"]
                ]

        return ErrorContext(
            error_type=error.__class__.__name__,
            error_message=self._sanitize_text(str(error)),
            traceback_lines=tb_lines,
            error_location=error_location,
            original_error=original_error,
            validation_errors=validation_errors
        )

    def _collect_template_context(
        self,
        template: Optional[Template],
        project_variables: Optional[Dict[str, Any]]
    ) -> TemplateContext:
        """Collect template information.
        
        Args:
            template: Template being processed
            project_variables: Variables provided for template
            
        Returns:
            TemplateContext with template information
        """
        if not template:
            return TemplateContext(
                template_name="unknown",
                template_version="unknown",
                required_variables=[],
                available_variables=[],
                missing_variables=[],
                template_files=[],
                validation_status="no_template"
            )

        # Get available variables
        available_vars = list(project_variables.keys()) if project_variables else []

        # Get required variables from template
        required_vars = []
        if hasattr(template, "variables") and template.variables:
            required_vars = [var.name for var in template.variables if var.required]

        # Find missing variables
        missing_vars = [var for var in required_vars if var not in available_vars]

        # Get template files
        template_files = []
        if hasattr(template, "files") and template.files:
            template_files = [f.source for f in template.files[:10]]  # Limit to 10 files

        return TemplateContext(
            template_name=template.name,
            template_version=getattr(template, "version", "unknown"),
            required_variables=required_vars,
            available_variables=available_vars,
            missing_variables=missing_vars,
            template_files=template_files,
            validation_status="valid" if not missing_vars else "missing_variables"
        )

    def _sanitize_text(self, text: str) -> str:
        """Sanitize text by removing PII.
        
        Args:
            text: Text to sanitize
            
        Returns:
            Sanitized text with PII removed
        """
        if not isinstance(text, str):
            text = str(text)

        for pattern, replacement in self.PII_PATTERNS:
            text = pattern.sub(replacement, text)

        return text

    def _sanitize_value(self, value: Any) -> Any:
        """Sanitize any value by removing PII.
        
        Args:
            value: Value to sanitize
            
        Returns:
            Sanitized value
        """
        if isinstance(value, str):
            return self._sanitize_text(value)
        elif isinstance(value, (list, tuple)):
            return [self._sanitize_value(item) for item in value]
        elif isinstance(value, dict):
            return {key: self._sanitize_value(val) for key, val in value.items()}
        else:
            return value
