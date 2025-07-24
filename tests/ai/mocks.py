# ABOUTME: Mock infrastructure for Ollama API testing with configurable behaviors
# ABOUTME: Provides realistic response mocks, network conditions, and edge case simulations

"""Mock infrastructure for testing Ollama AI integration.

This module provides comprehensive mocking utilities for testing the AI module
without requiring a real Ollama installation. It includes realistic API response
mocks, configurable behaviors, and network condition simulations.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

from httpx import ConnectError, ReadTimeout

from create_project.ai.ollama_client import OllamaResponse


class MockOllamaResponse:
    """Mock Ollama API response with configurable behavior."""

    def __init__(
        self,
        status_code: int = 200,
        json_data: Optional[Dict[str, Any]] = None,
        text: Optional[str] = None,
        raise_for_status: bool = False,
        headers: Optional[Dict[str, str]] = None,
    ):
        """Initialize mock response.

        Args:
            status_code: HTTP status code
            json_data: JSON response data
            text: Text response (if not JSON)
            raise_for_status: Whether to raise on bad status
            headers: Response headers
        """
        self.status_code = status_code
        self._json_data = json_data
        self.text = text or json.dumps(json_data or {})
        self._raise_for_status = raise_for_status
        self.headers = headers or {}

    def json(self) -> Dict[str, Any]:
        """Return JSON data."""
        if self._json_data is None:
            raise ValueError("No JSON data available")
        return self._json_data

    def raise_for_status(self) -> None:
        """Raise if status indicates error."""
        if self._raise_for_status or self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


class MockModelData:
    """Predefined model data for testing."""

    LLAMA_3_2 = {
        "name": "llama3.2:latest",
        "model": "llama3.2:latest",
        "modified_at": "2024-09-25T12:00:00Z",
        "size": "2022440019",
        "digest": "abc123",
        "details": "{\"parent_model\":\"\",\"format\":\"gguf\",\"family\":\"llama\",\"families\":[\"llama\"],\"parameter_size\":\"3.2B\",\"quantization_level\":\"Q4_K_M\"}",
    }

    CODELLAMA_7B = {
        "name": "codellama:7b",
        "model": "codellama:7b",
        "modified_at": "2024-08-15T10:30:00Z",
        "size": "3826793677",
        "digest": "def456",
        "details": "{\"parent_model\":\"\",\"format\":\"gguf\",\"family\":\"llama\",\"families\":[\"llama\"],\"parameter_size\":\"7B\",\"quantization_level\":\"Q4_0\"}",
    }

    MISTRAL_7B = {
        "name": "mistral:7b-instruct",
        "model": "mistral:7b-instruct",
        "modified_at": "2024-07-20T08:00:00Z",
        "size": "4113041887",
        "digest": "ghi789",
        "details": "{\"parent_model\":\"\",\"format\":\"gguf\",\"family\":\"mistral\",\"families\":[\"mistral\"],\"parameter_size\":\"7B\",\"quantization_level\":\"Q5_K_M\"}",
    }

    DEEPSEEK_CODER = {
        "name": "deepseek-coder:6.7b",
        "model": "deepseek-coder:6.7b",
        "modified_at": "2024-06-10T14:20:00Z",
        "size": "3600000000",
        "digest": "jkl012",
        "details": "{\"parent_model\":\"\",\"format\":\"gguf\",\"family\":\"deepseek\",\"families\":[\"deepseek\"],\"parameter_size\":\"6.7B\",\"quantization_level\":\"Q4_K_M\"}",
    }

    @classmethod
    def all_models(cls) -> List[Dict[str, Any]]:
        """Get all predefined models."""
        return [cls.LLAMA_3_2, cls.CODELLAMA_7B, cls.MISTRAL_7B, cls.DEEPSEEK_CODER]


class MockChatResponse:
    """Predefined chat completion responses."""

    ERROR_HELP = {
        "model": "llama3.2:latest",
        "created_at": "2024-11-17T12:00:00Z",
        "message": {
            "role": "assistant",
            "content": (
                "I see you're encountering a permission error. Here are some suggestions:\n\n"
                "1. **Check file permissions**: Use `ls -la` to verify permissions\n"
                "2. **Run with appropriate privileges**: You may need to use `sudo`\n"
                "3. **Verify ownership**: Ensure you own the target directory\n\n"
                "Try running: `chmod 755 /path/to/directory`"
            ),
        },
        "done": True,
        "total_duration": 1500000000,
        "eval_count": 95,
        "eval_duration": 950000000,
    }

    PROJECT_SUGGESTION = {
        "model": "codellama:7b",
        "created_at": "2024-11-17T12:05:00Z",
        "message": {
            "role": "assistant",
            "content": (
                "Based on your project structure, I recommend:\n\n"
                "1. **Add a README.md**: Document your project's purpose and setup\n"
                "2. **Include requirements.txt**: List all dependencies\n"
                "3. **Add .gitignore**: Exclude virtual environments and cache files\n"
                "4. **Create tests directory**: Set up pytest for testing\n\n"
                "Would you like me to help you create any of these files?"
            ),
        },
        "done": True,
        "total_duration": 2000000000,
        "eval_count": 120,
        "eval_duration": 1200000000,
    }

    EXPLANATION = {
        "model": "mistral:7b-instruct",
        "created_at": "2024-11-17T12:10:00Z",
        "message": {
            "role": "assistant",
            "content": (
                "This error occurs because Python cannot find the specified module. "
                "Common causes include:\n\n"
                "- The module is not installed in your environment\n"
                "- You're in the wrong virtual environment\n"
                "- There's a typo in the import statement\n"
                "- The PYTHONPATH is not configured correctly\n\n"
                "To fix this, try: `pip install <module-name>`"
            ),
        },
        "done": True,
        "total_duration": 1800000000,
        "eval_count": 110,
        "eval_duration": 1100000000,
    }

    STREAMING_CHUNKS = [
        {"message": {"content": "I'll "}, "done": False},
        {"message": {"content": "help you "}, "done": False},
        {"message": {"content": "with that "}, "done": False},
        {"message": {"content": "error."}, "done": False},
        {"message": {"content": ""}, "done": True, "total_duration": 500000000},
    ]


class MockNetworkConditions:
    """Simulate various network conditions."""

    @staticmethod
    def connection_error() -> ConnectError:
        """Simulate connection failure."""
        return ConnectError("Failed to connect to Ollama API")

    @staticmethod
    def timeout_error() -> ReadTimeout:
        """Simulate request timeout."""
        return ReadTimeout("Request timed out after 30 seconds")

    @staticmethod
    async def slow_response(delay: float = 2.0) -> None:
        """Simulate slow network response."""
        await asyncio.sleep(delay)

    @staticmethod
    def rate_limit_response() -> MockOllamaResponse:
        """Simulate rate limiting."""
        return MockOllamaResponse(
            status_code=429,
            json_data={"error": "Rate limit exceeded"},
            headers={"Retry-After": "60"},
        )

    @staticmethod
    def server_error() -> MockOllamaResponse:
        """Simulate server error."""
        return MockOllamaResponse(
            status_code=500, json_data={"error": "Internal server error"}
        )


class MockOllamaClient:
    """Configurable mock Ollama client for testing."""

    def __init__(
        self,
        available_models: Optional[List[Dict[str, Any]]] = None,
        default_response: Optional[Dict[str, Any]] = None,
        network_condition: Optional[str] = None,
        response_delay: float = 0.0,
    ):
        """Initialize mock client.

        Args:
            available_models: List of available models
            default_response: Default chat response
            network_condition: Simulate network issues
            response_delay: Delay before responding
        """
        self.available_models = available_models or MockModelData.all_models()
        self.default_response = default_response or MockChatResponse.ERROR_HELP
        self.network_condition = network_condition
        self.response_delay = response_delay
        self._request_count = 0
        self._last_request = None

    async def get(self, url: str, **kwargs) -> MockOllamaResponse:
        """Mock GET request."""
        self._request_count += 1
        self._last_request = {"method": "GET", "url": url, "kwargs": kwargs}

        if self.response_delay:
            await asyncio.sleep(self.response_delay)

        if self.network_condition == "connection_error":
            raise MockNetworkConditions.connection_error()
        elif self.network_condition == "timeout":
            raise MockNetworkConditions.timeout_error()
        elif self.network_condition == "rate_limit":
            return MockNetworkConditions.rate_limit_response()
        elif self.network_condition == "server_error":
            return MockNetworkConditions.server_error()

        # Handle specific endpoints
        if "/api/tags" in url:
            return MockOllamaResponse(json_data={"models": self.available_models})
        elif "/api/show" in url:
            model_name = kwargs.get("json", {}).get("name", "llama3.2:latest")
            model_data = next(
                (m for m in self.available_models if m["name"] == model_name),
                self.available_models[0],
            )
            return MockOllamaResponse(json_data=model_data)

        return MockOllamaResponse()

    async def post(self, url: str, **kwargs) -> MockOllamaResponse:
        """Mock POST request."""
        self._request_count += 1
        self._last_request = {"method": "POST", "url": url, "kwargs": kwargs}

        if self.response_delay:
            await asyncio.sleep(self.response_delay)

        if self.network_condition == "connection_error":
            raise MockNetworkConditions.connection_error()
        elif self.network_condition == "timeout":
            raise MockNetworkConditions.timeout_error()
        elif self.network_condition == "rate_limit":
            return MockNetworkConditions.rate_limit_response()
        elif self.network_condition == "server_error":
            return MockNetworkConditions.server_error()

        # Handle chat endpoint
        if "/api/chat" in url:
            return MockOllamaResponse(json_data=self.default_response)

        return MockOllamaResponse()

    def get_request_count(self) -> int:
        """Get number of requests made."""
        return self._request_count

    def get_last_request(self) -> Optional[Dict[str, Any]]:
        """Get details of last request."""
        return self._last_request

    def request(self, method: str, endpoint: str, data: Optional[Dict] = None, **kwargs) -> OllamaResponse:
        """Mock synchronous request."""
        self._request_count += 1
        self._last_request = {"method": method, "endpoint": endpoint, "data": data, "kwargs": kwargs}
        
        if self.network_condition == "connection_error":
            raise MockNetworkConditions.connection_error()
        elif self.network_condition == "timeout":
            raise MockNetworkConditions.timeout_error()
        
        # Handle specific endpoints
        if endpoint == "tags":
            return OllamaResponse(
                success=True,
                status_code=200,
                data={"models": self.available_models},
                response_time=0.1
            )
        elif endpoint == "chat":
            return OllamaResponse(
                success=True,
                status_code=200,
                data=self.default_response,
                response_time=0.2
            )
        
        return OllamaResponse(
            success=True,
            status_code=200,
            data={},
            response_time=0.1
        )

    def get_models(self) -> OllamaResponse:
        """Get available models (mock implementation)."""
        return self.request("GET", "tags")
    
    @property
    def is_available(self) -> bool:
        """Check if client is available."""
        return self.network_condition != "connection_error"
    
    def chat_completion(self, model: str, messages: list, stream: bool = False, **kwargs) -> OllamaResponse:
        """Mock chat completion."""
        return self.request("POST", "chat", data={"model": model, "messages": messages, "stream": stream, **kwargs})
    
    async def generate(self, model: str, prompt: str, stream: bool = False, **kwargs) -> OllamaResponse:
        """Mock generate completion - returns the default response."""
        if self.network_condition == "connection_error":
            raise httpx.ConnectError("Connection failed")
        elif self.network_condition == "timeout":
            raise httpx.TimeoutException("Request timed out", request=None)
        
        # Return the default response wrapped in OllamaResponse
        return OllamaResponse(
            success=True,
            status_code=200,
            data={"response": self.default_response["message"]["content"]},
            response_time=0.1
        )
    
    def close(self) -> None:
        """Mock close method."""
        pass


class MockCachePersistence:
    """Mock cache file operations for testing."""

    def __init__(self, initial_data: Optional[Dict[str, Any]] = None):
        """Initialize mock cache.

        Args:
            initial_data: Initial cache data
        """
        self.data = initial_data or {
            "version": 1,
            "entries": {},
            "metadata": {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_cleanup": datetime.now(timezone.utc).isoformat(),
            },
        }
        self.save_count = 0
        self.load_count = 0

    def save(self, data: Dict[str, Any]) -> None:
        """Mock save operation."""
        self.save_count += 1
        self.data = data

    def load(self) -> Dict[str, Any]:
        """Mock load operation."""
        self.load_count += 1
        return self.data

    def corrupt(self) -> None:
        """Simulate corrupted cache file."""
        self.data = {"invalid": "json"}

    def make_unreadable(self) -> None:
        """Simulate unreadable cache file."""
        self.data = None


def create_mock_ai_service(
    ollama_available: bool = True,
    model_count: int = 4,
    cache_enabled: bool = True,
    response_quality: str = "good",
) -> MagicMock:
    """Create a fully configured mock AI service.

    Args:
        ollama_available: Whether Ollama is available
        model_count: Number of available models
        cache_enabled: Whether caching is enabled
        response_quality: Quality of responses ("good", "poor", "empty")

    Returns:
        Configured mock AI service
    """
    mock_service = MagicMock()

    # Configure status
    mock_service.get_status.return_value = {
        "available": ollama_available,
        "ollama_version": "0.3.14" if ollama_available else None,
        "model_count": model_count if ollama_available else 0,
        "cache_enabled": cache_enabled,
        "last_check": datetime.now(timezone.utc).isoformat(),
    }

    # Configure response generation
    if response_quality == "good":
        response = MockChatResponse.ERROR_HELP["message"]["content"]
    elif response_quality == "poor":
        response = "Try again."
    else:
        response = ""

    mock_service.generate_help_response = AsyncMock(return_value=response)
    mock_service.generate_suggestions = AsyncMock(
        return_value=MockChatResponse.PROJECT_SUGGESTION["message"]["content"]
    )

    # Configure model listing
    if ollama_available:
        mock_service.list_models = AsyncMock(
            return_value=[m["name"] for m in MockModelData.all_models()[:model_count]]
        )
    else:
        mock_service.list_models = AsyncMock(
            side_effect=Exception("Ollama not available")
        )

    return mock_service


def create_streaming_response_mock() -> AsyncMock:
    """Create a mock that simulates streaming responses.

    Returns:
        AsyncMock that yields response chunks
    """

    async def stream_response(*args, **kwargs):
        """Simulate streaming response."""
        for chunk in MockChatResponse.STREAMING_CHUNKS:
            yield chunk
            if not chunk["done"]:
                await asyncio.sleep(0.1)  # Simulate network delay

    return AsyncMock(side_effect=stream_response)
