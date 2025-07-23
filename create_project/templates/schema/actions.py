# ABOUTME: Template actions schema definition using Pydantic models
# ABOUTME: Provides models for post-creation commands and actions

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class ActionType(str, Enum):
    """Types of template actions."""

    COMMAND = "command"
    PYTHON = "python"
    GIT = "git"
    COPY = "copy"
    MOVE = "move"
    DELETE = "delete"
    MKDIR = "mkdir"
    CHMOD = "chmod"


class Platform(str, Enum):
    """Supported platforms for actions."""

    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    UNIX = "unix"  # macOS + Linux


class TemplateAction(BaseModel):
    """Template action for post-creation commands."""

    name: str = Field(..., description="Action name for logging and identification")

    type: ActionType = Field(..., description="Type of action to perform")

    command: str = Field(..., description="Command to execute or action to perform")

    description: str = Field(
        ..., description="Human-readable description of the action"
    )

    working_directory: Optional[str] = Field(
        None, description="Working directory for the action (relative to project root)"
    )

    platforms: List[Platform] = Field(
        default_factory=lambda: [Platform.WINDOWS, Platform.MACOS, Platform.LINUX],
        description="Platforms where this action should run",
    )

    condition: Optional[str] = Field(
        None, description="Jinja2 condition for running this action"
    )

    required: bool = Field(
        default=True,
        description="Whether action failure should stop template generation",
    )

    timeout: Optional[int] = Field(None, description="Action timeout in seconds")

    environment: Dict[str, str] = Field(
        default_factory=dict, description="Environment variables for the action"
    )

    arguments: List[str] = Field(
        default_factory=list, description="Additional arguments for the action"
    )

    @field_validator("command")
    @classmethod
    def validate_command(cls, v):
        """Validate command is not empty."""
        if not v or not v.strip():
            raise ValueError("Command cannot be empty")
        return v.strip()

    @model_validator(mode="after")
    def validate_command_type_consistency(self):
        """Validate command based on action type."""
        command = self.command
        action_type = self.type

        if action_type == ActionType.PYTHON:
            # Python code should be valid
            if not command.strip().startswith(
                ("import ", "from ", "print(", "subprocess.")
            ):
                # Basic validation - should look like Python code
                pass
        elif action_type == ActionType.GIT:
            # Git commands should start with git
            if not command.strip().startswith("git "):
                raise ValueError("Git action command must start with 'git '")
        elif action_type == ActionType.COMMAND:
            # Shell commands - basic security check
            dangerous_commands = ["rm -rf", "del /f", "format", "fdisk", "mkfs"]
            if any(dangerous in command.lower() for dangerous in dangerous_commands):
                raise ValueError("Command contains potentially dangerous operations")

        return self

    @field_validator("working_directory")
    @classmethod
    def validate_working_directory(cls, v):
        """Validate working directory path."""
        if v is None:
            return v

        # Should be relative path
        if v.startswith("/") or ":" in v:
            raise ValueError("Working directory must be relative path")

        # No directory traversal
        if ".." in v:
            raise ValueError("Working directory cannot contain '..'")

        return v.strip()

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v):
        """Validate timeout value."""
        if v is not None and v <= 0:
            raise ValueError("Timeout must be positive")
        return v

    def is_supported_on_platform(self, platform: str) -> bool:
        """Check if action is supported on given platform."""
        platform_map = {
            "darwin": Platform.MACOS,
            "linux": Platform.LINUX,
            "win32": Platform.WINDOWS,
            "cygwin": Platform.WINDOWS,
        }

        current_platform = platform_map.get(platform.lower())
        if not current_platform:
            return False

        # Check direct match
        if current_platform in self.platforms:
            return True

        # Check UNIX platform (macOS + Linux)
        if Platform.UNIX in self.platforms and current_platform in [
            Platform.MACOS,
            Platform.LINUX,
        ]:
            return True

        return False

    def get_safe_command(self) -> str:
        """Get command with basic safety checks applied."""
        # This is a basic implementation - real security would be more complex
        command = self.command

        # Remove some dangerous patterns
        dangerous_patterns = [
            r"rm\s+-rf\s+/",
            r"del\s+/[fs]",
            r"format\s+[a-zA-Z]:",
            r">\s*/dev/null",
            r"&\s*$",
            r";\s*$",
        ]

        import re

        for pattern in dangerous_patterns:
            if re.search(pattern, command):
                raise ValueError(f"Command contains dangerous pattern: {pattern}")

        return command


class ActionGroup(BaseModel):
    """Group of related actions."""

    name: str = Field(..., description="Group name")

    description: str = Field(..., description="Group description")

    actions: List[TemplateAction] = Field(
        default_factory=list, description="Actions in this group"
    )

    condition: Optional[str] = Field(
        None, description="Condition for running this entire group"
    )

    parallel: bool = Field(
        default=False, description="Whether actions in this group can run in parallel"
    )

    continue_on_error: bool = Field(
        default=False,
        description="Whether to continue if an action in this group fails",
    )

    def validate_actions(self) -> List[str]:
        """Validate all actions in the group."""
        errors = []

        # Check for duplicate action names
        names = [action.name for action in self.actions]
        if len(names) != len(set(names)):
            duplicates = [name for name in set(names) if names.count(name) > 1]
            errors.append(
                f"Duplicate action names in group '{self.name}': {duplicates}"
            )

        return errors


class TemplateHooks(BaseModel):
    """Template hooks for different stages of project generation."""

    pre_generate: List[TemplateAction] = Field(
        default_factory=list, description="Actions to run before project generation"
    )

    post_generate: List[TemplateAction] = Field(
        default_factory=list, description="Actions to run after project generation"
    )

    pre_file: List[TemplateAction] = Field(
        default_factory=list, description="Actions to run before each file is generated"
    )

    post_file: List[TemplateAction] = Field(
        default_factory=list, description="Actions to run after each file is generated"
    )

    on_error: List[TemplateAction] = Field(
        default_factory=list, description="Actions to run when an error occurs"
    )

    cleanup: List[TemplateAction] = Field(
        default_factory=list, description="Actions to run for cleanup (always runs)"
    )

    def get_all_actions(self) -> List[TemplateAction]:
        """Get all actions from all hook stages."""
        all_actions = []
        all_actions.extend(self.pre_generate)
        all_actions.extend(self.post_generate)
        all_actions.extend(self.pre_file)
        all_actions.extend(self.post_file)
        all_actions.extend(self.on_error)
        all_actions.extend(self.cleanup)
        return all_actions

    def validate_hooks(self) -> List[str]:
        """Validate all hooks."""
        errors = []

        # Check for duplicate action names across all hooks
        all_actions = self.get_all_actions()
        names = [action.name for action in all_actions]
        if len(names) != len(set(names)):
            duplicates = [name for name in set(names) if names.count(name) > 1]
            errors.append(f"Duplicate action names across hooks: {duplicates}")

        return errors


class Config:
    """Pydantic configuration."""

    validate_assignment = True
    extra = "forbid"
