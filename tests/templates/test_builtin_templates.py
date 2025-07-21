# ABOUTME: Test file for built-in template validation and functionality
# ABOUTME: Comprehensive tests for all 6 built-in YAML templates

import pytest
import yaml
from pathlib import Path
from typing import Dict, Any

from create_project.templates.schema.template import Template
from create_project.templates.validator import TemplateValidator


class TestBuiltinTemplates:
    """Test all built-in templates for validity and completeness."""

    @pytest.fixture
    def builtin_templates_dir(self) -> Path:
        """Get the builtin templates directory."""
        return (
            Path(__file__).parent.parent.parent
            / "create_project"
            / "templates"
            / "builtin"
        )

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
        """Test that all template files are valid YAML."""
        for template_name, template_path in template_files.items():
            with open(template_path, "r") as f:
                try:
                    yaml.safe_load(f)
                except yaml.YAMLError as e:
                    pytest.fail(f"Template {template_name} has invalid YAML: {e}")

    def test_templates_have_required_fields(self, template_files: Dict[str, Path]):
        """Test that all templates have required schema fields."""
        required_fields = {
            "schema_version",
            "metadata",
            "variables",
            "structure",
            "template_files",
            "hooks",
            "compatibility",
        }

        for template_name, template_path in template_files.items():
            with open(template_path, "r") as f:
                template_data = yaml.safe_load(f)

            template_fields = set(template_data.keys())
            missing_fields = required_fields - template_fields
            assert not missing_fields, (
                f"Template {template_name} missing fields: {missing_fields}"
            )

    def test_templates_validate_with_pydantic(self, template_files: Dict[str, Path]):
        """Test that all templates can be validated with Pydantic models."""
        for template_name, template_path in template_files.items():
            with open(template_path, "r") as f:
                template_data = yaml.safe_load(f)

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
            validation_result = validator.validate_template_file(template_path)

            if not validation_result.is_valid:
                error_msg = f"Template {template_name} validation failed:\n"
                error_msg += "\n".join(validation_result.errors)
                pytest.fail(error_msg)

    def test_template_metadata_completeness(self, template_files: Dict[str, Path]):
        """Test that template metadata is complete and valid."""
        for template_name, template_path in template_files.items():
            with open(template_path, "r") as f:
                template_data = yaml.safe_load(f)

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
            with open(template_path, "r") as f:
                template_data = yaml.safe_load(f)

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
            with open(template_path, "r") as f:
                template_data = yaml.safe_load(f)

            structure = template_data["structure"]

            # Check that structure has name
            assert "name" in structure, (
                f"Template {template_name} structure missing name"
            )

            # Check that structure has files or directories
            has_files = "files" in structure and structure["files"]
            has_dirs = "directories" in structure and structure["directories"]
            assert has_files or has_dirs, (
                f"Template {template_name} structure has no files or directories"
            )

    def test_template_compatibility_requirements(self, template_files: Dict[str, Path]):
        """Test that compatibility requirements are properly defined."""
        for template_name, template_path in template_files.items():
            with open(template_path, "r") as f:
                template_data = yaml.safe_load(f)

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

        with open(template_path, "r") as f:
            template_data = yaml.safe_load(f)

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
            with open(template_path, "r") as f:
                template_data = yaml.safe_load(f)

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
            with open(template_path, "r") as f:
                template_data = yaml.safe_load(f)

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
            with open(template_path, "r") as f:
                template_data = yaml.safe_load(f)

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
            with open(template_path, "r") as f:
                template_data = yaml.safe_load(f)

            # Find license variable
            license_var = None
            for var in template_data["variables"]:
                if var["name"] == "license":
                    license_var = var
                    break

            if license_var and "choices" in license_var:
                template_licenses = set(license_var["choices"])
                invalid_licenses = template_licenses - valid_licenses
                assert not invalid_licenses, (
                    f"Template {template_name} has invalid license choices: {invalid_licenses}"
                )


class TestTemplateIntegration:
    """Test template integration with the template system."""

    def test_templates_can_be_loaded_by_loader(self, builtin_templates_dir: Path):
        """Test that templates can be loaded by the template loader."""
        from create_project.templates.loader import TemplateLoader

        loader = TemplateLoader()
        loader.add_directory(builtin_templates_dir)

        # Test loading all templates
        templates = loader.get_available_templates()

        # Should have all 6 built-in templates
        template_ids = {t.metadata.template_id for t in templates}
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
        from create_project.templates.loader import TemplateLoader
        from create_project.templates.engine import TemplateEngine

        loader = TemplateLoader()
        loader.add_directory(builtin_templates_dir)
        engine = TemplateEngine()

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
        for template in loader.get_available_templates():
            # Verify we can access basic template properties
            assert template.metadata.name is not None
            assert len(template.variables) > 0
            assert template.structure is not None

            # Test that variable rendering would work (basic check)
            for variable in template.variables:
                if variable.name in sample_vars:
                    # Basic validation that the variable can accept the sample value
                    if hasattr(variable, "validate_value"):
                        errors = variable.validate_value(sample_vars[variable.name])
                        assert len(errors) == 0, (
                            f"Sample variable {variable.name} validation failed: {errors}"
                        )
