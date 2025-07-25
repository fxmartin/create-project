# ABOUTME: Unit tests for virtual environment manager module
# ABOUTME: Tests venv creation with multiple tools and fallback mechanisms

"""Unit tests for virtual environment manager module."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from create_project.core.exceptions import VirtualEnvError
from create_project.core.venv_manager import VenvManager, VenvTool


class TestVenvManager:
    """Test VenvManager functionality."""

    @pytest.fixture
    def mock_which(self):
        """Mock shutil.which for tool detection."""
        with patch("shutil.which") as mock:
            # Default: all tools available
            def which_side_effect(cmd):
                if cmd == "uv":
                    return "/usr/local/bin/uv"
                elif cmd == "virtualenv":
                    return "/usr/local/bin/virtualenv"
                elif cmd.startswith("python"):
                    return f"/usr/bin/{cmd}"
                return None

            mock.side_effect = which_side_effect
            yield mock

    @pytest.fixture
    def mock_subprocess_run(self):
        """Mock subprocess.run for venv commands."""
        with patch("subprocess.run") as mock:
            # Default successful version check
            mock.return_value = MagicMock(
                returncode=0,
                stdout="tool version 1.0.0",
                stderr="",
            )
            yield mock

    @pytest.fixture
    def mock_sys_executable(self):
        """Mock sys.executable."""
        with patch("sys.executable", "/usr/bin/python3"):
            yield

    @pytest.fixture
    def venv_manager(self, mock_which, mock_subprocess_run, mock_sys_executable):
        """Create a VenvManager instance with mocked tools."""
        return VenvManager()

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project directory."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        return project_dir

    def test_init_with_all_tools(self, mock_which, mock_subprocess_run, mock_sys_executable):
        """Test VenvManager initialization with all tools available."""
        manager = VenvManager()

        assert VenvTool.UV in manager.available_tools
        assert VenvTool.VIRTUALENV in manager.available_tools
        assert VenvTool.VENV in manager.available_tools
        assert manager.preferred_tool == VenvTool.UV  # UV has highest priority

    def test_init_with_only_venv(self, mock_subprocess_run, mock_sys_executable):
        """Test VenvManager initialization with only venv available."""
        with patch("shutil.which", return_value=None):
            manager = VenvManager()

        assert VenvTool.UV not in manager.available_tools
        assert VenvTool.VIRTUALENV not in manager.available_tools
        assert VenvTool.VENV in manager.available_tools
        assert manager.preferred_tool == VenvTool.VENV

    def test_init_with_no_tools(self, mock_subprocess_run):
        """Test VenvManager initialization with no tools available."""
        with patch("shutil.which", return_value=None):
            # Also make venv detection fail
            mock_subprocess_run.return_value = MagicMock(returncode=1)

            manager = VenvManager()

        assert manager.preferred_tool is None
        assert not any(manager.available_tools.values())

    def test_init_with_tool_detection_timeout(self, mock_which, mock_sys_executable):
        """Test VenvManager initialization when tool detection times out."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd=["uv", "--version"],
                timeout=10,
            )

            manager = VenvManager()

        # Should handle timeout gracefully
        assert manager.preferred_tool is None or manager.preferred_tool != VenvTool.UV

    def test_create_venv_success_with_uv(self, venv_manager, mock_subprocess_run, temp_project):
        """Test successful virtual environment creation with uv."""
        mock_subprocess_run.reset_mock()

        result = venv_manager.create_venv(temp_project)

        assert result["success"] is True
        assert result["tool"] == VenvTool.UV.value
        assert "venv_path" in result
        assert "activation_instructions" in result

        # Verify uv venv command was called
        calls = mock_subprocess_run.call_args_list
        # Find the venv creation call (not version checks)
        venv_call = None
        for call_item in calls:
            args = call_item[0][0]
            if "venv" in args and str(temp_project) in str(args):
                venv_call = call_item
                break

        assert venv_call is not None
        assert args[0].endswith("uv")
        assert args[1] == "venv"

    def test_create_venv_with_custom_name(self, venv_manager, mock_subprocess_run, temp_project):
        """Test virtual environment creation with custom name."""
        mock_subprocess_run.reset_mock()

        result = venv_manager.create_venv(temp_project, venv_name="env")

        assert result["success"] is True
        assert "env" in result["venv_path"]

    def test_create_venv_with_python_version(self, venv_manager, mock_subprocess_run, temp_project):
        """Test virtual environment creation with specific Python version."""
        mock_subprocess_run.reset_mock()

        result = venv_manager.create_venv(temp_project, python_version="3.11")

        assert result["success"] is True

        # Check that Python version was passed to command
        venv_call = None
        for call_item in mock_subprocess_run.call_args_list:
            args = call_item[0][0]
            if "venv" in args and "--python" in args:
                venv_call = call_item
                break

        assert venv_call is not None
        assert "3.11" in args

    def test_create_venv_no_tools_available(self, temp_project):
        """Test virtual environment creation when no tools are available."""
        with patch("shutil.which", return_value=None):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1)

                manager = VenvManager()

        with pytest.raises(VirtualEnvError) as exc_info:
            manager.create_venv(temp_project)

        assert "No virtual environment tools available" in str(exc_info.value)

    def test_create_venv_project_not_exists(self, venv_manager):
        """Test virtual environment creation with non-existent project path."""
        with pytest.raises(VirtualEnvError) as exc_info:
            venv_manager.create_venv(Path("/nonexistent/project"))

        assert "does not exist" in str(exc_info.value)

    def test_create_venv_already_exists(self, venv_manager, temp_project):
        """Test virtual environment creation when venv already exists."""
        venv_path = temp_project / ".venv"
        venv_path.mkdir()

        with pytest.raises(VirtualEnvError) as exc_info:
            venv_manager.create_venv(temp_project)

        assert "already exists" in str(exc_info.value)

    def test_create_venv_with_fallback(self, venv_manager, mock_subprocess_run, temp_project):
        """Test virtual environment creation with fallback to secondary tool."""
        mock_subprocess_run.reset_mock()

        # Make UV fail, virtualenv succeed
        def run_side_effect(*args, **kwargs):
            cmd = args[0]
            if isinstance(cmd, list) and len(cmd) > 1:
                if cmd[0].endswith("uv") and cmd[1] == "venv":
                    return MagicMock(returncode=1, stderr="uv failed")
                elif cmd[0].endswith("virtualenv") and str(temp_project) in str(cmd):
                    return MagicMock(returncode=0, stdout="Success")
            return MagicMock(returncode=0, stdout="version check")

        mock_subprocess_run.side_effect = run_side_effect

        result = venv_manager.create_venv(temp_project)

        assert result["success"] is True
        assert result["tool"] == VenvTool.VIRTUALENV.value

    def test_create_venv_all_tools_fail(self, venv_manager, mock_subprocess_run, temp_project):
        """Test virtual environment creation when all tools fail."""
        mock_subprocess_run.return_value = MagicMock(
            returncode=1,
            stderr="Tool failed",
        )

        with pytest.raises(VirtualEnvError) as exc_info:
            venv_manager.create_venv(temp_project)

        assert "All virtual environment tools failed" in str(exc_info.value)

    def test_create_venv_with_cleanup_on_failure(self, venv_manager, mock_subprocess_run, temp_project):
        """Test that failed venv creation cleans up partial venv."""
        venv_path = temp_project / ".venv"

        # Create partial venv directory
        def run_side_effect(*args, **kwargs):
            # Create directory to simulate partial creation
            venv_path.mkdir(exist_ok=True)
            return MagicMock(returncode=1, stderr="Creation failed")

        mock_subprocess_run.side_effect = run_side_effect

        with patch("shutil.rmtree") as mock_rmtree:
            with pytest.raises(VirtualEnvError):
                venv_manager.create_venv(temp_project)

            # Verify cleanup was attempted
            mock_rmtree.assert_called_once_with(venv_path)

    def test_create_venv_with_requirements(self, venv_manager, mock_subprocess_run, temp_project):
        """Test virtual environment creation with requirements installation."""
        requirements_file = temp_project / "requirements.txt"
        requirements_file.write_text("requests==2.28.0\n")

        mock_subprocess_run.reset_mock()

        # Mock pip path existence
        original_exists = Path.exists

        def mock_exists(self):
            # Return True for pip paths, otherwise use original method
            return True if "pip" in str(self) else original_exists(self)

        with patch.object(Path, "exists", mock_exists):

            result = venv_manager.create_venv(
                temp_project,
                requirements_file=requirements_file
            )

        assert result["success"] is True

        # Check that pip install was called
        pip_call = None
        for call_item in mock_subprocess_run.call_args_list:
            args = call_item[0][0]
            if isinstance(args, list) and "install" in args and "-r" in args:
                pip_call = call_item
                break

        assert pip_call is not None

    def test_get_activation_instructions_windows(self, venv_manager, temp_project):
        """Test getting activation instructions for Windows."""
        venv_path = temp_project / ".venv"
        venv_path.mkdir()
        (venv_path / "Scripts").mkdir()

        with patch("sys.platform", "win32"):
            instructions = venv_manager.get_activation_instructions(temp_project)

        assert "windows_cmd" in instructions
        assert "windows_powershell" in instructions
        assert "Scripts" in instructions["windows_cmd"]

    def test_get_activation_instructions_unix(self, venv_manager, temp_project):
        """Test getting activation instructions for Unix systems."""
        venv_path = temp_project / ".venv"
        venv_path.mkdir()
        (venv_path / "bin").mkdir()

        with patch("sys.platform", "linux"):
            instructions = venv_manager.get_activation_instructions(temp_project)

        assert "bash_zsh" in instructions
        assert "fish" in instructions
        assert "csh" in instructions
        assert "source" in instructions["bash_zsh"]

    def test_get_activation_instructions_not_found(self, venv_manager, temp_project):
        """Test getting activation instructions when venv doesn't exist."""
        instructions = venv_manager.get_activation_instructions(temp_project)

        assert "error" in instructions
        assert "not found" in instructions["error"]

    def test_create_with_uv_specific(self, venv_manager, mock_subprocess_run, temp_project):
        """Test _create_with_uv method directly."""
        venv_path = temp_project / ".venv"

        result = venv_manager._create_with_uv(
            "/usr/local/bin/uv",
            venv_path,
            python_version="3.11"
        )

        assert "activation_instructions" in result

        # Check command construction
        call_args = mock_subprocess_run.call_args
        command = call_args[0][0]
        assert command == ["/usr/local/bin/uv", "venv", str(venv_path), "--python", "3.11"]

    def test_create_with_virtualenv_specific(self, venv_manager, mock_subprocess_run, temp_project):
        """Test _create_with_virtualenv method directly."""
        venv_path = temp_project / ".venv"

        result = venv_manager._create_with_virtualenv(
            "/usr/local/bin/virtualenv",
            venv_path,
            python_version="3.11"
        )

        # Check command construction
        call_args = mock_subprocess_run.call_args
        command = call_args[0][0]
        assert command[0] == "/usr/local/bin/virtualenv"
        assert "--python" in command
        assert "python3.11" in command

    def test_create_with_venv_specific(self, venv_manager, mock_subprocess_run, temp_project):
        """Test _create_with_venv method directly."""
        venv_path = temp_project / ".venv"

        with patch("shutil.which", return_value="/usr/bin/python3.11"):
            result = venv_manager._create_with_venv(
                "/usr/bin/python3",
                venv_path,
                python_version="3.11"
            )

        # Check that it tried to find the specific Python version
        call_args = mock_subprocess_run.call_args
        command = call_args[0][0]
        assert "-m" in command
        assert "venv" in command

    def test_create_with_venv_version_not_found(self, venv_manager, mock_subprocess_run, temp_project):
        """Test venv creation when specific Python version not found."""
        venv_path = temp_project / ".venv"

        with patch("shutil.which", return_value=None):
            result = venv_manager._create_with_venv(
                "/usr/bin/python3",
                venv_path,
                python_version="3.99"  # Non-existent version
            )

        # Should fall back to current Python
        call_args = mock_subprocess_run.call_args
        command = call_args[0][0]
        assert command[0] == "/usr/bin/python3"

    def test_install_requirements_success(self, venv_manager, mock_subprocess_run, temp_project):
        """Test successful requirements installation."""
        venv_path = temp_project / ".venv"
        venv_path.mkdir()

        # Create pip path
        if sys.platform == "win32":
            pip_dir = venv_path / "Scripts"
            pip_path = pip_dir / "pip.exe"
        else:
            pip_dir = venv_path / "bin"
            pip_path = pip_dir / "pip"

        pip_dir.mkdir()
        pip_path.touch()

        requirements_file = temp_project / "requirements.txt"
        requirements_file.write_text("requests==2.28.0\n")

        mock_subprocess_run.reset_mock()

        venv_manager._install_requirements(venv_path, requirements_file)

        # Verify pip install was called
        mock_subprocess_run.assert_called_once()
        args = mock_subprocess_run.call_args[0][0]
        assert str(pip_path) in args
        assert "install" in args
        assert "-r" in args
        assert str(requirements_file) in args

    def test_install_requirements_pip_not_found(self, venv_manager, mock_subprocess_run, temp_project):
        """Test requirements installation when pip not found."""
        venv_path = temp_project / ".venv"
        venv_path.mkdir()

        requirements_file = temp_project / "requirements.txt"
        requirements_file.write_text("requests==2.28.0\n")

        mock_subprocess_run.reset_mock()

        # Should log warning but not raise exception
        venv_manager._install_requirements(venv_path, requirements_file)

        # pip install should not be called
        mock_subprocess_run.assert_not_called()

    def test_install_requirements_failure(self, venv_manager, mock_subprocess_run, temp_project):
        """Test requirements installation failure handling."""
        venv_path = temp_project / ".venv"
        venv_path.mkdir()

        # Create pip path
        pip_dir = venv_path / "bin"
        pip_path = pip_dir / "pip"
        pip_dir.mkdir()
        pip_path.touch()

        requirements_file = temp_project / "requirements.txt"
        requirements_file.write_text("invalid-package-name\n")

        mock_subprocess_run.return_value = MagicMock(
            returncode=1,
            stderr="Could not find package",
        )

        # Should log error but not raise exception
        venv_manager._install_requirements(venv_path, requirements_file)

    def test_tool_priority_order(self):
        """Test that tool priority order is correct."""
        assert VenvManager.TOOL_PRIORITY == [
            VenvTool.UV,
            VenvTool.VIRTUALENV,
            VenvTool.VENV,
        ]

    def test_concurrent_venv_creation(self, venv_manager, mock_subprocess_run, tmp_path):
        """Test that VenvManager can handle concurrent venv creation attempts."""
        import threading

        results = []
        errors = []

        def create_venv(index):
            try:
                project_dir = tmp_path / f"project_{index}"
                project_dir.mkdir()
                result = venv_manager.create_venv(project_dir)
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Create multiple venvs concurrently
        threads = []
        for i in range(3):
            thread = threading.Thread(target=create_venv, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        assert len(errors) == 0
        assert len(results) == 3
        assert all(r["success"] for r in results)
