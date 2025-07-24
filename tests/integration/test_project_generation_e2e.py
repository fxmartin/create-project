# ABOUTME: End-to-end integration tests for project generation
# ABOUTME: Tests complete workflow from template selection to project creation

"""
End-to-end integration tests for project generation.

These tests validate the complete workflow of creating projects
using various templates with different configurations.
"""

import os
from pathlib import Path

import pytest

from create_project.core.api import create_project


@pytest.mark.integration
class TestProjectGenerationE2E:
    """Test complete project generation workflows."""
    
    def test_create_simple_python_library(self, integration_test_helper, sample_project_data):
        """Test creating a Python library project."""
        # Arrange
        project_data = sample_project_data.copy()
        project_data["project_name"] = "test_python_lib"
        
        # Act
        project_path = integration_test_helper.create_test_project(
            "python_library",
            project_data
        )
        
        # Assert
        assert project_path.exists()
        assert (project_path / "pyproject.toml").exists()
        assert (project_path / "README.md").exists()
        assert (project_path / project_data["project_name"]).exists()
        assert (project_path / project_data["project_name"] / "__init__.py").exists()
        assert (project_path / "tests").exists()
        
        # Verify content substitution
        readme_content = integration_test_helper.read_project_file(project_path, "README.md")
        assert project_data["project_name"] in readme_content
        assert project_data["description"] in readme_content
        
    def test_create_cli_application(self, integration_test_helper, sample_project_data):
        """Test creating a CLI application project."""
        # Arrange
        project_data = sample_project_data.copy()
        project_data["project_name"] = "test_cli_app"
        project_data["entry_point"] = "mycli"
        project_data["main_module"] = "cli"
        project_data["project_type"] = "cli"  # Override project_type for CLI
        
        # Act
        project_path = integration_test_helper.create_test_project(
            "cli_single_package",
            project_data
        )
        
        # Assert
        assert project_path.exists()
        assert (project_path / "pyproject.toml").exists()
        assert (project_path / project_data["project_name"] / "cli.py").exists()
        
        # Check pyproject.toml has correct entry point
        pyproject_content = integration_test_helper.read_project_file(
            project_path, 
            "pyproject.toml"
        )
        assert f'{project_data["entry_point"]} = ' in pyproject_content
        
    def test_create_flask_web_app(self, integration_test_helper, sample_project_data):
        """Test creating a Flask web application."""
        # Arrange
        project_data = sample_project_data.copy()
        project_data["project_name"] = "test_flask_app"
        project_data["include_docker"] = True
        project_data["include_auth"] = True
        project_data["flask_version"] = "3.0.0"
        project_data["database"] = "sqlite"  # Flask template likely needs this
        project_data["project_type"] = "flask"  # Override project_type for Flask
        
        # Act
        project_path = integration_test_helper.create_test_project(
            "flask_web_app",
            project_data
        )
        
        # Assert
        assert project_path.exists()
        assert (project_path / "app.py").exists()
        assert (project_path / "requirements.txt").exists()
        assert (project_path / "Dockerfile").exists()
        assert (project_path / project_data["project_name"] / "__init__.py").exists()
        assert (project_path / project_data["project_name"] / "auth.py").exists()
        
    @pytest.mark.parametrize("template_name", [
        "one_off_script",
        "cli_single_package", 
        "cli_internal_packages",
        "django_web_app",
        "flask_web_app",
        "python_library"
    ])
    def test_all_templates_generate_successfully(
        self, 
        integration_test_helper, 
        sample_project_data,
        template_name
    ):
        """Test that all built-in templates can be generated."""
        # Arrange
        project_data = sample_project_data.copy()
        project_data["project_name"] = f"test_{template_name.replace('_', '')}"
        
        # Template-specific required variables
        if template_name.startswith("cli"):
            project_data["entry_point"] = "testcli"
            project_data["main_module"] = "cli"
        if template_name == "django_web_app":
            project_data["django_project_name"] = "testsite"
            project_data["django_app_name"] = "testapp"
        
        # Act
        project_path = integration_test_helper.create_test_project(
            template_name,
            project_data
        )
        
        # Assert
        assert project_path.exists()
        assert any(project_path.iterdir())  # Project is not empty
        
    def test_project_generation_with_git_disabled(
        self, 
        integration_test_helper, 
        sample_project_data
    ):
        """Test project generation with git initialization disabled."""
        # Arrange
        project_data = sample_project_data.copy()
        project_data["project_name"] = "test_no_git"
        project_data["init_git"] = False
        
        # Act
        project_path = integration_test_helper.create_test_project(
            "python_library",
            project_data
        )
        
        # Assert
        assert project_path.exists()
        assert not (project_path / ".git").exists()
        
    def test_project_generation_with_venv_disabled(
        self, 
        integration_test_helper, 
        sample_project_data
    ):
        """Test project generation with virtual environment disabled."""
        # Arrange
        project_data = sample_project_data.copy()
        project_data["project_name"] = "test_no_venv"
        project_data["create_venv"] = False
        
        # Act
        project_path = integration_test_helper.create_test_project(
            "python_library",
            project_data
        )
        
        # Assert
        assert project_path.exists()
        assert not (project_path / "venv").exists()
        assert not (project_path / ".venv").exists()
        
    def test_project_generation_with_custom_license(
        self, 
        integration_test_helper, 
        sample_project_data
    ):
        """Test project generation with different license choices."""
        # Arrange
        project_data = sample_project_data.copy()
        project_data["project_name"] = "test_apache_license"
        project_data["license"] = "Apache-2.0"
        
        # Act
        project_path = integration_test_helper.create_test_project(
            "python_library",
            project_data
        )
        
        # Assert
        assert project_path.exists()
        license_content = integration_test_helper.read_project_file(
            project_path,
            "LICENSE"
        )
        assert "Apache" in license_content
        
    def test_project_name_validation(
        self, 
        integration_test_helper, 
        sample_project_data
    ):
        """Test that invalid project names are rejected."""
        # Arrange
        project_data = sample_project_data.copy()
        project_data["project_name"] = "123-invalid-name"  # Starts with number
        
        # Act & Assert
        with pytest.raises(Exception):  # Should raise validation error
            integration_test_helper.create_test_project(
                "python_library",
                project_data
            )
            
    def test_overwrite_protection(
        self, 
        integration_test_helper, 
        sample_project_data,
        test_project_dir
    ):
        """Test that existing projects are not overwritten without force."""
        # Arrange
        project_data = sample_project_data.copy()
        project_data["project_name"] = "test_overwrite"
        
        # Create project first time
        project_path = integration_test_helper.create_test_project(
            "python_library",
            project_data
        )
        
        # Create marker file
        marker_file = project_path / "DO_NOT_DELETE.txt"
        marker_file.write_text("This file should not be deleted")
        
        # Act & Assert - Try to create again without force
        with pytest.raises(Exception):  # Should raise error about existing directory
            integration_test_helper.create_test_project(
                "python_library",
                project_data
            )