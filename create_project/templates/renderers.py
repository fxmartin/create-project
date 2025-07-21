# ABOUTME: Template rendering system for files and directories
# ABOUTME: Handles the creation of project structures with Jinja2 templating

"""
Template Renderers

Responsible for rendering template files and creating directory structures
based on template definitions. Handles file content rendering, directory
creation, and conditional logic for project generation.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Union

import jinja2

from ..utils.logger import get_logger
from .engine import RenderingError, TemplateEngine
from .schema.structure import DirectoryItem, FileItem
from .schema.template import Template


class ProjectRenderer:
    """Renders project structures from templates."""

    def __init__(self, template_engine: TemplateEngine):
        """Initialize the project renderer.

        Args:
            template_engine: Template engine instance
        """
        self.engine = template_engine
        self.logger = get_logger(__name__)

    def render_project(
        self,
        template: Template,
        variables: Dict[str, Any],
        output_path: Union[str, Path],
        overwrite: bool = False,
    ) -> Dict[str, Any]:
        """Render a complete project from template.

        Args:
            template: Template to render
            variables: Resolved template variables
            output_path: Output directory path
            overwrite: Whether to overwrite existing files

        Returns:
            Dictionary with rendering results and statistics

        Raises:
            RenderingError: If rendering fails
        """
        output_path = Path(output_path)

        self.logger.info(
            f"Rendering project '{template.metadata.name}' to: {output_path}"
        )

        # Validate output path
        if output_path.exists() and not overwrite:
            if any(output_path.iterdir()):
                raise RenderingError(f"Output directory is not empty: {output_path}")

        # Create output directory if it doesn't exist
        output_path.mkdir(parents=True, exist_ok=True)

        # Track rendering statistics
        stats = {
            "files_created": 0,
            "directories_created": 0,
            "files_skipped": 0,
            "files_overwritten": 0,
            "errors": [],
        }

        try:
            # Render project structure
            self._render_directory(
                template.structure.root_directory,
                variables,
                output_path,
                overwrite,
                stats,
            )

            # Copy and render template files
            self._render_template_files(
                template, variables, output_path, overwrite, stats
            )

            self.logger.info(
                f"Project rendering complete: "
                f"{stats['files_created']} files, "
                f"{stats['directories_created']} directories created"
            )

            return stats

        except Exception as e:
            error_msg = f"Project rendering failed: {e}"
            self.logger.error(error_msg)
            stats["errors"].append(error_msg)
            raise RenderingError(error_msg)

    def _render_directory(
        self,
        directory: DirectoryItem,
        variables: Dict[str, Any],
        parent_path: Path,
        overwrite: bool,
        stats: Dict[str, Any],
    ) -> None:
        """Render a directory and its contents.

        Args:
            directory: Directory definition
            variables: Template variables
            parent_path: Parent directory path
            overwrite: Whether to overwrite existing files
            stats: Statistics tracking dictionary
        """
        # Evaluate directory condition
        if directory.condition and not self._evaluate_condition(
            directory.condition, variables
        ):
            self.logger.debug(f"Directory '{directory.name}' skipped due to condition")
            return

        # Render directory name
        dir_name = self.engine.render_template_string(directory.name, variables)
        dir_path = parent_path / dir_name

        # Create directory if it doesn't exist
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            stats["directories_created"] += 1
            self.logger.debug(f"Created directory: {dir_path}")

        # Render files in this directory
        for file_item in directory.files:
            self._render_file(file_item, variables, dir_path, overwrite, stats)

        # Render subdirectories
        for sub_directory in directory.directories:
            self._render_directory(sub_directory, variables, dir_path, overwrite, stats)

    def _render_file(
        self,
        file_item: FileItem,
        variables: Dict[str, Any],
        parent_path: Path,
        overwrite: bool,
        stats: Dict[str, Any],
    ) -> None:
        """Render a file from template.

        Args:
            file_item: File definition
            variables: Template variables
            parent_path: Parent directory path
            overwrite: Whether to overwrite existing files
            stats: Statistics tracking dictionary
        """
        # Evaluate file condition
        if file_item.condition and not self._evaluate_condition(
            file_item.condition, variables
        ):
            self.logger.debug(f"File '{file_item.name}' skipped due to condition")
            stats["files_skipped"] += 1
            return

        try:
            # Render file name
            file_name = self.engine.render_template_string(file_item.name, variables)
            file_path = parent_path / file_name

            # Check if file exists
            if file_path.exists() and not overwrite:
                self.logger.warning(f"File exists, skipping: {file_path}")
                stats["files_skipped"] += 1
                return

            # Determine file content source
            content = ""
            if file_item.content:
                # Inline content
                content = self.engine.render_template_string(
                    file_item.content, variables
                )
            elif file_item.template_file:
                # External template file
                try:
                    template = self.engine.jinja_env.get_template(
                        file_item.template_file
                    )
                    content = template.render(**variables)
                except jinja2.TemplateNotFound:
                    raise RenderingError(
                        f"Template file not found: {file_item.template_file}"
                    )
            elif file_item.binary_content:
                # Binary content (base64 encoded)
                import base64

                content = base64.b64decode(file_item.binary_content)

            # Track if file exists before writing
            file_existed = file_path.exists()

            # Write file
            if isinstance(content, bytes):
                with open(file_path, "wb") as f:
                    f.write(content)
            else:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

            # Set file permissions if specified
            if file_item.permissions:
                self._set_file_permissions(file_path, file_item.permissions)

            if file_existed:
                stats["files_overwritten"] += 1
            else:
                stats["files_created"] += 1

            self.logger.debug(f"Created file: {file_path}")

        except Exception as e:
            error_msg = f"Failed to render file '{file_item.name}': {e}"
            self.logger.error(error_msg)
            stats["errors"].append(error_msg)
            raise RenderingError(error_msg)

    def _render_template_files(
        self,
        template: Template,
        variables: Dict[str, Any],
        output_path: Path,
        overwrite: bool,
        stats: Dict[str, Any],
    ) -> None:
        """Render standalone template files.

        Args:
            template: Template object
            variables: Template variables
            output_path: Output path
            overwrite: Whether to overwrite existing files
            stats: Statistics tracking dictionary
        """
        if not template.template_files or not template.template_files.files:
            return

        for template_file in template.template_files.files:
            try:
                # Determine output file path
                if template_file.output_path:
                    output_file_path = output_path / template_file.output_path
                else:
                    output_file_path = output_path / template_file.name

                # Create parent directories
                output_file_path.parent.mkdir(parents=True, exist_ok=True)

                # Render template content
                jinja_template = self.engine.jinja_env.get_template(template_file.name)
                content = jinja_template.render(**variables)

                # Check if file exists
                if output_file_path.exists() and not overwrite:
                    self.logger.warning(
                        f"Template file exists, skipping: {output_file_path}"
                    )
                    stats["files_skipped"] += 1
                    continue

                # Write file
                with open(output_file_path, "w", encoding="utf-8") as f:
                    f.write(content)

                if output_file_path.exists() and not overwrite:
                    stats["files_overwritten"] += 1
                else:
                    stats["files_created"] += 1

                self.logger.debug(f"Rendered template file: {output_file_path}")

            except Exception as e:
                error_msg = (
                    f"Failed to render template file '{template_file.name}': {e}"
                )
                self.logger.error(error_msg)
                stats["errors"].append(error_msg)

    def _evaluate_condition(
        self, condition: Union[str, "ConditionalExpression"], variables: Dict[str, Any]
    ) -> bool:
        """Evaluate a Jinja2 condition expression.

        Args:
            condition: Jinja2 condition string or ConditionalExpression object
            variables: Template variables

        Returns:
            True if condition evaluates to truthy, False otherwise
        """
        try:
            # Handle ConditionalExpression objects
            from .schema.structure import ConditionalExpression

            if isinstance(condition, ConditionalExpression):
                condition = condition.expression

            # First check if it's a simple boolean string
            if condition.lower() in ("true", "1", "yes", "on"):
                return True
            elif condition.lower() in ("false", "0", "no", "off", ""):
                return False

            # If not a simple boolean, try to evaluate as Jinja2 template
            template_string = f"{{{{ {condition} }}}}"
            result = self.engine.render_template_string(template_string, variables)

            # Convert result to boolean
            if result.lower() in ("true", "1", "yes", "on"):
                return True
            elif result.lower() in ("false", "0", "no", "off", ""):
                return False
            else:
                # Try to evaluate as Python expression
                return bool(eval(result))

        except Exception as e:
            self.logger.warning(f"Failed to evaluate condition '{condition}': {e}")
            return False

    def _set_file_permissions(self, file_path: Path, permissions: str) -> None:
        """Set file permissions using octal notation.

        Args:
            file_path: Path to the file
            permissions: Octal permission string (e.g., "755")
        """
        try:
            # Convert octal string to integer
            perm_int = int(permissions, 8)
            os.chmod(file_path, perm_int)
            self.logger.debug(f"Set permissions {permissions} on: {file_path}")
        except Exception as e:
            self.logger.warning(f"Failed to set permissions on {file_path}: {e}")


class FileRenderer:
    """Renders individual files from templates."""

    def __init__(self, template_engine: TemplateEngine):
        """Initialize the file renderer.

        Args:
            template_engine: Template engine instance
        """
        self.engine = template_engine
        self.logger = get_logger(__name__)

    def render_file_content(
        self, template_content: str, variables: Dict[str, Any]
    ) -> str:
        """Render file content from template string.

        Args:
            template_content: Template content string
            variables: Template variables

        Returns:
            Rendered content

        Raises:
            RenderingError: If rendering fails
        """
        return self.engine.render_template_string(template_content, variables)

    def render_file_name(self, template_name: str, variables: Dict[str, Any]) -> str:
        """Render file name from template.

        Args:
            template_name: Template name string
            variables: Template variables

        Returns:
            Rendered file name

        Raises:
            RenderingError: If rendering fails
        """
        return self.engine.render_template_string(template_name, variables)

    def render_file_from_template(
        self, template_file_path: str, variables: Dict[str, Any]
    ) -> str:
        """Render file content from external template file.

        Args:
            template_file_path: Path to template file
            variables: Template variables

        Returns:
            Rendered content

        Raises:
            RenderingError: If rendering fails
        """
        try:
            template = self.engine.jinja_env.get_template(template_file_path)
            return template.render(**variables)
        except jinja2.TemplateNotFound:
            raise RenderingError(f"Template file not found: {template_file_path}")
        except jinja2.TemplateError as e:
            raise RenderingError(f"Template rendering error: {e}")


class DirectoryRenderer:
    """Renders directory structures from templates."""

    def __init__(self, template_engine: TemplateEngine):
        """Initialize the directory renderer.

        Args:
            template_engine: Template engine instance
        """
        self.engine = template_engine
        self.logger = get_logger(__name__)

    def create_directory_structure(
        self, structure: DirectoryItem, base_path: Path, variables: Dict[str, Any]
    ) -> List[Path]:
        """Create directory structure from template.

        Args:
            structure: Directory structure definition
            base_path: Base path for creation
            variables: Template variables

        Returns:
            List of created directory paths

        Raises:
            RenderingError: If directory creation fails
        """
        created_dirs = []

        try:
            self._create_directory_recursive(
                structure, base_path, variables, created_dirs
            )
            return created_dirs
        except Exception as e:
            raise RenderingError(f"Directory creation failed: {e}")

    def _create_directory_recursive(
        self,
        directory: DirectoryItem,
        parent_path: Path,
        variables: Dict[str, Any],
        created_dirs: List[Path],
    ) -> None:
        """Recursively create directory structure.

        Args:
            directory: Directory definition
            parent_path: Parent directory path
            variables: Template variables
            created_dirs: List to track created directories
        """
        # Render directory name
        dir_name = self.engine.render_template_string(directory.name, variables)
        dir_path = parent_path / dir_name

        # Create directory
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            created_dirs.append(dir_path)
            self.logger.debug(f"Created directory: {dir_path}")

        # Create subdirectories
        for sub_directory in directory.directories:
            self._create_directory_recursive(
                sub_directory, dir_path, variables, created_dirs
            )
