# ABOUTME: Base template schema definition using Pydantic models
# ABOUTME: Provides template metadata and core schema structure for validation

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, validator


class TemplateCategory(str, Enum):
    """Template categories based on project types."""

    SCRIPT = "script"
    CLI_SINGLE = "cli_single"
    CLI_COMPLEX = "cli_complex"
    DJANGO = "django"
    FLASK = "flask"
    LIBRARY = "library"
    CUSTOM = "custom"


class TemplateLicense(str, Enum):
    """Common license types for templates."""

    MIT = "MIT"
    APACHE_2_0 = "Apache-2.0"
    GPL_3_0 = "GPL-3.0"
    BSD_3_CLAUSE = "BSD-3-Clause"
    UNLICENSE = "Unlicense"
    PROPRIETARY = "Proprietary"


class TemplateMetadata(BaseModel):
    """Template metadata information."""

    name: str = Field(
        ..., description="Human-readable template name", min_length=1, max_length=100
    )

    description: str = Field(
        ..., description="Detailed template description", min_length=1, max_length=500
    )

    version: str = Field(
        ...,
        description="Template version (semantic versioning)",
        pattern=r"^(\d+)\.(\d+)\.(\d+)(-[\w\d\.-]+)?(\+[\w\d\.-]+)?$",
    )

    category: TemplateCategory = Field(..., description="Template category")

    tags: List[str] = Field(
        default_factory=list, description="Template tags for organization and search"
    )

    author: str = Field(
        ..., description="Template author name", min_length=1, max_length=100
    )

    author_email: Optional[str] = Field(
        None,
        description="Template author email",
        pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
    )

    license: TemplateLicense = Field(
        default=TemplateLicense.MIT, description="Template license"
    )

    created: datetime = Field(
        default_factory=datetime.now, description="Template creation date"
    )

    updated: Optional[datetime] = Field(None, description="Template last update date")

    min_python_version: str = Field(
        default="3.9.6",
        description="Minimum Python version required",
        pattern=r"^(\d+)\.(\d+)\.(\d+)$",
    )

    compatibility: List[str] = Field(
        default_factory=lambda: ["macOS", "Linux", "Windows"],
        description="Supported operating systems",
    )

    documentation_url: Optional[str] = Field(
        None, description="URL to template documentation"
    )

    source_url: Optional[str] = Field(None, description="URL to template source code")

    @validator("tags")
    def validate_tags(cls, v):
        """Validate tags are lowercase and alphanumeric."""
        if not v:
            return v

        for tag in v:
            if not tag.replace("-", "").replace("_", "").isalnum():
                raise ValueError(
                    f"Tag '{tag}' must be alphanumeric (hyphens and underscores allowed)"
                )
            if tag != tag.lower():
                raise ValueError(f"Tag '{tag}' must be lowercase")

        return v

    @validator("updated")
    def validate_updated_after_created(cls, v, values):
        """Ensure updated date is after created date."""
        if v is not None and "created" in values:
            if v < values["created"]:
                raise ValueError("Updated date must be after created date")
        return v

    @validator("compatibility")
    def validate_compatibility(cls, v):
        """Validate compatibility list contains valid OS names."""
        valid_os = {"macOS", "Linux", "Windows"}
        for os_name in v:
            if os_name not in valid_os:
                raise ValueError(f"Invalid OS '{os_name}'. Must be one of: {valid_os}")
        return v


class TemplateConfiguration(BaseModel):
    """Template configuration settings."""

    schema_version: str = Field(
        default="1.0.0",
        description="Template schema version",
        pattern=r"^(\d+)\.(\d+)\.(\d+)$",
    )

    template_suffix: str = Field(
        default=".j2", description="Template file suffix for Jinja2 templates"
    )

    ignore_patterns: List[str] = Field(
        default_factory=lambda: [
            "*.pyc",
            "__pycache__/",
            ".git/",
            ".DS_Store",
            "*.egg-info/",
            "build/",
            "dist/",
            ".pytest_cache/",
            ".mypy_cache/",
            ".venv/",
            "venv/",
        ],
        description="Patterns to ignore during template processing",
    )

    preserve_permissions: bool = Field(
        default=True, description="Whether to preserve file permissions"
    )

    encoding: str = Field(default="utf-8", description="Default file encoding")

    @validator("template_suffix")
    def validate_template_suffix(cls, v):
        """Validate template suffix starts with dot."""
        if not v.startswith("."):
            raise ValueError("Template suffix must start with '.'")
        return v


class BaseTemplate(BaseModel):
    """Base template model containing metadata and configuration."""

    metadata: TemplateMetadata = Field(..., description="Template metadata information")

    configuration: TemplateConfiguration = Field(
        default_factory=TemplateConfiguration,
        description="Template configuration settings",
    )

    def get_template_id(self) -> str:
        """Generate unique template identifier."""
        return f"{self.metadata.author}/{self.metadata.name.lower().replace(' ', '-')}"

    def is_compatible_with_python(self, python_version: str) -> bool:
        """Check if template is compatible with given Python version."""
        try:
            # Simple version comparison (assumes semantic versioning)
            min_parts = [int(x) for x in self.metadata.min_python_version.split(".")]
            check_parts = [int(x) for x in python_version.split(".")]

            return check_parts >= min_parts
        except (ValueError, AttributeError):
            return False

    def is_compatible_with_os(self, os_name: str) -> bool:
        """Check if template is compatible with given operating system."""
        return os_name in self.metadata.compatibility

    def validate_template(self) -> List[str]:
        """Validate template and return list of validation errors."""
        errors = []

        # Check required fields
        if not self.metadata.name.strip():
            errors.append("Template name cannot be empty")

        if not self.metadata.description.strip():
            errors.append("Template description cannot be empty")

        if not self.metadata.author.strip():
            errors.append("Template author cannot be empty")

        # Check version format
        try:
            parts = self.metadata.version.split(".")
            if len(parts) != 3 or not all(p.isdigit() for p in parts):
                errors.append("Template version must be in format X.Y.Z")
        except:
            errors.append("Invalid template version format")

        # Check Python version format
        try:
            parts = self.metadata.min_python_version.split(".")
            if len(parts) != 3 or not all(p.isdigit() for p in parts):
                errors.append("Python version must be in format X.Y.Z")
        except:
            errors.append("Invalid Python version format")

        return errors

    class Config:
        """Pydantic configuration."""

        validate_assignment = True
        extra = "forbid"
        json_encoders = {datetime: lambda v: v.isoformat()}
