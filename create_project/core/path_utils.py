# ABOUTME: Cross-platform path utilities with security validation
# ABOUTME: Handles OS-agnostic path operations and prevents path traversal attacks

"""
Cross-platform path utilities for secure project generation.

This module provides the PathHandler class which offers OS-agnostic path
operations with built-in security validation to prevent path traversal
attacks and other security vulnerabilities.
"""

import os
import platform
import unicodedata
from pathlib import Path
from typing import Union, List, Optional
from structlog import get_logger

from .exceptions import PathError, SecurityError


class PathHandler:
    """Cross-platform path handler with security validation.
    
    This class provides secure path operations that work consistently
    across Windows, macOS, and Linux platforms while preventing
    security vulnerabilities like path traversal attacks.
    
    Attributes:
        logger: Structured logger for path operations
        case_sensitive: Whether the current filesystem is case-sensitive
    """
    
    # Characters that are invalid in filenames across platforms
    INVALID_CHARS = {'<', '>', ':', '"', '/', '\\', '|', '?', '*'}
    
    # Reserved names on Windows
    RESERVED_NAMES = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    
    def __init__(self) -> None:
        """Initialize the PathHandler.
        
        Sets up logging and detects filesystem case sensitivity.
        """
        self.logger = get_logger(__name__)
        self.case_sensitive = self._detect_case_sensitivity()
        
        self.logger.info(
            "PathHandler initialized",
            platform=platform.system(),
            case_sensitive=self.case_sensitive
        )
    
    def _detect_case_sensitivity(self) -> bool:
        """Detect if the current filesystem is case-sensitive.
        
        Returns:
            True if filesystem is case-sensitive, False otherwise
        """
        # Most Unix-like systems are case-sensitive, Windows is not
        return platform.system() != 'Windows'
    
    def _is_windows_absolute_path(self, path_str: str) -> bool:
        """Check if a path string is a Windows absolute path.
        
        This detects Windows-style absolute paths like "C:\\Windows"
        even when running on Unix systems.
        
        Args:
            path_str: Path string to check
            
        Returns:
            True if path looks like Windows absolute path
        """
        if len(path_str) >= 3:
            # Check for drive letter pattern: "C:\\"
            if (path_str[0].isalpha() and 
                path_str[1] == ':' and 
                path_str[2] in ('\\', '/')):
                return True
        
        # Check for UNC paths: "\\\\server\\share"
        if path_str.startswith('\\\\'):
            return True
            
        return False
    
    def normalize_path(self, path: Union[str, Path]) -> Path:
        """Normalize a path for consistent cross-platform handling.
        
        This method:
        - Converts to pathlib.Path object
        - Resolves relative components (., ..)
        - Normalizes path separators
        - Handles Unicode normalization
        
        Args:
            path: Path to normalize (string or Path object)
            
        Returns:
            Normalized Path object
            
        Raises:
            PathError: If the path cannot be normalized
            SecurityError: If path traversal is detected
        """
        try:
            # Convert to Path object
            if isinstance(path, str):
                # Check for empty path
                if not path.strip():
                    raise PathError("Path cannot be empty")
                # Normalize Unicode characters
                path = unicodedata.normalize('NFC', path)
                path_obj = Path(path)
            else:
                path_obj = Path(path)
            
            # Check for potential security issues before resolving
            self._validate_path_components(path_obj)
            
            # Resolve the path (this handles . and .. components)
            normalized = path_obj.resolve()
            
            self.logger.debug(
                "Path normalized",
                original=str(path),
                normalized=str(normalized)
            )
            
            return normalized
            
        except Exception as e:
            error_msg = f"Failed to normalize path '{path}': {e}"
            self.logger.error(error_msg, error=str(e))
            raise PathError(error_msg, original_error=e) from e
    
    def safe_join(self, base_path: Union[str, Path], *paths: Union[str, Path]) -> Path:
        """Safely join paths while preventing traversal attacks.
        
        This method ensures that the resulting path is always within
        the base_path directory, preventing "../../../etc/passwd" style attacks.
        
        Args:
            base_path: Base directory path
            *paths: Additional path components to join
            
        Returns:
            Safely joined Path object
            
        Raises:
            SecurityError: If path traversal is attempted
            PathError: If path joining fails
        """
        try:
            # Normalize the base path
            base = self.normalize_path(base_path)
            
            # Join all path components
            if not paths:
                return base
            
            # Build the joined path step by step for security validation
            current_path = base
            for path_component in paths:
                if not path_component:
                    continue
                
                # Convert to string for processing
                component_str = str(path_component)
                
                # Check for dangerous patterns before normalization
                if '..' in component_str or component_str.startswith('/'):
                    # More detailed analysis of the component
                    component_parts = Path(component_str).parts
                    if '..' in component_parts:
                        error_msg = f"Path traversal attempt detected: '{path_component}' contains parent directory references"
                        self.logger.error(
                            error_msg,
                            base_path=str(base),
                            attempted_component=str(path_component)
                        )
                        raise SecurityError(error_msg)
                
                # For relative components, join directly without resolving first
                # This prevents the component from escaping via symlinks or complex paths
                component = Path(component_str)
                
                # If component is absolute, reject it as potentially dangerous
                if component.is_absolute() or self._is_windows_absolute_path(component_str):
                    error_msg = f"Absolute path components not allowed: '{path_component}'"
                    self.logger.error(error_msg, attempted_component=str(path_component))
                    raise SecurityError(error_msg)
                
                # Join with current path (don't resolve yet)
                joined_path = current_path / component
                
                # Now resolve and check
                new_path = joined_path.resolve()
                
                # Security check: ensure the new path is still under base
                try:
                    new_path.relative_to(base)
                except ValueError:
                    error_msg = f"Path traversal attempt detected: '{path_component}' would escape base directory"
                    self.logger.error(
                        error_msg,
                        base_path=str(base),
                        attempted_component=str(path_component),
                        resolved_path=str(new_path)
                    )
                    raise SecurityError(error_msg) from None
                
                current_path = new_path
            
            self.logger.debug(
                "Paths safely joined",
                base_path=str(base),
                components=[str(p) for p in paths],
                result=str(current_path)
            )
            
            return current_path
            
        except SecurityError:
            # Re-raise security errors
            raise
        except Exception as e:
            error_msg = f"Failed to safely join paths: {e}"
            self.logger.error(error_msg, error=str(e))
            raise PathError(error_msg, original_error=e) from e
    
    def validate_filename(self, filename: str) -> None:
        """Validate a filename for cross-platform compatibility.
        
        Args:
            filename: Filename to validate
            
        Raises:
            PathError: If filename is invalid
        """
        if not filename:
            raise PathError("Filename cannot be empty")
        
        if len(filename) > 255:
            raise PathError("Filename too long (max 255 characters)")
        
        # Check for invalid characters
        invalid_chars = self.INVALID_CHARS.intersection(set(filename))
        if invalid_chars:
            raise PathError(f"Filename contains invalid characters: {sorted(invalid_chars)}")
        
        # Check for reserved names on Windows
        name_upper = filename.upper()
        if name_upper in self.RESERVED_NAMES or any(
            name_upper.startswith(reserved + '.') for reserved in self.RESERVED_NAMES
        ):
            raise PathError(f"Filename '{filename}' is reserved on Windows")
        
        # Check for names that start or end with spaces or dots (Windows issue)
        if filename.startswith((' ', '.')) or filename.endswith((' ', '.')):
            raise PathError("Filename cannot start or end with spaces or dots")
        
        self.logger.debug("Filename validated", filename=filename)
    
    def _validate_path_components(self, path: Path) -> None:
        """Validate individual path components for security.
        
        Args:
            path: Path object to validate
            
        Raises:
            SecurityError: If path contains dangerous components
        """
        for part in path.parts:
            # Check for empty parts (double slashes)
            if not part or part == '/':
                continue
                
            # Check for dangerous traversal patterns
            if part in ('..', '.'):
                # Allow single dots, but log double dots
                if part == '..':
                    self.logger.warning(
                        "Path contains parent directory reference",
                        path=str(path),
                        component=part
                    )
            
            # Validate each component as a filename
            if part not in ('/', '..', '.'):
                try:
                    self.validate_filename(part)
                except PathError as e:
                    raise SecurityError(f"Invalid path component '{part}': {e}") from e
    
    def ensure_directory(self, path: Union[str, Path]) -> Path:
        """Ensure a directory exists, creating it if necessary.
        
        Args:
            path: Directory path to ensure exists
            
        Returns:
            Path object of the created/existing directory
            
        Raises:
            PathError: If directory cannot be created
        """
        try:
            normalized_path = self.normalize_path(path)
            
            if normalized_path.exists():
                if not normalized_path.is_dir():
                    raise PathError(f"Path exists but is not a directory: {normalized_path}")
                self.logger.debug("Directory already exists", path=str(normalized_path))
                return normalized_path
            
            # Create the directory with parents
            normalized_path.mkdir(parents=True, exist_ok=True)
            
            self.logger.info("Directory created", path=str(normalized_path))
            return normalized_path
            
        except Exception as e:
            error_msg = f"Failed to ensure directory '{path}': {e}"
            self.logger.error(error_msg, error=str(e))
            raise PathError(error_msg, original_error=e) from e
    
    def get_relative_path(self, path: Union[str, Path], base: Union[str, Path]) -> Path:
        """Get a path relative to a base directory.
        
        Args:
            path: The path to make relative
            base: The base directory
            
        Returns:
            Relative path from base to path
            
        Raises:
            PathError: If relative path cannot be computed
        """
        try:
            path_obj = self.normalize_path(path)
            base_obj = self.normalize_path(base)
            
            relative = path_obj.relative_to(base_obj)
            
            self.logger.debug(
                "Computed relative path",
                path=str(path_obj),
                base=str(base_obj),
                relative=str(relative)
            )
            
            return relative
            
        except ValueError as e:
            error_msg = f"Path '{path}' is not relative to base '{base}'"
            self.logger.error(error_msg)
            raise PathError(error_msg, original_error=e) from e
        except Exception as e:
            error_msg = f"Failed to compute relative path: {e}"
            self.logger.error(error_msg, error=str(e))
            raise PathError(error_msg, original_error=e) from e