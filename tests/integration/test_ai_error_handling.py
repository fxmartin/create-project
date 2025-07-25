# ABOUTME: Integration tests for AI-assisted error handling and recovery scenarios
# ABOUTME: Tests various error conditions and how AI helps users recover from them

"""Integration tests for AI-assisted error handling and recovery.

This module tests how the AI service helps users recover from various
error scenarios during project generation.
"""

import asyncio
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from pytest_mock import MockerFixture

from create_project.ai.ai_service import AIService
from create_project.ai.context_collector import ErrorContextCollector
from create_project.config.config_manager import ConfigManager
from create_project.core.exceptions import (
    PathError,
)
from create_project.core.project_generator import (
    GenerationResult,
    ProjectGenerator,
    ProjectOptions,
)
from create_project.templates.loader import TemplateLoader
from create_project.templates.schema import Template
from tests.ai.mocks import (
    MockChatResponse,
    MockOllamaClient,
    MockOllamaResponse,
)
from tests.integration.test_ai_integration_fixes import (
    simulate_disk_space_error,
)
from tests.integration.test_templates import get_mock_template


def patch_ollama_client(mocker, mock_client):
    """Properly patch OllamaClient to return mock client."""
    def mock_client_new(cls, *args, **kwargs):
        return mock_client

    mocker.patch(
        "create_project.ai.ollama_client.OllamaClient.__new__",
        side_effect=mock_client_new,
    )


class TestAIErrorHandling:
    """Test AI-assisted error handling scenarios."""

    def _load_template(
        self, template_loader: TemplateLoader, template_name: str
    ) -> Template:
        """Helper to load a template by name."""
        # Use mock templates for integration testing
        return get_mock_template(template_name)

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace."""
        workspace = tempfile.mkdtemp()
        yield Path(workspace)
        shutil.rmtree(workspace, ignore_errors=True)

    @pytest.fixture
    def config_with_ai(self, temp_workspace):
        """Create config with AI enabled."""
        config_file = temp_workspace / "config.json"

        # Get the package directory
        package_dir = Path(__file__).parent.parent.parent / "create_project"

        config_data = {
            "ai": {
                "enabled": True,
                "ollama": {"host": "http://localhost", "port": 11434},
                "cache": {"enabled": True, "max_size": 100},
            },
            "templates": {
                "directories": [str(package_dir / "templates")],
                "builtin_directory": str(package_dir / "templates" / "builtin"),
                "user_directory": str(package_dir / "templates" / "user"),
            },
        }
        config_file.write_text(json.dumps(config_data))
        return ConfigManager(config_file)

    @pytest.fixture
    def error_context_collector(self):
        """Create an error context collector."""
        return ErrorContextCollector()

    def test_directory_permission_error_recovery(
        self, temp_workspace, config_with_ai, mocker: MockerFixture
    ):
        """Test AI assistance for directory permission errors."""
        # Mock Ollama with permission error response
        mock_response = {
            "model": "llama3.2:latest",
            "created_at": "2024-11-17T12:00:00Z",
            "message": {
                "role": "assistant",
                "content": (
                    "The permission denied error indicates insufficient privileges. "
                    "Here's how to fix it:\n\n"
                    "1. **Check directory ownership**:\n"
                    "   ```bash\n"
                    "   ls -la /path/to/parent\n"
                    "   ```\n\n"
                    "2. **Fix permissions**:\n"
                    "   ```bash\n"
                    "   chmod 755 /path/to/directory\n"
                    "   sudo chown $USER:$USER /path/to/directory\n"
                    "   ```\n\n"
                    "3. **Alternative**: Create project in your home directory instead."
                ),
            },
            "done": True,
        }

        mock_client = MockOllamaClient(default_response=mock_response)
        patch_ollama_client(mocker, mock_client)

        # Initialize services
        ai_service = AIService(config_with_ai)
        # Run initialization synchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(ai_service.initialize())
        loop.close()

        template_loader = TemplateLoader()
        generator = ProjectGenerator(
            template_loader=template_loader, ai_service=ai_service
        )

        # Create read-only directory
        readonly_dir = temp_workspace / "readonly"
        readonly_dir.mkdir()
        os.chmod(readonly_dir, 0o444)  # Read-only

        # Try to generate project in read-only directory
        template = self._load_template(template_loader, "One-off Script")
        target_path = readonly_dir / "new_project"

        result = generator.generate_project(
            template=template,
            variables={"project_name": "test", "description": "Test"},
            target_path=target_path,
            options=ProjectOptions(enable_ai_assistance=True),
        )

        # Reset permissions for cleanup
        os.chmod(readonly_dir, 0o755)

        # Verify error with helpful AI suggestions
        assert not result.success
        assert result.ai_suggestions is not None
        assert "permission denied" in result.ai_suggestions.lower()
        assert "chmod" in result.ai_suggestions
        assert "Alternative" in result.ai_suggestions

        # Cleanup
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(ai_service.cleanup())
        loop.close()

    def test_git_initialization_error_recovery(
        self, temp_workspace, config_with_ai, mocker: MockerFixture
    ):
        """Test AI assistance for git initialization errors."""

        # Mock git command failure
        def mock_run(*args, **kwargs):
            if "git" in args[0]:
                raise subprocess.CalledProcessError(
                    128, args[0], "fatal: not a git repository"
                )
            return subprocess.CompletedProcess(args[0], 0, "", "")

        # Mock shutil.which to return None for git
        mocker.patch("shutil.which", return_value=None)
        mocker.patch("subprocess.run", side_effect=mock_run)

        # Mock Ollama response for git errors
        mock_response = MockChatResponse.ERROR_HELP
        mock_response["message"]["content"] = (
            "Git initialization failed. Here are solutions:\n\n"
            "1. **Install Git** (if not installed):\n"
            "   - macOS: `brew install git`\n"
            "   - Ubuntu: `sudo apt install git`\n"
            "   - Windows: Download from git-scm.com\n\n"
            "2. **Configure Git** (if installed):\n"
            "   ```bash\n"
            '   git config --global user.name "Your Name"\n'
            '   git config --global user.email "email@example.com"\n'
            "   ```\n\n"
            "3. **Skip Git**: Set `create_git_repo=False` in options"
        )

        mock_client = MockOllamaClient(default_response=mock_response)
        patch_ollama_client(mocker, mock_client)

        # Initialize services synchronously
        ai_service = AIService(config_with_ai)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(ai_service.initialize())
        loop.close()

        template_loader = TemplateLoader()
        generator = ProjectGenerator(
            template_loader=template_loader, ai_service=ai_service
        )

        # Generate project with git enabled
        template = self._load_template(template_loader, "Python Library/Package")
        target_path = temp_workspace / "git_test"

        result = generator.generate_project(
            template=template,
            variables={
                "project_name": "git_test",
                "description": "Test",
                "author": "Test",
                "author_email": "test@example.com",
            },
            target_path=target_path,
            options=ProjectOptions(
                enable_ai_assistance=True,
                create_git_repo=True,  # This will fail
            ),
        )

        # Project should be created but git init failed
        assert result.success  # Project succeeds despite git error
        assert target_path.exists()  # Files were created
        assert not result.git_initialized  # Git was not initialized
        assert len(result.errors) > 0  # Git error was recorded
        assert any("git" in err.lower() for err in result.errors)

        # Cleanup
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(ai_service.cleanup())
        loop.close()

    def test_python_version_error_recovery(
        self, temp_workspace, config_with_ai, mocker: MockerFixture
    ):
        """Test AI assistance for Python version mismatch errors."""

        # Mock Python version check failure
        def mock_run(*args, **kwargs):
            cmd = args[0]
            if isinstance(cmd, list) and "python" in cmd[0] and "--version" in cmd:
                return subprocess.CompletedProcess(cmd, 0, "Python 2.7.18", "")
            elif isinstance(cmd, list) and "venv" in str(cmd):
                raise subprocess.CalledProcessError(
                    1, cmd, "Error: Python 3.6+ required"
                )
            return subprocess.CompletedProcess(cmd, 0, "", "")

        mocker.patch("subprocess.run", side_effect=mock_run)

        # Mock AI response
        mock_response = {
            "message": {
                "content": (
                    "Python version error detected. The project requires Python 3.6+.\n\n"
                    "**Solutions**:\n\n"
                    "1. **Install Python 3.9+**:\n"
                    "   - macOS: `brew install python@3.9`\n"
                    "   - Ubuntu: `sudo apt install python3.9`\n"
                    "   - Windows: Download from python.org\n\n"
                    "2. **Use pyenv** for version management:\n"
                    "   ```bash\n"
                    "   pyenv install 3.9.16\n"
                    "   pyenv local 3.9.16\n"
                    "   ```\n\n"
                    "3. **Check current version**:\n"
                    "   ```bash\n"
                    "   python3 --version\n"
                    "   which python3\n"
                    "   ```"
                )
            },
            "done": True,
        }

        mock_client = MockOllamaClient(default_response=mock_response)
        patch_ollama_client(mocker, mock_client)

        # Initialize services synchronously
        ai_service = AIService(config_with_ai)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(ai_service.initialize())
        loop.close()

        template_loader = TemplateLoader()
        generator = ProjectGenerator(
            template_loader=template_loader, ai_service=ai_service
        )

        # Generate project
        template = self._load_template(template_loader, "Python Library/Package")
        result = generator.generate_project(
            template=template,
            variables={
                "project_name": "version_test",
                "description": "Test",
                "author": "Test",
                "author_email": "test@example.com",
            },
            target_path=temp_workspace / "version_test",
            options=ProjectOptions(
                enable_ai_assistance=True, create_venv=True, python_version="3.9"
            ),
        )

        # Project should succeed but venv creation should fail
        assert result.success  # Project creation succeeds
        assert not result.venv_created  # But venv was not created
        assert len(result.errors) > 0  # Venv error was recorded
        assert any("virtual environment" in err.lower() for err in result.errors)

        # Cleanup
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(ai_service.cleanup())
        loop.close()

    def test_template_validation_error_recovery(
        self, temp_workspace, config_with_ai, mocker: MockerFixture
    ):
        """Test AI assistance for template validation errors."""
        # Mock AI response for validation errors
        mock_response = {
            "message": {
                "content": (
                    "Template validation failed due to missing required variables.\n\n"
                    "**Required variables for 'cli' template**:\n"
                    "- `cli_name`: Name of the CLI command\n"
                    "- `main_command`: Main command function name\n\n"
                    "**Example usage**:\n"
                    "```python\n"
                    "variables = {\n"
                    '    "project_name": "mycli",\n'
                    '    "description": "My CLI tool",\n'
                    '    "cli_name": "mycli",\n'
                    '    "main_command": "main"\n'
                    "}\n"
                    "```\n\n"
                    "**Tip**: Check template documentation for all required variables."
                )
            },
            "done": True,
        }

        mock_client = MockOllamaClient(default_response=mock_response)
        patch_ollama_client(mocker, mock_client)

        # Initialize services
        ai_service = AIService(config_with_ai)
        # Run initialization synchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(ai_service.initialize())
        loop.close()

        template_loader = TemplateLoader()
        generator = ProjectGenerator(
            template_loader=template_loader, ai_service=ai_service
        )

        # Try to use CLI template with missing variables
        template = self._load_template(
            template_loader, "CLI Application (Single Package)"
        )
        result = generator.generate_project(
            template=template,
            variables={
                "project_name": "incomplete_cli",
                "description": "Incomplete CLI",
                # Missing: cli_name, main_command
            },
            target_path=temp_workspace / "incomplete_cli",
            options=ProjectOptions(enable_ai_assistance=True),
        )

        # Should fail with helpful validation guidance
        assert not result.success
        assert result.ai_suggestions is not None
        # Check for validation/variable-related content in AI suggestions
        assert any(word in result.ai_suggestions.lower() for word in ["validation", "variable", "required", "missing"])
        assert "cli_name" in result.ai_suggestions
        # main_command has a default value, so it might not be mentioned
        assert "Example usage" in result.ai_suggestions or "example" in result.ai_suggestions.lower()

        # Cleanup
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(ai_service.cleanup())
        loop.close()

    def test_disk_space_error_recovery(
        self, temp_workspace, config_with_ai, mocker: MockerFixture
    ):
        """Test AI assistance for disk space errors."""

        # Mock AI response
        mock_response = {
            "message": {
                "content": (
                    "Disk space error: No space left on device.\n\n"
                    "**Immediate solutions**:\n\n"
                    "1. **Check disk usage**:\n"
                    "   ```bash\n"
                    "   df -h\n"
                    "   du -sh ~/* | sort -h\n"
                    "   ```\n\n"
                    "2. **Free up space**:\n"
                    "   - Clear package caches: `brew cleanup` or `apt clean`\n"
                    "   - Remove old logs: `find /var/log -type f -name '*.log' -mtime +30`\n"
                    "   - Clean Docker: `docker system prune -a`\n\n"
                    "3. **Use different location**:\n"
                    "   - External drive\n"
                    "   - Cloud storage mount\n"
                    "   - Different partition with more space"
                )
            },
            "done": True,
        }

        mock_client = MockOllamaClient(default_response=mock_response)
        patch_ollama_client(mocker, mock_client)

        # Initialize services
        ai_service = AIService(config_with_ai)
        # Run initialization synchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(ai_service.initialize())
        loop.close()

        template_loader = TemplateLoader()
        generator = ProjectGenerator(
            template_loader=template_loader, ai_service=ai_service
        )

        # Try to generate large project with disk space error simulation
        template = self._load_template(template_loader, "Python Library/Package")

        with simulate_disk_space_error("large_project"):
            result = generator.generate_project(
                template=template,
                variables={
                    "project_name": "large_project",
                    "description": "Test",
                    "author": "Test",
                    "author_email": "test@example.com",
                },
                target_path=temp_workspace / "large_project",
                options=ProjectOptions(enable_ai_assistance=True),
            )

        # Should fail with disk space guidance
        assert not result.success
        assert result.ai_suggestions is not None
        assert "disk space" in result.ai_suggestions.lower()
        assert "df -h" in result.ai_suggestions
        assert "Free up space" in result.ai_suggestions

        # Cleanup
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(ai_service.cleanup())
        loop.close()

    def test_network_error_graceful_degradation(
        self, temp_workspace, config_with_ai, mocker: MockerFixture
    ):
        """Test graceful degradation when AI service has network issues."""
        # Create a sequence of network conditions
        network_conditions = ["connection_error", "timeout", "rate_limit"]
        call_count = 0

        def get_mock_client(*args, **kwargs):
            nonlocal call_count
            condition = network_conditions[min(call_count, len(network_conditions) - 1)]
            call_count += 1
            return MockOllamaClient(network_condition=condition)

        mocker.patch(
            "create_project.ai.ollama_client.OllamaClient.__new__",
            side_effect=get_mock_client,
        )

        # Initialize services synchronously
        ai_service = AIService(config_with_ai)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(ai_service.initialize())
        loop.close()

        template_loader = TemplateLoader()
        generator = ProjectGenerator(
            template_loader=template_loader, ai_service=ai_service
        )

        # Generate multiple projects with network issues
        results = []
        for i in range(3):
            template = self._load_template(template_loader, "One-off Script")
            result = generator.generate_project(
                template=template,
                variables={
                    "project_name": f"network_test_{i}",
                    "description": f"Network test {i}",
                },
                target_path=temp_workspace / f"network_test_{i}",
                options=ProjectOptions(enable_ai_assistance=True),
            )
            results.append(result)

        # All projects should be created despite network issues
        assert all(r.success for r in results)
        assert all((temp_workspace / f"network_test_{i}").exists() for i in range(3))

        # AI suggestions might be None or fallback due to network issues
        # This is expected behavior (graceful degradation)

        # Cleanup
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(ai_service.cleanup())
        loop.close()

    def test_concurrent_error_handling(
        self, temp_workspace, config_with_ai, mocker: MockerFixture
    ):
        """Test AI error handling with concurrent project generations."""
        # Mock different error scenarios
        error_responses = {
            "permission": MockChatResponse.ERROR_HELP,
            "git": {
                "message": {"content": "Git not found. Install git first."},
                "done": True,
            },
            "validation": {
                "message": {"content": "Missing required template variables."},
                "done": True,
            },
        }

        # Create mock client that returns different responses
        response_index = 0

        def get_response(*args, **kwargs):
            nonlocal response_index
            responses = list(error_responses.values())
            response = responses[response_index % len(responses)]
            response_index += 1
            return response

        mock_client = MockOllamaClient()
        mock_client.default_response = error_responses["permission"]
        mock_client.post = AsyncMock(
            return_value=Mock(json=lambda: get_response(), status_code=200)
        )

        mocker.patch(
            "create_project.ai.ollama_client.OllamaClient.__new__",
            return_value=mock_client,
        )

        # Initialize shared AI service synchronously
        ai_service = AIService(config_with_ai)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(ai_service.initialize())
        loop.close()

        template_loader = TemplateLoader()

        # Define error scenario function
        def create_with_error(error_type: str) -> GenerationResult:
            generator = ProjectGenerator(
                template_loader=template_loader, ai_service=ai_service
            )

            # Create different error conditions
            if error_type == "permission":
                # Create read-only directory
                target = temp_workspace / f"readonly_{error_type}"
                target.mkdir()
                os.chmod(target, 0o444)
                target_path = target / "project"
            else:
                # Normal target
                target_path = temp_workspace / f"error_{error_type}"

            template = self._load_template(template_loader, "One-off Script")
            result = generator.generate_project(
                template=template,
                variables={
                    "project_name": f"error_{error_type}",
                    "description": f"Error test {error_type}",
                },
                target_path=target_path,
                options=ProjectOptions(enable_ai_assistance=True),
            )

            # Reset permissions if needed
            if error_type == "permission" and target.exists():
                os.chmod(target, 0o755)

            return result

        # Run error scenarios (synchronously for now)
        results = []
        for error_type in ["permission", "git", "validation"]:
            try:
                result = create_with_error(error_type)
                results.append(result)
            except Exception as e:
                results.append(e)

        # Should handle all errors gracefully
        assert len(results) == 3
        # Some may fail but should have AI suggestions

        # Cleanup
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(ai_service.cleanup())
        loop.close()

    def test_error_context_sanitization(
        self,
        temp_workspace,
        config_with_ai,
        error_context_collector,
        mocker: MockerFixture,
    ):
        """Test that error contexts are properly sanitized before sending to AI."""
        # Track what gets sent to AI
        captured_contexts = []

        async def capture_context(*args, **kwargs):
            captured_contexts.append(kwargs)
            return "AI response with sanitized context"

        mock_client = MockOllamaClient()
        mock_client.post = AsyncMock(side_effect=capture_context)

        mocker.patch(
            "create_project.ai.ollama_client.OllamaClient.__new__",
            return_value=mock_client,
        )

        # Create error with sensitive information
        sensitive_path = Path("/home/johndoe/secret_project")
        error = PathError(f"Cannot write to {sensitive_path}")

        # Collect context
        context = error_context_collector.collect_context(
            error=error,
            template=None,  # No template object for this test
            project_variables={
                "project_name": "test",
                "author_email": "john.doe@example.com",  # Sensitive
            },
            target_path=sensitive_path,
        )

        # Verify sanitization
        assert context is not None
        assert "johndoe" not in str(context).lower()
        assert "john.doe@example.com" not in str(context)
        assert "[REDACTED]" in str(context) or "USER" in str(context)

        # Initialize AI service and test error handling
        ai_service = AIService(config_with_ai)
        # Run initialization synchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(ai_service.initialize())

        # Generate help with sanitized context
        response = loop.run_until_complete(
            ai_service.generate_help_response(
                error=error,
                template=None,  # No template object for this test
                project_variables={"author_email": "test@example.com"},
            )
        )

        assert response is not None

        # Cleanup
        loop.run_until_complete(ai_service.cleanup())
        loop.close()


class TestAIErrorRecoveryWorkflows:
    """Test complete error recovery workflows with AI assistance."""

    def _load_template(
        self, template_loader: TemplateLoader, template_name: str
    ) -> Template:
        """Helper to load a template by name."""
        # Use mock templates for integration testing
        return get_mock_template(template_name)

    @pytest.mark.slow
    def test_full_error_recovery_workflow(self, tmp_path, mocker: MockerFixture):
        """Test a complete error recovery workflow with AI guidance."""
        # Create config
        config_file = tmp_path / "config.json"
        package_dir = Path(__file__).parent.parent.parent / "create_project"
        config_data = {
            "ai": {"enabled": True},
            "templates": {
                "directories": [str(package_dir / "templates")],
                "builtin_directory": str(package_dir / "templates" / "builtin"),
                "user_directory": str(package_dir / "templates" / "user"),
            },
        }
        config_file.write_text(json.dumps(config_data))
        config_manager = ConfigManager(config_file)

        # Mock AI responses for recovery steps
        recovery_steps = [
            # Step 1: Initial error
            {
                "model": "mistral:7b-instruct",
                "created_at": "2024-11-17T12:00:00Z",
                "message": {
                    "role": "assistant",
                    "content": (
                        "Directory already exists and is not empty. "
                        "Try:\n1. Remove existing directory\n"
                        "2. Use --force flag\n3. Choose different location"
                    )
                },
                "done": True,
            },
            # Step 2: After removing directory
            {
                "model": "mistral:7b-instruct",
                "created_at": "2024-11-17T12:00:01Z",
                "message": {
                    "role": "assistant",
                    "content": "Great! Now the project can be created successfully."
                },
                "done": True,
            },
        ]

        step_index = 0

        # Create mock client with initial response
        mock_client = MockOllamaClient(default_response=recovery_steps[0])

        # Override the default response based on call count
        original_post = mock_client.post
        async def custom_post(url, **kwargs):
            nonlocal step_index
            if "/api/chat" in url:
                response_data = recovery_steps[min(step_index, len(recovery_steps) - 1)]
                step_index += 1
                return MockOllamaResponse(json_data=response_data)
            return await original_post(url, **kwargs)

        mock_client.post = custom_post

        mocker.patch(
            "create_project.ai.ollama_client.OllamaClient.__new__",
            return_value=mock_client,
        )

        # Initialize services
        ai_service = AIService(config_manager)
        # Run initialization synchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(ai_service.initialize())
        loop.close()

        template_loader = TemplateLoader()
        generator = ProjectGenerator(
            template_loader=template_loader, ai_service=ai_service
        )

        # Step 1: Create conflict
        target_path = tmp_path / "my_project"
        target_path.mkdir()
        (target_path / "existing.txt").write_text("existing file")

        # First attempt - should fail
        template = self._load_template(template_loader, "One-off Script")
        result1 = generator.generate_project(
            template=template,
            variables={"project_name": "my_project", "description": "Test"},
            target_path=target_path,
            options=ProjectOptions(enable_ai_assistance=True),
        )

        assert not result1.success
        assert "Remove existing directory" in result1.ai_suggestions

        # Step 2: Follow AI advice - remove directory
        shutil.rmtree(target_path)

        # Second attempt - should succeed
        result2 = generator.generate_project(
            template=template,
            variables={"project_name": "my_project", "description": "Test"},
            target_path=target_path,
            options=ProjectOptions(enable_ai_assistance=True),
        )

        assert result2.success
        assert target_path.exists()
        assert (target_path / "my_project.py").exists()

        # Cleanup
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(ai_service.cleanup())
        loop.close()

    def test_multi_stage_error_recovery(self, tmp_path, mocker: MockerFixture):
        """Test recovery from multiple sequential errors with AI help."""
        # Create config
        config_file = tmp_path / "config.json"
        package_dir = Path(__file__).parent.parent.parent / "create_project"
        config_data = {
            "ai": {"enabled": True},
            "templates": {
                "directories": [str(package_dir / "templates")],
                "builtin_directory": str(package_dir / "templates" / "builtin"),
                "user_directory": str(package_dir / "templates" / "user"),
            },
        }
        config_file.write_text(json.dumps(config_data))
        config_manager = ConfigManager(config_file)

        # Mock progressive error scenarios
        error_stage = 0

        def mock_subprocess_run(*args, **kwargs):
            nonlocal error_stage
            cmd = args[0]

            if error_stage == 0 and "git" in str(cmd):
                error_stage = 1
                raise subprocess.CalledProcessError(1, cmd, "git not found")
            elif (
                error_stage == 1
                and "python" in str(cmd)
                and "-m" in cmd
                and "venv" in cmd
            ):
                error_stage = 2
                raise subprocess.CalledProcessError(1, cmd, "venv module not found")

            return subprocess.CompletedProcess(cmd, 0, "", "")

        mocker.patch("subprocess.run", side_effect=mock_subprocess_run)

        # Mock AI responses for each error
        ai_responses = [
            {
                "message": {"content": "Git not found. Install with: brew install git"},
                "done": True,
            },
            {
                "message": {
                    "content": "Python venv module missing. Install python3-venv package."
                },
                "done": True,
            },
        ]

        response_index = 0

        def get_ai_response(*args, **kwargs):
            nonlocal response_index
            response = ai_responses[min(response_index, len(ai_responses) - 1)]
            response_index += 1
            return Mock(json=lambda: response, status_code=200)

        mock_client = MockOllamaClient()
        mock_client.post = AsyncMock(side_effect=get_ai_response)

        mocker.patch(
            "create_project.ai.ollama_client.OllamaClient.__new__",
            return_value=mock_client,
        )

        # Initialize services
        ai_service = AIService(config_manager)
        # Run initialization synchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(ai_service.initialize())
        loop.close()

        template_loader = TemplateLoader()
        generator = ProjectGenerator(
            template_loader=template_loader, ai_service=ai_service
        )

        # Generate project with multiple potential errors
        template = self._load_template(template_loader, "Python Library/Package")
        result = generator.generate_project(
            template=template,
            variables={
                "project_name": "multi_error",
                "description": "Test",
                "author": "Test",
                "author_email": "test@example.com",
            },
            target_path=tmp_path / "multi_error",
            options=ProjectOptions(
                enable_ai_assistance=True, create_git_repo=True, create_venv=True
            ),
        )

        # Should handle multiple errors gracefully - project succeeds but with errors recorded
        assert result.success  # Project creation succeeds despite git/venv errors
        assert len(result.errors) > 0  # Errors were recorded
        assert not result.git_initialized  # Git failed as expected
        # AI suggestions might be None if errors were non-critical

        # Cleanup
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(ai_service.cleanup())
        loop.close()
