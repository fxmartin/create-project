# ABOUTME: Unit tests for template rendering functionality
# ABOUTME: Tests project, file, and directory rendering with Jinja2 templates

"""Tests for template renderers."""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from create_project.templates.engine import RenderingError, TemplateEngine
from create_project.templates.renderers import (
    DirectoryRenderer,
    FileRenderer,
    ProjectRenderer,
)
from create_project.templates.schema.structure import DirectoryItem, FileItem
from create_project.templates.schema.template import Template


class TestProjectRenderer:
    """Tests for ProjectRenderer class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = Mock(spec=TemplateEngine)
        self.engine.render_template_string = Mock(side_effect=lambda s, v: s.format(**v))
        self.engine.jinja_env = Mock()

        self.renderer = ProjectRenderer(self.engine)

    def test_renderer_initialization(self):
        """Test project renderer initialization."""
        assert self.renderer.engine == self.engine
        assert hasattr(self.renderer, "logger")

    def test_render_project_success(self):
        """Test successful project rendering."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test-project"

            # Create mock template
            template = Mock(spec=Template)
            template.metadata = Mock()
            template.metadata.name = "test-template"
            template.structure = Mock()
            template.structure.root_directory = Mock(spec=DirectoryItem)
            template.structure.root_directory.name = "test-project"
            template.structure.root_directory.condition = None
            template.structure.root_directory.files = []
            template.structure.root_directory.directories = []
            template.template_files = None

            variables = {"project_name": "test-project"}

            stats = self.renderer.render_project(template, variables, output_path)

            assert output_path.exists()
            assert output_path.is_dir()
            assert "files_created" in stats
            assert "directories_created" in stats
            assert "files_skipped" in stats
            assert "errors" in stats

    def test_render_project_output_exists_no_overwrite(self):
        """Test project rendering when output exists and overwrite is False."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "existing-project"
            output_path.mkdir()
            (output_path / "existing_file.txt").touch()

            template = Mock(spec=Template)
            template.metadata = Mock()
            template.metadata.name = "test-template"

            variables = {}

            with pytest.raises(RenderingError, match="Output directory is not empty"):
                self.renderer.render_project(template, variables, output_path, overwrite=False)

    def test_render_project_with_overwrite(self):
        """Test project rendering with overwrite enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "existing-project"
            output_path.mkdir()
            (output_path / "existing_file.txt").touch()

            template = Mock(spec=Template)
            template.metadata = Mock()
            template.metadata.name = "test-template"
            template.structure = Mock()
            template.structure.root_directory = Mock(spec=DirectoryItem)
            template.structure.root_directory.name = "test-project"
            template.structure.root_directory.condition = None
            template.structure.root_directory.files = []
            template.structure.root_directory.directories = []
            template.template_files = None

            variables = {"project_name": "test-project"}

            # Should not raise exception with overwrite=True
            stats = self.renderer.render_project(template, variables, output_path, overwrite=True)

            assert "files_created" in stats

    def test_render_directory_with_condition_true(self):
        """Test directory rendering with condition that evaluates to True."""
        with tempfile.TemporaryDirectory() as temp_dir:
            parent_path = Path(temp_dir)

            directory = Mock(spec=DirectoryItem)
            directory.name = "test-dir"
            directory.condition = "include_feature"
            directory.files = []
            directory.directories = []

            variables = {"include_feature": True}
            stats = {"directories_created": 0, "files_created": 0, "files_skipped": 0, "errors": []}

            # Mock condition evaluation to return True
            self.renderer._evaluate_condition = Mock(return_value=True)

            self.renderer._render_directory(directory, variables, parent_path, False, stats)

            created_dir = parent_path / "test-dir"
            assert created_dir.exists()
            assert stats["directories_created"] == 1

    def test_render_directory_with_condition_false(self):
        """Test directory rendering with condition that evaluates to False."""
        with tempfile.TemporaryDirectory() as temp_dir:
            parent_path = Path(temp_dir)

            directory = Mock(spec=DirectoryItem)
            directory.name = "test-dir"
            directory.condition = "include_feature"
            directory.files = []
            directory.directories = []

            variables = {"include_feature": False}
            stats = {"directories_created": 0, "files_created": 0, "files_skipped": 0, "errors": []}

            # Mock condition evaluation to return False
            self.renderer._evaluate_condition = Mock(return_value=False)

            self.renderer._render_directory(directory, variables, parent_path, False, stats)

            created_dir = parent_path / "test-dir"
            assert not created_dir.exists()
            assert stats["directories_created"] == 0

    def test_render_file_with_inline_content(self):
        """Test file rendering with inline content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            parent_path = Path(temp_dir)

            file_item = Mock(spec=FileItem)
            file_item.name = "test-file.txt"
            file_item.condition = None
            file_item.content = "Hello {project_name}!"
            file_item.template_file = None
            file_item.binary_content = None
            file_item.permissions = None

            variables = {"project_name": "TestProject"}
            stats = {"files_created": 0, "files_skipped": 0, "files_overwritten": 0, "errors": []}

            self.renderer._render_file(file_item, variables, parent_path, False, stats)

            created_file = parent_path / "test-file.txt"
            assert created_file.exists()
            assert created_file.read_text() == "Hello TestProject!"
            assert stats["files_created"] == 1

    def test_render_file_with_template_file(self):
        """Test file rendering with external template file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            parent_path = Path(temp_dir)

            file_item = Mock(spec=FileItem)
            file_item.name = "output.txt"
            file_item.condition = None
            file_item.content = None
            file_item.template_file = "template.txt.j2"
            file_item.binary_content = None
            file_item.permissions = None

            variables = {"name": "World"}
            stats = {"files_created": 0, "files_skipped": 0, "files_overwritten": 0, "errors": []}

            # Mock template loading and rendering
            mock_template = Mock()
            mock_template.render.return_value = "Hello World!"
            self.engine.jinja_env.get_template.return_value = mock_template

            self.renderer._render_file(file_item, variables, parent_path, False, stats)

            created_file = parent_path / "output.txt"
            assert created_file.exists()
            assert created_file.read_text() == "Hello World!"
            assert stats["files_created"] == 1

    def test_render_file_skip_existing(self):
        """Test file rendering skipping existing files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            parent_path = Path(temp_dir)
            existing_file = parent_path / "existing.txt"
            existing_file.write_text("existing content")

            file_item = Mock(spec=FileItem)
            file_item.name = "existing.txt"
            file_item.condition = None
            file_item.content = "new content"
            file_item.template_file = None
            file_item.binary_content = None
            file_item.permissions = None

            variables = {}
            stats = {"files_created": 0, "files_skipped": 0, "files_overwritten": 0, "errors": []}

            self.renderer._render_file(file_item, variables, parent_path, False, stats)

            # File should not be overwritten
            assert existing_file.read_text() == "existing content"
            assert stats["files_skipped"] == 1
            assert stats["files_created"] == 0

    def test_render_file_with_condition_false(self):
        """Test file rendering with condition that evaluates to False."""
        with tempfile.TemporaryDirectory() as temp_dir:
            parent_path = Path(temp_dir)

            file_item = Mock(spec=FileItem)
            file_item.name = "conditional.txt"
            file_item.condition = "include_file"
            file_item.content = "content"
            file_item.template_file = None
            file_item.binary_content = None
            file_item.permissions = None

            variables = {"include_file": False}
            stats = {"files_created": 0, "files_skipped": 0, "files_overwritten": 0, "errors": []}

            # Mock condition evaluation to return False
            self.renderer._evaluate_condition = Mock(return_value=False)

            self.renderer._render_file(file_item, variables, parent_path, False, stats)

            created_file = parent_path / "conditional.txt"
            assert not created_file.exists()
            assert stats["files_skipped"] == 1

    def test_evaluate_condition_boolean_strings(self):
        """Test condition evaluation with boolean strings."""
        # Test truthy values
        assert self.renderer._evaluate_condition("true", {}) is True
        assert self.renderer._evaluate_condition("1", {}) is True
        assert self.renderer._evaluate_condition("yes", {}) is True
        assert self.renderer._evaluate_condition("on", {}) is True

        # Test falsy values
        assert self.renderer._evaluate_condition("false", {}) is False
        assert self.renderer._evaluate_condition("0", {}) is False
        assert self.renderer._evaluate_condition("no", {}) is False
        assert self.renderer._evaluate_condition("off", {}) is False
        assert self.renderer._evaluate_condition("", {}) is False

    def test_set_file_permissions(self):
        """Test setting file permissions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("test content")

            # Test setting permissions
            self.renderer._set_file_permissions(test_file, "755")

            # Check that file still exists (permissions were set without error)
            assert test_file.exists()


class TestFileRenderer:
    """Tests for FileRenderer class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = Mock(spec=TemplateEngine)
        self.engine.render_template_string = Mock(side_effect=lambda s, v: s.format(**v))

        self.renderer = FileRenderer(self.engine)

    def test_render_file_content(self):
        """Test rendering file content from template string."""
        template_content = "Hello {name}!"
        variables = {"name": "World"}

        result = self.renderer.render_file_content(template_content, variables)

        assert result == "Hello World!"
        self.engine.render_template_string.assert_called_once_with(template_content, variables)

    def test_render_file_name(self):
        """Test rendering file name from template."""
        template_name = "{project_name}.txt"
        variables = {"project_name": "myproject"}

        result = self.renderer.render_file_name(template_name, variables)

        assert result == "myproject.txt"
        self.engine.render_template_string.assert_called_once_with(template_name, variables)

    def test_render_file_from_template_success(self):
        """Test rendering file from external template file."""
        template_file_path = "template.txt.j2"
        variables = {"name": "World"}

        # Mock template loading and rendering
        mock_template = Mock()
        mock_template.render.return_value = "Hello World!"
        self.engine.jinja_env = Mock()
        self.engine.jinja_env.get_template.return_value = mock_template

        result = self.renderer.render_file_from_template(template_file_path, variables)

        assert result == "Hello World!"
        self.engine.jinja_env.get_template.assert_called_once_with(template_file_path)
        mock_template.render.assert_called_once_with(**variables)

    def test_render_file_from_template_not_found(self):
        """Test rendering file from non-existent template file."""
        import jinja2

        template_file_path = "nonexistent.txt.j2"
        variables = {"name": "World"}

        # Mock template not found error
        self.engine.jinja_env = Mock()
        self.engine.jinja_env.get_template.side_effect = jinja2.TemplateNotFound("template not found")

        with pytest.raises(RenderingError, match="Template file not found"):
            self.renderer.render_file_from_template(template_file_path, variables)


class TestDirectoryRenderer:
    """Tests for DirectoryRenderer class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = Mock(spec=TemplateEngine)
        self.engine.render_template_string = Mock(side_effect=lambda s, v: s.format(**v))

        self.renderer = DirectoryRenderer(self.engine)

    def test_create_directory_structure_simple(self):
        """Test creating simple directory structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)

            structure = Mock(spec=DirectoryItem)
            structure.name = "project-{name}"
            structure.directories = []

            variables = {"name": "test"}

            created_dirs = self.renderer.create_directory_structure(structure, base_path, variables)

            expected_dir = base_path / "project-test"
            assert expected_dir.exists()
            assert expected_dir in created_dirs

    def test_create_directory_structure_nested(self):
        """Test creating nested directory structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)

            # Create nested structure
            sub_dir = Mock(spec=DirectoryItem)
            sub_dir.name = "src"
            sub_dir.directories = []

            main_dir = Mock(spec=DirectoryItem)
            main_dir.name = "project-{name}"
            main_dir.directories = [sub_dir]

            variables = {"name": "test"}

            created_dirs = self.renderer.create_directory_structure(main_dir, base_path, variables)

            expected_main_dir = base_path / "project-test"
            expected_sub_dir = expected_main_dir / "src"

            assert expected_main_dir.exists()
            assert expected_sub_dir.exists()
            assert expected_main_dir in created_dirs
            assert expected_sub_dir in created_dirs

    def test_create_directory_structure_existing_dir(self):
        """Test creating directory structure when directory already exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)

            # Create directory first
            existing_dir = base_path / "existing"
            existing_dir.mkdir()

            structure = Mock(spec=DirectoryItem)
            structure.name = "existing"
            structure.directories = []

            variables = {}

            created_dirs = self.renderer.create_directory_structure(structure, base_path, variables)

            # Directory should still exist, but not be in created_dirs list
            assert existing_dir.exists()
            assert existing_dir not in created_dirs
