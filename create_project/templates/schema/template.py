# ABOUTME: Complete template schema combining all components
# ABOUTME: Provides the main Template model that integrates metadata, variables, structure, and actions

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, ValidationInfo

from .actions import ActionGroup, TemplateHooks
from .base_template import BaseTemplate
from .structure import ProjectStructure, TemplateFiles
from .variables import TemplateVariable


class TemplateCompatibility(BaseModel):
    """Template compatibility requirements."""

    min_python_version: str = Field(
        default="3.9.6", description="Minimum Python version required"
    )

    max_python_version: Optional[str] = Field(
        None, description="Maximum Python version supported"
    )

    supported_os: List[str] = Field(
        default_factory=lambda: ["macOS", "Linux", "Windows"],
        description="Supported operating systems",
    )

    dependencies: List[str] = Field(
        default_factory=list, description="External dependencies required"
    )

    @field_validator("min_python_version", "max_python_version")
    @classmethod
    def validate_python_version(cls, v: Optional[str]) -> Optional[str]:
        """Validate Python version format."""
        if v is None:
            return v

        import re

        if not re.match(r"^\d+\.\d+\.\d+$", v):
            raise ValueError("Python version must be in format X.Y.Z")

        return v


class TemplateUsageStats(BaseModel):
    """Template usage statistics."""

    downloads: int = Field(
        default=0, description="Number of times template was downloaded"
    )

    generations: int = Field(
        default=0, description="Number of times template was used to generate projects"
    )

    last_used: Optional[datetime] = Field(
        None, description="Last time template was used"
    )

    average_rating: Optional[float] = Field(None, description="Average user rating")

    @field_validator("average_rating")
    @classmethod
    def validate_rating(cls, v: Optional[float]) -> Optional[float]:
        """Validate rating is between 1 and 5."""
        if v is not None and (v < 1.0 or v > 5.0):
            raise ValueError("Rating must be between 1.0 and 5.0")
        return v


class Template(BaseTemplate):
    """Complete template definition with all components."""

    # Variables for user input
    variables: List[TemplateVariable] = Field(
        default_factory=list, description="Template variables for user input"
    )

    # Project structure
    structure: ProjectStructure = Field(
        ..., description="Project file and directory structure"
    )

    # Template files
    template_files: TemplateFiles = Field(
        default_factory=TemplateFiles,
        description="Template files for content generation",
    )

    # Actions and hooks
    hooks: TemplateHooks = Field(
        default_factory=TemplateHooks,
        description="Template hooks for different generation stages",
    )

    action_groups: List[ActionGroup] = Field(
        default_factory=list, description="Grouped actions for organization"
    )

    # Compatibility and requirements
    compatibility: TemplateCompatibility = Field(
        default_factory=TemplateCompatibility,
        description="Template compatibility requirements",
    )

    # Usage statistics (optional)
    usage_stats: Optional[TemplateUsageStats] = Field(
        None, description="Template usage statistics"
    )

    # Additional metadata
    examples: List[str] = Field(
        default_factory=list,
        description="Example projects generated from this template",
    )

    related_templates: List[str] = Field(
        default_factory=list, description="IDs of related templates"
    )

    @field_validator("variables")
    @classmethod
    def validate_variables(cls, v: List[TemplateVariable]) -> List[TemplateVariable]:
        """Validate template variables."""
        if not v:
            return v

        # Check for duplicate variable names
        names = [var.name for var in v]
        if len(names) != len(set(names)):
            duplicates = [name for name in set(names) if names.count(name) > 1]
            raise ValueError(f"Duplicate variable names: {duplicates}")

        return v

    def validate_template_complete(self) -> List[str]:
        """Comprehensive validation of the complete template."""
        errors = []

        # Validate base template
        base_errors = self.validate_template()
        errors.extend(base_errors)

        # Validate variables
        for var in self.variables:
            var_errors = var.validate_value(var.default)
            if var_errors:
                errors.extend([f"Variable '{var.name}': {err}" for err in var_errors])

        # Validate structure
        structure_errors = self.structure.validate_structure()
        errors.extend(structure_errors)

        # Validate template files
        template_file_errors = self.template_files.validate_templates()
        errors.extend(template_file_errors)

        # Validate hooks
        hook_errors = self.hooks.validate_hooks()
        errors.extend(hook_errors)

        # Validate action groups
        for group in self.action_groups:
            group_errors = group.validate_actions()
            errors.extend(group_errors)

        # Check variable usage in structure
        self._validate_variable_usage(errors)

        # Check template file references
        self._validate_template_file_references(errors)

        return errors

    def _validate_variable_usage(self, errors: List[str]):
        """Validate that variables used in structure are defined."""
        defined_vars = {var.name for var in self.variables}

        # Check variables in file names and content
        all_files = self.structure.get_all_files()
        for file in all_files:
            # Extract variables from file names (simple check for {{ var }})
            import re

            file_vars = re.findall(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}", file.name)
            for var in file_vars:
                if var not in defined_vars:
                    errors.append(
                        f"Undefined variable '{var}' used in file name: {file.name}"
                    )

            # Check content if it's inline
            if file.content:
                content_vars = re.findall(
                    r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}", file.content
                )
                for var in content_vars:
                    if var not in defined_vars:
                        errors.append(
                            f"Undefined variable '{var}' used in file content: {file.name}"
                        )

        # Check variables in directory names
        all_dirs = self.structure.get_all_directories()
        for directory in all_dirs:
            dir_vars = re.findall(
                r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}", directory.name
            )
            for var in dir_vars:
                if var not in defined_vars:
                    errors.append(
                        f"Undefined variable '{var}' used in directory name: {directory.name}"
                    )

    def _validate_template_file_references(self, errors: List[str]):
        """Validate that template file references exist."""
        available_templates = {tf.name for tf in self.template_files.files}

        all_files = self.structure.get_all_files()
        for file in all_files:
            if file.template_file and file.template_file not in available_templates:
                errors.append(
                    f"Template file '{file.template_file}' not found (referenced by {file.name})"
                )

    def get_variable_by_name(self, name: str) -> Optional[TemplateVariable]:
        """Get a variable by name."""
        for var in self.variables:
            if var.name == name:
                return var
        return None

    def get_required_variables(self) -> List[TemplateVariable]:
        """Get all required variables."""
        return [var for var in self.variables if var.required]

    def get_optional_variables(self) -> List[TemplateVariable]:
        """Get all optional variables."""
        return [var for var in self.variables if not var.required]

    def get_variables_by_type(self, var_type: str) -> List[TemplateVariable]:
        """Get variables by type."""
        return [var for var in self.variables if var.type == var_type]

    def estimate_generation_time(self) -> int:
        """Estimate generation time in seconds."""
        # Basic estimation based on structure complexity
        file_count = len(self.structure.get_all_files())
        dir_count = len(self.structure.get_all_directories())
        action_count = len(self.hooks.get_all_actions())

        # Rough estimates
        base_time = 5  # seconds
        file_time = file_count * 0.5
        dir_time = dir_count * 0.1
        action_time = action_count * 2

        return int(base_time + file_time + dir_time + action_time)

    def get_template_summary(self) -> Dict[str, Any]:
        """Get a summary of the template."""
        return {
            "name": self.metadata.name,
            "description": self.metadata.description,
            "version": self.metadata.version,
            "category": self.metadata.category,
            "author": self.metadata.author,
            "variable_count": len(self.variables),
            "file_count": len(self.structure.get_all_files()),
            "directory_count": len(self.structure.get_all_directories()),
            "action_count": len(self.hooks.get_all_actions()),
            "estimated_time": self.estimate_generation_time(),
            "compatibility": {
                "python_version": self.compatibility.min_python_version,
                "os": self.compatibility.supported_os,
            },
        }

    class Config:
        """Pydantic configuration."""

        validate_assignment = True
        extra = "forbid"
        json_encoders = {datetime: lambda v: v.isoformat()}
