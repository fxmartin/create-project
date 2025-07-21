# ABOUTME: File and directory structure schema definition using Pydantic models
# ABOUTME: Provides models for defining template file and directory structures with conditional logic

import os
import re
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class ItemType(str, Enum):
    """Types of items in template structure."""

    FILE = "file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"


class FileEncoding(str, Enum):
    """Supported file encodings."""

    UTF8 = "utf-8"
    ASCII = "ascii"
    LATIN1 = "latin-1"
    BINARY = "binary"


class FilePermissions(str, Enum):
    """Common file permission patterns."""

    READ_ONLY = "444"
    READ_WRITE = "644"
    EXECUTABLE = "755"
    SCRIPT = "755"
    PRIVATE = "600"
    PUBLIC = "644"


class ConditionalExpression(BaseModel):
    """Expression for conditional file/directory creation."""

    expression: str = Field(..., description="Jinja2 conditional expression")

    variables: Optional[List[str]] = Field(
        None, description="Variables used in the expression (for dependency tracking)"
    )

    @field_validator("expression")
    @classmethod
    def validate_expression(cls, v):
        """Basic validation of Jinja2 expression syntax."""
        if not v or not v.strip():
            raise ValueError("Expression cannot be empty")

        # Basic checks for Jinja2 syntax
        if not (v.startswith("{{") and v.endswith("}}")) and not (
            "{{" in v and "}}" in v
        ):
            # Allow simple variable references without {{ }}
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", v):
                raise ValueError(
                    "Expression must be valid Jinja2 syntax or simple variable name"
                )

        return v.strip()


class FileItem(BaseModel):
    """File item in template structure."""

    name: str = Field(..., description="File name (can include template variables)")

    type: ItemType = Field(default=ItemType.FILE, description="Item type")

    content: Optional[str] = Field(
        None, description="Inline file content (Jinja2 template)"
    )

    template_file: Optional[str] = Field(
        None, description="Path to template file relative to template directory"
    )

    source_file: Optional[str] = Field(
        None, description="Path to source file to copy (for binary files)"
    )

    encoding: FileEncoding = Field(
        default=FileEncoding.UTF8, description="File encoding"
    )

    permissions: FilePermissions = Field(
        default=FilePermissions.READ_WRITE, description="File permissions"
    )

    executable: bool = Field(
        default=False, description="Whether file should be executable"
    )

    condition: Optional[ConditionalExpression] = Field(
        None, description="Condition for creating this file"
    )

    target_path: Optional[str] = Field(
        None, description="Custom target path (overrides default path calculation)"
    )

    is_binary: bool = Field(
        default=False, description="Whether file is binary (no template processing)"
    )

    preserve_line_endings: bool = Field(
        default=False, description="Preserve original line endings"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        """Validate file name."""
        if not v or not v.strip():
            raise ValueError("File name cannot be empty")

        # Check for invalid characters (varies by OS, but these are common)
        invalid_chars = r'[<>:"|?*]'
        if re.search(invalid_chars, v):
            raise ValueError(f"File name contains invalid characters: {v}")

        # Check for reserved names on Windows
        reserved_names = {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            "COM1",
            "COM2",
            "COM3",
            "COM4",
            "COM5",
            "COM6",
            "COM7",
            "COM8",
            "COM9",
            "LPT1",
            "LPT2",
            "LPT3",
            "LPT4",
            "LPT5",
            "LPT6",
            "LPT7",
            "LPT8",
            "LPT9",
        }

        base_name = v.split(".")[0].upper()
        if base_name in reserved_names:
            raise ValueError(f"File name '{v}' is reserved on Windows")

        return v.strip()

    @field_validator("template_file", "source_file")
    @classmethod
    def validate_file_paths(cls, v):
        """Validate template and source file paths."""
        if v is None:
            return v

        # Normalize path separators
        v = v.replace("\\", "/")

        # Check for absolute paths (not allowed)
        if os.path.isabs(v):
            raise ValueError("Template and source file paths must be relative")

        # Check for directory traversal attempts
        if ".." in v:
            raise ValueError("Template and source file paths cannot contain '..'")

        return v

    @field_validator("permissions")
    @classmethod
    def validate_permissions(cls, v):
        """Validate file permissions."""
        if isinstance(v, str):
            # Check if it's a valid octal permission string
            if not re.match(r"^[0-7]{3}$", v):
                raise ValueError(
                    "Permissions must be a 3-digit octal string (e.g., '644')"
                )
        return v

    def validate_content_source(self):
        """Validate that exactly one content source is specified."""
        sources = [self.content, self.template_file, self.source_file]
        non_none_sources = [s for s in sources if s is not None]

        if len(non_none_sources) == 0:
            raise ValueError("File must have content, template_file, or source_file")
        elif len(non_none_sources) > 1:
            raise ValueError(
                "File can only have one of: content, template_file, or source_file"
            )

    def get_final_permissions(self) -> str:
        """Get final file permissions considering executable flag."""
        if self.executable:
            # Make file executable
            if self.permissions == FilePermissions.READ_WRITE:
                return FilePermissions.EXECUTABLE.value
            elif self.permissions == FilePermissions.READ_ONLY:
                return "555"  # Read and execute only

        return self.permissions.value

    def is_templated(self) -> bool:
        """Check if file content should be processed as template."""
        return not self.is_binary and (
            self.content is not None or self.template_file is not None
        )


class DirectoryItem(BaseModel):
    """Directory item in template structure."""

    name: str = Field(
        ..., description="Directory name (can include template variables)"
    )

    type: ItemType = Field(default=ItemType.DIRECTORY, description="Item type")

    files: List[FileItem] = Field(
        default_factory=list, description="Files in this directory"
    )

    directories: List["DirectoryItem"] = Field(
        default_factory=list, description="Subdirectories in this directory"
    )

    permissions: FilePermissions = Field(
        default=FilePermissions.EXECUTABLE, description="Directory permissions"
    )

    condition: Optional[ConditionalExpression] = Field(
        None, description="Condition for creating this directory"
    )

    target_path: Optional[str] = Field(
        None, description="Custom target path (overrides default path calculation)"
    )

    create_if_empty: bool = Field(
        default=True, description="Create directory even if it contains no files"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        """Validate directory name."""
        if not v or not v.strip():
            raise ValueError("Directory name cannot be empty")

        # Check for invalid characters
        invalid_chars = r'[<>:"|?*]'
        if re.search(invalid_chars, v):
            raise ValueError(f"Directory name contains invalid characters: {v}")

        # Check for reserved names
        reserved_names = {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            "COM1",
            "COM2",
            "COM3",
            "COM4",
            "COM5",
            "COM6",
            "COM7",
            "COM8",
            "COM9",
            "LPT1",
            "LPT2",
            "LPT3",
            "LPT4",
            "LPT5",
            "LPT6",
            "LPT7",
            "LPT8",
            "LPT9",
        }

        if v.upper() in reserved_names:
            raise ValueError(f"Directory name '{v}' is reserved on Windows")

        return v.strip()

    def get_all_files(self) -> List[FileItem]:
        """Get all files in this directory and subdirectories."""
        all_files = list(self.files)

        for subdir in self.directories:
            all_files.extend(subdir.get_all_files())

        return all_files

    def get_all_directories(self) -> List["DirectoryItem"]:
        """Get all directories in this directory and subdirectories."""
        all_dirs = list(self.directories)

        for subdir in self.directories:
            all_dirs.extend(subdir.get_all_directories())

        return all_dirs

    def find_file_by_name(self, name: str) -> Optional[FileItem]:
        """Find a file by name in this directory tree."""
        for file in self.files:
            if file.name == name:
                return file

        for subdir in self.directories:
            result = subdir.find_file_by_name(name)
            if result:
                return result

        return None

    def find_directory_by_name(self, name: str) -> Optional["DirectoryItem"]:
        """Find a directory by name in this directory tree."""
        for subdir in self.directories:
            if subdir.name == name:
                return subdir

            result = subdir.find_directory_by_name(name)
            if result:
                return result

        return None

    def validate_structure(self) -> List[str]:
        """Validate directory structure and return errors."""
        errors = []

        # Check for duplicate file names
        file_names = [f.name for f in self.files]
        if len(file_names) != len(set(file_names)):
            duplicates = [
                name for name in set(file_names) if file_names.count(name) > 1
            ]
            errors.append(
                f"Duplicate file names in directory '{self.name}': {duplicates}"
            )

        # Check for duplicate directory names
        dir_names = [d.name for d in self.directories]
        if len(dir_names) != len(set(dir_names)):
            duplicates = [name for name in set(dir_names) if dir_names.count(name) > 1]
            errors.append(
                f"Duplicate directory names in directory '{self.name}': {duplicates}"
            )

        # Check for name conflicts between files and directories
        file_names_set = set(file_names)
        dir_names_set = set(dir_names)
        conflicts = file_names_set.intersection(dir_names_set)
        if conflicts:
            errors.append(
                f"Name conflicts between files and directories in '{self.name}': {conflicts}"
            )

        # Validate files
        for file in self.files:
            try:
                file.validate_content_source()
            except ValueError as e:
                errors.append(
                    f"File '{file.name}' in directory '{self.name}': {str(e)}"
                )

        # Recursively validate subdirectories
        for subdir in self.directories:
            subdir_errors = subdir.validate_structure()
            errors.extend(subdir_errors)

        return errors

    def calculate_total_size(self) -> int:
        """Calculate total number of items in directory tree."""
        total = len(self.files) + len(self.directories)

        for subdir in self.directories:
            total += subdir.calculate_total_size()

        return total


class ProjectStructure(BaseModel):
    """Complete project structure definition."""

    root_directory: DirectoryItem = Field(
        ..., description="Root directory of the project"
    )

    global_ignore_patterns: List[str] = Field(
        default_factory=list, description="Global patterns to ignore during generation"
    )

    preserve_empty_directories: bool = Field(
        default=False, description="Whether to preserve empty directories"
    )

    def validate_structure(self) -> List[str]:
        """Validate entire project structure."""
        errors = []

        # Validate root directory
        root_errors = self.root_directory.validate_structure()
        errors.extend(root_errors)

        # Check for reasonable structure size
        total_items = self.root_directory.calculate_total_size()
        if total_items > 1000:
            errors.append(
                f"Project structure is very large ({total_items} items). Consider simplifying."
            )

        return errors

    def get_all_files(self) -> List[FileItem]:
        """Get all files in the project structure."""
        return self.root_directory.get_all_files()

    def get_all_directories(self) -> List[DirectoryItem]:
        """Get all directories in the project structure."""
        return self.root_directory.get_all_directories()

    def find_file_by_name(self, name: str) -> Optional[FileItem]:
        """Find a file by name anywhere in the project structure."""
        return self.root_directory.find_file_by_name(name)

    def find_directory_by_name(self, name: str) -> Optional[DirectoryItem]:
        """Find a directory by name anywhere in the project structure."""
        return self.root_directory.find_directory_by_name(name)


# Enable forward references for self-referencing models
DirectoryItem.model_rebuild()


class TemplateFile(BaseModel):
    """Template file content and metadata."""

    name: str = Field(..., description="Template file name")

    content: str = Field(..., description="Template file content (Jinja2 template)")

    encoding: FileEncoding = Field(
        default=FileEncoding.UTF8, description="Template file encoding"
    )

    description: Optional[str] = Field(
        None, description="Description of template file purpose"
    )

    variables_used: List[str] = Field(
        default_factory=list,
        description="Variables used in this template (for dependency tracking)",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        """Validate template file name."""
        if not v or not v.strip():
            raise ValueError("Template file name cannot be empty")

        if not v.endswith(".j2"):
            raise ValueError("Template file name must end with '.j2'")

        return v.strip()

    def get_output_name(self) -> str:
        """Get output file name (removes .j2 extension)."""
        return self.name[:-3] if self.name.endswith(".j2") else self.name


class TemplateFiles(BaseModel):
    """Collection of template files."""

    files: List[TemplateFile] = Field(
        default_factory=list, description="Template files"
    )

    base_path: str = Field(
        default="templates", description="Base path for template files"
    )

    def find_template(self, name: str) -> Optional[TemplateFile]:
        """Find template file by name."""
        for template in self.files:
            if template.name == name:
                return template
        return None

    def validate_templates(self) -> List[str]:
        """Validate all template files."""
        errors = []

        # Check for duplicate names
        names = [t.name for t in self.files]
        if len(names) != len(set(names)):
            duplicates = [name for name in set(names) if names.count(name) > 1]
            errors.append(f"Duplicate template file names: {duplicates}")

        return errors


# Configuration for the models
class Config:
    """Pydantic configuration."""

    validate_assignment = True
    extra = "forbid"
