# ABOUTME: Pytest fixtures and configuration for AI module tests
# ABOUTME: Provides shared test fixtures, mock factories, and test utilities

"""Pytest configuration and fixtures for AI module tests.

This module provides shared fixtures and utilities for testing the AI module,
including mock clients, sample data, and test helpers.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_mock import MockerFixture

from create_project.ai.types import PromptType
from tests.ai.mocks import (
    MockCachePersistence,
    MockChatResponse,
    MockModelData,
    MockOllamaClient,
    create_mock_ai_service,
    create_streaming_response_mock
)


# Test data directory
TEST_DATA_DIR = Path(__file__).parent / "test_data"


@pytest.fixture
def test_data_dir() -> Path:
    """Get test data directory path."""
    return TEST_DATA_DIR


@pytest.fixture
def sample_responses() -> Dict[str, Any]:
    """Load sample response data."""
    with open(TEST_DATA_DIR / "sample_responses.json") as f:
        return json.load(f)


@pytest.fixture
def sample_cache_data() -> Dict[str, Any]:
    """Load sample cache data."""
    with open(TEST_DATA_DIR / "sample_cache.json") as f:
        return json.load(f)


@pytest.fixture
def model_configs() -> Dict[str, Any]:
    """Load model configuration data."""
    with open(TEST_DATA_DIR / "model_configs.json") as f:
        return json.load(f)


@pytest.fixture
def mock_ollama_client() -> MockOllamaClient:
    """Create a default mock Ollama client."""
    return MockOllamaClient()


@pytest.fixture
def mock_ollama_unavailable() -> MockOllamaClient:
    """Create a mock client simulating Ollama unavailable."""
    return MockOllamaClient(
        available_models=[],
        network_condition="connection_error"
    )


@pytest.fixture
def mock_slow_ollama() -> MockOllamaClient:
    """Create a mock client with slow responses."""
    return MockOllamaClient(response_delay=2.0)


@pytest.fixture
def mock_rate_limited_ollama() -> MockOllamaClient:
    """Create a mock client with rate limiting."""
    return MockOllamaClient(network_condition="rate_limit")


@pytest.fixture
def mock_cache_persistence() -> MockCachePersistence:
    """Create a mock cache persistence handler."""
    return MockCachePersistence()


@pytest.fixture
def mock_corrupted_cache() -> MockCachePersistence:
    """Create a mock cache with corrupted data."""
    cache = MockCachePersistence()
    cache.corrupt()
    return cache


@pytest.fixture
def mock_ai_service() -> MagicMock:
    """Create a default mock AI service."""
    return create_mock_ai_service()


@pytest.fixture
def mock_ai_service_unavailable() -> MagicMock:
    """Create a mock AI service with Ollama unavailable."""
    return create_mock_ai_service(ollama_available=False)


@pytest.fixture
def mock_streaming_client() -> AsyncMock:
    """Create a mock client with streaming responses."""
    return create_streaming_response_mock()


@pytest.fixture
def mock_env_vars(mocker: MockerFixture) -> Dict[str, str]:
    """Mock environment variables for testing."""
    env_vars = {
        "APP_AI_ENABLED": "true",
        "APP_AI_OLLAMA_HOST": "http://test.local",
        "APP_AI_OLLAMA_PORT": "11435",
        "APP_AI_CACHE_MAX_SIZE": "200",
        "APP_AI_CACHE_TTL_SECONDS": "43200"
    }
    mocker.patch.dict(os.environ, env_vars)
    return env_vars


@pytest.fixture
def mock_httpx_client(mocker: MockerFixture) -> MagicMock:
    """Mock httpx AsyncClient."""
    mock_client = MagicMock()
    mock_client.get = AsyncMock()
    mock_client.post = AsyncMock()
    mock_client.aclose = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    
    mocker.patch("httpx.AsyncClient", return_value=mock_client)
    return mock_client


@pytest.fixture
def isolated_cache_dir(tmp_path: Path) -> Path:
    """Create an isolated cache directory for testing."""
    cache_dir = tmp_path / "ai_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


@pytest.fixture
def mock_subprocess_run(mocker: MockerFixture) -> MagicMock:
    """Mock subprocess.run for Ollama detection."""
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = "ollama version 0.3.14\n"
    return mock_run


@pytest.fixture
def mock_datetime_now(mocker: MockerFixture) -> MagicMock:
    """Mock datetime.now for consistent timestamps."""
    from datetime import datetime, timezone
    
    fixed_time = datetime(2024, 11, 17, 12, 0, 0, tzinfo=timezone.utc)
    mock_now = mocker.patch("datetime.datetime")
    mock_now.now.return_value = fixed_time
    mock_now.utcnow.return_value = fixed_time
    return mock_now


# Test helper functions
def assert_valid_response(response: str, min_length: int = 50) -> None:
    """Assert that an AI response is valid.
    
    Args:
        response: The response to validate
        min_length: Minimum acceptable length
    """
    assert response is not None
    assert isinstance(response, str)
    assert len(response) >= min_length
    assert not response.isspace()
    assert not all(c in "```\n " for c in response)


def assert_cache_entry_valid(entry: Dict[str, Any]) -> None:
    """Assert that a cache entry has valid structure.
    
    Args:
        entry: Cache entry to validate
    """
    required_fields = ["key", "prompt", "response", "model", "timestamp", "ttl"]
    for field in required_fields:
        assert field in entry, f"Missing required field: {field}"
    
    assert isinstance(entry["key"], str)
    assert isinstance(entry["prompt"], str)
    assert isinstance(entry["response"], str)
    assert isinstance(entry["model"], str)
    assert isinstance(entry["ttl"], (int, float))


def assert_model_info_valid(model: Dict[str, Any]) -> None:
    """Assert that model info has valid structure.
    
    Args:
        model: Model information to validate
    """
    required_fields = ["name", "model", "size", "modified_at"]
    for field in required_fields:
        assert field in model, f"Missing required field: {field}"
    
    assert isinstance(model["name"], str)
    assert isinstance(model["size"], int)
    assert model["size"] > 0


# Parametrized test data
ERROR_SCENARIOS = [
    ("permission_denied", "Permission denied", PromptType.ERROR_HELP),
    ("module_not_found", "ModuleNotFoundError", PromptType.ERROR_HELP),
    ("git_not_initialized", "fatal: not a git repository", PromptType.ERROR_HELP),
    ("file_not_found", "FileNotFoundError", PromptType.ERROR_HELP),
    ("syntax_error", "SyntaxError: invalid syntax", PromptType.ERROR_HELP)
]


NETWORK_CONDITIONS = [
    ("normal", None, 200),
    ("slow", "slow_network", 200),
    ("connection_error", "connection_error", None),
    ("timeout", "timeout", None),
    ("rate_limit", "rate_limit", 429),
    ("server_error", "server_error", 500)
]


MODEL_CAPABILITIES = [
    ("general", ["llama3.2:latest", "mistral:7b-instruct"]),
    ("code", ["codellama:7b", "deepseek-coder:6.7b"]),
    ("chat", ["llama3.2:latest", "mistral:7b-instruct"]),
    ("technical", ["codellama:7b", "deepseek-coder:6.7b"])
]


# Pytest markers
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "requires_ollama: marks tests that require Ollama to be installed"
    )