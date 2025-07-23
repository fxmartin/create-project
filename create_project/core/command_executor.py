# ABOUTME: Secure command executor for post-creation template commands
# ABOUTME: Handles command validation, whitelisting, and execution with security

"""
Command executor for post-creation template commands.

This module provides the CommandExecutor class which safely executes
template-defined post-creation commands with comprehensive security validation,
command whitelisting, injection attack prevention, and timeout handling.
"""

import shlex
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Union

from structlog import get_logger

from .exceptions import ProjectGenerationError, SecurityError


@dataclass
class ExecutionResult:
    """Result of command execution.

    Attributes:
        success: Whether command executed successfully
        command: The executed command
        returncode: Process return code
        stdout: Command standard output
        stderr: Command standard error
        duration: Execution duration in seconds
        timeout: Whether command timed out
    """

    success: bool
    command: str
    returncode: int
    stdout: str
    stderr: str
    duration: float
    timeout: bool = False


class CommandExecutor:
    """Secure command executor for post-creation commands.

    This class provides secure execution of template-defined post-creation
    commands with comprehensive security validation including:
    - Command whitelisting to prevent arbitrary code execution
    - Argument validation and sanitization
    - Injection attack prevention
    - Timeout handling for long-running commands
    - Comprehensive logging and error handling

    Attributes:
        logger: Structured logger for operations
        allowed_commands: Set of whitelisted command names
        max_timeout: Maximum allowed timeout for commands
        validate_args: Whether to validate command arguments
    """

    # Whitelist of allowed command executables
    ALLOWED_COMMANDS: Set[str] = {
        # Python tools
        "pip",
        "pip3",
        "python",
        "python3",
        "uv",
        # Node.js tools
        "npm",
        "yarn",
        "node",
        "npx",
        # Package managers
        "poetry",
        "pipenv",
        "conda",
        # Version control
        "git",
        # Build tools
        "make",
        "cmake",
        "cargo",
        "go",
        # File operations
        "chmod",
        "mkdir",
        "touch",
        "cp",
        "mv",
        # Text processing
        "echo",
        "cat",
        # System info
        "which",
        "whereis",
    }

    # Arguments that could be dangerous in any context
    DANGEROUS_ARGS: Set[str] = {
        # Shell operators
        "&&",
        "||",
        ";",
        "|",
        ">",
        ">>",
        "<",
        "<<",
        # Command substitution
        "$(",
        "`",
        "${",
        # Dangerous paths
        "/etc/passwd",
        "/etc/shadow",
        "/etc/hosts",
        "../etc/",
        "../../etc/",
        # Dangerous commands hidden in args
        "rm",
        "del",
        "format",
        "sudo",
        "su",
    }

    def __init__(
        self,
        additional_allowed_commands: Optional[Set[str]] = None,
        max_timeout: int = 300,
        validate_args: bool = True,
    ) -> None:
        """Initialize the CommandExecutor.

        Args:
            additional_allowed_commands: Additional commands to allow
            max_timeout: Maximum timeout in seconds (default: 5 minutes)
            validate_args: Whether to validate command arguments
        """
        self.logger = get_logger(__name__)

        # Combine default and additional allowed commands
        self.allowed_commands = self.ALLOWED_COMMANDS.copy()
        if additional_allowed_commands:
            self.allowed_commands.update(additional_allowed_commands)

        self.max_timeout = max_timeout
        self.validate_args = validate_args

        self.logger.info(
            "CommandExecutor initialized",
            allowed_commands=len(self.allowed_commands),
            max_timeout=max_timeout,
            validate_args=validate_args,
        )

    def execute_command(
        self,
        command: str,
        cwd: Union[str, Path],
        timeout: Optional[int] = None,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> ExecutionResult:
        """Execute a single command with security validation.

        Args:
            command: Command string to execute
            cwd: Working directory for command execution
            timeout: Command timeout in seconds (uses max_timeout if None)
            env_vars: Additional environment variables

        Returns:
            ExecutionResult with execution details

        Raises:
            SecurityError: If command fails security validation
            ProjectGenerationError: If execution setup fails
        """
        start_time = time.time()

        # Validate and parse command
        parsed_command = self._validate_and_parse_command(command)

        # Setup execution environment
        cwd_path = Path(cwd).resolve()
        if not cwd_path.exists():
            raise ProjectGenerationError(
                f"Working directory does not exist: {cwd_path}",
                details={"command": command, "cwd": str(cwd_path)},
            )

        effective_timeout = min(timeout or self.max_timeout, self.max_timeout)

        self.logger.info(
            "Executing command",
            command=command,
            cwd=str(cwd_path),
            timeout=effective_timeout,
        )

        try:
            # Prepare environment
            import os

            env = os.environ.copy()
            if env_vars:
                env.update(env_vars)

            # Execute command
            process = subprocess.run(
                parsed_command,
                cwd=cwd_path,
                capture_output=True,
                text=True,
                timeout=effective_timeout,
                env=env,
            )

            duration = time.time() - start_time

            result = ExecutionResult(
                success=process.returncode == 0,
                command=command,
                returncode=process.returncode,
                stdout=process.stdout,
                stderr=process.stderr,
                duration=duration,
                timeout=False,
            )

            self.logger.info(
                "Command executed",
                command=command,
                returncode=process.returncode,
                duration=duration,
                success=result.success,
            )

            if not result.success:
                self.logger.warning(
                    "Command failed",
                    command=command,
                    returncode=process.returncode,
                    stderr=process.stderr,
                )

            return result

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time

            result = ExecutionResult(
                success=False,
                command=command,
                returncode=-1,
                stdout="",
                stderr=f"Command timed out after {effective_timeout} seconds",
                duration=duration,
                timeout=True,
            )

            self.logger.error(
                "Command timed out",
                command=command,
                timeout=effective_timeout,
                duration=duration,
            )

            return result

        except Exception as e:
            duration = time.time() - start_time

            result = ExecutionResult(
                success=False,
                command=command,
                returncode=-1,
                stdout="",
                stderr=f"Execution failed: {e}",
                duration=duration,
            )

            self.logger.error(
                "Command execution failed",
                command=command,
                error=str(e),
                duration=duration,
            )

            return result

    def execute_commands(
        self,
        commands: List[str],
        cwd: Union[str, Path],
        timeout_per_command: Optional[int] = None,
        env_vars: Optional[Dict[str, str]] = None,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
        stop_on_failure: bool = True,
    ) -> List[ExecutionResult]:
        """Execute multiple commands in sequence.

        Args:
            commands: List of command strings to execute
            cwd: Working directory for command execution
            timeout_per_command: Timeout per command in seconds
            env_vars: Additional environment variables
            progress_callback: Optional progress callback (message, current, total)
            stop_on_failure: Whether to stop on first failure

        Returns:
            List of ExecutionResult for each command
        """
        if not commands:
            self.logger.info("No commands to execute")
            return []

        self.logger.info(
            "Executing command sequence",
            command_count=len(commands),
            cwd=str(cwd),
            stop_on_failure=stop_on_failure,
        )

        results: List[ExecutionResult] = []

        for i, command in enumerate(commands):
            if progress_callback:
                progress_callback(f"Executing: {command[:50]}...", i, len(commands))

            try:
                result = self.execute_command(
                    command=command,
                    cwd=cwd,
                    timeout=timeout_per_command,
                    env_vars=env_vars,
                )

                results.append(result)

                if not result.success and stop_on_failure:
                    self.logger.error(
                        "Stopping command sequence due to failure",
                        failed_command=command,
                        executed_count=len(results),
                        total_count=len(commands),
                    )
                    break

            except Exception as e:
                error_result = ExecutionResult(
                    success=False,
                    command=command,
                    returncode=-1,
                    stdout="",
                    stderr=f"Command validation or setup failed: {e}",
                    duration=0.0,
                )

                results.append(error_result)

                if stop_on_failure:
                    self.logger.error(
                        "Stopping command sequence due to validation error",
                        failed_command=command,
                        error=str(e),
                        executed_count=len(results),
                        total_count=len(commands),
                    )
                    break

        if progress_callback:
            progress_callback("Command sequence completed", len(results), len(commands))

        successful_count = sum(1 for result in results if result.success)

        self.logger.info(
            "Command sequence completed",
            total_commands=len(commands),
            executed_commands=len(results),
            successful_commands=successful_count,
            failed_commands=len(results) - successful_count,
        )

        return results

    def _validate_and_parse_command(self, command: str) -> List[str]:
        """Validate and parse command string for security.

        Args:
            command: Command string to validate

        Returns:
            Parsed command as list of arguments

        Raises:
            SecurityError: If command fails security validation
        """
        if not command or not command.strip():
            raise SecurityError("Empty command not allowed")

        # Remove leading/trailing whitespace
        command = command.strip()

        # Check for obviously dangerous patterns
        if any(
            dangerous in command.lower()
            for dangerous in ["rm -rf", "format c:", "del /s"]
        ):
            raise SecurityError(
                f"Dangerous command pattern detected: {command}",
                details={"command": command},
            )

        # Parse command safely
        try:
            parsed = shlex.split(command)
        except ValueError as e:
            raise SecurityError(
                f"Invalid command syntax: {e}", details={"command": command}
            ) from e

        if not parsed:
            raise SecurityError("Empty parsed command")

        # Extract command name (first argument)
        command_name = Path(parsed[0]).name.lower()

        # Check if command is whitelisted
        if command_name not in self.allowed_commands:
            raise SecurityError(
                f"Command '{command_name}' not in whitelist",
                details={
                    "command": command,
                    "command_name": command_name,
                    "allowed_commands": sorted(self.allowed_commands),
                },
            )

        # Validate arguments if enabled
        if self.validate_args and len(parsed) > 1:
            self._validate_arguments(parsed[1:], command)

        self.logger.debug(
            "Command validation successful",
            command=command,
            parsed_args=len(parsed),
            command_name=command_name,
        )

        return parsed

    def _validate_arguments(self, args: List[str], original_command: str) -> None:
        """Validate command arguments for security.

        Args:
            args: Command arguments to validate
            original_command: Original command string for error context

        Raises:
            SecurityError: If arguments contain dangerous patterns
        """
        for arg in args:
            # Check for dangerous argument patterns
            arg_lower = arg.lower()

            if any(dangerous in arg_lower for dangerous in self.DANGEROUS_ARGS):
                raise SecurityError(
                    f"Dangerous argument pattern detected: {arg}",
                    details={"command": original_command, "dangerous_arg": arg},
                )

            # Check for shell metacharacters that could enable injection
            if any(char in arg for char in ["$", "`", ";", "|", "&", ">", "<"]):
                # Allow some safe uses
                if not self._is_safe_metachar_usage(arg):
                    raise SecurityError(
                        f"Potentially dangerous shell metacharacter in argument: {arg}",
                        details={"command": original_command, "suspicious_arg": arg},
                    )

            # Check for absolute paths to sensitive directories
            if arg.startswith("/etc/") or "/../etc/" in arg:
                raise SecurityError(
                    f"Access to sensitive system directory not allowed: {arg}",
                    details={"command": original_command, "sensitive_path": arg},
                )

        self.logger.debug(
            "Argument validation successful",
            command=original_command,
            arg_count=len(args),
        )

    def _is_safe_metachar_usage(self, arg: str) -> bool:
        """Check if metacharacter usage is safe.

        Args:
            arg: Argument to check

        Returns:
            True if usage appears safe
        """
        # Allow $ in version specifications like "package>=1.0.0"
        if "$" in arg and any(op in arg for op in [">=", "<=", "==", "!=", "~=", ">"]):
            return True

        # Allow > and < in version specifications
        if any(op in arg for op in [">= ", "<= ", "== ", "!= ", "~= ", "> ", "< "]):
            return True

        # Add more safe patterns as needed
        return False
