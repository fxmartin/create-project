# ABOUTME: File template rendering with variable substitution and encoding handling
# ABOUTME: Processes template files with Jinja2 integration and cross-platform support

"""
File template renderer for project generation.

This module provides the FileRenderer class which processes template files
using Jinja2, handles various file encodings, sets appropriate permissions,
and integrates with the existing template system from Milestone 2.
"""

import os
import stat
import chardet
from pathlib import Path
from typing import Dict, Any, Optional, Union, Callable, List, Tuple
from structlog import get_logger

from .exceptions import TemplateError, PathError, ProjectGenerationError
from .path_utils import PathHandler
from ..templates.engine import TemplateEngine
from ..templates.loader import TemplateLoader


class FileRenderer:
    """Renders template files for project generation.
    
    This class handles the rendering of individual template files with
    Jinja2 variable substitution, proper encoding detection and handling,
    file permission setting, and integration with the template system.
    
    Attributes:
        path_handler: PathHandler for secure path operations
        template_engine: TemplateEngine from Milestone 2
        template_loader: TemplateLoader from Milestone 2
        logger: Structured logger for operations
        rendered_files: List of files rendered (for tracking/rollback)
    """
    
    def __init__(
        self,
        path_handler: Optional[PathHandler] = None,
        template_engine: Optional[TemplateEngine] = None,
        template_loader: Optional[TemplateLoader] = None
    ) -> None:
        """Initialize the FileRenderer.
        
        Args:
            path_handler: Optional PathHandler (creates new one if None)
            template_engine: Optional TemplateEngine (creates new one if None) 
            template_loader: Optional TemplateLoader (creates new one if None)
        """
        self.path_handler = path_handler or PathHandler()
        self.template_engine = template_engine or TemplateEngine()
        self.template_loader = template_loader or TemplateLoader()
        self.logger = get_logger(__name__)
        self.rendered_files: List[Path] = []
        
        self.logger.info(
            "FileRenderer initialized",
            has_template_engine=self.template_engine is not None,
            has_template_loader=self.template_loader is not None
        )
    
    def render_file(
        self,
        template_path: Union[str, Path],
        target_path: Union[str, Path],
        variables: Dict[str, Any],
        encoding: Optional[str] = None,
        executable: bool = False,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> None:
        """Render a single template file.
        
        Args:
            template_path: Path to the template file
            target_path: Where to write the rendered file
            variables: Template variables for substitution
            encoding: Optional file encoding (auto-detected if None)
            executable: Whether to make the file executable
            progress_callback: Optional progress callback
            
        Raises:
            TemplateError: If template processing fails
            PathError: If path operations fail
        """
        try:
            template_path = self.path_handler.normalize_path(template_path)
            target_path = self.path_handler.normalize_path(target_path)
            
            if progress_callback:
                progress_callback(f"Rendering: {target_path.name}")
            
            self.logger.debug(
                "Starting file rendering",
                template_path=str(template_path),
                target_path=str(target_path),
                executable=executable
            )
            
            # Check if template file exists
            if not template_path.exists():
                raise TemplateError(f"Template file not found: {template_path}")
            
            # Detect if this is a binary file
            is_binary = self._is_binary_file(template_path)
            
            if is_binary:
                # For binary files, just copy without template processing
                self._copy_binary_file(template_path, target_path, executable)
            else:
                # For text files, process as template
                self._render_text_file(
                    template_path, target_path, variables, encoding, executable
                )
            
            self.rendered_files.append(target_path)
            
            self.logger.info(
                "File rendered successfully",
                target_path=str(target_path),
                is_binary=is_binary
            )
            
        except Exception as e:
            error_msg = f"Failed to render file '{template_path}' to '{target_path}': {e}"
            self.logger.error(
                error_msg,
                template_path=str(template_path),
                target_path=str(target_path),
                error=str(e)
            )
            raise TemplateError(
                error_msg,
                details={
                    "template_path": str(template_path),
                    "target_path": str(target_path),
                    "variables": list(variables.keys()) if variables else []
                },
                original_error=e
            ) from e
    
    def render_files_from_structure(
        self,
        base_template_path: Union[str, Path],
        base_target_path: Union[str, Path], 
        file_structure: Dict[str, Any],
        variables: Dict[str, Any],
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> None:
        """Render multiple files from a structure definition.
        
        Args:
            base_template_path: Base path for template files
            base_target_path: Base path for target files
            file_structure: Structure definition with file mappings
            variables: Template variables for substitution
            progress_callback: Optional progress callback
        """
        try:
            base_template_path = self.path_handler.normalize_path(base_template_path)
            base_target_path = self.path_handler.normalize_path(base_target_path)
            
            self.logger.info(
                "Starting batch file rendering",
                base_template_path=str(base_template_path),
                base_target_path=str(base_target_path),
                file_count=self._count_files_in_structure(file_structure)
            )
            
            self._render_structure_recursive(
                file_structure,
                base_template_path,
                base_target_path,
                variables,
                progress_callback
            )
            
            self.logger.info(
                "Batch file rendering completed",
                files_rendered=len(self.rendered_files)
            )
            
        except Exception as e:
            error_msg = f"Failed to render files from structure: {e}"
            self.logger.error(error_msg, error=str(e))
            raise TemplateError(
                error_msg,
                details={
                    "base_template_path": str(base_template_path),
                    "base_target_path": str(base_target_path)
                },
                original_error=e
            ) from e
    
    def _render_structure_recursive(
        self,
        structure: Dict[str, Any],
        template_base: Path,
        target_base: Path,
        variables: Dict[str, Any],
        progress_callback: Optional[Callable[[str], None]] = None,
        current_path: str = ""
    ) -> None:
        """Recursively render files from structure definition.
        
        Args:
            structure: Current level of structure
            template_base: Base template directory
            target_base: Base target directory
            variables: Template variables
            progress_callback: Progress callback
            current_path: Current relative path in structure
        """
        for name, content in structure.items():
            if not name:
                continue
                
            current_template_path = template_base
            current_target_path = target_base
            
            if current_path:
                current_template_path = current_template_path / current_path
                current_target_path = current_target_path / current_path
            
            if isinstance(content, dict):
                # This is a directory - recurse into it
                new_path = f"{current_path}/{name}" if current_path else name
                self._render_structure_recursive(
                    content,
                    template_base,
                    target_base,
                    variables,
                    progress_callback,
                    new_path
                )
            elif content is None or isinstance(content, str):
                # This is a file to render
                template_file = current_template_path / name
                target_file = current_target_path / name
                
                # Remove .j2 extension if present in target
                if target_file.suffix == '.j2':
                    target_file = target_file.with_suffix('')
                
                # Check if file should be executable
                executable = self._should_be_executable(name, content)
                
                self.render_file(
                    template_file,
                    target_file,
                    variables,
                    executable=executable,
                    progress_callback=progress_callback
                )
    
    def _render_text_file(
        self,
        template_path: Path,
        target_path: Path,
        variables: Dict[str, Any],
        encoding: Optional[str] = None,
        executable: bool = False
    ) -> None:
        """Render a text template file.
        
        Args:
            template_path: Template file path
            target_path: Target file path  
            variables: Template variables
            encoding: File encoding (auto-detected if None)
            executable: Whether to make file executable
        """
        # Detect encoding if not provided
        if encoding is None:
            encoding = self._detect_encoding(template_path)
        
        try:
            # Read template content
            template_content = template_path.read_text(encoding=encoding)
            
            # Use template engine to render content
            rendered_content = self.template_engine.render_template_string(
                template_content, variables
            )
            
            # Ensure target directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write rendered content
            target_path.write_text(rendered_content, encoding=encoding)
            
            # Set file permissions
            self._set_file_permissions(target_path, executable)
            
            self.logger.debug(
                "Text file rendered",
                target_path=str(target_path),
                encoding=encoding,
                size=len(rendered_content)
            )
            
        except UnicodeDecodeError as e:
            raise TemplateError(
                f"Failed to decode template file '{template_path}' with encoding '{encoding}': {e}"
            ) from e
        except Exception as e:
            raise TemplateError(
                f"Failed to render text file '{template_path}': {e}"
            ) from e
    
    def _copy_binary_file(
        self,
        template_path: Path,
        target_path: Path,
        executable: bool = False
    ) -> None:
        """Copy a binary file without template processing.
        
        Args:
            template_path: Source binary file
            target_path: Target file path
            executable: Whether to make file executable
        """
        try:
            # Ensure target directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy binary file
            with open(template_path, 'rb') as source:
                with open(target_path, 'wb') as target:
                    target.write(source.read())
            
            # Set file permissions
            self._set_file_permissions(target_path, executable)
            
            self.logger.debug(
                "Binary file copied",
                target_path=str(target_path),
                size=target_path.stat().st_size
            )
            
        except Exception as e:
            raise TemplateError(
                f"Failed to copy binary file '{template_path}': {e}"
            ) from e
    
    def _is_binary_file(self, file_path: Path) -> bool:
        """Check if a file is binary.
        
        Args:
            file_path: File to check
            
        Returns:
            True if file appears to be binary
        """
        try:
            # Read a small chunk to check
            with open(file_path, 'rb') as f:
                chunk = f.read(8192)
                
            if not chunk:
                return False  # Empty file, treat as text
                
            # Check for null bytes (common in binary files)
            if b'\x00' in chunk:
                return True
                
            # Check for common binary file signatures
            if chunk.startswith(b'\x89PNG') or chunk.startswith(b'GIF8') or chunk.startswith(b'\xff\xd8\xff'):
                return True
                
            # Use chardet to detect if it's text
            try:
                result = chardet.detect(chunk)
                if result and result.get('confidence', 0) > 0.7:
                    return False  # High confidence text detection
                else:
                    return True  # Low confidence or failed detection, assume binary
            except:
                return True  # Cannot be decoded, likely binary
                
        except Exception:
            # If we can't read the file, assume it's binary to be safe
            return True
    
    def _detect_encoding(self, file_path: Path) -> str:
        """Detect the encoding of a text file.
        
        Args:
            file_path: File to detect encoding for
            
        Returns:
            Detected encoding string
        """
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                
            result = chardet.detect(raw_data)
            encoding = result.get('encoding', 'utf-8')
            
            # Default to utf-8 if detection is uncertain
            if not encoding or result.get('confidence', 0) < 0.5:
                encoding = 'utf-8'
                
            self.logger.debug(
                "Encoding detected",
                file_path=str(file_path),
                encoding=encoding,
                confidence=result.get('confidence', 0)
            )
            
            return encoding
            
        except Exception as e:
            self.logger.warning(
                "Failed to detect encoding, using utf-8",
                file_path=str(file_path),
                error=str(e)
            )
            return 'utf-8'
    
    def _set_file_permissions(self, file_path: Path, executable: bool = False) -> None:
        """Set appropriate file permissions.
        
        Args:
            file_path: File to set permissions for
            executable: Whether to make file executable
        """
        try:
            if executable:
                # Owner: rwx, Group: r-x, Others: r-x (755)
                permissions = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | \
                             stat.S_IRGRP | stat.S_IXGRP | \
                             stat.S_IROTH | stat.S_IXOTH
            else:
                # Owner: rw-, Group: r--, Others: r-- (644)
                permissions = stat.S_IRUSR | stat.S_IWUSR | \
                             stat.S_IRGRP | stat.S_IROTH
            
            os.chmod(file_path, permissions)
            
            self.logger.debug(
                "File permissions set",
                file_path=str(file_path),
                permissions=oct(permissions),
                executable=executable
            )
            
        except OSError as e:
            # Log warning but don't fail - some filesystems don't support chmod
            self.logger.warning(
                "Could not set file permissions",
                file_path=str(file_path),
                error=str(e)
            )
    
    def _should_be_executable(self, filename: str, content: Any) -> bool:
        """Determine if a file should be executable.
        
        Args:
            filename: Name of the file
            content: File content/metadata
            
        Returns:
            True if file should be executable
        """
        # Common executable file patterns
        executable_extensions = {'.sh', '.py', '.pl', '.rb'}
        executable_names = {'Makefile', 'makefile'}
        
        # Check file extension
        file_path = Path(filename)
        if file_path.suffix.lower() in executable_extensions:
            return True
            
        # Check specific filenames
        if file_path.name in executable_names:
            return True
            
        # Check if filename suggests it's a script
        if filename.startswith('run') or filename.endswith('script'):
            return True
            
        return False
    
    def _count_files_in_structure(self, structure: Dict[str, Any]) -> int:
        """Count the number of files in a structure.
        
        Args:
            structure: Structure definition
            
        Returns:
            Number of files (not directories)
        """
        count = 0
        for name, content in structure.items():
            if isinstance(content, dict):
                count += self._count_files_in_structure(content)
            elif content is None or isinstance(content, str):
                count += 1
        return count
    
    def get_rendered_files(self) -> List[Path]:
        """Get list of files rendered during last operation.
        
        Returns:
            List of Path objects for rendered files
        """
        return self.rendered_files.copy()
    
    def clear_rendered_files(self) -> None:
        """Clear the list of rendered files."""
        self.rendered_files.clear()
        self.logger.debug("Rendered files list cleared")
    
    def rollback_rendered_files(self) -> None:
        """Remove all rendered files (for error recovery).
        
        This method attempts to remove all files that were rendered
        during the last operation, useful for cleanup on errors.
        
        Raises:
            ProjectGenerationError: If rollback fails
        """
        if not self.rendered_files:
            self.logger.info("No rendered files to rollback")
            return
        
        self.logger.info(
            "Starting file rollback",
            files_to_remove=len(self.rendered_files)
        )
        
        rollback_errors = []
        
        # Remove files in reverse order
        for file_path in reversed(self.rendered_files):
            try:
                if file_path.exists() and file_path.is_file():
                    file_path.unlink()
                    self.logger.debug("Removed file", file_path=str(file_path))
                else:
                    self.logger.debug(
                        "File no longer exists",
                        file_path=str(file_path)
                    )
            except OSError as e:
                error_msg = f"Failed to remove file '{file_path}': {e}"
                rollback_errors.append(error_msg)
                self.logger.error(error_msg, file_path=str(file_path), error=str(e))
        
        # Clear the rendered files list
        self.rendered_files.clear()
        
        if rollback_errors:
            combined_error = "File rollback completed with errors:\n" + "\n".join(rollback_errors)
            self.logger.error("File rollback completed with errors", errors=rollback_errors)
            raise ProjectGenerationError(
                combined_error,
                details={"rollback_errors": rollback_errors}
            )
        else:
            self.logger.info("File rollback completed successfully")
    
    def validate_template_file(self, template_path: Union[str, Path]) -> bool:
        """Validate that a template file can be processed.
        
        Args:
            template_path: Path to template file
            
        Returns:
            True if file can be processed
            
        Raises:
            TemplateError: If template is invalid
        """
        template_path = self.path_handler.normalize_path(template_path)
        
        if not template_path.exists():
            raise TemplateError(f"Template file not found: {template_path}")
        
        if not template_path.is_file():
            raise TemplateError(f"Template path is not a file: {template_path}")
        
        # For binary files, just check if readable
        if self._is_binary_file(template_path):
            try:
                with open(template_path, 'rb') as f:
                    f.read(1)  # Try to read one byte
                return True
            except Exception as e:
                raise TemplateError(f"Cannot read binary template file '{template_path}': {e}")
        
        # For text files, validate template syntax
        try:
            encoding = self._detect_encoding(template_path)
            content = template_path.read_text(encoding=encoding)
            
            # Try to parse template syntax with Jinja2 directly (basic validation)
            # Using a simple environment to avoid variable resolution issues
            from jinja2 import Environment
            env = Environment()
            env.parse(content)  # Just check syntax, don't render
            return True
            
        except Exception as e:
            raise TemplateError(f"Invalid template syntax in '{template_path}': {e}")
    
    def preview_rendered_content(
        self,
        template_path: Union[str, Path],
        variables: Dict[str, Any],
        max_lines: int = 50
    ) -> str:
        """Preview what a template would render to (text files only).
        
        Args:
            template_path: Path to template file
            variables: Template variables
            max_lines: Maximum lines to include in preview
            
        Returns:
            Preview of rendered content (truncated if needed)
        """
        template_path = self.path_handler.normalize_path(template_path)
        
        if self._is_binary_file(template_path):
            return f"[Binary file: {template_path.name}]"
        
        try:
            encoding = self._detect_encoding(template_path)
            content = template_path.read_text(encoding=encoding)
            rendered = self.template_engine.render_template_string(content, variables)
            
            lines = rendered.split('\n')
            if len(lines) > max_lines:
                lines = lines[:max_lines]
                lines.append(f"... ({len(rendered.split(chr(10))) - max_lines} more lines)")
            
            return '\n'.join(lines)
            
        except Exception as e:
            return f"[Error previewing template: {e}]"