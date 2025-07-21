# ABOUTME: Unit tests for template action models
# ABOUTME: Tests post-creation actions and hooks with security validation

"""Tests for template action models."""

import pytest
from pydantic import ValidationError

from create_project.templates.schema.actions import (
    ActionGroup,
    ActionType,
    Platform,
    TemplateAction,
    TemplateHooks,
)


class TestTemplateAction:
    """Test template action model."""

    def test_minimal_action(self):
        """Test creating action with minimal fields."""
        action = TemplateAction(
            name="install",
            type=ActionType.COMMAND,
            command="npm install",
            description="Install npm dependencies",
        )
        assert action.name == "install"
        assert action.type == ActionType.COMMAND
        assert action.command == "npm install"
        assert action.required is True
        assert action.platforms == [Platform.WINDOWS, Platform.MACOS, Platform.LINUX]

    def test_action_with_all_fields(self):
        """Test action with all optional fields."""
        action = TemplateAction(
            name="setup",
            type=ActionType.PYTHON,
            command="print('Setting up project')",
            description="Initial setup",
            working_directory="src",
            platforms=[Platform.UNIX],
            condition="use_typescript == true",
            required=False,
            timeout=120,
            environment={"NODE_ENV": "development"},
            arguments=["--verbose", "--color"],
        )
        assert action.working_directory == "src"
        assert action.platforms == [Platform.UNIX]
        assert action.condition == "use_typescript == true"
        assert action.required is False
        assert action.timeout == 120
        assert action.environment == {"NODE_ENV": "development"}
        assert action.arguments == ["--verbose", "--color"]

    def test_empty_command_validation(self):
        """Test that empty commands are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            TemplateAction(
                name="empty",
                type=ActionType.COMMAND,
                command="",
                description="Empty command",
            )
        assert "Command cannot be empty" in str(exc_info.value)

    def test_dangerous_command_validation(self):
        """Test dangerous command patterns are rejected."""
        dangerous_commands = [
            "rm -rf /",
            "del /f /s /q C:\\*",
            "format C:",
            "fdisk /dev/sda",
        ]

        for cmd in dangerous_commands:
            with pytest.raises(ValidationError) as exc_info:
                TemplateAction(
                    name="dangerous",
                    type=ActionType.COMMAND,
                    command=cmd,
                    description="Dangerous command",
                )
            assert "dangerous" in str(exc_info.value).lower()

    def test_git_command_validation(self):
        """Test git commands must start with 'git'."""
        # Valid git command
        action = TemplateAction(
            name="git_init",
            type=ActionType.GIT,
            command="git init",
            description="Initialize git repo",
        )
        assert action.command == "git init"

        # Invalid git command
        with pytest.raises(ValidationError) as exc_info:
            TemplateAction(
                name="bad_git",
                type=ActionType.GIT,
                command="initialize repo",
                description="Bad git command",
            )
        assert "must start with 'git '" in str(exc_info.value)

    def test_working_directory_validation(self):
        """Test working directory validation."""
        # Valid relative path
        action = TemplateAction(
            name="test",
            type=ActionType.COMMAND,
            command="echo test",
            description="Test",
            working_directory="src/components",
        )
        assert action.working_directory == "src/components"

        # Absolute path should fail
        with pytest.raises(ValidationError):
            TemplateAction(
                name="test",
                type=ActionType.COMMAND,
                command="echo test",
                description="Test",
                working_directory="/absolute/path",
            )

        # Path traversal should fail
        with pytest.raises(ValidationError):
            TemplateAction(
                name="test",
                type=ActionType.COMMAND,
                command="echo test",
                description="Test",
                working_directory="../../../etc",
            )

    def test_timeout_validation(self):
        """Test timeout validation."""
        # Valid timeout
        action = TemplateAction(
            name="test",
            type=ActionType.COMMAND,
            command="npm test",
            description="Run tests",
            timeout=300,
        )
        assert action.timeout == 300

        # Negative timeout should fail
        with pytest.raises(ValidationError):
            TemplateAction(
                name="test",
                type=ActionType.COMMAND,
                command="npm test",
                description="Run tests",
                timeout=-1,
            )

    def test_platform_support(self):
        """Test platform support checking."""
        # Test UNIX platform (supports both macOS and Linux)
        action = TemplateAction(
            name="unix_only",
            type=ActionType.COMMAND,
            command="chmod +x script.sh",
            description="Make executable",
            platforms=[Platform.UNIX],
        )

        assert action.is_supported_on_platform("darwin") is True  # macOS
        assert action.is_supported_on_platform("linux") is True
        assert action.is_supported_on_platform("win32") is False

        # Test specific platform
        action = TemplateAction(
            name="windows_only",
            type=ActionType.COMMAND,
            command="dir",
            description="List directory",
            platforms=[Platform.WINDOWS],
        )

        assert action.is_supported_on_platform("win32") is True
        assert action.is_supported_on_platform("darwin") is False
        assert action.is_supported_on_platform("linux") is False

    def test_get_safe_command(self):
        """Test safe command retrieval."""
        # Safe command
        action = TemplateAction(
            name="safe",
            type=ActionType.COMMAND,
            command="npm install",
            description="Install dependencies",
        )
        assert action.get_safe_command() == "npm install"

        # Command with dangerous pattern
        action = TemplateAction(
            name="test",
            type=ActionType.COMMAND,
            command="echo test",  # Safe base command
            description="Test",
        )
        # Manually set a dangerous command to test get_safe_command
        action.command = "rm -rf /"

        with pytest.raises(ValueError) as exc_info:
            action.get_safe_command()
        assert "dangerous pattern" in str(exc_info.value)


class TestActionGroup:
    """Test action group model."""

    def test_action_group(self):
        """Test creating action group."""
        actions = [
            TemplateAction(
                name="install",
                type=ActionType.COMMAND,
                command="npm install",
                description="Install dependencies",
            ),
            TemplateAction(
                name="build",
                type=ActionType.COMMAND,
                command="npm run build",
                description="Build project",
            ),
        ]

        group = ActionGroup(
            name="Setup project",
            description="Initial project setup",
            actions=actions,
            condition="use_npm == true",
            parallel=False,
            continue_on_error=True,
        )

        assert group.name == "Setup project"
        assert len(group.actions) == 2
        assert group.condition == "use_npm == true"
        assert group.parallel is False
        assert group.continue_on_error is True

    def test_duplicate_action_names(self):
        """Test detection of duplicate action names."""
        actions = [
            TemplateAction(
                name="install",
                type=ActionType.COMMAND,
                command="npm install",
                description="Install npm",
            ),
            TemplateAction(
                name="install",  # Duplicate name
                type=ActionType.COMMAND,
                command="pip install -r requirements.txt",
                description="Install pip",
            ),
        ]

        group = ActionGroup(name="Setup", description="Setup actions", actions=actions)

        errors = group.validate_actions()
        assert len(errors) == 1
        assert "Duplicate action names" in errors[0]
        assert "'install'" in errors[0]


class TestTemplateHooks:
    """Test template hooks model."""

    def test_empty_hooks(self):
        """Test creating empty hooks."""
        hooks = TemplateHooks()
        assert hooks.pre_generate == []
        assert hooks.post_generate == []
        assert hooks.pre_file == []
        assert hooks.post_file == []
        assert hooks.on_error == []
        assert hooks.cleanup == []

    def test_hooks_with_actions(self):
        """Test hooks with various actions."""
        pre_gen_action = TemplateAction(
            name="validate",
            type=ActionType.PYTHON,
            command="print('Validating environment')",
            description="Validate environment",
        )

        post_gen_action = TemplateAction(
            name="install",
            type=ActionType.COMMAND,
            command="npm install",
            description="Install dependencies",
        )

        error_action = TemplateAction(
            name="cleanup_error",
            type=ActionType.DELETE,
            command="temp/",
            description="Remove temp files on error",
        )

        hooks = TemplateHooks(
            pre_generate=[pre_gen_action],
            post_generate=[post_gen_action],
            on_error=[error_action],
        )

        assert len(hooks.pre_generate) == 1
        assert len(hooks.post_generate) == 1
        assert len(hooks.on_error) == 1

        # Test get_all_actions
        all_actions = hooks.get_all_actions()
        assert len(all_actions) == 3
        assert pre_gen_action in all_actions
        assert post_gen_action in all_actions
        assert error_action in all_actions

    def test_duplicate_action_names_across_hooks(self):
        """Test detection of duplicate names across different hooks."""
        action1 = TemplateAction(
            name="setup",
            type=ActionType.COMMAND,
            command="echo 'pre'",
            description="Pre setup",
        )

        action2 = TemplateAction(
            name="setup",  # Same name in different hook
            type=ActionType.COMMAND,
            command="echo 'post'",
            description="Post setup",
        )

        hooks = TemplateHooks(pre_generate=[action1], post_generate=[action2])

        errors = hooks.validate_hooks()
        assert len(errors) == 1
        assert "Duplicate action names across hooks" in errors[0]
        assert "'setup'" in errors[0]

    def test_all_hook_types(self):
        """Test all hook types can be used."""
        hooks = TemplateHooks(
            pre_generate=[
                TemplateAction(
                    name="pre_gen",
                    type=ActionType.COMMAND,
                    command="echo 'Starting'",
                    description="Pre-generate",
                )
            ],
            post_generate=[
                TemplateAction(
                    name="post_gen",
                    type=ActionType.COMMAND,
                    command="echo 'Done'",
                    description="Post-generate",
                )
            ],
            pre_file=[
                TemplateAction(
                    name="pre_file",
                    type=ActionType.PYTHON,
                    command="print('Creating file')",
                    description="Pre-file",
                )
            ],
            post_file=[
                TemplateAction(
                    name="post_file",
                    type=ActionType.PYTHON,
                    command="print('File created')",
                    description="Post-file",
                )
            ],
            on_error=[
                TemplateAction(
                    name="error_handler",
                    type=ActionType.PYTHON,
                    command="print('Error occurred')",
                    description="Error handler",
                )
            ],
            cleanup=[
                TemplateAction(
                    name="cleanup",
                    type=ActionType.DELETE,
                    command="temp/",
                    description="Cleanup temp files",
                )
            ],
        )

        assert len(hooks.pre_generate) == 1
        assert len(hooks.post_generate) == 1
        assert len(hooks.pre_file) == 1
        assert len(hooks.post_file) == 1
        assert len(hooks.on_error) == 1
        assert len(hooks.cleanup) == 1

        all_actions = hooks.get_all_actions()
        assert len(all_actions) == 6
