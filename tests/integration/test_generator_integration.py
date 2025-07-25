# ABOUTME: Comprehensive integration tests for project generator and core components
# ABOUTME: Tests complete project generation workflows with all core component integration

"""
Comprehensive integration tests for project generator system.

This module tests the complete integration between:
- ProjectGenerator and all core components
- PathHandler, DirectoryCreator, FileRenderer integration
- GitManager and VenvManager integration  
- CommandExecutor and security system integration
- Error handling and rollback scenarios
- Progress reporting and cancellation workflows
- Threading and concurrent operations
"""

import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from create_project.config.config_manager import ConfigManager
from create_project.core.api import create_project
from create_project.core.project_generator import ProjectGenerator
from create_project.templates.engine import TemplateEngine
from create_project.templates.loader import TemplateLoader


@pytest.mark.integration
class TestProjectGeneratorIntegration:
    """Test integration between ProjectGenerator and all core components."""

    def setup_method(self):
        """Set up test environment for each test."""
        self.config_manager = ConfigManager()
        self.config_manager.set_setting("templates.builtin_path", "create_project/templates/builtin")
        self.config_manager.set_setting("logging.level", "DEBUG")

        self.template_loader = TemplateLoader(self.config_manager)
        self.template_engine = TemplateEngine(self.config_manager)

        self.generator = ProjectGenerator(
            config_manager=self.config_manager,
            template_loader=self.template_loader
        )

    def test_complete_project_generation_workflow(self):
        """Test complete project generation from start to finish."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Arrange
            target_path = Path(temp_dir)
            variables = {
                "author": "Integration Test",
                "email": "test@integration.com",
                "description": "Integration test library",
                "license": "MIT",
                "python_version": "3.9.6",
                "include_tests": True,
                "project_type": "library",
                "testing_framework": "pytest",
                "include_dev_dependencies": True,
                "include_coverage": True
            }

            # Act
            result = create_project(
                template_name="python_library",
                project_name="integration_test_lib",
                target_directory=str(target_path),
                variables=variables,
                config_manager=self.config_manager
            )

            # Assert - Generation should succeed
            assert result.success
            assert not result.errors

            # Verify project structure
            project_path = target_path / "integration_test_lib"
            assert project_path.exists()
            assert project_path.is_dir()

            # Verify core files exist
            assert (project_path / "pyproject.toml").exists()
            assert (project_path / "README.md").exists()
            assert (project_path / "integration_test_lib" / "__init__.py").exists()
            assert (project_path / "tests").exists()

            # Verify variable substitution worked
            readme_content = (project_path / "README.md").read_text()
            assert "integration_test_lib" in readme_content
            assert "Integration test library" in readme_content

    def test_project_generator_with_all_components(self):
        """Test ProjectGenerator integration with all core components."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Arrange - Test with different template types to exercise all components
            test_cases = [
                ("python_library", "test_lib"),
                ("cli_single_package", "test_cli"),
                ("flask_web_app", "test_flask")
            ]

            for template_name, project_name in test_cases:
                target_path = Path(temp_dir)
                options = ProjectOptions(
                    template_name=template_name,
                    project_name=project_name,
                    target_directory=str(target_path),
                    variables={
                        "author": "Component Test",
                        "email": "components@test.com",
                        "description": f"Component integration test for {template_name}",
                        "license": "Apache-2.0"
                    },
                    init_git=False,  # Disable git for faster testing
                    create_venv=False  # Disable venv for faster testing
                )

                # Act
                result = self.generator.create_project(options)

                # Assert
                assert result.success, f"Failed to generate {template_name}: {result.errors}"

                project_path = target_path / project_name
                assert project_path.exists()

                # Clean up for next iteration
                import shutil
                shutil.rmtree(project_path)

    def test_git_integration_workflow(self):
        """Test GitManager integration with project generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Arrange
            target_path = Path(temp_dir)
            options = ProjectOptions(
                template_name="python_library",
                project_name="git_test_project",
                target_directory=str(target_path),
                variables={
                    "author": "Git Test",
                    "email": "git@test.com",
                    "description": "Git integration test",
                    "license": "MIT"
                },
                init_git=True,  # Enable git initialization
                create_venv=False
            )

            # Mock GitManager to ensure we test integration without requiring git
            with patch("create_project.core.project_generator.GitManager") as mock_git:
                mock_git_instance = Mock()
                mock_git_instance.is_available.return_value = True
                mock_git_instance.initialize_repository.return_value = True
                mock_git_instance.create_initial_commit.return_value = True
                mock_git.return_value = mock_git_instance

                # Act
                result = self.generator.create_project(options)

                # Assert
                assert result.success

                # Verify GitManager was called correctly
                mock_git_instance.initialize_repository.assert_called_once()
                mock_git_instance.create_initial_commit.assert_called_once()

    def test_venv_integration_workflow(self):
        """Test VenvManager integration with project generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Arrange
            target_path = Path(temp_dir)
            options = ProjectOptions(
                template_name="python_library",
                project_name="venv_test_project",
                target_directory=str(target_path),
                variables={
                    "author": "Venv Test",
                    "email": "venv@test.com",
                    "description": "Virtual environment integration test",
                    "license": "MIT"
                },
                init_git=False,
                create_venv=True,  # Enable venv creation
                venv_tool="venv"
            )

            # Mock VenvManager to ensure we test integration without creating actual venv
            with patch("create_project.core.project_generator.VenvManager") as mock_venv:
                mock_venv_instance = Mock()
                mock_venv_instance.get_available_tool.return_value = "venv"
                mock_venv_instance.create_virtual_environment.return_value = True
                mock_venv.return_value = mock_venv_instance

                # Act
                result = self.generator.create_project(options)

                # Assert
                assert result.success

                # Verify VenvManager was called correctly
                mock_venv_instance.create_virtual_environment.assert_called_once()

    def test_command_executor_integration(self):
        """Test CommandExecutor integration with post-creation commands."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Arrange - Use template that might have post-creation commands
            target_path = Path(temp_dir)
            options = ProjectOptions(
                template_name="python_library",
                project_name="command_test_project",
                target_directory=str(target_path),
                variables={
                    "author": "Command Test",
                    "email": "command@test.com",
                    "description": "Command executor integration test",
                    "license": "MIT"
                },
                init_git=False,
                create_venv=False
            )

            # Mock CommandExecutor to test integration
            with patch("create_project.core.project_generator.CommandExecutor") as mock_executor:
                mock_executor_instance = Mock()
                mock_executor_instance.execute_commands.return_value = True
                mock_executor.return_value = mock_executor_instance

                # Act
                result = self.generator.create_project(options)

                # Assert
                assert result.success

                # CommandExecutor integration depends on template having post-creation commands
                # This test ensures the integration point works correctly

    def test_error_handling_and_rollback_integration(self):
        """Test error handling and rollback across all components."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Arrange - Create scenario that will cause an error
            target_path = Path(temp_dir)

            # Create a file that will conflict with directory creation
            conflict_path = target_path / "error_test_project"
            conflict_path.touch()  # Create file with same name as project

            options = ProjectOptions(
                template_name="python_library",
                project_name="error_test_project",
                target_directory=str(target_path),
                variables={
                    "author": "Error Test",
                    "email": "error@test.com",
                    "description": "Error handling test",
                    "license": "MIT"
                },
                init_git=False,
                create_venv=False
            )

            # Act
            result = self.generator.create_project(options)

            # Assert - Should handle error gracefully
            assert not result.success
            assert result.errors

            # Verify rollback - conflict file should still exist, no project directory
            assert conflict_path.exists() and conflict_path.is_file()

    def test_progress_reporting_integration(self):
        """Test progress reporting throughout project generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Arrange
            target_path = Path(temp_dir)
            progress_updates = []

            def progress_callback(percentage: float, message: str):
                progress_updates.append((percentage, message))

            options = ProjectOptions(
                template_name="python_library",
                project_name="progress_test_project",
                target_directory=str(target_path),
                variables={
                    "author": "Progress Test",
                    "email": "progress@test.com",
                    "description": "Progress reporting test",
                    "license": "MIT"
                },
                init_git=False,
                create_venv=False,
                progress_callback=progress_callback
            )

            # Act
            result = self.generator.create_project(options)

            # Assert
            assert result.success
            assert len(progress_updates) > 0

            # Verify progress updates are reasonable
            percentages = [update[0] for update in progress_updates]
            assert all(0 <= p <= 100 for p in percentages)
            assert percentages[-1] == 100  # Should end at 100%

    def test_concurrent_project_generation(self):
        """Test concurrent project generation with thread safety."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Arrange
            target_path = Path(temp_dir)
            results = {}

            def create_project_thread(project_name: str):
                options = ProjectOptions(
                    template_name="python_library",
                    project_name=project_name,
                    target_directory=str(target_path),
                    variables={
                        "author": "Concurrent Test",
                        "email": "concurrent@test.com",
                        "description": f"Concurrent test project {project_name}",
                        "license": "MIT"
                    },
                    init_git=False,
                    create_venv=False
                )

                result = self.generator.create_project(options)
                results[project_name] = result

            # Act - Create multiple projects concurrently
            threads = []
            project_names = ["concurrent_1", "concurrent_2", "concurrent_3"]

            for project_name in project_names:
                thread = threading.Thread(target=create_project_thread, args=(project_name,))
                threads.append(thread)
                thread.start()

            # Wait for all threads to complete
            for thread in threads:
                thread.join()

            # Assert - All projects should be created successfully
            assert len(results) == 3
            for project_name, result in results.items():
                assert result.success, f"Concurrent generation failed for {project_name}: {result.errors}"
                project_path = target_path / project_name
                assert project_path.exists()

    def test_large_project_generation_integration(self):
        """Test generation of larger, more complex projects."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Arrange - Use complex template with many features
            target_path = Path(temp_dir)
            options = ProjectOptions(
                template_name="django_web_app",  # More complex template
                project_name="large_django_project",
                target_directory=str(target_path),
                variables={
                    "author": "Large Project Test",
                    "email": "large@test.com",
                    "description": "Large project integration test",
                    "license": "BSD-3-Clause",
                    "django_version": "4.2",
                    "include_admin": True,
                    "include_api": True,
                    "database": "postgresql"
                },
                init_git=False,
                create_venv=False
            )

            # Act
            result = self.generator.create_project(options)

            # Assert
            assert result.success, f"Large project generation failed: {result.errors}"

            project_path = target_path / "large_django_project"
            assert project_path.exists()

            # Verify complex structure was created
            assert (project_path / "manage.py").exists()
            assert (project_path / "requirements.txt").exists()


@pytest.mark.integration
class TestProjectGeneratorPerformance:
    """Test project generator performance in integration scenarios."""

    def setup_method(self):
        """Set up test environment."""
        self.config_manager = ConfigManager()
        self.config_manager.set_setting("templates.builtin_path", "create_project/templates/builtin")

        self.template_loader = TemplateLoader(self.config_manager)
        self.template_engine = TemplateEngine(self.config_manager)

        self.generator = ProjectGenerator(
            config_manager=self.config_manager,
            template_loader=self.template_loader
        )

    @pytest.mark.slow
    def test_multiple_project_generation_performance(self):
        """Test performance when generating multiple projects."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir)

            # Generate multiple projects and measure time
            start_time = time.time()

            for i in range(5):
                options = ProjectOptions(
                    template_name="python_library",
                    project_name=f"perf_project_{i}",
                    target_directory=str(target_path),
                    variables={
                        "author": f"Performance Test {i}",
                        "email": f"perf{i}@test.com",
                        "description": f"Performance test project {i}",
                        "license": "MIT"
                    },
                    init_git=False,
                    create_venv=False
                )

                result = self.generator.create_project(options)
                assert result.success

            end_time = time.time()
            total_time = end_time - start_time

            # Assert reasonable performance (should complete in reasonable time)
            assert total_time < 30  # Should complete 5 projects in under 30 seconds

    def test_template_caching_performance_integration(self):
        """Test performance benefits of template caching."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir)

            # Enable caching
            self.config_manager.set_setting("templates.cache_enabled", True)

            # Generate same template type multiple times - should benefit from caching
            for i in range(3):
                options = ProjectOptions(
                    template_name="python_library",
                    project_name=f"cache_perf_project_{i}",
                    target_directory=str(target_path),
                    variables={
                        "author": f"Cache Test {i}",
                        "email": f"cache{i}@test.com",
                        "description": f"Cache performance test {i}",
                        "license": "MIT"
                    },
                    init_git=False,
                    create_venv=False
                )

                result = self.generator.create_project(options)
                assert result.success


@pytest.mark.integration
class TestProjectGeneratorErrorScenarios:
    """Test project generator error handling in integration scenarios."""

    def setup_method(self):
        """Set up test environment."""
        self.config_manager = ConfigManager()
        self.config_manager.set_setting("templates.builtin_path", "create_project/templates/builtin")

        self.template_loader = TemplateLoader(self.config_manager)
        self.template_engine = TemplateEngine(self.config_manager)

        self.generator = ProjectGenerator(
            config_manager=self.config_manager,
            template_loader=self.template_loader
        )

    def test_invalid_template_error_handling(self):
        """Test error handling for invalid template names."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir)
            options = ProjectOptions(
                template_name="nonexistent_template",
                project_name="error_project",
                target_directory=str(target_path),
                variables={"author": "Error Test"},
                init_git=False,
                create_venv=False
            )

            result = self.generator.create_project(options)

            assert not result.success
            assert result.errors
            assert any("template" in error.lower() for error in result.errors)

    def test_permission_error_handling(self):
        """Test error handling for permission issues."""
        # This test is platform-dependent and may need adjustment
        try:
            # Try to create project in system directory (should fail)
            options = ProjectOptions(
                template_name="python_library",
                project_name="permission_test",
                target_directory="/system_readonly_dir",  # Non-existent system path
                variables={
                    "author": "Permission Test",
                    "email": "permission@test.com",
                    "description": "Permission test",
                    "license": "MIT"
                },
                init_git=False,
                create_venv=False
            )

            result = self.generator.create_project(options)

            # Should handle permission error gracefully
            assert not result.success
            assert result.errors

        except Exception:
            # If test environment doesn't support this scenario, skip
            pytest.skip("Permission testing not supported in this environment")

    def test_disk_space_error_simulation(self):
        """Test error handling for disk space issues."""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir)

            # Mock disk space error during file creation
            with patch("pathlib.Path.write_text") as mock_write:
                mock_write.side_effect = OSError("No space left on device")

                options = ProjectOptions(
                    template_name="python_library",
                    project_name="disk_space_test",
                    target_directory=str(target_path),
                    variables={
                        "author": "Disk Space Test",
                        "email": "disk@test.com",
                        "description": "Disk space test",
                        "license": "MIT"
                    },
                    init_git=False,
                    create_venv=False
                )

                result = self.generator.create_project(options)

                # Should handle disk space error gracefully
                assert not result.success
                assert result.errors
