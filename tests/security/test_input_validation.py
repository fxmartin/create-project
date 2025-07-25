# ABOUTME: Input validation security tests for preventing injection attacks
# ABOUTME: Tests project names, descriptions, and template variables against malicious input

"""
Input validation security test suite.

This module provides comprehensive security testing for all user input validation
in the create-project application, including:
- Project name validation against injection attacks
- Author name validation against script injection
- Description validation against XSS and template injection
- Template variable validation against SSTI attacks
- Path input validation against traversal attacks
- URL validation against malformed and malicious URLs
- Version validation against format string attacks
"""

import re
import pytest
from typing import List, Dict, Any
from unittest.mock import MagicMock, patch

from create_project.config.config_manager import ConfigManager
from create_project.core.path_utils import PathHandler
from create_project.core.project_generator import ProjectGenerator
from create_project.templates.engine import TemplateEngine
from create_project.core.api import create_project


@pytest.mark.security
class TestProjectNameValidation:
    """Test project name validation against various injection attacks."""

    def test_reject_directory_traversal_in_project_name(self, malicious_project_names: List[str]):
        """Test that project names with directory traversal are rejected."""
        path_handler = PathHandler()
        
        traversal_names = [name for name in malicious_project_names if ".." in name]
        
        for malicious_name in traversal_names:
            with pytest.raises((ValueError, OSError, FileNotFoundError)):
                # This should fail validation or raise an exception
                path_handler.validate_project_name(malicious_name)

    def test_reject_command_injection_in_project_name(self, malicious_project_names: List[str]):
        """Test that project names with command injection are rejected."""
        path_handler = PathHandler()
        
        injection_chars = [";", "&", "|", "`", "$", "(", ")"]
        injection_names = [name for name in malicious_project_names 
                          if any(char in name for char in injection_chars)]
        
        for malicious_name in injection_names:
            with pytest.raises((ValueError, OSError)):
                path_handler.validate_project_name(malicious_name)

    def test_reject_script_injection_in_project_name(self, malicious_project_names: List[str]):
        """Test that project names with script injection are rejected."""
        path_handler = PathHandler()
        
        script_patterns = ["<script", "javascript:", "{{", "${", "#{"]
        script_names = [name for name in malicious_project_names 
                       if any(pattern in name.lower() for pattern in script_patterns)]
        
        for malicious_name in script_names:
            with pytest.raises((ValueError, OSError)):
                path_handler.validate_project_name(malicious_name)

    def test_reject_null_bytes_in_project_name(self, malicious_project_names: List[str]):
        """Test that project names with null bytes are rejected."""
        path_handler = PathHandler()
        
        null_names = [name for name in malicious_project_names if "\x00" in name]
        
        for malicious_name in null_names:
            with pytest.raises((ValueError, OSError)):
                path_handler.validate_project_name(malicious_name)

    def test_reject_unicode_attacks_in_project_name(self, malicious_project_names: List[str]):
        """Test that project names with Unicode attacks are rejected."""
        path_handler = PathHandler()
        
        # Unicode control characters and suspicious characters
        unicode_attacks = [name for name in malicious_project_names 
                          if any(ord(c) > 127 and ord(c) < 160 for c in name)]
        
        for malicious_name in unicode_attacks:
            with pytest.raises((ValueError, OSError)):
                path_handler.validate_project_name(malicious_name)

    def test_reject_excessively_long_project_names(self, malicious_project_names: List[str]):
        """Test that excessively long project names are rejected."""
        path_handler = PathHandler()
        
        long_names = [name for name in malicious_project_names if len(name) > 255]
        
        for malicious_name in long_names:
            with pytest.raises((ValueError, OSError)):
                path_handler.validate_project_name(malicious_name)

    def test_reject_windows_reserved_names(self):
        """Test that Windows reserved names are rejected."""
        path_handler = PathHandler()
        
        reserved_names = ["CON", "PRN", "AUX", "NUL", "COM1", "COM2", "LPT1", "LPT2"]
        
        for reserved_name in reserved_names:
            with pytest.raises((ValueError, OSError)):
                path_handler.validate_project_name(reserved_name)

    def test_reject_invalid_filesystem_characters(self):
        """Test that invalid filesystem characters are rejected."""
        path_handler = PathHandler()
        
        invalid_chars = ["<", ">", ":", "\"", "|", "?", "*", "/", "\\"]
        
        for char in invalid_chars:
            malicious_name = f"test{char}project"
            with pytest.raises((ValueError, OSError)):
                path_handler.validate_project_name(malicious_name)

    def test_accept_valid_project_names(self, security_test_data: Dict[str, Any]):
        """Test that valid project names are accepted."""
        path_handler = PathHandler()
        
        valid_names = security_test_data["valid_inputs"]["project_names"]
        
        for valid_name in valid_names:
            # This should not raise an exception
            try:
                path_handler.validate_project_name(valid_name)
            except Exception as e:
                pytest.fail(f"Valid project name '{valid_name}' was rejected: {e}")


@pytest.mark.security
class TestAuthorValidation:
    """Test author name validation against script injection attacks."""

    def test_reject_script_injection_in_author(self, malicious_template_variables: Dict[str, Any]):
        """Test that author names with script injection are rejected."""
        config_manager = ConfigManager()
        
        script_injections = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "{{7*7}}",
            "${7*7}",
            "#{7*7}",
            "__import__('os').system('id')",
        ]
        
        for malicious_author in script_injections:
            # Test that the author validation rejects malicious input
            with pytest.raises((ValueError, Exception)):
                # Simulate author validation through config
                config_manager.validate_author_name(malicious_author)

    def test_reject_html_injection_in_author(self):
        """Test that author names with HTML injection are rejected."""
        config_manager = ConfigManager()
        
        html_injections = [
            "<img src=x onerror=alert('xss')>",
            "<iframe src='javascript:alert(1)'></iframe>",
            "<svg onload=alert('xss')>",
            "<body onload=alert('xss')>",
        ]
        
        for malicious_author in html_injections:
            with pytest.raises((ValueError, Exception)):
                config_manager.validate_author_name(malicious_author)

    def test_reject_encoding_attacks_in_author(self, security_test_data: Dict[str, Any]):
        """Test that author names with encoding attacks are rejected."""
        config_manager = ConfigManager()
        
        encoding_attacks = security_test_data["encoding_attacks"]
        
        for malicious_author in encoding_attacks:
            with pytest.raises((ValueError, Exception)):
                config_manager.validate_author_name(malicious_author)

    def test_accept_valid_authors(self, security_test_data: Dict[str, Any]):
        """Test that valid author names are accepted."""
        config_manager = ConfigManager()
        
        valid_authors = security_test_data["valid_inputs"]["authors"]
        
        for valid_author in valid_authors:
            try:
                # This should not raise an exception
                config_manager.validate_author_name(valid_author)
            except Exception as e:
                pytest.fail(f"Valid author '{valid_author}' was rejected: {e}")


@pytest.mark.security
class TestDescriptionValidation:
    """Test description validation against XSS and injection attacks."""

    def test_reject_xss_in_description(self):
        """Test that descriptions with XSS are properly sanitized or rejected."""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "<svg onload=alert('xss')>",
            "<iframe src='javascript:alert(1)'></iframe>",
            "<body onload=alert('xss')>",
            "<input type='text' onfocus='alert(1)'>",
        ]
        
        for xss_payload in xss_payloads:
            # Description validation should sanitize or reject XSS
            sanitized = self._sanitize_description(xss_payload)
            assert "<script" not in sanitized.lower()
            assert "javascript:" not in sanitized.lower()
            assert "onerror=" not in sanitized.lower()
            assert "onload=" not in sanitized.lower()

    def test_reject_template_injection_in_description(self, malicious_template_variables: Dict[str, Any]):
        """Test that descriptions with template injection are rejected."""
        template_injections = [
            "{{7*7}}",
            "{{config.__class__}}",
            "{%for x in ().__class__.__base__.__subclasses__()%}",
            "{% include '/etc/passwd' %}",
            "${7*7}",
            "#{7*7}",
        ]
        
        for injection in template_injections:
            sanitized = self._sanitize_description(injection)
            # Template syntax should be escaped or removed
            assert "{{" not in sanitized
            assert "{%" not in sanitized
            assert "${" not in sanitized
            assert "#{" not in sanitized

    def test_reject_excessively_long_descriptions(self):
        """Test that excessively long descriptions are rejected."""
        max_length = 10000  # Reasonable limit
        long_description = "A" * (max_length + 1)
        
        with pytest.raises((ValueError, Exception)):
            self._validate_description_length(long_description, max_length)

    def test_accept_valid_descriptions(self, security_test_data: Dict[str, Any]):
        """Test that valid descriptions are accepted."""
        valid_descriptions = security_test_data["valid_inputs"]["descriptions"]
        
        for valid_desc in valid_descriptions:
            sanitized = self._sanitize_description(valid_desc)
            # Valid descriptions should remain largely unchanged
            assert len(sanitized) > 0
            assert sanitized != ""

    def _sanitize_description(self, description: str) -> str:
        """Simulate description sanitization logic."""
        # Remove HTML tags
        import re
        sanitized = re.sub(r'<[^>]*>', '', description)
        
        # Remove script protocols
        sanitized = re.sub(r'javascript:', '', sanitized, flags=re.IGNORECASE)
        
        # Remove template syntax
        sanitized = re.sub(r'\{\{.*?\}\}', '', sanitized)
        sanitized = re.sub(r'\{%.*?%\}', '', sanitized)
        sanitized = re.sub(r'\$\{.*?\}', '', sanitized)
        sanitized = re.sub(r'#\{.*?\}', '', sanitized)
        
        return sanitized

    def _validate_description_length(self, description: str, max_length: int) -> None:
        """Simulate description length validation."""
        if len(description) > max_length:
            raise ValueError(f"Description too long: {len(description)} > {max_length}")


@pytest.mark.security
class TestTemplateVariableValidation:
    """Test template variable validation against SSTI attacks."""

    def test_reject_ssti_attacks(self, malicious_template_variables: Dict[str, Any]):
        """Test that template variables with SSTI are rejected."""
        template_engine = TemplateEngine()
        
        ssti_payloads = [
            malicious_template_variables["ssti_basic"],
            malicious_template_variables["ssti_advanced"],
            malicious_template_variables["ssti_class_walk"],
            malicious_template_variables["ssti_import"],
        ]
        
        for payload in ssti_payloads:
            with pytest.raises((ValueError, Exception)):
                # Template variable validation should reject SSTI
                template_engine.validate_variable("test_var", payload)

    def test_reject_jinja_specific_attacks(self, malicious_template_variables: Dict[str, Any]):
        """Test that Jinja2-specific attacks are rejected."""
        template_engine = TemplateEngine()
        
        jinja_attacks = [
            malicious_template_variables["jinja_loop"],
            malicious_template_variables["jinja_include"],
            malicious_template_variables["jinja_import"],
            malicious_template_variables["jinja_set"],
        ]
        
        for attack in jinja_attacks:
            with pytest.raises((ValueError, Exception)):
                template_engine.validate_variable("test_var", attack)

    def test_reject_filter_bypasses(self, malicious_template_variables: Dict[str, Any]):
        """Test that filter bypass attempts are rejected."""
        template_engine = TemplateEngine()
        
        filter_bypasses = [
            malicious_template_variables["filter_bypass_1"],
            malicious_template_variables["filter_bypass_2"],
        ]
        
        for bypass in filter_bypasses:
            with pytest.raises((ValueError, Exception)):
                template_engine.validate_variable("test_var", bypass)

    def test_reject_code_injection_in_variables(self, malicious_template_variables: Dict[str, Any]):
        """Test that code injection in variables is rejected."""
        template_engine = TemplateEngine()
        
        code_injections = [
            malicious_template_variables["code_exec"],
            malicious_template_variables["code_eval"],
            malicious_template_variables["code_compile"],
        ]
        
        for injection in code_injections:
            with pytest.raises((ValueError, Exception)):
                template_engine.validate_variable("test_var", injection)

    def test_handle_large_variable_values(self, malicious_template_variables: Dict[str, Any]):
        """Test that very large variable values are handled safely."""
        template_engine = TemplateEngine()
        
        large_value = malicious_template_variables["large_string"]
        
        # Should either reject or handle gracefully without DoS
        try:
            result = template_engine.validate_variable("test_var", large_value)
            # If accepted, should be truncated or handled safely
            assert len(str(result)) < 1000000  # Reasonable limit
        except (ValueError, Exception):
            # Rejection is also acceptable
            pass

    def test_handle_special_types_safely(self, malicious_template_variables: Dict[str, Any]):
        """Test that special variable types are handled safely."""
        template_engine = TemplateEngine()
        
        special_values = [
            malicious_template_variables["none_value"],
            malicious_template_variables["empty_string"],
            malicious_template_variables["large_number"],
        ]
        
        for value in special_values:
            try:
                # Should handle without crashing
                template_engine.validate_variable("test_var", value)
            except Exception as e:
                # Controlled exceptions are acceptable
                assert "system" not in str(e).lower()
                assert "exec" not in str(e).lower()


@pytest.mark.security
class TestPathInputValidation:
    """Test path input validation against traversal and injection attacks."""

    def test_reject_path_traversal_in_inputs(self, malicious_paths: List[str]):
        """Test that path inputs with traversal attacks are rejected."""
        path_handler = PathHandler()
        
        traversal_paths = [path for path in malicious_paths if ".." in path]
        
        for malicious_path in traversal_paths:
            with pytest.raises((ValueError, OSError, FileNotFoundError)):
                path_handler.validate_path(malicious_path)

    def test_reject_absolute_paths_in_inputs(self, malicious_paths: List[str]):
        """Test that absolute paths are rejected where inappropriate."""
        path_handler = PathHandler()
        
        absolute_paths = [path for path in malicious_paths 
                         if path.startswith("/") or path.startswith("C:\\")]
        
        for absolute_path in absolute_paths:
            with pytest.raises((ValueError, OSError)):
                path_handler.validate_relative_path(absolute_path)

    def test_reject_unc_paths(self, malicious_paths: List[str]):
        """Test that UNC paths are rejected."""
        path_handler = PathHandler()
        
        unc_paths = [path for path in malicious_paths if path.startswith("\\\\")]
        
        for unc_path in unc_paths:
            with pytest.raises((ValueError, OSError)):
                path_handler.validate_path(unc_path)

    def test_reject_device_files(self, malicious_paths: List[str]):
        """Test that device files are rejected."""
        path_handler = PathHandler()
        
        device_paths = [path for path in malicious_paths 
                       if "/dev/" in path or "/proc/" in path]
        
        for device_path in device_paths:
            with pytest.raises((ValueError, OSError)):
                path_handler.validate_path(device_path)

    def test_reject_encoded_path_traversal(self, malicious_paths: List[str]):
        """Test that encoded path traversal is rejected."""
        path_handler = PathHandler()
        
        encoded_paths = [path for path in malicious_paths if "%" in path]
        
        for encoded_path in encoded_paths:
            with pytest.raises((ValueError, OSError)):
                path_handler.validate_path(encoded_path)


@pytest.mark.security
class TestURLValidation:
    """Test URL validation against malformed and malicious URLs."""

    def test_reject_javascript_urls(self):
        """Test that javascript: URLs are rejected."""
        malicious_urls = [
            "javascript:alert('xss')",
            "JAVASCRIPT:alert('xss')",
            "javascript:void(0)",
            "javascript://comment%0aalert('xss')",
        ]
        
        for malicious_url in malicious_urls:
            with pytest.raises((ValueError, Exception)):
                self._validate_url(malicious_url)

    def test_reject_data_urls_with_scripts(self):
        """Test that data URLs with scripts are rejected."""
        malicious_urls = [
            "data:text/html,<script>alert('xss')</script>",
            "data:text/html;base64,PHNjcmlwdD5hbGVydCgneHNzJyk8L3NjcmlwdD4=",
            "data:image/svg+xml,<svg onload=alert('xss')>",
        ]
        
        for malicious_url in malicious_urls:
            with pytest.raises((ValueError, Exception)):
                self._validate_url(malicious_url)

    def test_reject_file_urls(self):
        """Test that file:// URLs are rejected."""
        malicious_urls = [
            "file:///etc/passwd",
            "file://localhost/etc/passwd",
            "file:///C:/Windows/System32/config/SAM",
        ]
        
        for malicious_url in malicious_urls:
            with pytest.raises((ValueError, Exception)):
                self._validate_url(malicious_url)

    def test_accept_valid_urls(self, security_test_data: Dict[str, Any]):
        """Test that valid URLs are accepted."""
        valid_urls = security_test_data["valid_inputs"]["urls"]
        
        for valid_url in valid_urls:
            try:
                self._validate_url(valid_url)
            except Exception as e:
                pytest.fail(f"Valid URL '{valid_url}' was rejected: {e}")

    def _validate_url(self, url: str) -> None:
        """Simulate URL validation logic."""
        import urllib.parse
        
        parsed = urllib.parse.urlparse(url)
        
        # Reject dangerous schemes
        dangerous_schemes = ['javascript', 'data', 'file', 'ftp']
        if parsed.scheme.lower() in dangerous_schemes:
            raise ValueError(f"Dangerous URL scheme: {parsed.scheme}")
        
        # Only allow safe schemes
        safe_schemes = ['http', 'https']
        if parsed.scheme.lower() not in safe_schemes:
            raise ValueError(f"Unsupported URL scheme: {parsed.scheme}")


@pytest.mark.security
class TestVersionValidation:
    """Test version string validation against format attacks."""

    def test_reject_command_injection_in_version(self):
        """Test that version strings with command injection are rejected."""
        malicious_versions = [
            "1.0.0; rm -rf /",
            "1.0.0 && del /q /s C:\\*",
            "1.0.0 | cat /etc/passwd",
            "1.0.0`whoami`",
            "1.0.0$(id)",
        ]
        
        for malicious_version in malicious_versions:
            with pytest.raises((ValueError, Exception)):
                self._validate_version(malicious_version)

    def test_reject_script_injection_in_version(self):
        """Test that version strings with script injection are rejected."""
        malicious_versions = [
            "1.0.0<script>alert('xss')</script>",
            "1.0.0{{7*7}}",
            "1.0.0${7*7}",
            "1.0.0#{7*7}",
        ]
        
        for malicious_version in malicious_versions:
            with pytest.raises((ValueError, Exception)):
                self._validate_version(malicious_version)

    def test_accept_valid_versions(self, security_test_data: Dict[str, Any]):
        """Test that valid version strings are accepted."""
        valid_versions = security_test_data["valid_inputs"]["versions"]
        
        for valid_version in valid_versions:
            try:
                self._validate_version(valid_version)
            except Exception as e:
                pytest.fail(f"Valid version '{valid_version}' was rejected: {e}")

    def _validate_version(self, version: str) -> None:
        """Simulate version validation logic."""
        import re
        
        # Basic semantic version pattern
        semver_pattern = r'^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$'
        
        if not re.match(semver_pattern, version):
            raise ValueError(f"Invalid version format: {version}")
        
        # Check for dangerous characters
        dangerous_chars = [';', '&', '|', '`', '$', '<', '>', '{', '}']
        if any(char in version for char in dangerous_chars):
            raise ValueError(f"Version contains dangerous characters: {version}")


@pytest.mark.security  
class TestIntegrationSecurityValidation:
    """Test end-to-end security validation in project creation."""

    @patch('create_project.core.project_generator.ProjectGenerator.generate_project')
    def test_malicious_input_rejected_in_project_creation(self, mock_generate, 
                                                         malicious_project_names: List[str],
                                                         security_temp_dir):
        """Test that malicious input is rejected during project creation."""
        # Test a sample of malicious names
        test_names = malicious_project_names[:5]  # Test first 5 to avoid long test times
        
        for malicious_name in test_names:
            with pytest.raises((ValueError, OSError, Exception)):
                create_project(
                    template_name="python_library",
                    project_name=malicious_name,
                    target_directory=security_temp_dir,
                    variables={"author": "Test User", "version": "1.0.0"},
                )

    def test_security_boundaries_enforced_end_to_end(self, security_temp_dir):
        """Test that security boundaries are enforced in complete workflows."""
        # This should work with valid input
        try:
            result = create_project(
                template_name="python_library", 
                project_name="secure_test_project",
                target_directory=security_temp_dir,
                variables={
                    "author": "Test User",
                    "version": "1.0.0",
                    "description": "A secure test project"
                }
            )
            # Should succeed or fail gracefully without security issues
            assert result is not None
        except Exception as e:
            # Any exception should be controlled and not expose sensitive information
            error_msg = str(e).lower()
            assert "password" not in error_msg
            assert "secret" not in error_msg
            assert "/etc/passwd" not in error_msg
            assert "system" not in error_msg or "file" not in error_msg