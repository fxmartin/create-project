# ABOUTME: Mock infrastructure for AI module testing
# ABOUTME: Provides realistic mocks for Ollama API and related components

"""Mock infrastructure for AI module testing."""

from .cache_mocks import MockCacheManager
from .context_mocks import MockCompleteErrorContext, MockContextCollector
from .ollama_mocks import (
    MockOllamaClient,
    MockOllamaDetector,
    MockOllamaResponse,
    OllamaMockScenario,
    create_mock_model_info,
    create_mock_ollama_status,
)

__all__ = [
    "MockOllamaClient",
    "MockOllamaDetector",
    "MockOllamaResponse",
    "OllamaMockScenario",
    "create_mock_model_info",
    "create_mock_ollama_status",
    "MockCacheManager",
    "MockCompleteErrorContext",
    "MockContextCollector",
]