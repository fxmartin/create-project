# ABOUTME: Comprehensive unit tests for AIService facade
# ABOUTME: Tests initialization, status checking, response generation, caching, and error handling

"""Unit tests for AIService facade."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from create_project.ai.ai_service import AIService, AIServiceConfig, AIServiceStatus
from create_project.ai.exceptions import (
    AIError,
    ModelNotAvailableError,
    OllamaNotFoundError,
    ResponseTimeoutError,
)
from create_project.ai.types import PromptType
from create_project.templates.schema.template import Template

from tests.unit.ai.mocks import (
    MockCacheManager,
    MockContextCollector,
    MockOllamaClient,
    MockOllamaDetector,
    OllamaMockScenario,
    create_mock_model_info,
)


class TestAIServiceConfig:
    """Test AIServiceConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = AIServiceConfig()
        
        assert config.enabled is True
        assert config.ollama_url == "http://localhost:11434"
        assert config.ollama_timeout == 30
        assert config.cache_enabled is True
        assert config.cache_ttl_hours == 24
        assert config.max_cache_entries == 100
        assert config.context_collection_enabled is True
        assert config.max_context_size_kb == 4
        assert len(config.preferred_models) > 0
        assert "codellama:13b" in config.preferred_models
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = AIServiceConfig(
            enabled=False,
            ollama_url="http://custom:11434",
            cache_enabled=False,
            preferred_models=["custom-model"],
        )
        
        assert config.enabled is False
        assert config.ollama_url == "http://custom:11434"
        assert config.cache_enabled is False
        assert config.preferred_models == ["custom-model"]


class TestAIServiceStatus:
    """Test AIServiceStatus dataclass."""
    
    def test_status_creation(self):
        """Test status object creation."""
        status = AIServiceStatus(
            service_available=True,
            ollama_available=True,
            models_loaded=3,
            cache_enabled=True,
            context_collection_enabled=True,
            ollama_status=None,
            error_message=None,
        )
        
        assert status.service_available is True
        assert status.ollama_available is True
        assert status.models_loaded == 3
        assert status.error_message is None


class TestAIService:
    """Test AIService facade."""
    
    @pytest.fixture
    def ai_config(self):
        """Create test AI configuration."""
        return AIServiceConfig(
            enabled=True,
            cache_enabled=True,
            context_collection_enabled=True,
        )
    
    @pytest.fixture
    def mock_detector(self):
        """Create mock Ollama detector."""
        return MockOllamaDetector(
            is_installed=True,
            is_running=True,
            is_serving=True,
        )
    
    @pytest.fixture
    def mock_client(self):
        """Create mock Ollama client."""
        return MockOllamaClient(scenario=OllamaMockScenario.SUCCESS)
    
    @pytest.fixture
    def mock_cache(self):
        """Create mock cache manager."""
        return MockCacheManager(cache_enabled=True)
    
    @pytest.fixture
    def mock_context_collector(self):
        """Create mock context collector."""
        return MockContextCollector()
    
    def test_initialization(self, ai_config):
        """Test AI service initialization."""
        service = AIService(ai_config=ai_config)
        
        assert service.config == ai_config
        assert service._initialized is False
        assert service._detector is None
        assert service._client is None
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, ai_config, mock_detector, mock_client):
        """Test successful initialization."""
        service = AIService(ai_config=ai_config)
        
        with patch("create_project.ai.ai_service.OllamaDetector", return_value=mock_detector):
            with patch("create_project.ai.ai_service.OllamaClient", return_value=mock_client):
                with patch("create_project.ai.ai_service.ModelManager") as MockModelManager:
                    mock_manager = MockModelManager.return_value
                    mock_manager.get_models.return_value = [
                        create_mock_model_info("codellama:13b"),
                        create_mock_model_info("llama2:7b"),
                    ]
                    
                    status = await service.initialize()
        
        assert status.service_available is True
        assert status.ollama_available is True
        assert status.models_loaded == 2
        assert status.cache_enabled is True
        assert service._initialized is True
    
    @pytest.mark.asyncio
    async def test_initialize_disabled(self):
        """Test initialization when service is disabled."""
        config = AIServiceConfig(enabled=False)
        service = AIService(ai_config=config)
        
        status = await service.initialize()
        
        assert status.service_available is False
        assert status.error_message == "AI service disabled in configuration"
        assert service._initialized is True
    
    @pytest.mark.asyncio
    async def test_initialize_ollama_not_found(self, ai_config):
        """Test initialization when Ollama is not found."""
        service = AIService(ai_config=ai_config)
        
        mock_detector = MockOllamaDetector(
            is_installed=False,
            is_running=False,
            error_message="Ollama not installed",
        )
        
        with patch("create_project.ai.ai_service.OllamaDetector", return_value=mock_detector):
            status = await service.initialize()
        
        assert status.service_available is False
        assert status.ollama_available is False
        assert "Ollama unavailable" in status.error_message
        assert service._initialized is True
    
    @pytest.mark.asyncio
    async def test_initialize_already_initialized(self, ai_config, mock_detector, mock_client):
        """Test initialization when already initialized."""
        service = AIService(ai_config=ai_config)
        
        # First initialization
        with patch("create_project.ai.ai_service.OllamaDetector", return_value=mock_detector):
            with patch("create_project.ai.ai_service.OllamaClient", return_value=mock_client):
                with patch("create_project.ai.ai_service.ModelManager") as MockModelManager:
                    mock_manager = MockModelManager.return_value
                    mock_manager.get_models.return_value = []
                    
                    status1 = await service.initialize()
        
        # Second initialization should return same status
        status2 = await service.initialize()
        assert status1 == status2
    
    @pytest.mark.asyncio
    async def test_get_status(self, ai_config, mock_detector, mock_client):
        """Test getting service status."""
        with patch("create_project.ai.ai_service.OllamaDetector", return_value=mock_detector):
            with patch("create_project.ai.ai_service.OllamaClient", return_value=mock_client):
                with patch("create_project.ai.ai_service.ModelManager") as MockModelManager:
                    mock_manager = MockModelManager.return_value
                    mock_manager.get_models.return_value = []
                    
                    service = AIService(ai_config=ai_config)
                    
                    # Status before initialization - will trigger initialization
                    status = await service.get_status()
                    assert status.service_available is True  # Should be available with mocks
                    
                    # Status after should be the same
                    status2 = await service.get_status()
                    assert status2.service_available is True
                    assert service._initialized is True
    
    @pytest.mark.asyncio
    async def test_is_available(self, ai_config, mock_detector, mock_client):
        """Test checking if service is available."""
        with patch("create_project.ai.ai_service.OllamaDetector", return_value=mock_detector):
            with patch("create_project.ai.ai_service.OllamaClient", return_value=mock_client):
                with patch("create_project.ai.ai_service.ModelManager") as MockModelManager:
                    mock_manager = MockModelManager.return_value
                    mock_manager.get_models.return_value = []
                    
                    service = AIService(ai_config=ai_config)
                    
                    # is_available() will trigger initialization with mocks
                    available = await service.is_available()
                    assert available is True
                    
                    # Check again to ensure consistency
                    assert await service.is_available() is True
    
    @pytest.mark.asyncio
    async def test_get_available_models_not_initialized(self, ai_config):
        """Test getting models when not initialized."""
        service = AIService(ai_config=ai_config)
        
        with pytest.raises(OllamaNotFoundError):
            await service.get_available_models()
    
    @pytest.mark.asyncio
    async def test_get_available_models_initialized(self, ai_config, mock_detector, mock_client):
        """Test getting available models."""
        service = AIService(ai_config=ai_config)
        
        expected_models = [
            create_mock_model_info("codellama:13b"),
            create_mock_model_info("llama2:7b"),
        ]
        
        with patch("create_project.ai.ai_service.OllamaDetector", return_value=mock_detector):
            with patch("create_project.ai.ai_service.OllamaClient", return_value=mock_client):
                with patch("create_project.ai.ai_service.ModelManager") as MockModelManager:
                    mock_manager = MockModelManager.return_value
                    mock_manager.get_models.return_value = expected_models
                    
                    await service.initialize()
                    service._model_manager = mock_manager
        
        models = await service.get_available_models()
        assert len(models) == 2
        assert models == expected_models
    
    @pytest.mark.asyncio
    async def test_generate_help_response_not_available(self, ai_config):
        """Test generating help response when service not available."""
        service = AIService(ai_config=ai_config)
        
        error = ValueError("Test error")
        response = await service.generate_help_response(error=error)
        
        # Should return fallback help
        assert response is not None
        assert isinstance(response, str)
    
    @pytest.mark.asyncio
    async def test_generate_help_response_with_cache_hit(self, ai_config, mock_detector, mock_client):
        """Test generating help response with cache hit."""
        service = AIService(ai_config=ai_config)
        
        # Initialize with mocks
        with patch("create_project.ai.ai_service.OllamaDetector", return_value=mock_detector):
            with patch("create_project.ai.ai_service.OllamaClient", return_value=mock_client):
                with patch("create_project.ai.ai_service.ModelManager") as MockModelManager:
                    mock_manager = MockModelManager.return_value
                    mock_manager.get_models.return_value = []
                    
                    # Initialize cache manager
                    mock_cache = MockCacheManager()
                    cached_response = "Cached help response"
                    
                    with patch("create_project.ai.ai_service.ResponseCacheManager", return_value=mock_cache):
                        await service.initialize()
                        service._cache_manager = mock_cache
        
        # Mock cache methods
        with patch.object(service._cache_manager, "generate_key", return_value="test_key"):
            with patch.object(service._cache_manager, "get", return_value=cached_response):
                error = ValueError("Test error")
                response = await service.generate_help_response(error=error)
        
        assert response == cached_response
    
    @pytest.mark.asyncio
    async def test_generate_help_response_with_cache_miss(self, ai_config, mock_detector, mock_client):
        """Test generating help response with cache miss."""
        service = AIService(ai_config=ai_config)
        
        # Initialize with mocks
        with patch("create_project.ai.ai_service.OllamaDetector", return_value=mock_detector):
            with patch("create_project.ai.ai_service.OllamaClient", return_value=mock_client):
                with patch("create_project.ai.ai_service.ModelManager") as MockModelManager:
                    with patch("create_project.ai.ai_service.ResponseGenerator") as MockGenerator:
                        mock_manager = MockModelManager.return_value
                        mock_manager.get_models.return_value = []
                        
                        mock_generator = MockGenerator.return_value
                        expected_response = "Generated help response"
                        mock_generator.generate_response = AsyncMock(return_value=expected_response)
                        
                        mock_cache = MockCacheManager(always_miss=True)
                        
                        with patch("create_project.ai.ai_service.ResponseCacheManager", return_value=mock_cache):
                            await service.initialize()
                            service._cache_manager = mock_cache
                            service._response_generator = mock_generator
        
        # Mock cache methods
        with patch.object(service._cache_manager, "generate_key", return_value="test_key"):
            with patch.object(service._cache_manager, "get", return_value=None):
                with patch.object(service._cache_manager, "put") as mock_put:
                    error = ValueError("Test error")
                    response = await service.generate_help_response(error=error)
        
        assert response == expected_response
        assert mock_put.called
    
    @pytest.mark.asyncio
    async def test_generate_help_response_with_error_context(self, ai_config, mock_detector, mock_client):
        """Test generating help response with error context."""
        service = AIService(ai_config=ai_config)
        
        # Initialize with mocks
        with patch("create_project.ai.ai_service.OllamaDetector", return_value=mock_detector):
            with patch("create_project.ai.ai_service.OllamaClient", return_value=mock_client):
                with patch("create_project.ai.ai_service.ModelManager") as MockModelManager:
                    with patch("create_project.ai.ai_service.ResponseGenerator") as MockGenerator:
                        mock_manager = MockModelManager.return_value
                        mock_manager.get_models.return_value = []
                        
                        mock_generator = MockGenerator.return_value
                        expected_response = "Generated help response with context"
                        mock_generator.generate_response = AsyncMock(return_value=expected_response)
                        
                        mock_context = MockContextCollector()
                        
                        with patch("create_project.ai.ai_service.ErrorContextCollector", return_value=mock_context):
                            await service.initialize()
                            service._context_collector = mock_context
                            service._response_generator = mock_generator
        
        error = ValueError("Test error")
        response = await service.generate_help_response(
            error=error,
            target_path=Path("/test/project"),
        )
        
        assert response == expected_response
        assert mock_context.collect_count == 1
        assert mock_context.last_error == error
    
    @pytest.mark.asyncio
    async def test_generate_help_response_with_template_context(self, ai_config, mock_detector, mock_client):
        """Test generating help response with template context."""
        service = AIService(ai_config=ai_config)
        
        # Initialize with mocks
        with patch("create_project.ai.ai_service.OllamaDetector", return_value=mock_detector):
            with patch("create_project.ai.ai_service.OllamaClient", return_value=mock_client):
                with patch("create_project.ai.ai_service.ModelManager") as MockModelManager:
                    with patch("create_project.ai.ai_service.ResponseGenerator") as MockGenerator:
                        mock_manager = MockModelManager.return_value
                        mock_manager.get_models.return_value = []
                        
                        mock_generator = MockGenerator.return_value
                        expected_response = "Template help response"
                        mock_generator.generate_response = AsyncMock(return_value=expected_response)
                        
                        await service.initialize()
                        service._response_generator = mock_generator
        
        # Create mock template
        template = MagicMock(spec=Template)
        template.name = "Test Template"  # Changed from template.metadata.name
        template.description = "Test description"
        
        error = ValueError("Template processing error")
        response = await service.generate_help_response(
            error=error,
            template=template,
        )
        
        assert response == expected_response
    
    @pytest.mark.asyncio
    async def test_generate_help_response_error_handling(self, ai_config, mock_detector, mock_client):
        """Test error handling in generate_help_response."""
        service = AIService(ai_config=ai_config)
        
        # Initialize with mocks
        with patch("create_project.ai.ai_service.OllamaDetector", return_value=mock_detector):
            with patch("create_project.ai.ai_service.OllamaClient", return_value=mock_client):
                with patch("create_project.ai.ai_service.ModelManager") as MockModelManager:
                    with patch("create_project.ai.ai_service.ResponseGenerator") as MockGenerator:
                        mock_manager = MockModelManager.return_value
                        mock_manager.get_models.return_value = []
                        
                        mock_generator = MockGenerator.return_value
                        mock_generator.generate_response = AsyncMock(
                            side_effect=AIError("Connection failed")
                        )
                        
                        await service.initialize()
                        service._response_generator = mock_generator
        
        error = ValueError("Test error")
        response = await service.generate_help_response(error=error)
        
        # Should return fallback help when AI fails
        assert response is not None
        assert isinstance(response, str)
        assert "Test error" in response
    
    @pytest.mark.asyncio
    async def test_stream_help_response(self, ai_config, mock_detector, mock_client):
        """Test streaming help response generation."""
        service = AIService(ai_config=ai_config)
        
        # Initialize with mocks
        with patch("create_project.ai.ai_service.OllamaDetector", return_value=mock_detector):
            with patch("create_project.ai.ai_service.OllamaClient", return_value=mock_client):
                with patch("create_project.ai.ai_service.ModelManager") as MockModelManager:
                    with patch("create_project.ai.ai_service.ResponseGenerator") as MockGenerator:
                        mock_manager = MockModelManager.return_value
                        mock_manager.get_models.return_value = []
                        
                        mock_generator = MockGenerator.return_value
                        
                        async def mock_stream(*args, **kwargs):
                            chunks = ["chunk1 ", "chunk2 ", "chunk3"]
                            for chunk in chunks:
                                yield chunk
                        
                        mock_generator.stream_response = mock_stream
                        
                        await service.initialize()
                        service._response_generator = mock_generator
        
        chunks = []
        error = ValueError("Test error")
        async for chunk in service.stream_help_response(error=error):
            chunks.append(chunk)
        
        assert len(chunks) == 3
        assert chunks[0] == "chunk1 "
    
    @pytest.mark.asyncio
    async def test_get_suggestions(self, ai_config, mock_detector, mock_client):
        """Test getting AI suggestions."""
        service = AIService(ai_config=ai_config)
        
        # Initialize with mocks
        with patch("create_project.ai.ai_service.OllamaDetector", return_value=mock_detector):
            with patch("create_project.ai.ai_service.OllamaClient", return_value=mock_client):
                with patch("create_project.ai.ai_service.ModelManager") as MockModelManager:
                    with patch("create_project.ai.ai_service.ResponseGenerator") as MockGenerator:
                        mock_manager = MockModelManager.return_value
                        mock_manager.get_models.return_value = []
                        
                        mock_generator = MockGenerator.return_value
                        mock_response = "- Use absolute paths\n- Check permissions\n- Verify dependencies"
                        mock_generator.generate_response = AsyncMock(return_value=mock_response)
                        
                        await service.initialize()
                        service._response_generator = mock_generator
        
        suggestions = await service.get_suggestions(
            context={"error": "Path not found"},
            suggestion_type="path",
        )
        
        assert isinstance(suggestions, list)
        assert len(suggestions) == 3
        assert suggestions[0] == "Use absolute paths"
    
    @pytest.mark.asyncio
    async def test_get_suggestions_fallback(self, ai_config):
        """Test getting fallback suggestions when AI unavailable."""
        service = AIService(ai_config=ai_config)
        
        suggestions = await service.get_suggestions(
            context={"error": "Template error"},
            suggestion_type="template",
        )
        
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        assert any("template" in s.lower() for s in suggestions)
    
    @pytest.mark.asyncio
    async def test_cleanup(self, ai_config, mock_detector, mock_client):
        """Test service cleanup."""
        service = AIService(ai_config=ai_config)
        
        # Initialize
        with patch("create_project.ai.ai_service.OllamaDetector", return_value=mock_detector):
            with patch("create_project.ai.ai_service.OllamaClient", return_value=mock_client):
                with patch("create_project.ai.ai_service.ModelManager") as MockModelManager:
                    mock_manager = MockModelManager.return_value
                    mock_manager.get_models.return_value = []
                    
                    # Add mock cache manager
                    mock_cache = MockCacheManager()
                    with patch("create_project.ai.ai_service.ResponseCacheManager", return_value=mock_cache):
                        await service.initialize()
                        service._cache_manager = mock_cache
        
        # Mock client close method
        service._client.close = MagicMock()
        
        # Cleanup
        await service.cleanup()
        
        assert service._client.close.called
        assert mock_cache.persist_count == 1
    
    @pytest.mark.asyncio
    async def test_context_manager(self, ai_config, mock_detector, mock_client):
        """Test async context manager functionality."""
        # Use mocks for the entire context
        with patch("create_project.ai.ai_service.OllamaDetector", return_value=mock_detector):
            with patch("create_project.ai.ai_service.OllamaClient", return_value=mock_client):
                with patch("create_project.ai.ai_service.ModelManager") as MockModelManager:
                    mock_manager = MockModelManager.return_value
                    mock_manager.get_models.return_value = []
                    
                    async with AIService(ai_config=ai_config) as service:
                        # Should be initialized
                        assert service._initialized is True
                        assert await service.is_available() is True
                    
                    # After exit, cleanup should have been called
                    # (We can't easily test this without more mocking)