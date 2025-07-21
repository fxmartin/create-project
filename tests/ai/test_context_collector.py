# ABOUTME: Comprehensive test suite for ErrorContextCollector
# ABOUTME: Tests context collection, PII sanitization, and error handling

"""
Test suite for ErrorContextCollector.

Tests context collection functionality including:
- System information collection
- Project parameter extraction
- Error traceback processing
- Template context gathering
- PII sanitization
- Error handling and edge cases
"""

import os
import sys
import platform
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import pytest

from create_project.ai.context_collector import (
    ErrorContextCollector,
    SystemContext,
    ProjectContext,
    ErrorContext,
    TemplateContext,
    CompleteErrorContext
)
from create_project.ai.exceptions import ContextCollectionError
from create_project.core.exceptions import (
    ProjectGenerationError,
    TemplateError,
    PathError
)
from create_project.templates.schema.template import Template
from create_project.templates.schema.variables import TemplateVariable
from create_project.templates.schema.structure import TemplateFile


class TestSystemContext:
    """Test SystemContext dataclass."""
    
    def test_system_context_creation(self):
        """Test creating SystemContext."""
        context = SystemContext(
            os_name="Linux",
            os_version="5.4.0",
            python_version="3.9.6",
            platform_machine="x86_64",
            available_disk_space_gb=100.5,
            working_directory="/home/[USER]/project",
            environment_variables={"PATH": "/usr/bin", "PYTHONPATH": "/usr/lib"}
        )
        
        assert context.os_name == "Linux"
        assert context.os_version == "5.4.0"
        assert context.python_version == "3.9.6"
        assert context.platform_machine == "x86_64"
        assert context.available_disk_space_gb == 100.5
        assert context.working_directory == "/home/[USER]/project"
        assert context.environment_variables == {"PATH": "/usr/bin", "PYTHONPATH": "/usr/lib"}


class TestProjectContext:
    """Test ProjectContext dataclass."""
    
    def test_project_context_creation(self):
        """Test creating ProjectContext."""
        context = ProjectContext(
            template_name="python_library",
            target_path="/projects/[USER]/myproject",
            project_variables={"name": "myproject", "author": "[EMAIL]"},
            options={"create_git_repo": True, "create_venv": True},
            attempted_operations=["create_directory", "render_files"],
            partial_results={"files_created": 5, "directories_created": 3}
        )
        
        assert context.template_name == "python_library"
        assert context.target_path == "/projects/[USER]/myproject"
        assert context.project_variables == {"name": "myproject", "author": "[EMAIL]"}
        assert context.options == {"create_git_repo": True, "create_venv": True}
        assert context.attempted_operations == ["create_directory", "render_files"]
        assert context.partial_results == {"files_created": 5, "directories_created": 3}


class TestErrorContext:
    """Test ErrorContext dataclass."""
    
    def test_error_context_creation(self):
        """Test creating ErrorContext."""
        context = ErrorContext(
            error_type="TemplateError",
            error_message="Template variable 'author' is missing",
            traceback_lines=[
                'File "/home/[USER]/project/generator.py", line 123, in render',
                'template.render(variables)',
                'jinja2.exceptions.UndefinedError: Template variable not found'
            ],
            error_location='File "/home/[USER]/project/generator.py", line 123',
            original_error="UndefinedError: Template variable not found",
            validation_errors=["Missing required variable: author"]
        )
        
        assert context.error_type == "TemplateError"
        assert "Template variable 'author' is missing" in context.error_message
        assert len(context.traceback_lines) == 3
        assert "line 123" in context.error_location
        assert "UndefinedError" in context.original_error
        assert context.validation_errors == ["Missing required variable: author"]


class TestTemplateContext:
    """Test TemplateContext dataclass."""
    
    def test_template_context_creation(self):
        """Test creating TemplateContext."""
        context = TemplateContext(
            template_name="python_library",
            template_version="1.0.0",
            required_variables=["name", "author", "description"],
            available_variables=["name", "description"],
            missing_variables=["author"],
            template_files=["setup.py", "README.md", "src/__init__.py"],
            validation_status="missing_variables"
        )
        
        assert context.template_name == "python_library"
        assert context.template_version == "1.0.0"
        assert context.required_variables == ["name", "author", "description"]
        assert context.available_variables == ["name", "description"]
        assert context.missing_variables == ["author"]
        assert context.template_files == ["setup.py", "README.md", "src/__init__.py"]
        assert context.validation_status == "missing_variables"


class TestCompleteErrorContext:
    """Test CompleteErrorContext dataclass."""
    
    def test_complete_error_context_creation(self):
        """Test creating CompleteErrorContext."""
        system_ctx = SystemContext(
            os_name="Linux", os_version="5.4.0", python_version="3.9.6",
            platform_machine="x86_64", available_disk_space_gb=100.0,
            working_directory="/home/[USER]", environment_variables={}
        )
        
        project_ctx = ProjectContext(
            template_name="python_library", target_path="/projects/[USER]/test",
            project_variables={}, options={}, attempted_operations=[], partial_results={}
        )
        
        error_ctx = ErrorContext(
            error_type="TemplateError", error_message="Test error",
            traceback_lines=[], error_location=None, original_error=None, validation_errors=[]
        )
        
        template_ctx = TemplateContext(
            template_name="python_library", template_version="1.0.0",
            required_variables=[], available_variables=[], missing_variables=[],
            template_files=[], validation_status="valid"
        )
        
        complete_ctx = CompleteErrorContext(
            timestamp="2023-07-21T10:30:00",
            context_version="1.0.0",
            system=system_ctx,
            project=project_ctx,
            error=error_ctx,
            template=template_ctx,
            context_size_bytes=1024,
            collection_duration_ms=150.5
        )
        
        assert complete_ctx.timestamp == "2023-07-21T10:30:00"
        assert complete_ctx.context_version == "1.0.0"
        assert complete_ctx.context_size_bytes == 1024
        assert complete_ctx.collection_duration_ms == 150.5
        assert isinstance(complete_ctx.system, SystemContext)
        assert isinstance(complete_ctx.project, ProjectContext)
        assert isinstance(complete_ctx.error, ErrorContext)
        assert isinstance(complete_ctx.template, TemplateContext)


class TestErrorContextCollector:
    """Test ErrorContextCollector class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.collector = ErrorContextCollector()
        
        # Create mock template
        self.mock_template = Mock(spec=Template)
        self.mock_template.name = "test_template"
        self.mock_template.version = "1.0.0"
        
        # Create mock template variables
        required_var = Mock(spec=TemplateVariable)
        required_var.name = "name"
        required_var.required = True
        
        optional_var = Mock(spec=TemplateVariable)
        optional_var.name = "description"
        optional_var.required = False
        
        self.mock_template.variables = [required_var, optional_var]
        
        # Create mock template files
        file1 = Mock(spec=TemplateFile)
        file1.source = "setup.py.j2"
        
        file2 = Mock(spec=TemplateFile)
        file2.source = "README.md.j2"
        
        self.mock_template.files = [file1, file2]
    
    def test_initialization(self):
        """Test ErrorContextCollector initialization."""
        collector = ErrorContextCollector()
        assert collector.CONTEXT_VERSION == "1.0.0"
        assert collector.MAX_CONTEXT_SIZE == 4096
        assert len(collector.PII_PATTERNS) > 0
    
    @patch('platform.system')
    @patch('platform.version')
    @patch('platform.machine')
    @patch('shutil.disk_usage')
    @patch.dict(os.environ, {'PATH': '/usr/bin:/bin', 'PYTHONPATH': '/home/user/lib'})
    def test_collect_system_context(self, mock_disk, mock_machine, mock_version, mock_system):
        """Test system context collection."""
        mock_system.return_value = "Linux"
        mock_version.return_value = "5.4.0-generic"
        mock_machine.return_value = "x86_64"
        
        # Mock disk usage (total, used, free)
        mock_disk.return_value = (1000000000000, 500000000000, 500000000000)  # 500GB free
        
        context = self.collector._collect_system_context()
        
        assert context.os_name == "Linux"
        assert context.os_version == "5.4.0-generic"
        assert context.python_version == sys.version
        assert context.platform_machine == "x86_64"
        assert context.available_disk_space_gb > 0
        assert 'PATH' in context.environment_variables
        assert 'PYTHONPATH' in context.environment_variables
    
    @patch('shutil.disk_usage')
    def test_collect_system_context_with_error(self, mock_disk):
        """Test system context collection handles errors gracefully."""
        mock_disk.side_effect = OSError("Permission denied")
        
        context = self.collector._collect_system_context()
        
        # Should return default values on error
        assert context.os_name != "unknown" or platform.system() == context.os_name
        assert context.available_disk_space_gb == 0.0
    
    def test_collect_project_context(self):
        """Test project context collection."""
        project_variables = {"name": "myproject", "author": "test@example.com"}
        target_path = Path("/home/testuser/projects/myproject")
        options = {"create_git_repo": True, "create_venv": True}
        attempted_operations = ["create_directory", "render_files"]
        partial_results = {"files_created": 3}
        
        context = self.collector._collect_project_context(
            self.mock_template, project_variables, target_path, options,
            attempted_operations, partial_results
        )
        
        assert context.template_name == "test_template"
        assert "/home/[USER]/" in context.target_path
        assert context.project_variables["name"] == "myproject"
        assert context.project_variables["author"] == "[EMAIL]"
        assert context.options == options
        assert context.attempted_operations == attempted_operations
        assert context.partial_results == partial_results
    
    def test_collect_project_context_with_none_values(self):
        """Test project context collection with None values."""
        context = self.collector._collect_project_context(
            None, None, None, None, None, None
        )
        
        assert context.template_name == "unknown"
        assert context.target_path == "unknown"
        assert context.project_variables == {}
        assert context.options == {}
        assert context.attempted_operations == []
        assert context.partial_results == {}
    
    def test_collect_error_context(self):
        """Test error context collection."""
        try:
            # Create a test error with traceback
            raise TemplateError("Template variable missing", details={"validation_errors": ["Missing: name"]})
        except TemplateError as e:
            context = self.collector._collect_error_context(e)
            
            assert context.error_type == "TemplateError"
            assert "Template variable missing" in context.error_message
            assert len(context.traceback_lines) > 0
            assert context.validation_errors == ["Missing: name"]
    
    def test_collect_error_context_with_original_error(self):
        """Test error context collection with original error."""
        original = ValueError("Original error")
        error = ProjectGenerationError("Wrapper error", original_error=original)
        
        context = self.collector._collect_error_context(error)
        
        assert context.error_type == "ProjectGenerationError"
        assert "Wrapper error" in context.error_message
        assert "Original error" in context.original_error
    
    def test_collect_template_context(self):
        """Test template context collection."""
        project_variables = {"name": "myproject"}  # Missing "description"
        
        context = self.collector._collect_template_context(self.mock_template, project_variables)
        
        assert context.template_name == "test_template"
        assert context.template_version == "1.0.0"
        assert "name" in context.required_variables
        assert "name" in context.available_variables
        assert len(context.missing_variables) == 0  # "name" is available, "description" is optional
        assert len(context.template_files) == 2
        assert context.validation_status == "valid"
    
    def test_collect_template_context_with_missing_variables(self):
        """Test template context collection with missing variables."""
        project_variables = {"description": "A test project"}  # Missing required "name"
        
        context = self.collector._collect_template_context(self.mock_template, project_variables)
        
        assert context.template_name == "test_template"
        assert "name" in context.required_variables
        assert "name" in context.missing_variables
        assert context.validation_status == "missing_variables"
    
    def test_collect_template_context_no_template(self):
        """Test template context collection with no template."""
        context = self.collector._collect_template_context(None, None)
        
        assert context.template_name == "unknown"
        assert context.template_version == "unknown"
        assert context.required_variables == []
        assert context.available_variables == []
        assert context.missing_variables == []
        assert context.template_files == []
        assert context.validation_status == "no_template"
    
    def test_sanitize_text_removes_pii(self):
        """Test PII sanitization in text."""
        test_cases = [
            ("/Users/johnsmith/project", "/Users/[USER]/project"),
            ("/home/alice/work", "/home/[USER]/work"),
            ("C:\\Users\\bob\\Documents", "C:\\Users\\[USER]\\Documents"),
            ("Contact: john@example.com", "Contact: [EMAIL]"),
            ("IP: 192.168.1.1", "IP: [IP_ADDRESS]"),
            ("/tmp/temp123", "/tmp/[TEMP]"),
        ]
        
        for original, expected in test_cases:
            sanitized = self.collector._sanitize_text(original)
            assert sanitized == expected
    
    def test_sanitize_value_handles_different_types(self):
        """Test value sanitization for different data types."""
        # String
        assert self.collector._sanitize_value("/Users/test") == "/Users/[USER]"
        
        # List
        result = self.collector._sanitize_value(["/Users/test", "john@example.com"])
        assert result == ["/Users/[USER]", "[EMAIL]"]
        
        # Dict
        result = self.collector._sanitize_value({"path": "/Users/test", "email": "john@example.com"})
        assert result == {"path": "/Users/[USER]", "email": "[EMAIL]"}
        
        # Other types (unchanged)
        assert self.collector._sanitize_value(42) == 42
        assert self.collector._sanitize_value(True) is True
    
    @patch('create_project.ai.context_collector.datetime')
    def test_collect_context_complete(self, mock_datetime):
        """Test complete context collection."""
        # Mock datetime
        mock_start = Mock()
        mock_start.isoformat.return_value = "2023-07-21T10:30:00"
        mock_datetime.now.return_value = mock_start
        
        # Mock time difference for duration
        mock_end = Mock()
        mock_datetime.now.side_effect = [mock_start, mock_end]
        mock_end.__sub__ = Mock(return_value=Mock())
        mock_end.__sub__.return_value.total_seconds.return_value = 0.15
        
        # Create test error
        error = TemplateError("Test error")
        project_variables = {"name": "test"}
        target_path = Path("/test/project")
        options = {"create_git": True}
        
        # Collect context
        context = self.collector.collect_context(
            error=error,
            template=self.mock_template,
            project_variables=project_variables,
            target_path=target_path,
            options=options
        )
        
        assert isinstance(context, CompleteErrorContext)
        assert context.timestamp == "2023-07-21T10:30:00"
        assert context.context_version == "1.0.0"
        assert context.collection_duration_ms == 150.0
        assert context.context_size_bytes > 0
        
        # Verify all components are present
        assert isinstance(context.system, SystemContext)
        assert isinstance(context.project, ProjectContext)
        assert isinstance(context.error, ErrorContext)
        assert isinstance(context.template, TemplateContext)
    
    @patch.object(ErrorContextCollector, '_collect_system_context')
    def test_collect_context_handles_errors(self, mock_system):
        """Test context collection handles errors gracefully."""
        mock_system.side_effect = Exception("System collection failed")
        
        error = TemplateError("Test error")
        
        with pytest.raises(ContextCollectionError) as exc_info:
            self.collector.collect_context(error)
        
        assert "Context collection failed" in str(exc_info.value)
        assert exc_info.value.details["original_error"] == "Test error"
    
    def test_collect_context_warns_on_large_context(self):
        """Test warning when context size exceeds target."""
        # Create a large error message to exceed size limit
        large_error = TemplateError("x" * 5000)  # Larger than 4KB target
        
        with patch.object(self.collector.logger, 'warning') as mock_warn:
            context = self.collector.collect_context(large_error)
            
            # Should warn about large context
            mock_warn.assert_called_once()
            call_args = mock_warn.call_args
            assert "Context size exceeds target" in str(call_args)
    
    def test_pii_patterns_comprehensive(self):
        """Test comprehensive PII pattern matching."""
        test_text = """
        User directory: /Users/johnsmith/projects/myapp
        Home: /home/alice/work/project
        Windows: C:\\Users\\bob\\Documents\\code
        Email: contact@example.com
        Another email: user.name+tag@domain.co.uk
        IP addresses: 192.168.1.1 and 10.0.0.1
        Temp files: /tmp/build_12345 and /tmp/cache_abcde
        """
        
        sanitized = self.collector._sanitize_text(test_text)
        
        # Check that all PII is sanitized
        assert "/Users/[USER]/" in sanitized
        assert "/home/[USER]/" in sanitized
        assert "C:\\Users\\[USER]\\" in sanitized
        assert "[EMAIL]" in sanitized
        assert "[IP_ADDRESS]" in sanitized
        assert "/tmp/[TEMP]" in sanitized
        
        # Verify original PII is removed
        assert "johnsmith" not in sanitized
        assert "alice" not in sanitized
        assert "bob" not in sanitized
        assert "contact@example.com" not in sanitized
        assert "192.168.1.1" not in sanitized
        assert "build_12345" not in sanitized
    
    def test_context_size_calculation(self):
        """Test context size calculation."""
        error = TemplateError("Small error")
        context = self.collector.collect_context(error)
        
        # Context size should be reasonable
        assert context.context_size_bytes > 100  # Should have some content
        assert context.context_size_bytes < 10000  # Should not be huge for simple error
    
    def test_collection_duration_measurement(self):
        """Test that collection duration is measured."""
        error = TemplateError("Test error")
        context = self.collector.collect_context(error)
        
        # Duration should be positive
        assert context.collection_duration_ms > 0
        assert context.collection_duration_ms < 10000  # Should be under 10 seconds