# ABOUTME: pytest configuration for integration tests
# ABOUTME: Provides fixtures and utilities for end-to-end testing

"""
pytest configuration for integration tests.

This module provides:
- Application instance for integration testing
- Test database and file system setup
- Mock services for external dependencies
- Integration test utilities
"""

import asyncio
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator
from unittest.mock import MagicMock, patch

import pytest

from create_project.config import ConfigManager
from create_project.core.api import create_project
from create_project.templates.engine import TemplateEngine
from create_project.templates.loader import TemplateLoader

# Import GUI fixtures to make them available in integration tests
from tests.gui.conftest import mock_config_manager


@pytest.fixture(scope="session")
def integration_app() -> Dict[str, Any]:
    """
    Create application instance for integration testing.
    
    Returns a dictionary with initialized application components.
    """
    # Create test configuration
    config = ConfigManager()
    
    # Set test-specific configurations
    config.set_setting("ai.enabled", False)  # Disable AI for predictable tests
    config.set_setting("logging.level", "DEBUG")
    config.set_setting("templates.builtin_path", "create_project/templates/builtin")
    
    # Initialize components
    template_loader = TemplateLoader(config_manager=config)
    template_engine = TemplateEngine(config_manager=config)
    
    return {
        "config": config,
        "template_loader": template_loader,
        "template_engine": template_engine,
    }


@pytest.fixture
def test_project_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """
    Create a temporary directory for test project generation.
    
    Yields:
        Path to temporary directory
    """
    project_dir = tmp_path / "test_projects"
    project_dir.mkdir(parents=True, exist_ok=True)
    yield project_dir
    # Cleanup happens automatically with tmp_path


@pytest.fixture
def mock_git():
    """
    Mock git operations for integration tests.
    
    Returns a mock that simulates successful git operations.
    """
    with patch("create_project.core.git_manager.GitManager") as mock:
        instance = mock.return_value
        instance.is_available.return_value = True
        instance.initialize_repository.return_value = True
        instance.create_initial_commit.return_value = True
        yield instance


@pytest.fixture
def mock_venv():
    """
    Mock virtual environment creation for integration tests.
    
    Returns a mock that simulates successful venv operations.
    """
    with patch("create_project.core.venv_manager.VenvManager") as mock:
        instance = mock.return_value
        instance.get_available_tool.return_value = "venv"
        instance.create_virtual_environment.return_value = True
        yield instance


@pytest.fixture
def sample_project_data() -> Dict[str, Any]:
    """
    Provide sample project data for integration tests.
    
    Returns:
        Dictionary with common project creation parameters
    """
    return {
        "project_name": "test_integration_project",
        "author": "Integration Test",
        "email": "test@integration.com",
        "description": "A test project for integration testing",
        "license": "MIT",
        "python_version": "3.9.6",
        "include_tests": True,
        "init_git": True,
        "create_venv": True,
        "project_type": "library",
        "testing_framework": "pytest",
        "include_dev_dependencies": True,
        "include_coverage": True,
    }


@pytest.fixture
def integration_test_helper(integration_app, test_project_dir):
    """
    Helper class for integration testing.
    
    Provides utility methods for common integration test operations.
    """
    class IntegrationTestHelper:
        def __init__(self, app_components, project_dir):
            self.app = app_components
            self.project_dir = project_dir
            
        def create_test_project(self, template_name: str, variables: Dict[str, Any]) -> Path:
            """Create a test project and return its path."""
            project_name = variables["project_name"]
            
            # Use the API to create project
            result = create_project(
                template_name=template_name,
                project_name=project_name,
                target_directory=str(self.project_dir),
                variables=variables,
                config_manager=self.app["config"]
            )
            
            if not result.success:
                raise RuntimeError(f"Failed to create test project: {result.errors}")
                
            return self.project_dir / project_name
            
        def verify_project_structure(self, project_path: Path, expected_files: list) -> bool:
            """Verify that expected files exist in the project."""
            for file_path in expected_files:
                full_path = project_path / file_path
                if not full_path.exists():
                    return False
            return True
            
        def read_project_file(self, project_path: Path, file_name: str) -> str:
            """Read content of a file in the generated project."""
            file_path = project_path / file_name
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            return file_path.read_text()
    
    return IntegrationTestHelper(integration_app, test_project_dir)


@pytest.fixture(autouse=True)
def cleanup_test_artifacts():
    """
    Automatically clean up test artifacts after each test.
    
    This fixture runs after each test to ensure clean state.
    """
    yield
    # Cleanup happens here after test completes
    # The tmp_path fixture handles most cleanup automatically


@pytest.fixture
def mock_external_services():
    """
    Mock all external services for integration tests.
    
    Provides mocks for:
    - Git operations
    - Virtual environment creation
    - AI services
    - Network requests
    """
    with patch("create_project.ai.ai_service.AIService") as ai_mock:
        ai_instance = ai_mock.return_value
        ai_instance.is_available.return_value = False
        
        with patch("requests.get") as requests_mock:
            requests_mock.return_value.status_code = 200
            
            yield {
                "ai": ai_instance,
                "requests": requests_mock,
            }


# Markers for categorizing integration tests
pytest.mark.integration = pytest.mark.mark(name="integration")
pytest.mark.slow = pytest.mark.mark(name="slow")
pytest.mark.requires_network = pytest.mark.mark(name="requires_network")


@pytest.fixture
def run_async():
    """Helper to run async functions in tests."""
    def _run_async(coro):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    return _run_async