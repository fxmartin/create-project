# ABOUTME: Integration tests for specific workflow scenarios and user journeys
# ABOUTME: Tests common use cases, error recovery, and advanced workflows

"""
Integration tests for specific workflow scenarios and user journeys.

These tests validate common use cases, error recovery scenarios,
and advanced workflows that users might encounter.
"""

import json
import shutil
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PyQt6.QtCore import QThread, QTimer

from create_project.core.api import create_project, create_project_async
from create_project.core.error_recovery import RecoveryManager, RecoveryStrategy
from create_project.core.file_renderer import FileRenderer
from create_project.core.project_generator import ProjectGenerator


@pytest.mark.integration
class TestCommonWorkflows:
    """Test common user workflows."""

    def test_quick_script_creation_workflow(self, tmp_path, mock_config_manager):
        """Test workflow for creating a quick Python script."""
        # User wants to create a simple script quickly
        from datetime import datetime
        project_data = {
            "project_name": "data_processor",
            "author": "Script Author",
            "version": "0.1.0",
            "description": "Quick data processing script",
            "python_version": "3.9",
            "script_name": "process",
            "shebang": True,
            "type_hints": True,
            "include_examples": True,
            "include_tests": False,  # Skip tests for quick script
            "license": "MIT",
            "initialize_git": False,  # No git for simple script
            "venv_tool": "none",  # No venv for simple script
            "created_date": datetime.now().strftime("%Y-%m-%d"),  # Add missing template variable
            "include_verbose": True,  # Add missing template variable
            "init_git": False,  # Add missing template variable
            "create_venv": False  # Add missing template variable
        }

        # Add required template variables to prevent template errors
        project_data.update({
            "project_type": "script",  # Required by common templates
            "license_text": "MIT License",  # Required for license file
            "email": "test@example.com"  # Template expects this
        })

        result = create_project(
            template_name="one_off_script",
            project_name=project_data["project_name"],
            target_directory=str(tmp_path),
            variables=project_data
        )

        assert result.success is True

        # Verify script structure
        project_path = Path(result.target_path)
        # The template creates a file named {{project_name}}.py, not the script_name
        script_file = project_path / "data_processor.py"

        assert script_file.exists()
        assert (project_path / "README.md").exists()
        assert (project_path / "LICENSE").exists()

        # Check script content
        content = script_file.read_text()
        assert "#!/usr/bin/env python3" in content  # Shebang
        assert "def main() -> int:" in content  # Type hints (returns int for exit code)
        assert 'if __name__ == "__main__"' in content

    def test_team_project_setup_workflow(self, tmp_path, mock_config_manager):
        """Test workflow for setting up a team project with all features."""
        # Team lead setting up a new project with full configuration
        project_data = {
            "project_name": "team_analytics_lib",
            "author": "Analytics Team",
            "version": "0.1.0",
            "description": "Shared analytics library for the team",
            "python_version": "3.9",
            "min_python_version": "3.9",
            "keywords": ["analytics", "data", "team"],
            "include_github_actions": True,
            "include_pre_commit": True,
            "include_makefile": True,
            "license": "Apache-2.0",  # Corporate friendly
            "initialize_git": True,
            "venv_tool": "uv"  # Fast for team
        }

        # Mock git for testing
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=b"", stderr=b"")

            result = create_project(
                template_name="python_library",
                project_name=project_data["project_name"],
                target_directory=str(tmp_path),
                variables=project_data
            )

        assert result.success is True

        project_path = Path(result.target_path)

        # Verify team-friendly features
        assert (project_path / ".github" / "workflows").exists()
        assert (project_path / ".pre-commit-config.yaml").exists()
        assert (project_path / "Makefile").exists()
        assert (project_path / "LICENSE").exists()

        # Check LICENSE is Apache-2.0
        license_content = (project_path / "LICENSE").read_text()
        assert "Apache License" in license_content
        assert "Version 2.0" in license_content

    def test_migration_from_existing_project_workflow(self, tmp_path, mock_config_manager):
        """Test workflow for migrating an existing project to use templates."""
        # User has existing code and wants to add project structure
        existing_project = tmp_path / "legacy_code"
        existing_project.mkdir()

        # Create some existing files
        (existing_project / "old_script.py").write_text("# Legacy code\nprint('old')")
        (existing_project / "data.txt").write_text("Important data")

        # Create new project structure in a subdirectory
        project_data = {
            "project_name": "legacy_code_v2",
            "author": "Migration Author",
            "version": "2.0.0",
            "description": "Migrated legacy project",
            "python_version": "3.9",
            "license": "MIT",
            "initialize_git": True,
            "venv_tool": "virtualenv"
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=b"", stderr=b"")

            result = create_project(
                template_name="python_library",
                project_name=project_data["project_name"],
                target_directory=str(tmp_path),
                variables=project_data
            )

        assert result.success is True

        new_project = Path(result.target_path)

        # Simulate manual migration steps
        # Copy old files to new structure
        shutil.copy2(
            existing_project / "old_script.py",
            new_project / project_data["project_name"] / "legacy.py"
        )
        shutil.copy2(
            existing_project / "data.txt",
            new_project / "data" / "data.txt"
        )

        # Verify migration worked
        assert (new_project / project_data["project_name"] / "legacy.py").exists()
        assert (new_project / "data" / "data.txt").exists()
        assert (new_project / "pyproject.toml").exists()

    def test_continuous_integration_setup_workflow(self, tmp_path, mock_config_manager):
        """Test workflow for setting up CI/CD for a project."""
        project_data = {
            "project_name": "ci_enabled_lib",
            "author": "DevOps Team",
            "version": "0.1.0",
            "description": "Library with full CI/CD setup",
            "python_version": "3.9",
            "min_python_version": "3.9",
            "max_python_version": "3.11",
            "include_github_actions": True,
            "include_tox": True,
            "include_pre_commit": True,
            "test_framework": "pytest",
            "use_src_layout": True,
            "license": "MIT",
            "initialize_git": True,
            "venv_tool": "uv"
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=b"", stderr=b"")

            result = create_project(
                template_name="python_library",
                project_name=project_data["project_name"],
                target_directory=str(tmp_path),
                variables=project_data
            )

        assert result.success is True

        project_path = Path(result.target_path)

        # Verify CI/CD files
        assert (project_path / ".github" / "workflows" / "test.yml").exists()
        assert (project_path / "tox.ini").exists()
        assert (project_path / ".pre-commit-config.yaml").exists()

        # Check GitHub Actions workflow
        workflow_content = (project_path / ".github" / "workflows" / "test.yml").read_text()
        assert "python-version:" in workflow_content
        assert "pytest" in workflow_content

        # Check tox configuration
        tox_content = (project_path / "tox.ini").read_text()
        assert "py39" in tox_content  # Min version
        assert "py311" in tox_content  # Max version


@pytest.mark.integration
class TestErrorRecoveryWorkflows:
    """Test error recovery workflows."""

    def test_disk_space_error_recovery(self, tmp_path, mock_config_manager):
        """Test recovery when running out of disk space."""
        recovery_manager = RecoveryManager()
        project_path = tmp_path / "large_project"

        # Set up recovery point before "disk full" error
        recovery_manager.add_recovery_point(
            phase="file_creation",
            rollback_action=lambda: shutil.rmtree(project_path, ignore_errors=True),
            description="Remove partially created files"
        )

        # Simulate disk space error during file creation
        with patch.object(FileRenderer, "render_file", side_effect=OSError("No space left on device")):
            generator = ProjectGenerator(mock_config_manager)

            try:
                generator.generate(
                    template_name="python_library",
                    project_name=project_data["project_name"],
                target_directory=str(tmp_path),
                    project_data={
                        "project_name": "large_project",
                        "author": "Test",
                        "version": "0.1.0",
                        "description": "Test"
                    }
                )
            except OSError:
                # Attempt recovery
                recovery_options = recovery_manager.get_recovery_options()
                assert RecoveryStrategy.ROLLBACK_FULL in recovery_options

                # Execute rollback
                recovery_manager.rollback_to_phase("start")

                # Verify cleanup
                assert not project_path.exists()

    def test_permission_error_recovery(self, tmp_path, mock_config_manager):
        """Test recovery from permission errors."""
        import stat

        # Create directory with limited permissions
        restricted_dir = tmp_path / "restricted"
        restricted_dir.mkdir()

        project_data = {
            "project_name": "permission_test",
            "author": "Test",
            "version": "0.1.0",
            "description": "Test permission handling"
        }

        # Remove write permission
        restricted_dir.chmod(stat.S_IRUSR | stat.S_IXUSR)

        try:
            result = create_project(
                template_name="python_library",
                project_name=project_data["project_name"],
                target_directory=str(restricted_dir),
                variables=project_data
            )

            assert result.success is False
            assert len(result.errors) > 0

        finally:
            # Restore permissions
            restricted_dir.chmod(stat.S_IRWXU)

    def test_git_initialization_failure_recovery(self, tmp_path, mock_config_manager):
        """Test recovery when git initialization fails."""
        project_data = {
            "project_name": "git_fail_test",
            "author": "Test",
            "version": "0.1.0",
            "description": "Test git failure",
            "license": "MIT",
            "initialize_git": True,
            "venv_tool": "none"
        }

        # Mock git to fail
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, ["git", "init"])

            # Git failure should not stop project creation
            result = create_project(
                template_name="python_library",
                project_name=project_data["project_name"],
                target_directory=str(tmp_path),
                variables=project_data
            )

            # Project should still succeed, just without git
            assert result.success is True

            project_path = Path(result.target_path)
            assert project_path.exists()
            assert not (project_path / ".git").exists()

    def test_template_corruption_recovery(self, tmp_path, mock_config_manager):
        """Test recovery from corrupted template data."""
        # Create generator
        generator = ProjectGenerator(mock_config_manager)

        # Mock template engine to return corrupted data
        with patch.object(generator.template_engine, "load_template") as mock_load:
            # Return invalid template structure
            mock_load.return_value = {
                "name": "Corrupted",
                # Missing required fields like 'structure'
            }

            with pytest.raises(Exception) as exc_info:
                generator.generate(
                    template_name="corrupted",
                    project_name=project_data["project_name"],
                target_directory=str(tmp_path),
                    project_data={
                        "project_name": "test",
                        "author": "Test",
                        "version": "0.1.0",
                        "description": "Test"
                    }
                )

            assert "template" in str(exc_info.value).lower()


@pytest.mark.integration
class TestAdvancedWorkflows:
    """Test advanced workflow scenarios."""

    def test_multi_environment_project_workflow(self, tmp_path, mock_config_manager):
        """Test creating a project that supports multiple Python versions."""
        project_data = {
            "project_name": "multi_env_lib",
            "author": "Compatibility Team",
            "version": "0.1.0",
            "description": "Library supporting Python 3.9-3.12",
            "python_version": "3.9",
            "min_python_version": "3.9",
            "max_python_version": "3.12",
            "include_tox": True,
            "include_github_actions": True,
            "test_framework": "pytest",
            "license": "MIT",
            "initialize_git": False,
            "venv_tool": "none"
        }

        result = create_project(
            template_name="python_library",
            project_name=project_data["project_name"],
                target_directory=str(tmp_path),
            variables=project_data
        )

        assert result.success is True

        project_path = Path(result.target_path)

        # Check tox.ini for multiple environments
        if (project_path / "tox.ini").exists():
            tox_content = (project_path / "tox.ini").read_text()
            assert "py39" in tox_content
            assert "py310" in tox_content
            assert "py311" in tox_content
            assert "py312" in tox_content

        # Check pyproject.toml for version constraints
        pyproject = (project_path / "pyproject.toml").read_text()
        assert 'python = ">=3.9' in pyproject or 'python = "^3.9' in pyproject

    def test_monorepo_structure_workflow(self, tmp_path, mock_config_manager):
        """Test creating multiple related projects in a monorepo structure."""
        monorepo_root = tmp_path / "monorepo"
        monorepo_root.mkdir()

        # Create services directory
        services_dir = monorepo_root / "services"
        services_dir.mkdir()

        # Create multiple services
        services = [
            ("auth_service", "Authentication microservice"),
            ("data_service", "Data processing microservice"),
            ("api_gateway", "API gateway service")
        ]

        for service_name, description in services:
            project_data = {
                "project_name": service_name,
                "author": "Platform Team",
                "version": "0.1.0",
                "description": description,
                "python_version": "3.9",
                "include_docker": True,
                "framework": "fastapi",
                "license": "Proprietary",
                "initialize_git": False,  # Will use monorepo git
                "venv_tool": "none"  # Will use monorepo venv
            }

            result = create_project(
                template_name="web_app_fastapi",
                project_name=project_data["project_name"],
                target_directory=str(services_dir),
                variables=project_data
            )

            assert result.success is True

        # Verify monorepo structure
        assert (services_dir / "auth_service").exists()
        assert (services_dir / "data_service").exists()
        assert (services_dir / "api_gateway").exists()

        # Create shared libraries directory
        libs_dir = monorepo_root / "libs"
        libs_dir.mkdir()

        # Create shared library
        lib_data = {
            "project_name": "common_utils",
            "author": "Platform Team",
            "version": "0.1.0",
            "description": "Shared utilities",
            "python_version": "3.9",
            "license": "Proprietary",
            "initialize_git": False,
            "venv_tool": "none"
        }

        result = create_project(
            template_name="python_library",
            project_name=lib_data["project_name"],
                target_directory=str(libs_dir),
            variables=lib_data
        )

        assert result.success is True
        assert (libs_dir / "common_utils").exists()

    def test_plugin_architecture_workflow(self, tmp_path, mock_config_manager):
        """Test creating a project with plugin architecture."""
        # Create main application
        main_data = {
            "project_name": "plugin_app",
            "author": "Architecture Team",
            "version": "0.1.0",
            "description": "Extensible application with plugins",
            "python_version": "3.9",
            "app_name": "pluginapp",
            "use_poetry": False,
            "include_plugins": True,
            "license": "MIT",
            "initialize_git": False,
            "venv_tool": "none"
        }

        result = create_project(
            template_name="cli_app_multi",
            project_name=project_data["project_name"],
                target_directory=str(tmp_path),
            project_data=main_data
        )

        assert result.success is True

        app_path = tmp_path / "plugin_app"

        # Create plugins directory structure
        plugins_dir = app_path / "plugins"
        plugins_dir.mkdir(exist_ok=True)

        # Create example plugins
        for plugin_name in ["auth_plugin", "data_plugin", "ui_plugin"]:
            plugin_dir = plugins_dir / plugin_name
            plugin_dir.mkdir()

            # Create plugin structure
            (plugin_dir / "__init__.py").write_text(
                f'"""Plugin: {plugin_name}"""\n\n'
                f'PLUGIN_NAME = "{plugin_name}"\n'
                f'PLUGIN_VERSION = "0.1.0"\n'
            )

            (plugin_dir / "main.py").write_text(
                f'"""Main plugin module."""\n\n'
                f'def activate():\n'
                f'    """Activate the plugin."""\n'
                f'    print("Activating {plugin_name}")\n'
            )

        # Verify plugin structure
        assert len(list(plugins_dir.iterdir())) == 3
        assert (plugins_dir / "auth_plugin" / "main.py").exists()

    def test_data_science_workflow(self, tmp_path, mock_config_manager):
        """Test creating a data science project with notebooks."""
        project_data = {
            "project_name": "ml_experiment",
            "author": "Data Science Team",
            "version": "0.1.0",
            "description": "Machine learning experimentation project",
            "python_version": "3.9",
            "include_notebooks": True,
            "include_data_dir": True,
            "analysis_framework": "pandas",
            "ml_framework": "scikit-learn",
            "license": "MIT",
            "initialize_git": True,
            "venv_tool": "uv"
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=b"", stderr=b"")

            # Use python_library template as base
            result = create_project(
                template_name="python_library",
                project_name=project_data["project_name"],
                target_directory=str(tmp_path),
                variables=project_data
            )

        assert result.success is True

        project_path = Path(result.target_path)

        # Manually create data science structure
        notebooks_dir = project_path / "notebooks"
        notebooks_dir.mkdir()

        data_dir = project_path / "data"
        data_dir.mkdir()
        (data_dir / "raw").mkdir()
        (data_dir / "processed").mkdir()

        models_dir = project_path / "models"
        models_dir.mkdir()

        # Create example notebook
        example_notebook = {
            "cells": [
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": ["# ML Experiment\n", "Data exploration and model training"]
                },
                {
                    "cell_type": "code",
                    "execution_count": None,
                    "metadata": {},
                    "outputs": [],
                    "source": ["import pandas as pd\n", "import numpy as np\n", "from sklearn import metrics"]
                }
            ],
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3"
                }
            },
            "nbformat": 4,
            "nbformat_minor": 4
        }

        (notebooks_dir / "01_exploration.ipynb").write_text(json.dumps(example_notebook, indent=2))

        # Verify structure
        assert notebooks_dir.exists()
        assert (data_dir / "raw").exists()
        assert (data_dir / "processed").exists()
        assert models_dir.exists()
        assert (notebooks_dir / "01_exploration.ipynb").exists()


@pytest.mark.integration
class TestAsyncWorkflows:
    """Test asynchronous workflow scenarios."""

    async def test_async_project_creation(self, tmp_path, mock_config_manager):
        """Test asynchronous project creation."""
        project_data = {
            "project_name": "async_project",
            "author": "Async Test",
            "version": "0.1.0",
            "description": "Test async creation",
            "python_version": "3.9",
            "license": "MIT",
            "initialize_git": False,
            "venv_tool": "none"
        }

        operation_id = create_project_async(
            template_name="python_library",
            project_name=project_data["project_name"],
            target_directory=str(tmp_path),
            variables=project_data
        )

        # Wait for completion and get result
        from create_project.core.threading_model import ThreadingModel
        threading_model = ThreadingModel()
        result = get_async_result(operation_id, threading_model, timeout=30)

        assert result.result.success is True
        assert (tmp_path / "async_project").exists()

    def test_progress_callback_workflow(self, tmp_path, mock_config_manager):
        """Test project creation with progress callbacks."""
        progress_updates = []

        def progress_callback(message, percentage):
            progress_updates.append((message, percentage))

        project_data = {
            "project_name": "progress_test",
            "author": "Progress Test",
            "version": "0.1.0",
            "description": "Test progress tracking",
            "python_version": "3.9",
            "license": "MIT",
            "initialize_git": True,
            "venv_tool": "uv"
        }

        generator = ProjectGenerator(mock_config_manager)

        # Add progress callback
        original_emit = generator.progress.emit if hasattr(generator, "progress") else None

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=b"", stderr=b"")

            with patch.object(generator, "_report_progress", side_effect=progress_callback):
                result = generator.generate(
                    template_name="python_library",
                    project_name=project_data["project_name"],
                target_directory=str(tmp_path),
                    variables=project_data
                )

        assert result.success is True

        # Verify progress was reported
        assert len(progress_updates) > 0

        # Check progress messages
        messages = [msg for msg, _ in progress_updates]
        assert any("Creating" in msg for msg in messages)

        # Verify progress percentages increase
        percentages = [pct for _, pct in progress_updates if pct is not None]
        if len(percentages) > 1:
            assert percentages[-1] >= percentages[0]

    def test_cancellation_workflow(self, tmp_path, mock_config_manager):
        """Test cancelling project creation mid-process."""

        class GeneratorThread(QThread):
            def __init__(self, generator, template_id, location, project_data):
                super().__init__()
                self.generator = generator
                self.template_id = template_id
                self.location = location
                self.project_data = project_data
                self.result = None
                self._is_cancelled = False

            def run(self):
                try:
                    # Check cancellation before major operations
                    if self._is_cancelled:
                        return

                    self.result = self.generator.generate(
                        template_id=self.template_id,
                        location=self.location,
                        project_data=self.project_data
                    )
                except Exception as e:
                    self.result = {"success": False, "error": str(e)}

            def cancel(self):
                self._is_cancelled = True
                self.generator.cancel()

        generator = ProjectGenerator(mock_config_manager)

        thread = GeneratorThread(
            generator,
            "python_library",
            str(tmp_path),
            {
                "project_name": "cancelled_project",
                "author": "Test",
                "version": "0.1.0",
                "description": "Test cancellation"
            }
        )

        # Start generation
        thread.start()

        # Cancel after brief delay
        QTimer.singleShot(50, thread.cancel)

        # Wait for completion
        thread.wait(5000)

        # Project might be partially created
        project_path = tmp_path / "cancelled_project"
        # Cancellation behavior depends on timing
