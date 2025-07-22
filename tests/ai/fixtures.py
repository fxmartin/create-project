# ABOUTME: Additional test fixtures for AI module testing
# ABOUTME: Provides complex fixtures and test data generators for comprehensive testing

"""Additional fixtures and test data generators for AI module tests.

This module provides more complex fixtures and data generators that complement
the basic fixtures in conftest.py.
"""

import random
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple

from create_project.ai.exceptions import (
    AIError,
    CacheError,
    ModelNotAvailableError,
    OllamaNotFoundError,
    ResponseTimeoutError,
)
from create_project.ai.types import PromptType


class TestDataGenerator:
    """Generate test data for various AI module scenarios."""

    @staticmethod
    def generate_error_context(
        error_type: str = "generic",
        include_traceback: bool = True,
        include_system_info: bool = True,
    ) -> Dict[str, Any]:
        """Generate error context for testing.

        Args:
            error_type: Type of error to simulate
            include_traceback: Whether to include traceback
            include_system_info: Whether to include system info

        Returns:
            Error context dictionary
        """
        context = {
            "error_type": error_type,
            "error_message": f"Test {error_type} error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if include_traceback:
            context["traceback"] = [
                {
                    "file": f"/path/to/file{i}.py",
                    "line": 100 + i,
                    "function": f"function_{i}",
                    "code": f"raise {error_type}Error('Test error')",
                }
                for i in range(3)
            ]

        if include_system_info:
            context["system_info"] = {
                "platform": "darwin",
                "python_version": "3.9.6",
                "cpu_count": 8,
                "memory_available": 8589934592,
                "disk_free": 107374182400,
            }

        return context

    @staticmethod
    def generate_project_context(
        template: str = "basic", has_errors: bool = False
    ) -> Dict[str, Any]:
        """Generate project generation context.

        Args:
            template: Template name
            has_errors: Whether to include errors

        Returns:
            Project context dictionary
        """
        context = {
            "template": template,
            "project_name": f"test_project_{random.randint(1000, 9999)}",
            "target_dir": f"/tmp/projects/test_{random.randint(1000, 9999)}",
            "options": {"git_init": True, "create_venv": True, "install_deps": True},
        }

        if has_errors:
            context["validation_errors"] = [
                {"field": "project_name", "error": "Invalid characters"},
                {"field": "target_dir", "error": "Directory already exists"},
            ]

        return context

    @staticmethod
    def generate_cache_entries(
        count: int = 10, expired_ratio: float = 0.2
    ) -> List[Dict[str, Any]]:
        """Generate cache entries for testing.

        Args:
            count: Number of entries to generate
            expired_ratio: Ratio of expired entries

        Returns:
            List of cache entries
        """
        entries = []
        now = datetime.now(timezone.utc)

        for i in range(count):
            is_expired = i < int(count * expired_ratio)
            timestamp = now - timedelta(hours=25 if is_expired else 1)

            entry = {
                "key": "".join(
                    random.choices(string.ascii_lowercase + string.digits, k=12)
                ),
                "prompt": f"Test prompt {i}",
                "response": f"Test response {i} with some helpful content",
                "model": random.choice(
                    ["llama3.2:latest", "codellama:7b", "mistral:7b"]
                ),
                "timestamp": timestamp.isoformat(),
                "ttl": 86400,
                "access_count": random.randint(0, 10),
                "last_accessed": timestamp.isoformat(),
            }
            entries.append(entry)

        return entries

    @staticmethod
    def generate_ollama_response(
        prompt_type: PromptType, quality: str = "good", model: str = "llama3.2:latest"
    ) -> Dict[str, Any]:
        """Generate Ollama API response for testing.

        Args:
            prompt_type: Type of prompt
            quality: Response quality (good, poor, empty)
            model: Model name

        Returns:
            Ollama API response
        """
        if quality == "empty":
            content = ""
        elif quality == "poor":
            content = "Try again."
        else:
            # Generate quality response based on prompt type
            if prompt_type == PromptType.ERROR_HELP:
                content = (
                    "I can help you resolve this error. Based on the context provided:\n\n"
                    "1. First, check your file permissions\n"
                    "2. Ensure all dependencies are installed\n"
                    "3. Verify your Python environment is activated\n\n"
                    "Here's a specific solution for your issue..."
                )
            elif prompt_type == PromptType.PROJECT_SUGGESTION:
                content = (
                    "Here are some suggestions for your project:\n\n"
                    "- Add comprehensive documentation\n"
                    "- Set up continuous integration\n"
                    "- Include unit tests for critical functionality\n"
                    "- Consider using type hints throughout"
                )
            elif prompt_type == PromptType.EXPLANATION:
                content = (
                    "Let me explain this concept:\n\n"
                    "This error typically occurs when the system cannot find "
                    "the required resources. The underlying cause is often "
                    "related to configuration or environment setup issues."
                )
            else:
                content = "Here's some general assistance for your query."

        return {
            "model": model,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "message": {"role": "assistant", "content": content},
            "done": True,
            "total_duration": random.randint(1000000000, 3000000000),
            "eval_count": len(content.split()),
            "eval_duration": random.randint(500000000, 1500000000),
        }

    @staticmethod
    def generate_model_list(
        count: int = 5, include_details: bool = True
    ) -> List[Dict[str, Any]]:
        """Generate list of Ollama models.

        Args:
            count: Number of models to generate
            include_details: Whether to include detailed info

        Returns:
            List of model information
        """
        families = ["llama", "mistral", "codellama", "deepseek", "phi", "qwen"]
        sizes = ["3.2B", "7B", "13B", "70B"]
        quantizations = ["Q4_0", "Q4_K_M", "Q5_K_M", "Q8_0"]

        models = []
        for i in range(count):
            family = random.choice(families)
            size = random.choice(sizes)
            quant = random.choice(quantizations)

            model = {
                "name": f"{family}:{size.lower()}-{quant.lower()}",
                "model": f"{family}:{size.lower()}-{quant.lower()}",
                "modified_at": (
                    datetime.now(timezone.utc) - timedelta(days=random.randint(1, 30))
                ).isoformat(),
                "size": random.randint(2000000000, 8000000000),
                "digest": "".join(random.choices(string.hexdigits.lower(), k=12)),
            }

            if include_details:
                model["details"] = {
                    "parent_model": "",
                    "format": "gguf",
                    "family": family,
                    "families": [family],
                    "parameter_size": size,
                    "quantization_level": quant,
                }

            models.append(model)

        return models


class ErrorScenarios:
    """Collection of error scenarios for testing."""

    @staticmethod
    def get_network_errors() -> List[Tuple[str, Exception]]:
        """Get network-related error scenarios.

        Returns:
            List of (description, exception) tuples
        """
        return [
            ("Connection refused", ConnectionRefusedError("Connection refused")),
            ("Timeout", TimeoutError("Request timed out")),
            ("DNS resolution failed", OSError("Name or service not known")),
            ("Connection reset", ConnectionResetError("Connection reset by peer")),
            ("SSL error", Exception("SSL: CERTIFICATE_VERIFY_FAILED")),
        ]

    @staticmethod
    def get_ai_module_errors() -> List[Tuple[str, Exception]]:
        """Get AI module-specific errors.

        Returns:
            List of (description, exception) tuples
        """
        return [
            ("Ollama not found", OllamaNotFoundError("Ollama is not installed")),
            (
                "Model unavailable",
                ModelNotAvailableError("llama3.2:latest", "Model not found"),
            ),
            (
                "Response timeout",
                ResponseTimeoutError("Response generation timed out", 30),
            ),
            ("Cache error", CacheError("Failed to load cache", FileNotFoundError())),
            ("Generic AI error", AIError("AI service initialization failed")),
        ]

    @staticmethod
    def get_validation_errors() -> List[Dict[str, Any]]:
        """Get validation error scenarios.

        Returns:
            List of validation error dictionaries
        """
        return [
            {
                "field": "prompt",
                "error": "Prompt exceeds maximum length",
                "value": "x" * 10000,
            },
            {
                "field": "model",
                "error": "Invalid model name",
                "value": "invalid-model-name",
            },
            {
                "field": "temperature",
                "error": "Temperature must be between 0 and 2",
                "value": 3.5,
            },
            {
                "field": "context_length",
                "error": "Context length exceeds model limit",
                "value": 200000,
            },
        ]


class MockResponseStreamer:
    """Simulate streaming responses for testing."""

    def __init__(self, chunks: List[str], delay: float = 0.1):
        """Initialize streamer.

        Args:
            chunks: List of response chunks
            delay: Delay between chunks in seconds
        """
        self.chunks = chunks
        self.delay = delay
        self._index = 0

    async def __aiter__(self):
        """Async iteration over chunks."""
        import asyncio

        for chunk in self.chunks:
            await asyncio.sleep(self.delay)
            yield {"message": {"content": chunk}, "done": chunk == self.chunks[-1]}

    def reset(self):
        """Reset streamer to beginning."""
        self._index = 0


def create_test_prompt_context(
    prompt_type: PromptType,
    include_error: bool = True,
    include_project: bool = True,
    include_system: bool = True,
) -> Dict[str, Any]:
    """Create a complete prompt context for testing.

    Args:
        prompt_type: Type of prompt to generate context for
        include_error: Include error context
        include_project: Include project context
        include_system: Include system context

    Returns:
        Complete context dictionary
    """
    context = {"prompt_type": prompt_type.value}

    if include_error:
        context["error_context"] = TestDataGenerator.generate_error_context()

    if include_project:
        context["project_context"] = TestDataGenerator.generate_project_context()

    if include_system:
        context["system_context"] = {
            "platform": "darwin",
            "python_version": "3.9.6",
            "app_version": "1.0.0",
            "ollama_version": "0.3.14",
        }

    return context


def assert_streaming_response_valid(chunks: List[Dict[str, Any]]) -> None:
    """Assert that streaming response chunks are valid.

    Args:
        chunks: List of response chunks
    """
    assert len(chunks) > 0, "No chunks received"

    # All chunks except last should have done=False
    for chunk in chunks[:-1]:
        assert chunk.get("done") is False
        assert "message" in chunk
        assert "content" in chunk["message"]

    # Last chunk should have done=True
    last_chunk = chunks[-1]
    assert last_chunk.get("done") is True

    # Concatenated content should form coherent response
    full_content = "".join(
        chunk["message"]["content"]
        for chunk in chunks
        if chunk.get("message", {}).get("content")
    )
    assert len(full_content) > 0
