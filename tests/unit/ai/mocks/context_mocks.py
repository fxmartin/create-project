# ABOUTME: Mock implementations for context collector testing
# ABOUTME: Simulates error context collection for various scenarios

"""Context collector mock implementations."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class MockCompleteErrorContext:
    """Mock CompleteErrorContext for testing."""
    error_info: Dict[str, Any]
    template_info: Optional[Dict[str, Any]] = None
    project_info: Optional[Dict[str, Any]] = None
    operation_info: Optional[Dict[str, Any]] = None
    environment_info: Optional[Dict[str, Any]] = None
    relevant_files: List[Dict[str, str]] = None
    context_size_bytes: int = 1024
    collection_duration_ms: float = 10.5
    
    def __post_init__(self):
        """Initialize defaults."""
        if self.relevant_files is None:
            self.relevant_files = []


class MockContextCollector:
    """Mock implementation of ErrorContextCollector."""
    
    def __init__(
        self,
        max_context_size: int = 4096,
        raise_on_collect: bool = False,
        predefined_context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize mock context collector."""
        self.max_context_size = max_context_size
        self.raise_on_collect = raise_on_collect
        self.predefined_context = predefined_context or {}
        
        # Tracking
        self.collect_count = 0
        self.last_error = None
        self.last_project_path = None
        self.collected_files = []
        
    def collect_error_context(
        self,
        error: Exception,
        project_path: Optional[Path] = None,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Mock collect_error_context method."""
        self.collect_count += 1
        self.last_error = error
        self.last_project_path = project_path
        
        if self.raise_on_collect:
            raise RuntimeError("Mock context collection error")
        
        if self.predefined_context:
            return self.predefined_context
        
        # Create mock context
        context = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "project_path": str(project_path) if project_path else None,
            "timestamp": "2024-01-01T12:00:00Z",
            "python_version": "3.9.0",
            "os": "darwin",
            "traceback": [
                {
                    "file": "test.py",
                    "line": 42,
                    "function": "test_function",
                    "code": "raise ValueError('test error')",
                }
            ],
        }
        
        if project_path:
            # Simulate collecting files
            self.collected_files = [
                "pyproject.toml",
                "src/__init__.py",
                "tests/test_main.py",
            ]
            context["relevant_files"] = {
                "pyproject.toml": '[tool.poetry]\nname = "test-project"',
                "src/__init__.py": "__version__ = '0.1.0'",
            }
        
        if additional_context:
            context["additional"] = additional_context
        
        return context
    
    def get_relevant_files(
        self,
        error: Exception,
        project_path: Path,
        max_files: int = 5,
    ) -> List[str]:
        """Mock get_relevant_files method."""
        if self.raise_on_collect:
            raise RuntimeError("Mock file collection error")
        
        # Return predefined files or generate based on error type
        if self.collected_files:
            return self.collected_files[:max_files]
        
        # Generate files based on error type
        if "import" in str(error).lower():
            return ["pyproject.toml", "requirements.txt", "setup.py"]
        elif "syntax" in str(error).lower():
            return ["main.py", "src/__init__.py"]
        else:
            return ["README.md", "pyproject.toml", "src/main.py"]
    
    def format_context_for_prompt(self, context: Dict[str, Any]) -> str:
        """Mock format_context_for_prompt method."""
        if self.raise_on_collect:
            raise RuntimeError("Mock formatting error")
        
        # Simple formatting
        lines = [
            f"Error: {context.get('error_type', 'Unknown')}",
            f"Message: {context.get('error_message', 'No message')}",
        ]
        
        if context.get("relevant_files"):
            lines.append("\nRelevant files:")
            for file, content in context["relevant_files"].items():
                lines.append(f"\n{file}:\n{content[:100]}...")
        
        return "\n".join(lines)
    
    def collect_context(
        self,
        error: Exception,
        template: Any = None,
        project_variables: Optional[Dict[str, Any]] = None,
        target_path: Optional[Path] = None,
        options: Optional[Dict[str, Any]] = None,
        attempted_operations: Optional[List[str]] = None,
        partial_results: Optional[Dict[str, Any]] = None,
    ) -> MockCompleteErrorContext:
        """Mock collect_context method matching the AI service interface."""
        self.collect_count += 1
        self.last_error = error
        self.last_project_path = target_path
        
        if self.raise_on_collect:
            raise RuntimeError("Mock context collection error")
        
        # Create mock error info
        error_info = {
            "type": type(error).__name__,
            "message": str(error),
            "traceback": ["mock traceback line 1", "mock traceback line 2"],
        }
        
        # Create mock template info if template provided
        template_info = None
        if template:
            template_info = {
                "name": getattr(template, 'name', 'mock_template'),
                "description": getattr(template, 'description', 'Mock template'),
            }
        
        # Create mock project info
        project_info = None
        if project_variables or target_path:
            project_info = {
                "variables": project_variables or {},
                "target_path": str(target_path) if target_path else None,
            }
        
        # Create mock operation info
        operation_info = None
        if attempted_operations or partial_results:
            operation_info = {
                "attempted": attempted_operations or [],
                "results": partial_results or {},
            }
        
        # Return mock context
        return MockCompleteErrorContext(
            error_info=error_info,
            template_info=template_info,
            project_info=project_info,
            operation_info=operation_info,
            environment_info={"python": "3.9.0", "os": "darwin"},
            relevant_files=[],
            context_size_bytes=len(str(error_info)),
            collection_duration_ms=5.0,
        )