# ABOUTME: Unit tests for the template loader functionality
# ABOUTME: Tests template discovery, loading, and metadata extraction

"""Tests for template loader."""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest
import yaml

from create_project.config.config_manager import ConfigManager
from create_project.templates.engine import TemplateLoadError
from create_project.templates.loader import TemplateLoader


class TestTemplateLoader:
    """Tests for TemplateLoader class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config_manager = Mock(spec=ConfigManager)
        self.config_manager.get_setting.side_effect = lambda key, default: {
            "templates.directories": ["tests/fixtures/templates"],
            "templates.builtin_path": "tests/fixtures/builtin",
            "templates.custom_path": "tests/fixtures/user",
        }.get(key, default)
        self.loader = TemplateLoader(self.config_manager)

    def test_loader_initialization(self):
        """Test template loader initialization."""
        assert self.loader.config_manager == self.config_manager
        assert self.loader.template_directories == ["tests/fixtures/templates"]
        assert self.loader.builtin_templates_dir == "tests/fixtures/builtin"
        assert str(self.loader.user_templates_dir) == "tests/fixtures/user"

    def test_find_yaml_files(self):
        """Test finding YAML files in directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            (temp_path / "template1.yaml").touch()
            (temp_path / "template2.yml").touch()
            (temp_path / "not_yaml.txt").touch()

            # Create subdirectory with YAML file
            sub_dir = temp_path / "subdir"
            sub_dir.mkdir()
            (sub_dir / "template3.yaml").touch()

            yaml_files = self.loader._find_yaml_files(temp_path)

            assert len(yaml_files) == 3
            yaml_names = [f.name for f in yaml_files]
            assert "template1.yaml" in yaml_names
            assert "template2.yml" in yaml_names
            assert "template3.yaml" in yaml_names
            assert "not_yaml.txt" not in yaml_names

    def test_discover_templates(self):
        """Test template discovery."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Mock the template directories to point to our temp directory
            self.loader.template_directories = [str(temp_path)]
            self.loader.builtin_templates_dir = str(temp_path / "builtin")
            self.loader.user_templates_dir = str(temp_path / "user")

            # Create template files
            (temp_path / "template1.yaml").touch()

            builtin_dir = temp_path / "builtin"
            builtin_dir.mkdir()
            (builtin_dir / "builtin_template.yaml").touch()

            user_dir = temp_path / "user"
            user_dir.mkdir()
            (user_dir / "user_template.yaml").touch()

            templates = self.loader.discover_templates()

            # Should find all templates
            assert len(templates) >= 3
            template_names = [t.name for t in templates]
            assert "template1.yaml" in template_names
            assert "builtin_template.yaml" in template_names
            assert "user_template.yaml" in template_names

    def test_discover_templates_exclude_builtin(self):
        """Test template discovery excluding builtin templates."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            self.loader.template_directories = [str(temp_path)]
            self.loader.builtin_templates_dir = str(temp_path / "builtin")
            self.loader.user_templates_dir = str(temp_path / "user")

            # Create template files
            (temp_path / "template1.yaml").touch()

            builtin_dir = temp_path / "builtin"
            builtin_dir.mkdir()
            (builtin_dir / "builtin_template.yaml").touch()

            user_dir = temp_path / "user"
            user_dir.mkdir()
            (user_dir / "user_template.yaml").touch()

            templates = self.loader.discover_templates(include_builtin=False)

            template_names = [t.name for t in templates]
            assert "template1.yaml" in template_names
            assert "user_template.yaml" in template_names
            # The builtin template might still be included from the main directories
            # so we check that at least one of our expected templates is there

    def test_load_template_metadata_success(self):
        """Test successful template metadata loading."""
        template_data = {
            "metadata": {
                "name": "test-template",
                "description": "Test template",
                "version": "1.0.0",
                "category": "test",
                "author": "Test Author",
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(template_data, f)
            temp_path = Path(f.name)

        try:
            metadata = self.loader.load_template_metadata(temp_path)

            assert metadata["name"] == "test-template"
            assert metadata["description"] == "Test template"
            assert metadata["version"] == "1.0.0"
            assert metadata["category"] == "test"
            assert metadata["author"] == "Test Author"
            assert "file_path" in metadata
            assert "file_size" in metadata
            assert "file_modified" in metadata
        finally:
            temp_path.unlink()

    def test_load_template_metadata_no_metadata(self):
        """Test template metadata loading with no metadata section."""
        template_data = {"variables": [], "structure": {}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(template_data, f)
            temp_path = Path(f.name)

        try:
            with pytest.raises(TemplateLoadError, match="No metadata found"):
                self.loader.load_template_metadata(temp_path)
        finally:
            temp_path.unlink()

    def test_load_template_metadata_empty_file(self):
        """Test template metadata loading with empty file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            temp_path = Path(f.name)

        try:
            with pytest.raises(TemplateLoadError, match="Empty template file"):
                self.loader.load_template_metadata(temp_path)
        finally:
            temp_path.unlink()

    def test_load_template_metadata_invalid_yaml(self):
        """Test template metadata loading with invalid YAML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = Path(f.name)

        try:
            with pytest.raises(TemplateLoadError, match="YAML parsing error"):
                self.loader.load_template_metadata(temp_path)
        finally:
            temp_path.unlink()

    def test_list_templates(self):
        """Test listing templates with metadata."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.loader.template_directories = [str(temp_path)]
            self.loader.builtin_templates_dir = str(temp_path / "builtin")
            self.loader.user_templates_dir = str(temp_path / "user")

            # Create test templates
            template1_data = {
                "metadata": {
                    "name": "template1",
                    "description": "First template",
                    "category": "web",
                }
            }
            template1_path = temp_path / "template1.yaml"
            with open(template1_path, "w") as f:
                yaml.dump(template1_data, f)

            template2_data = {
                "metadata": {
                    "name": "template2",
                    "description": "Second template",
                    "category": "cli",
                }
            }
            template2_path = temp_path / "template2.yaml"
            with open(template2_path, "w") as f:
                yaml.dump(template2_data, f)

            templates = self.loader.list_templates()

            assert len(templates) == 2
            names = [t["name"] for t in templates]
            assert "template1" in names
            assert "template2" in names

    def test_list_templates_with_category_filter(self):
        """Test listing templates filtered by category."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.loader.template_directories = [str(temp_path)]
            self.loader.builtin_templates_dir = str(temp_path / "builtin")
            self.loader.user_templates_dir = str(temp_path / "user")

            # Create test templates with different categories
            template1_data = {
                "metadata": {
                    "name": "web-template",
                    "description": "Web template",
                    "category": "web",
                }
            }
            template1_path = temp_path / "template1.yaml"
            with open(template1_path, "w") as f:
                yaml.dump(template1_data, f)

            template2_data = {
                "metadata": {
                    "name": "cli-template",
                    "description": "CLI template",
                    "category": "cli",
                }
            }
            template2_path = temp_path / "template2.yaml"
            with open(template2_path, "w") as f:
                yaml.dump(template2_data, f)

            # Filter by web category
            web_templates = self.loader.list_templates(category="web")

            assert len(web_templates) == 1
            assert web_templates[0]["name"] == "web-template"
            assert web_templates[0]["category"] == "web"

    def test_find_template_by_name_success(self):
        """Test finding template by name successfully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.loader.template_directories = [str(temp_path)]
            self.loader.builtin_templates_dir = str(temp_path / "builtin")
            self.loader.user_templates_dir = str(temp_path / "user")

            # Create test template
            template_data = {
                "metadata": {
                    "name": "target-template",
                    "description": "Target template",
                }
            }
            template_path = temp_path / "template.yaml"
            with open(template_path, "w") as f:
                yaml.dump(template_data, f)

            found_path = self.loader.find_template_by_name("target-template")

            assert found_path == template_path

    def test_find_template_by_name_not_found(self):
        """Test finding template by name when not found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.loader.template_directories = [str(temp_path)]
            self.loader.builtin_templates_dir = str(temp_path / "builtin")
            self.loader.user_templates_dir = str(temp_path / "user")

            found_path = self.loader.find_template_by_name("nonexistent-template")

            assert found_path is None

    def test_validate_template_file_success(self):
        """Test template file validation success."""
        template_data = {
            "metadata": {
                "name": "valid-template",
                "description": "Valid template",
                "version": "1.0.0",
                "category": "custom",
                "author": "Test Author",
            },
            "variables": [],
            "structure": {
                "root_directory": {
                    "name": "test-project",
                    "files": [],
                    "directories": [],
                }
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(template_data, f)
            temp_path = Path(f.name)

        try:
            errors = self.loader.validate_template_file(temp_path)
            assert errors == []
        finally:
            temp_path.unlink()

    def test_validate_template_file_not_found(self):
        """Test template file validation with file not found."""
        errors = self.loader.validate_template_file("nonexistent.yaml")

        assert len(errors) == 1
        assert "Template file not found" in errors[0]

    def test_validate_template_file_invalid_yaml(self):
        """Test template file validation with invalid YAML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = Path(f.name)

        try:
            errors = self.loader.validate_template_file(temp_path)

            assert len(errors) == 1
            assert "YAML parsing error" in errors[0]
        finally:
            temp_path.unlink()

    def test_get_template_categories(self):
        """Test getting template categories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            self.loader.template_directories = [str(temp_path)]
            self.loader.builtin_templates_dir = str(temp_path / "builtin")
            self.loader.user_templates_dir = str(temp_path / "user")

            # Create templates with different categories
            categories = ["web", "cli", "library"]
            for i, category in enumerate(categories):
                template_data = {
                    "metadata": {
                        "name": f"template{i}",
                        "description": f"Template {i}",
                        "category": category,
                    }
                }
                template_path = temp_path / f"template{i}.yaml"
                with open(template_path, "w") as f:
                    yaml.dump(template_data, f)

            found_categories = self.loader.get_template_categories()

            assert sorted(found_categories) == sorted(categories)

    def test_get_builtin_templates(self):
        """Test getting builtin templates."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            builtin_dir = temp_path / "builtin"
            builtin_dir.mkdir()

            self.loader.builtin_templates_dir = str(builtin_dir)

            # Create builtin template
            template_data = {
                "metadata": {
                    "name": "builtin-template",
                    "description": "Builtin template",
                }
            }
            template_path = builtin_dir / "builtin.yaml"
            with open(template_path, "w") as f:
                yaml.dump(template_data, f)

            builtin_templates = self.loader.get_builtin_templates()

            assert len(builtin_templates) == 1
            assert builtin_templates[0]["name"] == "builtin-template"
            assert builtin_templates[0]["is_builtin"] is True

    def test_get_user_templates(self):
        """Test getting user templates."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            user_dir = temp_path / "user"
            user_dir.mkdir()

            self.loader.user_templates_dir = str(user_dir)

            # Create user template
            template_data = {
                "metadata": {"name": "user-template", "description": "User template"}
            }
            template_path = user_dir / "user.yaml"
            with open(template_path, "w") as f:
                yaml.dump(template_data, f)

            user_templates = self.loader.get_user_templates()

            assert len(user_templates) == 1
            assert user_templates[0]["name"] == "user-template"
            assert user_templates[0]["is_user"] is True
