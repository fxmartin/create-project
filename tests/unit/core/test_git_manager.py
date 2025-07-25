# ABOUTME: Unit tests for git manager module
# ABOUTME: Tests git repository initialization, configuration, and commits

"""Unit tests for git manager module."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, call

import pytest

from create_project.core.git_manager import GitManager, GitConfig
from create_project.core.exceptions import GitError


class TestGitConfig:
    """Test GitConfig class."""

    def test_init_defaults(self):
        """Test GitConfig initialization with defaults."""
        config = GitConfig()
        
        assert config.user_name is None
        assert config.user_email is None
        assert config.initial_commit_message == "Initial commit"

    def test_init_custom(self):
        """Test GitConfig initialization with custom values."""
        config = GitConfig(
            user_name="John Doe",
            user_email="john@example.com",
            initial_commit_message="First commit",
        )
        
        assert config.user_name == "John Doe"
        assert config.user_email == "john@example.com"
        assert config.initial_commit_message == "First commit"


class TestGitManager:
    """Test GitManager functionality."""

    @pytest.fixture
    def mock_which(self):
        """Mock shutil.which for git detection."""
        with patch("shutil.which") as mock:
            mock.return_value = "/usr/bin/git"
            yield mock

    @pytest.fixture
    def mock_subprocess_run(self):
        """Mock subprocess.run for git commands."""
        with patch("subprocess.run") as mock:
            # Default successful git version check
            mock.return_value = MagicMock(
                returncode=0,
                stdout="git version 2.39.0",
                stderr="",
            )
            yield mock

    @pytest.fixture
    def git_manager(self, mock_which, mock_subprocess_run):
        """Create a GitManager instance with mocked git."""
        return GitManager()

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project directory."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        return project_dir

    def test_init_with_git_available(self, mock_which, mock_subprocess_run):
        """Test GitManager initialization with git available."""
        manager = GitManager()
        
        assert manager._git_available is True
        assert manager.git_path == "/usr/bin/git"
        
        # Verify git version was checked
        mock_which.assert_called_once_with("git")
        mock_subprocess_run.assert_called_once()
        args = mock_subprocess_run.call_args[0][0]
        assert args == ["/usr/bin/git", "--version"]

    def test_init_without_git(self, mock_which):
        """Test GitManager initialization without git."""
        mock_which.return_value = None
        
        manager = GitManager()
        
        assert manager._git_available is False
        assert manager.git_path is None

    def test_init_with_broken_git(self, mock_which, mock_subprocess_run):
        """Test GitManager initialization with broken git installation."""
        mock_subprocess_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="git: command not found",
        )
        
        manager = GitManager()
        
        assert manager._git_available is False
        assert manager.git_path is None

    def test_init_with_timeout(self, mock_which, mock_subprocess_run):
        """Test GitManager initialization with git timeout."""
        mock_subprocess_run.side_effect = subprocess.TimeoutExpired(
            cmd=["git", "--version"],
            timeout=10,
        )
        
        manager = GitManager()
        
        assert manager._git_available is False
        assert manager.git_path is None

    def test_init_with_exception(self, mock_which, mock_subprocess_run):
        """Test GitManager initialization with exception."""
        mock_subprocess_run.side_effect = OSError("Command failed")
        
        manager = GitManager()
        
        assert manager._git_available is False
        assert manager.git_path is None

    def test_is_git_available_true(self, mock_which, mock_subprocess_run):
        """Test is_git_available returns True when git exists."""
        manager = GitManager()
        
        assert manager.is_git_available() is True

    def test_is_git_available_false(self, mock_which):
        """Test is_git_available returns False when git missing."""
        mock_which.return_value = None
        manager = GitManager()
        
        # Reset the cached value to test the method
        manager._git_available = None
        assert manager.is_git_available() is False

    def test_init_repository_success(self, git_manager, mock_subprocess_run, temp_project):
        """Test successful repository initialization."""
        # Reset mock to track git init call
        mock_subprocess_run.reset_mock()
        
        git_manager.init_repository(temp_project)
        
        # Verify git init was called
        mock_subprocess_run.assert_called_once()
        args = mock_subprocess_run.call_args[0][0]
        assert args == ["/usr/bin/git", "init"]
        assert mock_subprocess_run.call_args[1]["cwd"] == temp_project

    def test_init_repository_with_config(self, git_manager, mock_subprocess_run, temp_project):
        """Test repository initialization with git config."""
        mock_subprocess_run.reset_mock()
        
        config = GitConfig(
            user_name="Test User",
            user_email="test@example.com",
        )
        
        git_manager.init_repository(temp_project, config)
        
        # Should call: git init, git config user.name, git config user.email
        assert mock_subprocess_run.call_count == 3
        
        calls = mock_subprocess_run.call_args_list
        assert calls[0][0][0] == ["/usr/bin/git", "init"]
        assert calls[1][0][0] == ["/usr/bin/git", "config", "user.name", "Test User"]
        assert calls[2][0][0] == ["/usr/bin/git", "config", "user.email", "test@example.com"]

    def test_init_repository_without_git(self, temp_project):
        """Test repository initialization without git available."""
        with patch("shutil.which", return_value=None):
            manager = GitManager()
        
        with pytest.raises(GitError) as exc_info:
            manager.init_repository(temp_project)
        
        assert "Git is not available" in str(exc_info.value)

    def test_init_repository_nonexistent_path(self, git_manager):
        """Test repository initialization with non-existent path."""
        with pytest.raises(GitError) as exc_info:
            git_manager.init_repository(Path("/nonexistent/path"))
        
        assert "does not exist" in str(exc_info.value)

    def test_init_repository_not_directory(self, git_manager, tmp_path):
        """Test repository initialization with non-directory path."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("content")
        
        with pytest.raises(GitError) as exc_info:
            git_manager.init_repository(file_path)
        
        assert "not a directory" in str(exc_info.value)

    def test_init_repository_git_init_failure(self, git_manager, mock_subprocess_run, temp_project):
        """Test repository initialization when git init fails."""
        mock_subprocess_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="fatal: cannot create repository",
        )
        
        with pytest.raises(GitError) as exc_info:
            git_manager.init_repository(temp_project)
        
        assert "Git init failed" in str(exc_info.value)
        assert "fatal: cannot create repository" in str(exc_info.value)

    def test_init_repository_timeout(self, git_manager, mock_subprocess_run, temp_project):
        """Test repository initialization timeout."""
        mock_subprocess_run.side_effect = subprocess.TimeoutExpired(
            cmd=["git", "init"],
            timeout=30,
        )
        
        with pytest.raises(GitError) as exc_info:
            git_manager.init_repository(temp_project)
        
        assert "timed out" in str(exc_info.value)

    def test_init_repository_exception(self, git_manager, mock_subprocess_run, temp_project):
        """Test repository initialization with exception."""
        mock_subprocess_run.side_effect = OSError("Permission denied")
        
        with pytest.raises(GitError) as exc_info:
            git_manager.init_repository(temp_project)
        
        assert "Failed to initialize git repository" in str(exc_info.value)

    def test_create_initial_commit_success(self, git_manager, mock_subprocess_run, temp_project):
        """Test successful initial commit creation."""
        # Create .git directory to simulate initialized repo
        git_dir = temp_project / ".git"
        git_dir.mkdir()
        
        mock_subprocess_run.reset_mock()
        
        git_manager.create_initial_commit(temp_project, message="Test commit")
        
        # Should call: git add ., git commit -m
        assert mock_subprocess_run.call_count == 2
        
        calls = mock_subprocess_run.call_args_list
        assert calls[0][0][0] == ["/usr/bin/git", "add", "."]
        assert calls[1][0][0] == ["/usr/bin/git", "commit", "-m", "Test commit"]

    def test_create_initial_commit_default_message(self, git_manager, mock_subprocess_run, temp_project):
        """Test initial commit with default message."""
        git_dir = temp_project / ".git"
        git_dir.mkdir()
        
        mock_subprocess_run.reset_mock()
        
        git_manager.create_initial_commit(temp_project)
        
        # Check commit message
        calls = mock_subprocess_run.call_args_list
        assert calls[1][0][0] == ["/usr/bin/git", "commit", "-m", "Initial commit"]

    def test_create_initial_commit_from_config(self, git_manager, mock_subprocess_run, temp_project):
        """Test initial commit with message from config."""
        git_dir = temp_project / ".git"
        git_dir.mkdir()
        
        mock_subprocess_run.reset_mock()
        
        config = GitConfig(initial_commit_message="Custom initial commit")
        git_manager.create_initial_commit(temp_project, git_config=config)
        
        # Check commit message
        calls = mock_subprocess_run.call_args_list
        assert calls[1][0][0] == ["/usr/bin/git", "commit", "-m", "Custom initial commit"]

    def test_create_initial_commit_nothing_to_commit(self, git_manager, mock_subprocess_run, temp_project):
        """Test initial commit when repository is clean."""
        git_dir = temp_project / ".git"
        git_dir.mkdir()
        
        mock_subprocess_run.reset_mock()
        # git add succeeds, git commit returns "nothing to commit"
        mock_subprocess_run.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),
            MagicMock(
                returncode=1,
                stdout="nothing to commit, working tree clean",
                stderr="",
            ),
        ]
        
        # Should not raise an exception
        git_manager.create_initial_commit(temp_project)

    def test_create_initial_commit_without_git(self, temp_project):
        """Test initial commit without git available."""
        with patch("shutil.which", return_value=None):
            manager = GitManager()
        
        git_dir = temp_project / ".git"
        git_dir.mkdir()
        
        with pytest.raises(GitError) as exc_info:
            manager.create_initial_commit(temp_project)
        
        assert "Git is not available" in str(exc_info.value)

    def test_create_initial_commit_no_repo(self, git_manager, temp_project):
        """Test initial commit without initialized repository."""
        with pytest.raises(GitError) as exc_info:
            git_manager.create_initial_commit(temp_project)
        
        assert "No git repository found" in str(exc_info.value)

    def test_create_initial_commit_add_failure(self, git_manager, mock_subprocess_run, temp_project):
        """Test initial commit when git add fails."""
        git_dir = temp_project / ".git"
        git_dir.mkdir()
        
        mock_subprocess_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="fatal: pathspec '.' did not match any files",
        )
        
        with pytest.raises(GitError) as exc_info:
            git_manager.create_initial_commit(temp_project)
        
        assert "Git add failed" in str(exc_info.value)

    def test_create_initial_commit_commit_failure(self, git_manager, mock_subprocess_run, temp_project):
        """Test initial commit when git commit fails."""
        git_dir = temp_project / ".git"
        git_dir.mkdir()
        
        mock_subprocess_run.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),  # git add succeeds
            MagicMock(
                returncode=1,
                stdout="",
                stderr="fatal: unable to write commit",
            ),  # git commit fails
        ]
        
        with pytest.raises(GitError) as exc_info:
            git_manager.create_initial_commit(temp_project)
        
        assert "Git commit failed" in str(exc_info.value)

    def test_get_repository_status_success(self, git_manager, mock_subprocess_run, temp_project):
        """Test getting repository status successfully."""
        git_dir = temp_project / ".git"
        git_dir.mkdir()
        
        mock_subprocess_run.return_value = MagicMock(
            returncode=0,
            stdout="M  file1.txt\nA  file2.txt\n",
            stderr="",
        )
        
        status = git_manager.get_repository_status(temp_project)
        
        assert status["initialized"] is True
        assert status["git_available"] is True
        assert status["clean"] is False
        assert status["changes_count"] == 2
        assert len(status["changes"]) == 2
        assert "M  file1.txt" in status["changes"]

    def test_get_repository_status_clean(self, git_manager, mock_subprocess_run, temp_project):
        """Test getting status of clean repository."""
        git_dir = temp_project / ".git"
        git_dir.mkdir()
        
        mock_subprocess_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr="",
        )
        
        status = git_manager.get_repository_status(temp_project)
        
        assert status["initialized"] is True
        assert status["git_available"] is True
        assert status["clean"] is True
        assert status["changes_count"] == 0
        assert status["changes"] == []

    def test_get_repository_status_no_git(self, temp_project):
        """Test getting status without git available."""
        with patch("shutil.which", return_value=None):
            manager = GitManager()
        
        status = manager.get_repository_status(temp_project)
        
        assert status["initialized"] is False
        assert status["git_available"] is False
        assert "Git is not available" in status["error"]

    def test_get_repository_status_no_repo(self, git_manager, temp_project):
        """Test getting status without initialized repository."""
        status = git_manager.get_repository_status(temp_project)
        
        assert status["initialized"] is False
        assert status["git_available"] is True
        assert "No git repository found" in status["error"]

    def test_get_repository_status_failure(self, git_manager, mock_subprocess_run, temp_project):
        """Test getting status when git status fails."""
        git_dir = temp_project / ".git"
        git_dir.mkdir()
        
        mock_subprocess_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="fatal: not a git repository",
        )
        
        status = git_manager.get_repository_status(temp_project)
        
        assert status["initialized"] is True
        assert status["git_available"] is True
        assert "Git status failed" in status["error"]

    def test_get_repository_status_timeout(self, git_manager, mock_subprocess_run, temp_project):
        """Test getting status with timeout."""
        git_dir = temp_project / ".git"
        git_dir.mkdir()
        
        mock_subprocess_run.side_effect = subprocess.TimeoutExpired(
            cmd=["git", "status"],
            timeout=30,
        )
        
        status = git_manager.get_repository_status(temp_project)
        
        assert status["initialized"] is True
        assert status["git_available"] is True
        assert "timed out" in status["error"]

    def test_configure_repository_user_config(self, git_manager, mock_subprocess_run, temp_project):
        """Test configuring repository with user settings."""
        config = GitConfig(
            user_name="Test User",
            user_email="test@example.com",
        )
        
        mock_subprocess_run.reset_mock()  # Reset to clear the init call
        
        git_manager._configure_repository(temp_project, config)
        
        # Should set both user.name and user.email
        assert mock_subprocess_run.call_count == 2
        
        calls = mock_subprocess_run.call_args_list
        assert calls[0][0][0] == ["/usr/bin/git", "config", "user.name", "Test User"]
        assert calls[1][0][0] == ["/usr/bin/git", "config", "user.email", "test@example.com"]

    def test_configure_repository_partial_config(self, git_manager, mock_subprocess_run, temp_project):
        """Test configuring repository with partial settings."""
        config = GitConfig(user_name="Test User")  # No email
        
        mock_subprocess_run.reset_mock()  # Reset to clear the init call
        
        git_manager._configure_repository(temp_project, config)
        
        # Should only set user.name
        assert mock_subprocess_run.call_count == 1
        assert mock_subprocess_run.call_args[0][0] == ["/usr/bin/git", "config", "user.name", "Test User"]

    def test_configure_repository_failure_continues(self, git_manager, mock_subprocess_run, temp_project):
        """Test configuration continues even if individual settings fail."""
        mock_subprocess_run.reset_mock()  # Reset to clear the init call
        mock_subprocess_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="error: could not set config",
        )
        
        config = GitConfig(
            user_name="Test User",
            user_email="test@example.com",
        )
        
        # Should not raise exception
        git_manager._configure_repository(temp_project, config)
        
        # Both config attempts should be made
        assert mock_subprocess_run.call_count == 2

    def test_run_git_command_success(self, git_manager, mock_subprocess_run, temp_project):
        """Test running git command successfully."""
        mock_subprocess_run.reset_mock()  # Reset to clear the init call
        
        result = git_manager._run_git_command(["status"], temp_project)
        
        assert result.returncode == 0
        mock_subprocess_run.assert_called_once_with(
            ["/usr/bin/git", "status"],
            cwd=temp_project,
            capture_output=True,
            text=True,
            timeout=60,
        )

    def test_run_git_command_no_git_path(self, git_manager, temp_project):
        """Test running git command without git path."""
        git_manager.git_path = None
        
        with pytest.raises(GitError) as exc_info:
            git_manager._run_git_command(["status"], temp_project)
        
        assert "Git executable not found" in str(exc_info.value)

    def test_run_git_command_custom_timeout(self, git_manager, mock_subprocess_run, temp_project):
        """Test running git command with custom timeout."""
        mock_subprocess_run.reset_mock()  # Reset to clear the init call
        
        result = git_manager._run_git_command(["log"], temp_project, timeout=120)
        
        mock_subprocess_run.assert_called_once()
        assert mock_subprocess_run.call_args[1]["timeout"] == 120