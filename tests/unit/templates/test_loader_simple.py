# ABOUTME: Simplified unit tests for template loader - focuses on core functionality
# ABOUTME: Tests template discovery and loading with actual API methods

"""
Unit tests for create_project.templates.loader module.
Simplified to test actual available API methods.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from create_project.config.config_manager import ConfigManager
from create_project.templates.engine import TemplateLoadError
from create_project.templates.loader import TemplateLoader


class TestTemplateLoader:
    """Test the TemplateLoader class."""

    @pytest.fixture
    def mock_config_manager(self):
        """Create a mock ConfigManager."""
        config = Mock(spec=ConfigManager)
        config.get_setting.side_effect = lambda key, default=None: {
            "templates.builtin_path": "create_project/templates/builtin",
            "templates.directories": [],
            "templates.custom_path": "~/.project-creator/templates",
        }.get(key, default)
        return config

    @pytest.fixture
    def template_loader(self, mock_config_manager):
        """Create a TemplateLoader instance for testing."""
        return TemplateLoader(config_manager=mock_config_manager)

    @pytest.fixture
    def sample_template_data(self):
        """Create sample template data for testing."""
        return {
            "metadata": {
                "name": "Test Template",
                "description": "A test template for testing",
                "version": "1.0.0",
                "author": "Test Author",
                "template_id": "test_template",
                "category": "test",
                "tags": ["test", "sample"]
            },
            "variables": [
                {
                    "name": "project_name",
                    "type": "string",
                    "description": "Project name",
                    "required": True
                }
            ],
            "structure": {
                "root_directory": {
                    "name": "{{project_name}}",
                    "files": [
                        {
                            "name": "README.md",
                            "content": "# {{project_name}}"
                        }
                    ]
                }
            }
        }

    @pytest.fixture
    def temp_template_dir(self, sample_template_data):
        """Create a temporary directory with sample templates."""
        temp_dir = Path(tempfile.mkdtemp())

        # Create sample template file
        template_path = temp_dir / "test_template.yaml"
        template_path.write_text(yaml.dump(sample_template_data))

        # Create another template
        template2_data = sample_template_data.copy()
        template2_data["metadata"]["name"] = "Second Template"
        template2_data["metadata"]["template_id"] = "second_template"
        template2_path = temp_dir / "second_template.yaml"
        template2_path.write_text(yaml.dump(template2_data))

        return temp_dir

    def test_init_with_config_manager(self, mock_config_manager):
        """Test TemplateLoader initialization with ConfigManager."""
        loader = TemplateLoader(config_manager=mock_config_manager)
        assert loader.config_manager is mock_config_manager

    def test_init_without_config_manager(self):
        """Test TemplateLoader initialization without ConfigManager."""
        loader = TemplateLoader()
        assert loader.config_manager is not None

    def test_discover_templates_empty(self, template_loader):
        """Test template discovery returns list."""
        with patch.object(template_loader, "_find_yaml_files", return_value=[]):
            templates = template_loader.discover_templates()

        assert isinstance(templates, list)

    def test_find_yaml_files_success(self, template_loader, temp_template_dir):
        """Test finding YAML files in directory."""
        yaml_files = template_loader._find_yaml_files(temp_template_dir)

        assert len(yaml_files) >= 2
        assert all(f.suffix in [".yaml", ".yml"] for f in yaml_files)

    def test_find_yaml_files_empty_dir(self, template_loader):
        """Test finding YAML files in empty directory."""
        empty_dir = Path(tempfile.mkdtemp())
        yaml_files = template_loader._find_yaml_files(empty_dir)

        assert yaml_files == []

    def test_find_yaml_files_nonexistent_dir(self, template_loader):
        """Test finding YAML files in nonexistent directory."""
        nonexistent_dir = Path("/nonexistent/directory")
        yaml_files = template_loader._find_yaml_files(nonexistent_dir)

        assert yaml_files == []

    def test_load_template_metadata_success(self, template_loader, temp_template_dir):
        """Test loading template metadata successfully."""
        template_path = temp_template_dir / "test_template.yaml"

        metadata = template_loader.load_template_metadata(template_path)

        assert isinstance(metadata, dict)
        assert metadata["name"] == "Test Template"
        assert metadata["template_id"] == "test_template"
        assert metadata["version"] == "1.0.0"

    def test_load_template_metadata_file_not_found(self, template_loader):
        """Test loading metadata from nonexistent file."""
        with pytest.raises(TemplateLoadError) as exc_info:
            template_loader.load_template_metadata("/nonexistent/template.yaml")

        assert "No such file or directory" in str(exc_info.value)

    def test_load_template_metadata_invalid_yaml(self, template_loader):
        """Test loading metadata from invalid YAML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: [")
            invalid_file = Path(f.name)

        with pytest.raises(TemplateLoadError) as exc_info:
            template_loader.load_template_metadata(invalid_file)

        assert "YAML parsing error" in str(exc_info.value)

    def test_list_templates_success(self, template_loader, temp_template_dir):
        """Test listing templates successfully."""
        with patch.object(template_loader, "discover_templates", return_value=[temp_template_dir / "test_template.yaml"]):
            templates = template_loader.list_templates()

        assert isinstance(templates, list)
        if templates:  # Only check if templates were found
            assert all(isinstance(t, dict) for t in templates)

    def test_list_templates_with_category_filter(self, template_loader, temp_template_dir):
        """Test listing templates with category filter."""
        template_files = [temp_template_dir / "test_template.yaml"]

        with patch.object(template_loader, "discover_templates", return_value=template_files):
            templates = template_loader.list_templates(category="test")

        assert isinstance(templates, list)

    def test_list_templates_empty(self, template_loader):
        """Test listing templates when none found."""
        with patch.object(template_loader, "discover_templates", return_value=[]):
            templates = template_loader.list_templates()

        assert templates == []

    def test_find_template_by_name_success(self, template_loader, temp_template_dir):
        """Test finding template by name successfully."""
        template_files = [temp_template_dir / "test_template.yaml"]

        with patch.object(template_loader, "discover_templates", return_value=template_files):
            template_path = template_loader.find_template_by_name("test_template")

        assert template_path is not None
        assert isinstance(template_path, Path)

    def test_find_template_by_name_not_found(self, template_loader):
        """Test finding nonexistent template by name."""
        with patch.object(template_loader, "discover_templates", return_value=[]):
            template_path = template_loader.find_template_by_name("nonexistent")

        assert template_path is None

    def test_validate_template_file_valid(self, template_loader, temp_template_dir):
        """Test validating valid template file."""
        template_path = temp_template_dir / "test_template.yaml"

        errors = template_loader.validate_template_file(template_path)

        assert isinstance(errors, list)

    def test_validate_template_file_not_found(self, template_loader):
        """Test validating nonexistent template file."""
        errors = template_loader.validate_template_file("/nonexistent/template.yaml")

        assert isinstance(errors, list)
        assert len(errors) > 0

    def test_validate_template_file_invalid_yaml(self, template_loader):
        """Test validating template with invalid YAML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: [")
            invalid_file = Path(f.name)

        errors = template_loader.validate_template_file(invalid_file)

        assert isinstance(errors, list)
        assert len(errors) > 0

    def test_get_template_categories(self, template_loader):
        """Test getting template categories."""
        with patch.object(template_loader, "list_templates", return_value=[
            {"category": "script"}, {"category": "library"}, {"category": "script"}
        ]):
            categories = template_loader.get_template_categories()

        assert isinstance(categories, list)
        assert "script" in categories
        assert "library" in categories

    def test_get_builtin_templates(self, template_loader):
        """Test getting builtin templates."""
        builtin_templates = template_loader.get_builtin_templates()

        assert isinstance(builtin_templates, list)

    def test_get_user_templates(self, template_loader):
        """Test getting user templates."""
        user_templates = template_loader.get_user_templates()

        assert isinstance(user_templates, list)

    def test_loader_configuration_setup(self, mock_config_manager):
        """Test that loader correctly sets up configuration."""
        loader = TemplateLoader(config_manager=mock_config_manager)

        assert hasattr(loader, "builtin_templates_dir")
        assert hasattr(loader, "user_templates_dir")
        assert hasattr(loader, "template_directories")

    def test_error_handling_graceful(self, template_loader):
        """Test that loader handles errors gracefully."""
        # Should not crash on nonexistent directories
        nonexistent = Path("/totally/nonexistent/path")
        yaml_files = template_loader._find_yaml_files(nonexistent)
        assert yaml_files == []

        # Should handle invalid paths gracefully
        try:
            template_loader.load_template_metadata("/invalid/path")
            assert False, "Should have raised an exception"
        except TemplateLoadError:
            pass  # Expected behavior


class TestTemplateLoaderIntegration:
    """Integration tests for template loader."""

    def test_real_config_integration(self):
        """Test template loader with real config manager."""
        loader = TemplateLoader()

        # Should initialize without error
        assert loader.config_manager is not None

        # Should be able to discover templates
        templates = loader.discover_templates()
        assert isinstance(templates, list)

    def test_builtin_templates_exist(self):
        """Test that builtin templates can be found."""
        loader = TemplateLoader()

        # Should find builtin templates
        builtin_templates = loader.get_builtin_templates()
        assert isinstance(builtin_templates, list)

        # If builtin templates exist, test loading them
        if builtin_templates:
            categories = loader.get_template_categories()
            assert isinstance(categories, list)
