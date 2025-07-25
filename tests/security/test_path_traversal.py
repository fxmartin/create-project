# ABOUTME: Path traversal security tests for preventing directory traversal attacks
# ABOUTME: Tests file and directory operations against malicious path manipulation

"""
Path traversal security test suite.

This module provides comprehensive security testing for path handling and file operations
in the create-project application, including:
- Directory traversal attack prevention (../, ../../)
- Absolute path injection prevention (/etc/, C:\Windows\)
- Symlink attack prevention and detection
- UNC path injection prevention (Windows)
- Path normalization bypass prevention
- Template file path security validation
- Output directory restriction enforcement
"""

import os
import tempfile
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch
import pytest

from create_project.core.path_utils import PathHandler
from create_project.core.project_generator import ProjectGenerator
from create_project.core.directory_creator import DirectoryCreator
from create_project.core.file_renderer import FileRenderer
from create_project.config.config_manager import ConfigManager


@pytest.mark.security
@pytest.mark.traversal
class TestDirectoryTraversalPrevention:
    """Test prevention of directory traversal attacks."""

    def test_reject_basic_directory_traversal(self, malicious_paths: List[str]):
        """Test that basic directory traversal attacks are prevented."""
        path_handler = PathHandler()
        
        basic_traversal = [path for path in malicious_paths if "../" in path or "..\\" in path]
        
        for malicious_path in basic_traversal:
            with pytest.raises((ValueError, OSError, FileNotFoundError)):
                validated_path = path_handler.validate_path(malicious_path)
                # If validation passes, ensure the resolved path is safe
                if validated_path:
                    resolved = Path(validated_path).resolve()
                    # Should not escape intended directory
                    assert not str(resolved).startswith("/etc")
                    assert not str(resolved).startswith("/root")
                    assert "C:\\Windows" not in str(resolved)

    def test_reject_encoded_directory_traversal(self, malicious_paths: List[str]):
        """Test that encoded directory traversal attacks are prevented."""
        path_handler = PathHandler()
        
        encoded_traversal = [path for path in malicious_paths if "%" in path]
        
        for encoded_path in encoded_traversal:
            with pytest.raises((ValueError, OSError)):
                # URL decoding should be handled safely
                path_handler.validate_path(encoded_path)

    def test_reject_unicode_directory_traversal(self, malicious_paths: List[str]):
        """Test that Unicode-encoded directory traversal is prevented."""
        path_handler = PathHandler()
        
        unicode_traversal = [
            "\u002e\u002e\u002f",  # Unicode ../
            "\u002e\u002e\u005c",  # Unicode ..\
            "..%u2215",  # Unicode slash
            "..%u005c",  # Unicode backslash
        ]
        
        for unicode_path in unicode_traversal:
            with pytest.raises((ValueError, OSError)):
                path_handler.validate_path(unicode_path)

    def test_reject_double_encoded_traversal(self):
        """Test that double-encoded traversal attacks are prevented."""
        path_handler = PathHandler()
        
        double_encoded = [
            "%252e%252e%252f",  # Double-encoded ../
            "%25252e%25252e%25252f",  # Triple-encoded ../
            "%2e%2e%2f%2e%2e%2f%2e%2e%2f",  # Multiple levels
        ]
        
        for encoded_path in double_encoded:
            with pytest.raises((ValueError, OSError)):
                path_handler.validate_path(encoded_path)

    def test_reject_mixed_separator_traversal(self):
        """Test that mixed path separator traversal is prevented."""
        path_handler = PathHandler()
        
        mixed_separators = [
            "../\\../",
            "..\\/../",
            "../\\..\\/../",
            "..\\..\\../",
        ]
        
        for mixed_path in mixed_separators:
            with pytest.raises((ValueError, OSError)):
                path_handler.validate_path(mixed_path)

    def test_directory_creation_traversal_prevention(self, security_temp_dir):
        """Test that directory creation prevents traversal attacks."""
        directory_creator = DirectoryCreator(PathHandler())
        
        malicious_dirs = [
            "../../../etc",
            "..\\..\\..\\windows",
            "normal/../../../etc",
            "projects/../../../root",
        ]
        
        for malicious_dir in malicious_dirs:
            target_path = security_temp_dir / malicious_dir
            
            with pytest.raises((ValueError, OSError, PermissionError)):
                directory_creator.create_directory(target_path)


@pytest.mark.security
@pytest.mark.traversal  
class TestAbsolutePathRejection:
    """Test prevention of absolute path injection attacks."""

    def test_reject_unix_absolute_paths(self, malicious_paths: List[str]):
        """Test that Unix absolute paths are rejected where inappropriate."""
        path_handler = PathHandler()
        
        unix_absolute = [path for path in malicious_paths if path.startswith("/")]
        
        for absolute_path in unix_absolute:
            with pytest.raises((ValueError, OSError)):
                # Should reject absolute paths in relative path contexts
                path_handler.validate_relative_path(absolute_path)

    def test_reject_windows_absolute_paths(self, malicious_paths: List[str]):
        """Test that Windows absolute paths are rejected where inappropriate."""
        path_handler = PathHandler()
        
        windows_absolute = [path for path in malicious_paths 
                           if len(path) > 2 and path[1] == ":" and path[0].isalpha()]
        
        for absolute_path in windows_absolute:
            with pytest.raises((ValueError, OSError)):
                path_handler.validate_relative_path(absolute_path)

    def test_reject_unc_paths(self, malicious_paths: List[str]):
        """Test that UNC paths are rejected."""
        path_handler = PathHandler()
        
        unc_paths = [path for path in malicious_paths if path.startswith("\\\\")]
        
        for unc_path in unc_paths:
            with pytest.raises((ValueError, OSError)):
                path_handler.validate_path(unc_path)

    def test_reject_extended_path_syntax(self):
        """Test that Windows extended path syntax is rejected."""
        path_handler = PathHandler()
        
        extended_paths = [
            "\\\\?\\C:\\Windows\\System32",
            "\\\\?\\UNC\\server\\share",
            "\\\\.\\PhysicalDrive0",
            "\\\\.\\pipe\\malicious",
        ]
        
        for extended_path in extended_paths:
            with pytest.raises((ValueError, OSError)):
                path_handler.validate_path(extended_path)

    def test_absolute_path_in_project_creation(self, security_temp_dir):
        """Test that absolute paths are handled safely in project creation."""
        config_manager = ConfigManager()
        
        malicious_targets = [
            "/etc/passwd",
            "/root/.ssh",
            "C:\\Windows\\System32",
            "\\\\server\\share",
        ]
        
        for malicious_target in malicious_targets:
            with pytest.raises((ValueError, OSError, PermissionError)):
                # Should reject creating projects in absolute system paths
                generator = ProjectGenerator(config_manager)
                generator.validate_target_path(Path(malicious_target))


@pytest.mark.security
@pytest.mark.traversal
class TestSymlinkAttackPrevention:
    """Test prevention of symlink attacks."""

    def test_detect_symlink_in_path(self, security_temp_dir):
        """Test that symlinks in paths are detected and handled safely."""
        path_handler = PathHandler()
        
        # Create a symlink pointing outside the allowed area
        symlink_path = security_temp_dir / "malicious_link"
        target_path = Path("/etc/passwd")
        
        try:
            symlink_path.symlink_to(target_path)
            
            # Should detect and reject symlink traversal
            with pytest.raises((ValueError, OSError, PermissionError)):
                path_handler.validate_path(symlink_path)
        except (OSError, NotImplementedError):
            # Symlink creation may fail on some systems, skip test
            pytest.skip("Symlink creation not supported on this system")

    def test_prevent_symlink_creation_outside_project(self, security_temp_dir):
        """Test that symlinks cannot be created pointing outside project directory."""
        file_renderer = FileRenderer(PathHandler())
        
        # Template content that tries to create a symlink
        malicious_template = {
            "evil_link": {"symlink_target": "/etc/passwd"}
        }
        
        with pytest.raises((ValueError, OSError, PermissionError)):
            # Should prevent creation of dangerous symlinks
            file_renderer.create_symlink(
                security_temp_dir / "evil_link",
                "/etc/passwd"
            )

    def test_symlink_following_prevention(self, security_temp_dir):
        """Test that symlink following is prevented where dangerous."""
        path_handler = PathHandler()
        
        # Create a directory structure with symlinks
        project_dir = security_temp_dir / "project"
        project_dir.mkdir()
        
        link_path = project_dir / "dangerous_link"
        try:
            link_path.symlink_to("/etc")
            
            # Attempting to use the symlink should be prevented
            with pytest.raises((ValueError, OSError, PermissionError)):
                path_handler.validate_path(link_path / "passwd")
        except (OSError, NotImplementedError):
            pytest.skip("Symlink creation not supported on this system")


@pytest.mark.security
@pytest.mark.traversal
class TestPathNormalizationSecurity:
    """Test security of path normalization and canonicalization."""

    def test_prevent_normalization_bypasses(self):
        """Test that path normalization bypasses are prevented."""
        path_handler = PathHandler()
        
        normalization_bypasses = [
            "normal/./../../etc/passwd",
            "normal/foo/../../../etc/passwd", 
            "normal//../../etc/passwd",
            "normal\\..\\..\\..\\windows\\system32",
            "normal/...../etc/passwd",  # Multiple dots
            "normal/.. /etc/passwd",    # Space after dots
        ]
        
        for bypass_path in normalization_bypasses:
            with pytest.raises((ValueError, OSError)):
                normalized = path_handler.normalize_path(bypass_path)
                # If normalization succeeds, check it's safe
                if normalized:
                    assert "/etc" not in str(normalized)
                    assert "\\windows" not in str(normalized).lower()

    def test_case_sensitivity_security(self):
        """Test that case sensitivity doesn't create security vulnerabilities."""
        path_handler = PathHandler()
        
        case_variations = [
            "../ETC/passwd",
            "../Etc/Passwd", 
            "..\\WINDOWS\\System32",
            "..\\Windows\\system32",
        ]
        
        for case_path in case_variations:
            with pytest.raises((ValueError, OSError)):
                path_handler.validate_path(case_path)

    def test_unicode_normalization_security(self):
        """Test that Unicode normalization doesn't create vulnerabilities."""
        path_handler = PathHandler()
        
        unicode_attacks = [
            "normal/\u002e\u002e/\u002e\u002e/etc",  # Unicode dots
            "normal/\uff0e\uff0e/\uff0e\uff0e/etc",  # Fullwidth dots
            "normal/\u2024\u2024/etc",  # One dot leader
            "normal/\u2025\u2025/etc",  # Two dot leader
        ]
        
        for unicode_path in unicode_attacks:
            with pytest.raises((ValueError, OSError)):
                path_handler.validate_path(unicode_path)


@pytest.mark.security
@pytest.mark.traversal
class TestTemplatePathSecurity:
    """Test security of template file path handling."""

    def test_template_file_access_restrictions(self, security_temp_dir):
        """Test that template files cannot access restricted paths."""
        template_engine = MagicMock()
        
        # Malicious template paths
        malicious_template_paths = [
            "../../../etc/passwd",
            "/etc/passwd", 
            "C:\\Windows\\System32\\config\\SAM",
            "../../.ssh/id_rsa",
            "../../../../../root/.bashrc",
        ]
        
        for malicious_path in malicious_template_paths:
            with pytest.raises((ValueError, OSError, FileNotFoundError)):
                # Template loading should reject dangerous paths
                template_engine.load_template_file(malicious_path)

    def test_template_include_security(self):
        """Test that template includes cannot access restricted files."""
        from jinja2 import Environment, FileSystemLoader, SecurityError
        
        # Create a restricted Jinja2 environment
        env = Environment(
            loader=FileSystemLoader("/tmp"),  # Restricted to /tmp
            autoescape=True
        )
        
        malicious_includes = [
            "{% include '/etc/passwd' %}",
            "{% include '../../../etc/passwd' %}",
            "{% include 'C:/Windows/System32/config/SAM' %}",
        ]
        
        for malicious_include in malicious_includes:
            template = env.from_string(malicious_include)
            with pytest.raises((SecurityError, OSError, FileNotFoundError)):
                template.render()

    def test_template_variable_path_injection(self, security_temp_dir):
        """Test that template variables cannot inject malicious paths."""
        from jinja2 import Environment, DictLoader
        
        env = Environment(loader=DictLoader({
            "test.html": "{% include path_var %}"
        }))
        
        malicious_path_vars = [
            "/etc/passwd",
            "../../../etc/passwd",
            "C:\\Windows\\System32\\drivers\\etc\\hosts",
        ]
        
        template = env.get_template("test.html")
        
        for malicious_path in malicious_path_vars:
            with pytest.raises((Exception,)):  # Should raise some kind of security error
                template.render(path_var=malicious_path)


@pytest.mark.security
@pytest.mark.traversal
class TestOutputDirectoryValidation:
    """Test validation and restrictions on output directories."""

    def test_restrict_system_directory_access(self, security_temp_dir):
        """Test that system directories cannot be used as output."""
        directory_creator = DirectoryCreator(PathHandler())
        
        system_directories = [
            "/etc",
            "/root", 
            "/sys",
            "/proc",
            "C:\\Windows",
            "C:\\Program Files",
            "C:\\Users\\Administrator",
        ]
        
        for system_dir in system_directories:
            with pytest.raises((ValueError, OSError, PermissionError)):
                directory_creator.validate_target_directory(Path(system_dir))

    def test_prevent_overwriting_important_files(self, security_temp_dir):
        """Test that important files cannot be overwritten."""
        file_renderer = FileRenderer(PathHandler())
        
        important_files = [
            "/etc/passwd",
            "/etc/shadow",
            "/boot/grub/grub.cfg",
            "C:\\Windows\\System32\\config\\SAM",
            "C:\\boot.ini",
        ]
        
        for important_file in important_files:
            with pytest.raises((ValueError, OSError, PermissionError)):
                file_renderer.validate_output_file(Path(important_file))

    def test_validate_project_directory_boundaries(self, security_temp_dir):
        """Test that project creation stays within designated boundaries."""
        project_generator = ProjectGenerator(ConfigManager())
        
        # Create a project in a safe location
        safe_project_dir = security_temp_dir / "safe_project"
        
        # Should succeed in safe location
        try:
            project_generator.validate_target_path(safe_project_dir)
        except Exception as e:
            pytest.fail(f"Safe project directory was rejected: {e}")
        
        # Should reject dangerous locations
        dangerous_locations = [
            Path("/etc/malicious_project"),
            Path("C:\\Windows\\malicious_project"),
            Path("/root/malicious_project"),
        ]
        
        for dangerous_location in dangerous_locations:
            with pytest.raises((ValueError, OSError, PermissionError)):
                project_generator.validate_target_path(dangerous_location)

    def test_nested_project_security(self, security_temp_dir):
        """Test security of nested project structures."""
        directory_creator = DirectoryCreator(PathHandler())
        
        # Create a legitimate project structure
        project_root = security_temp_dir / "legitimate_project"
        project_root.mkdir()
        
        # Test that nested creation doesn't escape boundaries
        nested_paths = [
            project_root / "../../../etc/passwd",
            project_root / "..\\..\\..\\windows\\system32",
            project_root / "subdir" / "../../../etc/passwd",
        ]
        
        for nested_path in nested_paths:
            with pytest.raises((ValueError, OSError)):
                directory_creator.create_directory(nested_path)


@pytest.mark.security
@pytest.mark.traversal
class TestDeviceFileAccess:
    """Test prevention of device file access."""

    def test_reject_unix_device_files(self, malicious_paths: List[str]):
        """Test that Unix device files are rejected."""
        path_handler = PathHandler()
        
        device_files = [path for path in malicious_paths 
                       if "/dev/" in path or "/proc/" in path]
        
        for device_file in device_files:
            with pytest.raises((ValueError, OSError)):
                path_handler.validate_path(device_file)

    def test_reject_windows_device_files(self):
        """Test that Windows device files are rejected."""
        path_handler = PathHandler()
        
        windows_devices = [
            "CON", "PRN", "AUX", "NUL",
            "COM1", "COM2", "COM3", "COM4",
            "LPT1", "LPT2", "LPT3", "LPT4",
            "\\\\.\\PhysicalDrive0",
            "\\\\.\\pipe\\name",
        ]
        
        for device in windows_devices:
            with pytest.raises((ValueError, OSError)):
                path_handler.validate_path(device)

    def test_reject_special_files(self):
        """Test that special files and directories are rejected."""
        path_handler = PathHandler()
        
        special_files = [
            "/proc/self/environ",
            "/proc/version",
            "/proc/self/cmdline",
            "/sys/class/dmi/id/product_name",
            "C:\\$Recycle.Bin",
            "C:\\System Volume Information",
        ]
        
        for special_file in special_files:
            with pytest.raises((ValueError, OSError)):
                path_handler.validate_path(special_file)


@pytest.mark.security
@pytest.mark.traversal
class TestPathTraversalIntegration:
    """Test path traversal prevention in integrated scenarios."""

    @patch('create_project.core.project_generator.ProjectGenerator.generate_project')
    def test_end_to_end_path_traversal_prevention(self, mock_generate, malicious_paths: List[str], security_temp_dir):
        """Test that path traversal is prevented in end-to-end project creation."""
        from create_project.core.api import create_project
        
        # Test a subset of malicious paths
        test_paths = malicious_paths[:3]
        
        for malicious_path in test_paths:
            with pytest.raises((ValueError, OSError, FileNotFoundError)):
                create_project(
                    template_name="python_library",
                    project_name="test_project",
                    target_directory=malicious_path,  # Malicious target directory
                    variables={"author": "Test User", "version": "1.0.0"},
                )

    def test_template_path_injection_prevention(self, security_temp_dir):
        """Test that template paths cannot be injected through user input."""
        config_manager = ConfigManager()
        
        # Malicious template names that try path traversal
        malicious_template_names = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/etc/passwd",
            "C:\\Windows\\System32\\drivers\\etc\\hosts",
        ]
        
        for malicious_template in malicious_template_names:
            with pytest.raises((ValueError, OSError, FileNotFoundError)):
                # Template loading should reject malicious paths
                from create_project.templates.loader import TemplateLoader
                loader = TemplateLoader(config_manager)
                loader.find_template_by_name(malicious_template)

    def test_variable_file_path_injection(self, security_temp_dir):
        """Test that file paths in variables cannot cause traversal."""
        from create_project.core.file_renderer import FileRenderer
        
        file_renderer = FileRenderer(PathHandler())
        
        # Variables containing malicious file paths
        malicious_variables = {
            "config_file": "../../../etc/passwd",
            "data_file": "/etc/shadow",
            "log_file": "C:\\Windows\\System32\\config\\SAM",
            "output_file": "..\\..\\..\\important.txt",
        }
        
        # Template that uses these variables for file paths
        template_content = "Config: {{ config_file }}\nData: {{ data_file }}"
        
        for var_name, malicious_path in malicious_variables.items():
            rendered = file_renderer.render_template_string(template_content, {var_name: malicious_path})
            
            # Rendered content should not contain actual malicious paths
            # (they should be sanitized or escaped)
            assert "/etc/passwd" not in rendered
            assert "C:\\Windows" not in rendered
            assert "..\\" not in rendered and "../" not in rendered