# ABOUTME: Comprehensive unit tests for ErrorContextCollector with PII sanitization and context collection
# ABOUTME: Tests system context, project context, error context, template context, and sanitization features

"""Unit tests for context collector module."""

import os
import platform
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from create_project.ai.context_collector import (
    CompleteErrorContext,
    ErrorContext,
    ErrorContextCollector,
    ProjectContext,
    SystemContext,
    TemplateContext,
)
from create_project.ai.exceptions import ContextCollectionError
from create_project.core.exceptions import ProjectGenerationError
from create_project.templates.schema.template import Template


class TestSystemContext:
    """Test SystemContext dataclass."""

    def test_system_context_creation(self):
        """Test creating SystemContext instance."""
        context = SystemContext(
            os_name="Darwin",
            os_version="23.5.0",
            python_version="3.9.6",
            platform_machine="arm64",
            available_disk_space_gb=100.5,
            working_directory="/Users/[USER]/project",
            environment_variables={"PATH": "/usr/bin", "PYTHONPATH": "/path/to/python"}
        )
        
        assert context.os_name == "Darwin"
        assert context.os_version == "23.5.0"
        assert context.python_version == "3.9.6"
        assert context.platform_machine == "arm64"
        assert context.available_disk_space_gb == 100.5
        assert context.working_directory == "/Users/[USER]/project"
        assert len(context.environment_variables) == 2


class TestProjectContext:
    """Test ProjectContext dataclass."""

    def test_project_context_creation(self):
        """Test creating ProjectContext instance."""
        context = ProjectContext(
            template_name="web_app",
            target_path="/Users/[USER]/my_project",
            project_variables={"project_name": "MyApp", "author": "Developer"},
            options={"create_venv": True, "init_git": True},
            attempted_operations=["create_directory", "render_template"],
            partial_results={"files_created": 5, "directories_created": 2}
        )
        
        assert context.template_name == "web_app"
        assert context.target_path == "/Users/[USER]/my_project"
        assert context.project_variables["project_name"] == "MyApp"
        assert context.options["create_venv"] is True
        assert "create_directory" in context.attempted_operations
        assert context.partial_results["files_created"] == 5


class TestErrorContext:
    """Test ErrorContext dataclass."""

    def test_error_context_creation(self):
        """Test creating ErrorContext instance."""
        context = ErrorContext(
            error_type="FileNotFoundError",
            error_message="Template file not found",
            traceback_lines=["File 'template.py', line 42", "FileNotFoundError"],
            error_location="File 'template.py', line 42",
            original_error="OSError: No such file or directory",
            validation_errors=["Missing required variable: project_name"]
        )
        
        assert context.error_type == "FileNotFoundError"
        assert context.error_message == "Template file not found"
        assert len(context.traceback_lines) == 2
        assert context.error_location == "File 'template.py', line 42"
        assert context.original_error == "OSError: No such file or directory"
        assert len(context.validation_errors) == 1


class TestTemplateContext:
    """Test TemplateContext dataclass."""

    def test_template_context_creation(self):
        """Test creating TemplateContext instance."""
        context = TemplateContext(
            template_name="python_package",
            template_version="1.2.0",
            required_variables=["project_name", "author"],
            available_variables=["project_name"],
            missing_variables=["author"],
            template_files=["setup.py.j2", "README.md.j2"],
            validation_status="missing_variables"
        )
        
        assert context.template_name == "python_package"
        assert context.template_version == "1.2.0"
        assert "project_name" in context.required_variables
        assert "author" in context.missing_variables
        assert len(context.template_files) == 2
        assert context.validation_status == "missing_variables"


class TestCompleteErrorContext:
    """Test CompleteErrorContext dataclass."""

    def test_complete_error_context_creation(self):
        """Test creating CompleteErrorContext instance."""
        system_ctx = SystemContext(
            os_name="Darwin", os_version="23.5.0", python_version="3.9.6",
            platform_machine="arm64", available_disk_space_gb=100.0,
            working_directory="/path", environment_variables={}
        )
        
        project_ctx = ProjectContext(
            template_name="test", target_path="/target", project_variables={},
            options={}, attempted_operations=[], partial_results={}
        )
        
        error_ctx = ErrorContext(
            error_type="TestError", error_message="Test error",
            traceback_lines=[], error_location=None, original_error=None,
            validation_errors=[]
        )
        
        template_ctx = TemplateContext(
            template_name="test", template_version="1.0",
            required_variables=[], available_variables=[], missing_variables=[],
            template_files=[], validation_status="valid"
        )
        
        complete_ctx = CompleteErrorContext(
            timestamp="2024-01-01T00:00:00",
            context_version="1.0.0",
            system=system_ctx,
            project=project_ctx,
            error=error_ctx,
            template=template_ctx,
            context_size_bytes=1024,
            collection_duration_ms=50.0
        )
        
        assert complete_ctx.timestamp == "2024-01-01T00:00:00"
        assert complete_ctx.context_version == "1.0.0"
        assert complete_ctx.context_size_bytes == 1024
        assert complete_ctx.collection_duration_ms == 50.0


class TestErrorContextCollector:
    """Test ErrorContextCollector class."""

    @pytest.fixture
    def collector(self):
        """Create error context collector instance."""
        return ErrorContextCollector()

    @pytest.fixture
    def mock_template(self):
        """Create mock template for testing."""
        template = Mock(spec=Template)
        template.name = "test_template"
        template.version = "1.0.0"
        
        # Mock variables
        mock_var1 = Mock()
        mock_var1.name = "project_name"
        mock_var1.required = True
        
        mock_var2 = Mock()
        mock_var2.name = "author"
        mock_var2.required = False
        
        template.variables = [mock_var1, mock_var2]
        
        # Mock files
        mock_file1 = Mock()
        mock_file1.source = "template1.j2"
        mock_file2 = Mock()
        mock_file2.source = "template2.j2"
        
        template.files = [mock_file1, mock_file2]
        
        return template

    def test_initialization(self, collector):
        """Test collector initialization."""
        assert collector.CONTEXT_VERSION == "1.0.0"
        assert collector.MAX_CONTEXT_SIZE == 4096
        assert len(collector.PII_PATTERNS) > 0
        assert collector.logger is not None

    def test_collect_context_success(self, collector, mock_template):
        """Test successful context collection."""
        error = ValueError("Test error")
        project_variables = {"project_name": "TestApp", "author": "TestUser"}
        target_path = Path("/tmp/test_project")
        options = {"create_venv": True}
        attempted_operations = ["create_dir", "render_template"]
        partial_results = {"files_created": 3}
        
        with patch.object(collector, '_collect_system_context') as mock_system, \
             patch.object(collector, '_collect_project_context') as mock_project, \
             patch.object(collector, '_collect_error_context') as mock_error, \
             patch.object(collector, '_collect_template_context') as mock_template_ctx:
            
            # Mock return values
            mock_system.return_value = SystemContext(
                os_name="Darwin", os_version="23.5.0", python_version="3.9.6",
                platform_machine="arm64", available_disk_space_gb=100.0,
                working_directory="/path", environment_variables={}
            )
            
            mock_project.return_value = ProjectContext(
                template_name="test", target_path="/target", project_variables={},
                options={}, attempted_operations=[], partial_results={}
            )
            
            mock_error.return_value = ErrorContext(
                error_type="ValueError", error_message="Test error",
                traceback_lines=[], error_location=None, original_error=None,
                validation_errors=[]
            )
            
            mock_template_ctx.return_value = TemplateContext(
                template_name="test", template_version="1.0",
                required_variables=[], available_variables=[], missing_variables=[],
                template_files=[], validation_status="valid"
            )
            
            context = collector.collect_context(
                error=error,
                template=mock_template,
                project_variables=project_variables,
                target_path=target_path,
                options=options,
                attempted_operations=attempted_operations,
                partial_results=partial_results
            )
            
            assert isinstance(context, CompleteErrorContext)
            assert context.context_version == "1.0.0"
            assert context.system.os_name == "Darwin"
            assert context.error.error_type == "ValueError"
            assert context.context_size_bytes > 0
            assert context.collection_duration_ms >= 0

    def test_collect_context_failure(self, collector):
        """Test context collection failure handling."""
        error = ValueError("Test error")
        
        with patch.object(collector, '_collect_system_context', side_effect=Exception("System error")):
            with pytest.raises(ContextCollectionError) as exc_info:
                collector.collect_context(error)
            
            assert "Context collection failed" in str(exc_info.value)
            assert exc_info.value.original_error is not None

    def test_collect_context_large_size_warning(self, collector):
        """Test warning when context size exceeds limit."""
        error = ValueError("Test error")
        
        with patch.object(collector, '_collect_system_context'), \
             patch.object(collector, '_collect_project_context'), \
             patch.object(collector, '_collect_error_context'), \
             patch.object(collector, '_collect_template_context'), \
             patch.object(collector, 'MAX_CONTEXT_SIZE', 100):  # Very small limit
            
            # Mock large context returns
            large_data = "x" * 200  # Larger than limit
            mock_system = SystemContext(
                os_name=large_data, os_version="23.5.0", python_version="3.9.6",
                platform_machine="arm64", available_disk_space_gb=100.0,
                working_directory="/path", environment_variables={}
            )
            
            collector._collect_system_context.return_value = mock_system
            collector._collect_project_context.return_value = ProjectContext(
                template_name="test", target_path="/target", project_variables={},
                options={}, attempted_operations=[], partial_results={}
            )
            collector._collect_error_context.return_value = ErrorContext(
                error_type="ValueError", error_message="Test error",
                traceback_lines=[], error_location=None, original_error=None,
                validation_errors=[]
            )
            collector._collect_template_context.return_value = TemplateContext(
                template_name="test", template_version="1.0",
                required_variables=[], available_variables=[], missing_variables=[],
                template_files=[], validation_status="valid"
            )
            
            with patch.object(collector.logger, 'warning') as mock_warning:
                context = collector.collect_context(error)
                
                # Should warn about large context
                mock_warning.assert_called()
                warning_call = mock_warning.call_args
                assert "Context size exceeds target" in warning_call[0][0]

    @patch('create_project.ai.context_collector.shutil.disk_usage')
    @patch('create_project.ai.context_collector.platform.system')
    @patch('create_project.ai.context_collector.platform.version')
    @patch('create_project.ai.context_collector.platform.machine')
    def test_collect_system_context_success(self, mock_machine, mock_version, mock_system, mock_disk, collector):
        """Test successful system context collection."""
        # Mock system calls
        mock_system.return_value = "Darwin"
        mock_version.return_value = "23.5.0"
        mock_machine.return_value = "arm64"
        mock_disk.return_value = (1000000000000, 500000000000, 400000000000)  # total, used, free
        
        with patch.dict(os.environ, {"PATH": "/usr/bin", "PYTHONPATH": "/python/path"}):
            context = collector._collect_system_context()
            
            assert context.os_name == "Darwin"
            assert context.os_version == "23.5.0"
            assert context.platform_machine == "arm64"
            assert context.available_disk_space_gb == round(400000000000 / (1024**3), 2)
            assert "PATH" in context.environment_variables
            assert context.environment_variables["PATH"] == "/usr/bin"

    @patch('create_project.ai.context_collector.shutil.disk_usage')
    def test_collect_system_context_disk_error(self, mock_disk, collector):
        """Test system context collection with disk usage error."""
        mock_disk.side_effect = OSError("Permission denied")
        
        with patch.object(collector.logger, 'warning') as mock_warning:
            context = collector._collect_system_context()
            
            # Should still return context with fallback values
            assert context.available_disk_space_gb == 0.0
            assert context.os_name in ["Darwin", "Linux", "Windows", "unknown"]
            mock_warning.assert_called()

    @patch('create_project.ai.context_collector.platform.system')
    def test_collect_system_context_platform_error(self, mock_system, collector):
        """Test system context collection with platform errors."""
        mock_system.side_effect = Exception("Platform error")
        
        with patch.object(collector.logger, 'warning') as mock_warning:
            context = collector._collect_system_context()
            
            # Should use fallback values
            assert context.os_name == "unknown"
            assert context.python_version == sys.version  # This should still work
            mock_warning.assert_called()

    def test_collect_project_context_with_template(self, collector, mock_template):
        """Test project context collection with template."""
        project_variables = {"project_name": "TestApp", "author": "TestUser"}
        target_path = Path("/var/lib/test_project")  # Use path that won't be sanitized
        options = {"create_venv": True, "init_git": False}
        attempted_operations = ["create_directory", "render_template"]
        partial_results = {"files_created": 5, "directories_created": 2}
        
        context = collector._collect_project_context(
            template=mock_template,
            project_variables=project_variables,
            target_path=target_path,
            options=options,
            attempted_operations=attempted_operations,
            partial_results=partial_results
        )
        
        assert context.template_name == "test_template"
        assert context.target_path == "/var/lib/test_project"
        assert context.project_variables["project_name"] == "TestApp"
        assert context.options["create_venv"] is True
        assert "create_directory" in context.attempted_operations
        assert context.partial_results["files_created"] == 5

    def test_collect_project_context_without_template(self, collector):
        """Test project context collection without template."""
        context = collector._collect_project_context(
            template=None,
            project_variables=None,
            target_path=None,
            options=None,
            attempted_operations=None,
            partial_results=None
        )
        
        assert context.template_name == "unknown"
        assert context.target_path == "unknown"
        assert context.project_variables == {}
        assert context.options == {}
        assert context.attempted_operations == []
        assert context.partial_results == {}

    def test_collect_project_context_sanitization(self, collector, mock_template):
        """Test project context collection sanitizes PII."""
        project_variables = {
            "author_email": "user@example.com",
            "home_path": "/Users/john/project"
        }
        target_path = Path("/Users/jane/my_project")
        
        context = collector._collect_project_context(
            template=mock_template,
            project_variables=project_variables,
            target_path=target_path,
            options={},
            attempted_operations=[],
            partial_results={}
        )
        
        # Should sanitize email and user paths
        assert context.project_variables["author_email"] == "[EMAIL]"
        assert "[USER]" in context.project_variables["home_path"]
        assert "[USER]" in context.target_path

    def test_collect_error_context_basic_error(self, collector):
        """Test error context collection for basic error."""
        error = ValueError("Test error message")
        
        context = collector._collect_error_context(error)
        
        assert context.error_type == "ValueError"
        assert context.error_message == "Test error message"
        assert context.original_error is None
        assert context.validation_errors == []

    def test_collect_error_context_with_traceback(self, collector):
        """Test error context collection with traceback."""
        try:
            raise ValueError("Error with traceback")
        except ValueError as e:
            context = collector._collect_error_context(e)
            
            assert context.error_type == "ValueError"
            assert context.error_message == "Error with traceback"
            assert len(context.traceback_lines) > 0
            assert context.error_location is not None

    def test_collect_error_context_project_generation_error(self, collector):
        """Test error context collection for ProjectGenerationError."""
        original_error = FileNotFoundError("Template not found")
        error = ProjectGenerationError("Generation failed", original_error=original_error)
        
        context = collector._collect_error_context(error)
        
        assert context.error_type == "ProjectGenerationError"
        assert "Generation failed" in context.error_message
        assert "Template not found" in context.original_error

    def test_collect_error_context_with_validation_errors(self, collector):
        """Test error context collection with validation errors."""
        validation_errors = ["Missing required field: name", "Invalid email format"]
        error = Exception("Validation failed")
        error.details = {"validation_errors": validation_errors}
        
        context = collector._collect_error_context(error)
        
        assert len(context.validation_errors) == 2
        assert "Missing required field: name" in context.validation_errors
        assert "Invalid email format" in context.validation_errors

    def test_collect_template_context_with_template(self, collector, mock_template):
        """Test template context collection with template."""
        project_variables = {"project_name": "TestApp", "description": "Test description"}
        
        context = collector._collect_template_context(mock_template, project_variables)
        
        assert context.template_name == "test_template"
        assert context.template_version == "1.0.0"
        assert "project_name" in context.required_variables
        assert "project_name" in context.available_variables
        assert len(context.missing_variables) == 0  # project_name is provided
        assert len(context.template_files) == 2
        assert context.validation_status == "valid"

    def test_collect_template_context_missing_variables(self, collector, mock_template):
        """Test template context collection with missing variables."""
        # Only provide partial variables
        project_variables = {"description": "Test description"}
        
        context = collector._collect_template_context(mock_template, project_variables)
        
        assert context.template_name == "test_template"
        assert "project_name" in context.required_variables
        assert "project_name" not in context.available_variables
        assert "project_name" in context.missing_variables
        assert context.validation_status == "missing_variables"

    def test_collect_template_context_without_template(self, collector):
        """Test template context collection without template."""
        context = collector._collect_template_context(None, {"var": "value"})
        
        assert context.template_name == "unknown"
        assert context.template_version == "unknown"
        assert context.required_variables == []
        assert context.available_variables == []
        assert context.missing_variables == []
        assert context.template_files == []
        assert context.validation_status == "no_template"

    def test_collect_template_context_many_files(self, collector, mock_template):
        """Test template context collection limits file count."""
        # Create template with many files
        files = []
        for i in range(15):  # More than the 10 file limit
            mock_file = Mock()
            mock_file.source = f"template_{i}.j2"
            files.append(mock_file)
        
        mock_template.files = files
        
        context = collector._collect_template_context(mock_template, {})
        
        # Should limit to 10 files
        assert len(context.template_files) == 10
        assert context.template_files[0] == "template_0.j2"
        assert context.template_files[9] == "template_9.j2"

    def test_sanitize_text_basic(self, collector):
        """Test basic text sanitization."""
        text = "Hello world"
        result = collector._sanitize_text(text)
        assert result == "Hello world"

    def test_sanitize_text_user_paths(self, collector):
        """Test sanitization of user paths."""
        test_cases = [
            ("/Users/john/project", "/Users/[USER]/project"),
            ("/home/jane/work", "/home/[USER]/work"),
            (r"C:\Users\bob\documents", r"C:\Users\[USER]\documents"),
        ]
        
        for original, expected in test_cases:
            result = collector._sanitize_text(original)
            assert result == expected

    def test_sanitize_text_email_addresses(self, collector):
        """Test sanitization of email addresses."""
        test_cases = [
            ("Contact user@example.com for help", "Contact [EMAIL] for help"),
            ("Emails: test@test.org, admin@site.net", "Emails: [EMAIL], [EMAIL]"),
            ("No emails here", "No emails here"),
        ]
        
        for original, expected in test_cases:
            result = collector._sanitize_text(original)
            assert result == expected

    def test_sanitize_text_ip_addresses(self, collector):
        """Test sanitization of IP addresses."""
        test_cases = [
            ("Server at 192.168.1.1", "Server at [IP_ADDRESS]"),
            ("Connect to 10.0.0.1:8080", "Connect to [IP_ADDRESS]:8080"),
            ("Invalid IP 999.999.999.999", "Invalid IP [IP_ADDRESS]"),  # Regex matches any 1-3 digit pattern
            ("Not an IP: 1234.5678.9012.3456", "Not an IP: 1234.5678.9012.3456"),  # 4+ digits not matched
        ]
        
        for original, expected in test_cases:
            result = collector._sanitize_text(original)
            assert result == expected

    def test_sanitize_text_temp_paths(self, collector):
        """Test sanitization of temporary paths."""
        test_cases = [
            ("/tmp/temp_file_123", "/tmp/[TEMP]"),
            ("/tmp/my-temp-dir", "/tmp/[TEMP]"),
            ("/tmp/", "/tmp/"),  # Just /tmp/ not matched
        ]
        
        for original, expected in test_cases:
            result = collector._sanitize_text(original)
            assert result == expected

    def test_sanitize_text_non_string_input(self, collector):
        """Test sanitization with non-string input."""
        result = collector._sanitize_text(12345)
        assert result == "12345"
        
        result = collector._sanitize_text(None)
        assert result == "None"

    def test_sanitize_value_string(self, collector):
        """Test value sanitization for strings."""
        result = collector._sanitize_value("user@example.com")
        assert result == "[EMAIL]"

    def test_sanitize_value_list(self, collector):
        """Test value sanitization for lists."""
        original = ["/Users/john/file", "user@test.com", "normal text"]
        result = collector._sanitize_value(original)
        
        assert result[0] == "/Users/[USER]/file"
        assert result[1] == "[EMAIL]"
        assert result[2] == "normal text"

    def test_sanitize_value_tuple(self, collector):
        """Test value sanitization for tuples."""
        original = ("/Users/jane/project", "admin@site.org")
        result = collector._sanitize_value(original)
        
        assert isinstance(result, list)  # Tuple becomes list
        assert result[0] == "/Users/[USER]/project"
        assert result[1] == "[EMAIL]"

    def test_sanitize_value_dict(self, collector):
        """Test value sanitization for dictionaries."""
        original = {
            "email": "user@example.com",
            "path": "/home/user/docs",
            "count": 42
        }
        result = collector._sanitize_value(original)
        
        assert result["email"] == "[EMAIL]"
        assert result["path"] == "/home/[USER]/docs"
        assert result["count"] == 42

    def test_sanitize_value_nested_structures(self, collector):
        """Test value sanitization for nested structures."""
        original = {
            "users": [
                {"email": "user1@test.com", "path": "/Users/user1"},
                {"email": "user2@test.com", "path": "/Users/user2"}
            ],
            "config": {
                "admin_email": "admin@example.org",
                "log_path": "/tmp/app_logs"
            }
        }
        result = collector._sanitize_value(original)
        
        assert result["users"][0]["email"] == "[EMAIL]"
        assert result["users"][0]["path"] == "/Users/[USER]"
        assert result["users"][1]["email"] == "[EMAIL]"
        assert result["config"]["admin_email"] == "[EMAIL]"
        assert result["config"]["log_path"] == "/tmp/[TEMP]"

    def test_sanitize_value_other_types(self, collector):
        """Test value sanitization for other types."""
        # Numbers, booleans, None should pass through unchanged
        assert collector._sanitize_value(42) == 42
        assert collector._sanitize_value(3.14) == 3.14
        assert collector._sanitize_value(True) is True
        assert collector._sanitize_value(False) is False
        assert collector._sanitize_value(None) is None

    def test_pii_patterns_complete(self, collector):
        """Test that all PII patterns work correctly."""
        test_text = """
        User path: /Users/testuser/project
        Home path: /home/developer/work
        Windows path: C:\\Users\\admin\\documents
        Email: contact@company.com
        IP: 192.168.1.100
        Temp: /tmp/temp_123_file
        """
        
        result = collector._sanitize_text(test_text)
        
        assert "/Users/[USER]" in result
        assert "/home/[USER]" in result
        assert "C:\\Users\\[USER]" in result
        assert "[EMAIL]" in result
        assert "[IP_ADDRESS]" in result
        assert "/tmp/[TEMP]" in result

    def test_context_version_constant(self, collector):
        """Test context version constant."""
        assert collector.CONTEXT_VERSION == "1.0.0"

    def test_max_context_size_constant(self, collector):
        """Test max context size constant."""
        assert collector.MAX_CONTEXT_SIZE == 4096

    def test_integration_full_context_collection(self, collector):
        """Test full integration of context collection."""
        # Create a real error with traceback
        try:
            raise FileNotFoundError("Template file missing")
        except FileNotFoundError as error:
            # Create minimal mock template
            template = Mock()
            template.name = "integration_test"
            template.version = "1.0"
            template.variables = []
            template.files = []
            
            project_variables = {"name": "TestProject"}
            target_path = Path("/tmp/integration_test")
            
            context = collector.collect_context(
                error=error,
                template=template,
                project_variables=project_variables,
                target_path=target_path
            )
            
            # Verify complete context structure
            assert isinstance(context, CompleteErrorContext)
            assert context.context_version == "1.0.0"
            assert context.system.os_name in ["Darwin", "Linux", "Windows"]
            assert context.project.template_name == "integration_test"
            assert context.error.error_type == "FileNotFoundError"
            assert context.template.template_name == "integration_test"
            assert context.context_size_bytes > 0
            assert context.collection_duration_ms >= 0

    def test_concurrent_context_collection(self, collector):
        """Test concurrent context collection is thread-safe."""
        import threading
        
        results = []
        errors = []
        
        def collect_context_thread():
            try:
                error = ValueError(f"Thread error {threading.current_thread().ident}")
                context = collector.collect_context(error)
                results.append(context)
            except Exception as e:
                errors.append(e)
        
        # Run multiple threads concurrently
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=collect_context_thread)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # All should succeed
        assert len(errors) == 0
        assert len(results) == 3
        
        # Each context should be unique but well-formed
        for context in results:
            assert isinstance(context, CompleteErrorContext)
            assert context.context_version == "1.0.0"