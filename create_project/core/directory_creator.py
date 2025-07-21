# ABOUTME: Directory structure creation with rollback and validation
# ABOUTME: Creates nested project directories with cross-platform compatibility

"""
Directory structure creator for project generation.

This module provides the DirectoryCreator class which creates nested directory
structures for projects with support for rollback on errors, dry-run mode,
and cross-platform permission handling.
"""

import os
import stat
from pathlib import Path
from typing import Dict, List, Union, Optional, Any, Callable
from structlog import get_logger

from .exceptions import PathError, ProjectGenerationError
from .path_utils import PathHandler


class DirectoryCreator:
    """Creates directory structures for project generation.
    
    This class handles the creation of nested directory structures
    based on template specifications, with support for rollback,
    dry-run mode, and proper permission handling.
    
    Attributes:
        base_path: Base directory where structure will be created
        path_handler: PathHandler for secure path operations
        logger: Structured logger for operations
        created_dirs: List of directories created (for rollback)
        dry_run: Whether to run in dry-run mode
    """
    
    def __init__(
        self, 
        base_path: Union[str, Path], 
        path_handler: Optional[PathHandler] = None
    ) -> None:
        """Initialize the DirectoryCreator.
        
        Args:
            base_path: Base directory for structure creation
            path_handler: Optional PathHandler (creates new one if None)
        """
        self.path_handler = path_handler or PathHandler()
        self.base_path = self.path_handler.normalize_path(base_path)
        self.logger = get_logger(__name__)
        self.created_dirs: List[Path] = []
        self.dry_run = False
        
        self.logger.info(
            "DirectoryCreator initialized",
            base_path=str(self.base_path)
        )
    
    def create_structure(
        self, 
        structure: Dict[str, Any], 
        dry_run: bool = False,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> None:
        """Create directory structure from template data.
        
        Args:
            structure: Dictionary defining the directory structure
                      Format: {"dir_name": {"subdir": {}, "file.txt": None}}
            dry_run: If True, don't actually create directories
            progress_callback: Optional callback for progress reporting
            
        Raises:
            ProjectGenerationError: If directory creation fails
        """
        self.dry_run = dry_run
        self.created_dirs.clear()
        
        try:
            self.logger.info(
                "Starting directory structure creation",
                dry_run=dry_run,
                base_path=str(self.base_path)
            )
            
            if progress_callback:
                progress_callback("Creating directory structure...")
            
            # Ensure base directory exists
            if not dry_run:
                self.path_handler.ensure_directory(self.base_path)
            
            # Create the structure recursively
            self._create_recursive(structure, self.base_path, progress_callback)
            
            self.logger.info(
                "Directory structure creation completed",
                directories_created=len(self.created_dirs),
                dry_run=dry_run
            )
            
        except Exception as e:
            error_msg = f"Failed to create directory structure: {e}"
            self.logger.error(
                error_msg,
                error=str(e),
                created_dirs=[str(d) for d in self.created_dirs]
            )
            
            # Attempt rollback if not in dry-run mode
            if not dry_run and self.created_dirs:
                try:
                    self.rollback()
                except Exception as rollback_error:
                    self.logger.error(
                        "Rollback failed",
                        rollback_error=str(rollback_error)
                    )
            
            raise ProjectGenerationError(
                error_msg,
                details={
                    "base_path": str(self.base_path),
                    "dry_run": dry_run,
                    "created_dirs": [str(d) for d in self.created_dirs]
                },
                original_error=e
            ) from e
    
    def _create_recursive(
        self,
        structure: Dict[str, Any],
        current_path: Path,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> None:
        """Recursively create directory structure.
        
        Args:
            structure: Dictionary defining structure at current level
            current_path: Current directory path
            progress_callback: Optional progress callback
        """
        for name, content in structure.items():
            if not name:
                continue
                
            # Use path_handler for safe path joining
            item_path = self.path_handler.safe_join(current_path, name)
            
            if content is None:
                # This is a file placeholder - skip for now
                # Files will be handled by FileRenderer
                self.logger.debug("Skipping file placeholder", file=str(item_path))
                continue
            elif isinstance(content, dict):
                # This is a directory
                self._create_directory(item_path, progress_callback)
                
                # Recursively create subdirectories
                if content:  # If directory has contents
                    self._create_recursive(content, item_path, progress_callback)
            else:
                self.logger.warning(
                    "Unknown structure item type",
                    item=name,
                    type=type(content),
                    path=str(item_path)
                )
    
    def _create_directory(
        self, 
        dir_path: Path,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> None:
        """Create a single directory.
        
        Args:
            dir_path: Path of directory to create
            progress_callback: Optional progress callback
        """
        if progress_callback:
            progress_callback(f"Creating directory: {dir_path.name}")
        
        if self.dry_run:
            self.logger.info("DRY RUN: Would create directory", path=str(dir_path))
            return
        
        try:
            # Check if directory already exists
            if dir_path.exists():
                if dir_path.is_dir():
                    self.logger.debug(
                        "Directory already exists", 
                        path=str(dir_path)
                    )
                    return
                else:
                    raise ProjectGenerationError(
                        f"Path exists but is not a directory: {dir_path}"
                    )
            
            # Create the directory
            dir_path.mkdir(parents=False, exist_ok=False)
            self.created_dirs.append(dir_path)
            
            # Set appropriate permissions
            self._set_directory_permissions(dir_path)
            
            self.logger.debug("Directory created", path=str(dir_path))
            
        except FileExistsError:
            # Handle race condition where directory was created between check and mkdir
            if dir_path.is_dir():
                self.logger.debug(
                    "Directory created by another process",
                    path=str(dir_path)
                )
                return
            else:
                raise ProjectGenerationError(
                    f"Path exists but is not a directory: {dir_path}"
                )
        except OSError as e:
            error_msg = f"Failed to create directory '{dir_path}': {e}"
            self.logger.error(error_msg, path=str(dir_path), error=str(e))
            raise ProjectGenerationError(
                error_msg,
                details={"path": str(dir_path), "error_code": e.errno},
                original_error=e
            ) from e
    
    def _set_directory_permissions(self, dir_path: Path) -> None:
        """Set appropriate permissions for a directory.
        
        Args:
            dir_path: Directory path to set permissions for
        """
        try:
            # Set standard directory permissions: owner rwx, group rx, others rx
            # This is 755 in octal notation
            permissions = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | \
                         stat.S_IRGRP | stat.S_IXGRP | \
                         stat.S_IROTH | stat.S_IXOTH
            
            os.chmod(dir_path, permissions)
            
            self.logger.debug(
                "Directory permissions set",
                path=str(dir_path),
                permissions=oct(permissions)
            )
            
        except OSError as e:
            # Log warning but don't fail - permissions might not be changeable
            # on all filesystems (e.g., FAT32, some network filesystems)
            self.logger.warning(
                "Could not set directory permissions",
                path=str(dir_path),
                error=str(e)
            )
    
    def rollback(self) -> None:
        """Remove all created directories in reverse order.
        
        This method attempts to clean up all directories that were
        created during structure creation, in reverse order to handle
        nested directories properly.
        
        Raises:
            ProjectGenerationError: If rollback fails
        """
        if not self.created_dirs:
            self.logger.info("No directories to rollback")
            return
        
        self.logger.info(
            "Starting directory rollback",
            directories_to_remove=len(self.created_dirs)
        )
        
        rollback_errors = []
        
        # Remove directories in reverse order (deepest first)
        for dir_path in reversed(self.created_dirs):
            try:
                if dir_path.exists() and dir_path.is_dir():
                    # Only remove if directory is empty
                    if not any(dir_path.iterdir()):
                        dir_path.rmdir()
                        self.logger.debug("Removed directory", path=str(dir_path))
                    else:
                        self.logger.warning(
                            "Directory not empty, skipping removal",
                            path=str(dir_path)
                        )
                else:
                    self.logger.debug(
                        "Directory no longer exists",
                        path=str(dir_path)
                    )
            except OSError as e:
                error_msg = f"Failed to remove directory '{dir_path}': {e}"
                rollback_errors.append(error_msg)
                self.logger.error(error_msg, path=str(dir_path), error=str(e))
        
        # Clear the created directories list
        self.created_dirs.clear()
        
        if rollback_errors:
            combined_error = "Rollback completed with errors:\n" + "\n".join(rollback_errors)
            self.logger.error("Rollback completed with errors", errors=rollback_errors)
            raise ProjectGenerationError(
                combined_error,
                details={"rollback_errors": rollback_errors}
            )
        else:
            self.logger.info("Directory rollback completed successfully")
    
    def get_created_directories(self) -> List[Path]:
        """Get list of directories created during last operation.
        
        Returns:
            List of Path objects for created directories
        """
        return self.created_dirs.copy()
    
    def validate_structure(self, structure: Dict[str, Any]) -> None:
        """Validate a directory structure definition.
        
        Args:
            structure: Directory structure to validate
            
        Raises:
            ProjectGenerationError: If structure is invalid
        """
        self.logger.debug("Validating directory structure")
        
        try:
            self._validate_structure_recursive(structure, [])
            self.logger.debug("Directory structure validation passed")
        except Exception as e:
            error_msg = f"Directory structure validation failed: {e}"
            self.logger.error(error_msg, error=str(e))
            raise ProjectGenerationError(
                error_msg,
                original_error=e
            ) from e
    
    def _validate_structure_recursive(
        self, 
        structure: Dict[str, Any], 
        path_stack: List[str]
    ) -> None:
        """Recursively validate directory structure.
        
        Args:
            structure: Structure dictionary to validate
            path_stack: Current path components (for error reporting)
        """
        for name, content in structure.items():
            if not name:
                raise ProjectGenerationError(
                    f"Empty name in directory structure at path: {'/'.join(path_stack)}"
                )
            
            # Validate the name using PathHandler
            try:
                self.path_handler.validate_filename(name)
            except PathError as e:
                raise ProjectGenerationError(
                    f"Invalid directory/file name '{name}' at path {'/'.join(path_stack)}: {e}"
                ) from e
            
            current_path = path_stack + [name]
            
            if isinstance(content, dict):
                # Recursive validation for directories
                self._validate_structure_recursive(content, current_path)
            elif content is not None:
                # Unknown content type
                raise ProjectGenerationError(
                    f"Invalid structure content type for '{name}' at path {'/'.join(path_stack)}: "
                    f"expected dict or None, got {type(content)}"
                )
    
    def preview_structure(self, structure: Dict[str, Any]) -> List[str]:
        """Generate a preview of the directory structure.
        
        Args:
            structure: Directory structure to preview
            
        Returns:
            List of strings representing the directory tree
        """
        preview_lines = []
        
        def add_preview_recursive(
            struct: Dict[str, Any], 
            indent: int = 0,
            prefix: str = ""
        ) -> None:
            items = list(struct.items())
            for i, (name, content) in enumerate(items):
                is_last = (i == len(items) - 1)
                current_prefix = "└── " if is_last else "├── "
                line = " " * indent + current_prefix + name
                
                if isinstance(content, dict):
                    line += "/"  # Mark directories
                    preview_lines.append(line)
                    
                    # Add subdirectory contents
                    if content:
                        next_indent = indent + 4
                        add_preview_recursive(content, next_indent)
                else:
                    # File placeholder
                    preview_lines.append(line)
        
        preview_lines.append(f"{self.base_path.name}/")
        add_preview_recursive(structure, 4)
        
        return preview_lines