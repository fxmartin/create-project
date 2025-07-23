# ABOUTME: Git repository management for project generation
# ABOUTME: Handles git repository initialization and initial commit creation

"""
Git repository manager for project generation.

This module provides the GitManager class which handles git repository
operations including initialization, configuration, and initial commit
creation with proper error handling for missing git installations.
"""

import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from structlog import get_logger

from .exceptions import GitError


class GitConfig:
    """Git configuration for repository setup.

    Attributes:
        user_name: Git user name
        user_email: Git user email
        initial_commit_message: Message for initial commit
    """

    def __init__(
        self,
        user_name: Optional[str] = None,
        user_email: Optional[str] = None,
        initial_commit_message: str = "Initial commit",
    ) -> None:
        """Initialize git configuration.

        Args:
            user_name: Git user name (uses global config if None)
            user_email: Git user email (uses global config if None)
            initial_commit_message: Message for initial commit
        """
        self.user_name = user_name
        self.user_email = user_email
        self.initial_commit_message = initial_commit_message


class GitManager:
    """Git repository manager for project generation.

    This class handles git repository operations including:
    - Checking git availability
    - Repository initialization
    - Configuration setup
    - Initial commit creation
    - Error handling for missing git installations

    Attributes:
        logger: Structured logger for operations
        git_path: Path to git executable (cached after first check)
    """

    def __init__(self) -> None:
        """Initialize the GitManager."""
        self.logger = get_logger(__name__)
        self.git_path: Optional[str] = None

        # Cache git availability check
        self._git_available = self.is_git_available()
        self.logger.info(
            "GitManager initialized",
            git_available=self._git_available,
            git_path=self.git_path,
        )

    def is_git_available(self) -> bool:
        """Check if git is installed and accessible.

        Returns:
            True if git is available, False otherwise
        """
        try:
            # Try to find git executable
            git_path = shutil.which("git")
            if not git_path:
                self.logger.warning("Git executable not found in PATH")
                return False

            # Verify git works by getting version
            result = subprocess.run(
                [git_path, "--version"], capture_output=True, text=True, timeout=10
            )

            if result.returncode != 0:
                self.logger.warning(
                    "Git version check failed",
                    returncode=result.returncode,
                    stderr=result.stderr,
                )
                return False

            self.git_path = git_path
            self.logger.debug(
                "Git availability confirmed",
                git_path=git_path,
                version_output=result.stdout.strip(),
            )
            return True

        except subprocess.TimeoutExpired:
            self.logger.warning("Git version check timed out")
            return False
        except Exception as e:
            self.logger.warning("Git availability check failed", error=str(e))
            return False

    def init_repository(
        self, project_path: Path, git_config: Optional[GitConfig] = None
    ) -> None:
        """Initialize git repository in project directory.

        Args:
            project_path: Path to project directory
            git_config: Optional git configuration

        Raises:
            GitError: If git is not available or initialization fails
        """
        if not self._git_available:
            raise GitError(
                "Git is not available - repository initialization skipped",
                details={"project_path": str(project_path)},
            )

        if not project_path.exists():
            raise GitError(
                f"Project directory does not exist: {project_path}",
                details={"project_path": str(project_path)},
            )

        if not project_path.is_dir():
            raise GitError(
                f"Project path is not a directory: {project_path}",
                details={"project_path": str(project_path)},
            )

        try:
            # Initialize git repository
            self.logger.info(
                "Initializing git repository", project_path=str(project_path)
            )

            result = self._run_git_command(["init"], cwd=project_path, timeout=30)

            if result.returncode != 0:
                raise GitError(
                    f"Git init failed: {result.stderr}",
                    details={
                        "project_path": str(project_path),
                        "command": "git init",
                        "stderr": result.stderr,
                    },
                )

            # Configure git if config provided
            if git_config:
                self._configure_repository(project_path, git_config)

            self.logger.info(
                "Git repository initialized successfully",
                project_path=str(project_path),
            )

        except subprocess.TimeoutExpired:
            raise GitError(
                "Git init timed out", details={"project_path": str(project_path)}
            )
        except Exception as e:
            raise GitError(
                f"Failed to initialize git repository: {e}",
                details={"project_path": str(project_path)},
                original_error=e,
            ) from e

    def create_initial_commit(
        self,
        project_path: Path,
        message: Optional[str] = None,
        git_config: Optional[GitConfig] = None,
    ) -> None:
        """Create initial commit with all generated files.

        Args:
            project_path: Path to project directory
            message: Commit message (uses config default if None)
            git_config: Optional git configuration

        Raises:
            GitError: If git is not available or commit creation fails
        """
        if not self._git_available:
            raise GitError(
                "Git is not available - initial commit skipped",
                details={"project_path": str(project_path)},
            )

        if not (project_path / ".git").exists():
            raise GitError(
                "No git repository found - initialize repository first",
                details={"project_path": str(project_path)},
            )

        try:
            commit_message = message
            if not commit_message and git_config:
                commit_message = git_config.initial_commit_message
            if not commit_message:
                commit_message = "Initial commit"

            self.logger.info(
                "Creating initial commit",
                project_path=str(project_path),
                message=commit_message,
            )

            # Add all files
            result = self._run_git_command(["add", "."], cwd=project_path, timeout=60)

            if result.returncode != 0:
                raise GitError(
                    f"Git add failed: {result.stderr}",
                    details={
                        "project_path": str(project_path),
                        "command": "git add .",
                        "stderr": result.stderr,
                    },
                )

            # Create commit
            result = self._run_git_command(
                ["commit", "-m", commit_message], cwd=project_path, timeout=60
            )

            if result.returncode != 0:
                # Check if it's because there are no changes
                if "nothing to commit" in result.stdout.lower():
                    self.logger.info(
                        "No files to commit - repository is clean",
                        project_path=str(project_path),
                    )
                    return

                raise GitError(
                    f"Git commit failed: {result.stderr}",
                    details={
                        "project_path": str(project_path),
                        "command": f"git commit -m '{commit_message}'",
                        "stderr": result.stderr,
                    },
                )

            self.logger.info(
                "Initial commit created successfully",
                project_path=str(project_path),
                message=commit_message,
            )

        except subprocess.TimeoutExpired:
            raise GitError(
                "Git commit timed out", details={"project_path": str(project_path)}
            )
        except Exception as e:
            raise GitError(
                f"Failed to create initial commit: {e}",
                details={"project_path": str(project_path)},
                original_error=e,
            ) from e

    def get_repository_status(self, project_path: Path) -> Dict[str, Any]:
        """Get git repository status information.

        Args:
            project_path: Path to project directory

        Returns:
            Dictionary with repository status information

        Raises:
            GitError: If git is not available or status check fails
        """
        if not self._git_available:
            return {
                "initialized": False,
                "git_available": False,
                "error": "Git is not available",
            }

        try:
            git_dir = project_path / ".git"
            if not git_dir.exists():
                return {
                    "initialized": False,
                    "git_available": True,
                    "error": "No git repository found",
                }

            # Get status
            result = self._run_git_command(
                ["status", "--porcelain"], cwd=project_path, timeout=30
            )

            if result.returncode != 0:
                return {
                    "initialized": True,
                    "git_available": True,
                    "error": f"Git status failed: {result.stderr}",
                }

            # Parse status output
            changes = result.stdout.strip().split("\n") if result.stdout.strip() else []

            return {
                "initialized": True,
                "git_available": True,
                "clean": len(changes) == 0,
                "changes_count": len(changes),
                "changes": changes,
            }

        except subprocess.TimeoutExpired:
            return {
                "initialized": True,
                "git_available": True,
                "error": "Git status timed out",
            }
        except Exception as e:
            return {
                "initialized": True,
                "git_available": True,
                "error": f"Failed to get repository status: {e}",
            }

    def _configure_repository(self, project_path: Path, git_config: GitConfig) -> None:
        """Configure git repository settings.

        Args:
            project_path: Path to project directory
            git_config: Git configuration

        Raises:
            GitError: If configuration fails
        """
        if git_config.user_name:
            result = self._run_git_command(
                ["config", "user.name", git_config.user_name],
                cwd=project_path,
                timeout=15,
            )

            if result.returncode != 0:
                self.logger.warning(
                    "Failed to set git user.name",
                    user_name=git_config.user_name,
                    stderr=result.stderr,
                )

        if git_config.user_email:
            result = self._run_git_command(
                ["config", "user.email", git_config.user_email],
                cwd=project_path,
                timeout=15,
            )

            if result.returncode != 0:
                self.logger.warning(
                    "Failed to set git user.email",
                    user_email=git_config.user_email,
                    stderr=result.stderr,
                )

        self.logger.debug(
            "Git repository configured",
            project_path=str(project_path),
            user_name=git_config.user_name,
            user_email=git_config.user_email,
        )

    def _run_git_command(
        self, args: List[str], cwd: Path, timeout: int = 60
    ) -> subprocess.CompletedProcess:
        """Run a git command with error handling.

        Args:
            args: Git command arguments (without 'git')
            cwd: Working directory
            timeout: Command timeout in seconds

        Returns:
            CompletedProcess result
        """
        if not self.git_path:
            raise GitError("Git executable not found")

        command = [self.git_path] + args

        self.logger.debug(
            "Running git command", command=command, cwd=str(cwd), timeout=timeout
        )

        return subprocess.run(
            command, cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
