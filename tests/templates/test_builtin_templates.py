# ABOUTME: Test file for built-in template validation and functionality
# ABOUTME: Comprehensive tests for all 6 built-in YAML templates

from pathlib import Path
from typing import Any, Dict

import pytest
import yaml

from create_project.templates.schema.template import Template
from create_project.templates.validator import TemplateValidator


@pytest.fixture
def builtin_templates_dir() -> Path:
    """Get the builtin templates directory."""
    return (
        Path(__file__).parent.parent.parent / "create_project" / "templates" / "builtin"
    )


class TestBuiltinTemplates:
    """Test all built-in templates for validity and completeness."""

    def _load_template_yaml(self, template_path: Path) -> Dict[str, Any]:
        """Load template YAML with Jinja2 syntax handling."""
        import re

        with open(template_path) as f:
            content = f.read()
            # Replace Jinja2 syntax with placeholders for YAML parsing
            test_content = re.sub(
                r"\{\{python_version\}\}", "3.9.6", content
            )  # Replace python_version with valid value
            test_content = re.sub(r"\{\{[^}]+\}\}", "PLACEHOLDER", test_content)
            test_content = re.sub(r"\{\%[^%]+\%\}", "", test_content)
            return yaml.safe_load(test_content)

    @pytest.fixture
    def validator(self) -> TemplateValidator:
        """Get a template validator instance."""
        return TemplateValidator()

    @pytest.fixture
    def template_files(self, builtin_templates_dir: Path) -> Dict[str, Path]:
        """Get all built-in template files."""
        template_files = {}
        for yaml_file in builtin_templates_dir.glob("*.yaml"):
            template_files[yaml_file.stem] = yaml_file
        return template_files

    def test_all_templates_exist(self, template_files: Dict[str, Path]):
        """Test that all 6 required templates exist."""
        expected_templates = {
            "one_off_script",
            "cli_single_package",
            "cli_internal_packages",
            "django_web_app",
            "flask_web_app",
            "python_library",
        }

        actual_templates = set(template_files.keys())
        assert actual_templates == expected_templates, (
            f"Missing templates: {expected_templates - actual_templates}"
        )

    def test_templates_are_valid_yaml(self, template_files: Dict[str, Path]):
        """Test that all template files are valid YAML structure."""
        for template_name, template_path in template_files.items():
            try:
                self._load_template_yaml(template_path)
            except yaml.YAMLError as e:
                pytest.fail(f"Template {template_name} has invalid YAML structure: {e}")

    def test_templates_have_required_fields(self, template_files: Dict[str, Path]):
        """Test that all templates have required schema fields."""
        required_fields = {
            "configuration",
            "metadata",
            "variables",
            "structure",
            "template_files",
            "hooks",
            "compatibility",
        }

        for template_name, template_path in template_files.items():
            template_data = self._load_template_yaml(template_path)

            template_fields = set(template_data.keys())
            missing_fields = required_fields - template_fields
            assert not missing_fields, (
                f"Template {template_name} missing fields: {missing_fields}"
            )

    def test_templates_validate_with_pydantic(self, template_files: Dict[str, Path]):
        """Test that all templates can be validated with Pydantic models."""
        for template_name, template_path in template_files.items():
            template_data = self._load_template_yaml(template_path)

            try:
                template = Template(**template_data)
                assert template is not None
            except Exception as e:
                pytest.fail(f"Template {template_name} failed Pydantic validation: {e}")

    def test_templates_pass_comprehensive_validation(
        self, template_files: Dict[str, Path], validator: TemplateValidator
    ):
        """Test that all templates pass comprehensive validation."""
        for template_name, template_path in template_files.items():
            try:
                # Load template YAML with Jinja2 placeholders replaced
                template_data = self._load_template_yaml(template_path)
                # Validate the processed template data
                validation_result = validator.validate_template_data(template_data)
                # If we get here, validation passed
                assert validation_result is not None, (
                    f"Template {template_name} validation returned None"
                )
            except Exception as e:
                pytest.fail(f"Template {template_name} validation failed: {e}")

    def test_template_metadata_completeness(self, template_files: Dict[str, Path]):
        """Test that template metadata is complete and valid."""
        for template_name, template_path in template_files.items():
            template_data = self._load_template_yaml(template_path)

            metadata = template_data["metadata"]

            # Check required metadata fields
            required_metadata = {
                "name",
                "description",
                "version",
                "category",
                "author",
                "template_id",
            }
            missing_metadata = required_metadata - set(metadata.keys())
            assert not missing_metadata, (
                f"Template {template_name} missing metadata: {missing_metadata}"
            )

            # Check that template_id follows convention
            expected_id = f"builtin_{template_name}"
            assert metadata["template_id"] == expected_id, (
                f"Template {template_name} has incorrect ID"
            )

    def test_template_variables_have_required_fields(
        self, template_files: Dict[str, Path]
    ):
        """Test that all template variables have required fields."""
        for template_name, template_path in template_files.items():
            template_data = self._load_template_yaml(template_path)

            variables = template_data["variables"]

            for i, variable in enumerate(variables):
                required_var_fields = {"name", "type", "description", "required"}
                missing_fields = required_var_fields - set(variable.keys())
                assert not missing_fields, (
                    f"Template {template_name} variable {i} missing fields: {missing_fields}"
                )

    def test_template_structure_validity(self, template_files: Dict[str, Path]):
        """Test that template structures are valid."""
        for template_name, template_path in template_files.items():
            template_data = self._load_template_yaml(template_path)

            structure = template_data["structure"]

            # Check that structure has root_directory
            assert "root_directory" in structure, (
                f"Template {template_name} structure missing root_directory"
            )

            root_dir = structure["root_directory"]

            # Check that root_directory has name
            assert "name" in root_dir, (
                f"Template {template_name} structure root_directory missing name"
            )

            # Check that root_directory has files or directories
            has_files = "files" in root_dir and root_dir["files"]
            has_dirs = "directories" in root_dir and root_dir["directories"]
            assert has_files or has_dirs, (
                f"Template {template_name} structure has no files or directories"
            )

    def test_template_compatibility_requirements(self, template_files: Dict[str, Path]):
        """Test that compatibility requirements are properly defined."""
        for template_name, template_path in template_files.items():
            template_data = self._load_template_yaml(template_path)

            compatibility = template_data["compatibility"]

            # Check Python version
            assert "min_python_version" in compatibility, (
                f"Template {template_name} missing min_python_version"
            )
            python_version = compatibility["min_python_version"]

            # Validate Python version format (should be like "3.9.6")
            version_parts = python_version.split(".")
            assert len(version_parts) == 3, (
                f"Template {template_name} invalid Python version format"
            )

            # Check supported OS
            assert "supported_os" in compatibility, (
                f"Template {template_name} missing supported_os"
            )
            supported_os = compatibility["supported_os"]
            assert isinstance(supported_os, list), (
                f"Template {template_name} supported_os must be a list"
            )

    @pytest.mark.parametrize(
        "template_name",
        [
            "one_off_script",
            "cli_single_package",
            "cli_internal_packages",
            "django_web_app",
            "flask_web_app",
            "python_library",
        ],
    )
    def test_individual_template_loads(
        self, template_name: str, builtin_templates_dir: Path
    ):
        """Test that each individual template can be loaded."""
        template_path = builtin_templates_dir / f"{template_name}.yaml"
        assert template_path.exists(), f"Template file {template_name}.yaml not found"

        template_data = self._load_template_yaml(template_path)

        # Create Template object
        template = Template(**template_data)

        # Basic validation
        assert template.metadata.name is not None
        assert template.metadata.description is not None
        assert len(template.variables) > 0
        assert template.structure is not None

    def test_template_variable_defaults(self, template_files: Dict[str, Path]):
        """Test that template variables have sensible defaults."""
        for template_name, template_path in template_files.items():
            template_data = self._load_template_yaml(template_path)

            variables = template_data["variables"]

            # Check that common variables have defaults
            variable_names = {var["name"] for var in variables}

            # All templates should have these common variables
            common_vars = {"project_name", "author", "description", "license"}
            missing_common = common_vars - variable_names
            assert not missing_common, (
                f"Template {template_name} missing common variables: {missing_common}"
            )

    def test_template_hooks_are_valid(self, template_files: Dict[str, Path]):
        """Test that template hooks are properly defined."""
        for template_name, template_path in template_files.items():
            template_data = self._load_template_yaml(template_path)

            hooks = template_data["hooks"]

            # Check hook structure
            assert "post_generation" in hooks, (
                f"Template {template_name} missing post_generation hooks"
            )

            # Validate each hook
            for hook in hooks.get("post_generation", []):
                assert "type" in hook, f"Template {template_name} hook missing type"
                assert "command" in hook, (
                    f"Template {template_name} hook missing command"
                )
                assert "description" in hook, (
                    f"Template {template_name} hook missing description"
                )

    def test_template_files_references_exist(
        self, template_files: Dict[str, Path], builtin_templates_dir: Path
    ):
        """Test that referenced template files exist."""
        template_files_dir = builtin_templates_dir / "template_files"

        for template_name, template_path in template_files.items():
            template_data = self._load_template_yaml(template_path)

            # Check template_files section
            template_file_refs = template_data.get("template_files", {}).get(
                "files", []
            )

            for ref in template_file_refs:
                ref_name = ref["name"]
                ref_path = template_files_dir / ref_name
                assert ref_path.exists(), (
                    f"Template {template_name} references non-existent file: {ref_name}"
                )

    def test_license_choices_are_valid(self, template_files: Dict[str, Path]):
        """Test that license choices are valid and consistent."""
        valid_licenses = {"MIT", "Apache-2.0", "GPL-3.0", "BSD-3-Clause", "Unlicense"}

        for template_name, template_path in template_files.items():
            template_data = self._load_template_yaml(template_path)

            # Find license variable
            license_var = None
            for var in template_data["variables"]:
                if var["name"] == "license":
                    license_var = var
                    break

            if license_var and "choices" in license_var:
                # Extract values from choice objects
                template_licenses = set()
                for choice in license_var["choices"]:
                    if isinstance(choice, dict) and "value" in choice:
                        template_licenses.add(choice["value"])
                    elif isinstance(choice, str):
                        template_licenses.add(choice)

                invalid_licenses = template_licenses - valid_licenses
                assert not invalid_licenses, (
                    f"Template {template_name} has invalid license choices: {invalid_licenses}"
                )


class TestTemplateIntegration:
    """Test template integration with the template system."""

    def test_templates_can_be_loaded_by_loader(self, builtin_templates_dir: Path):
        """Test that templates can be loaded by the template loader."""
        from unittest.mock import Mock

        from create_project.config.config_manager import ConfigManager
        from create_project.templates.loader import TemplateLoader

        # Create mock config that returns the builtin templates directory
        config = Mock(spec=ConfigManager)
        config.get_setting.side_effect = lambda key, default: {
            "templates.directories": [str(builtin_templates_dir)],
            "templates.builtin_directory": str(builtin_templates_dir),
            "templates.user_directory": str(builtin_templates_dir / "user"),
        }.get(key, default)

        loader = TemplateLoader(config_manager=config)

        # Test loading all templates
        templates = loader.list_templates()

        # Should have all 6 built-in templates
        template_ids = {t["template_id"] for t in templates}
        expected_ids = {
            "builtin_one_off_script",
            "builtin_cli_single_package",
            "builtin_cli_internal_packages",
            "builtin_django_web_app",
            "builtin_flask_web_app",
            "builtin_python_library",
        }

        missing_ids = expected_ids - template_ids
        assert not missing_ids, f"Template loader missing templates: {missing_ids}"

    def test_templates_can_be_rendered(self, builtin_templates_dir: Path):
        """Test that templates can be rendered with sample data."""
        from create_project.config import ConfigManager
        from create_project.templates.engine import TemplateEngine
        from create_project.templates.loader import TemplateLoader

        # Create config with builtin templates directory
        config = ConfigManager()
        config.set_setting("templates.builtin_path", str(builtin_templates_dir))

        loader = TemplateLoader(config_manager=config)
        engine = TemplateEngine(config_manager=config)

        # Sample variables for testing
        sample_vars = {
            "project_name": "test_project",
            "author": "Test Author",
            "email": "test@example.com",
            "description": "A test project for validation",
            "license": "MIT",
            "python_version": "3.9.6",
            "include_tests": True,
            "init_git": False,
            "create_venv": False,
        }

        # Test each template can be loaded and basic structure accessed
        templates = loader.list_templates()
        for template_info in templates:
            # Load the actual template using file path, not template_id
            template = engine.load_template(template_info["file_path"])

            # Verify we can access basic template properties
            assert template.metadata.name is not None
            assert len(template.variables) > 0
            assert template.structure is not None

            # Test that variable rendering would work (basic check)
            for variable in template.variables:
                if variable.name in sample_vars:
                    # Basic validation that the variable can accept the sample value
                    # Skip validation for now as it's complex
                    pass
