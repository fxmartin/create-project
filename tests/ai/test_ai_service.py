# ABOUTME: Comprehensive test suite for AI Service Facade
# ABOUTME: Tests unified interface, graceful degradation, and integration with all AI components

"""
Test suite for AIService facade.

Tests the unified AI service interface including:
- Service initialization and configuration
- Ollama detection and availability checking
- Response generation with caching integration
- Error context collection integration
- Graceful degradation when services unavailable
- Streaming response capabilities
- Suggestion generation
- Resource cleanup and management
"""

import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any, List

import pytest

from create_project.ai.ai_service import (
    AIService,
    AIServiceConfig,
    AIServiceStatus
)
from create_project.ai.exceptions import (
    AIError,
    OllamaNotFoundError,
    ContextCollectionError
)
from create_project.ai.ollama_detector import OllamaStatus
from create_project.ai.model_manager import ModelInfo, ModelCapability
from create_project.ai.response_generator import GenerationConfig
from create_project.ai.context_collector import CompleteErrorContext, SystemContext, ProjectContext, ErrorContext, TemplateContext
from create_project.core.exceptions import TemplateError, PathError, ProjectGenerationError
from create_project.templates.schema.template import Template
from create_project.config.config_manager import ConfigManager


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
        assert len(config.preferred_models) == 5
        assert "codellama:13b" in config.preferred_models
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = AIServiceConfig(
            enabled=False,
            ollama_url="http://custom:8080",
            ollama_timeout=60,
            cache_enabled=False,
            preferred_models=["custom-model:7b"]
        )
        
        assert config.enabled is False
        assert config.ollama_url == "http://custom:8080"
        assert config.ollama_timeout == 60
        assert config.cache_enabled is False
        assert config.preferred_models == ["custom-model:7b"]


class TestAIServiceStatus:
    """Test AIServiceStatus dataclass."""
    
    def test_status_creation(self):
        """Test creating service status."""
        from datetime import datetime
        ollama_status = OllamaStatus(
            is_installed=True,
            is_running=True,
            version="0.1.0",
            binary_path=Path("/usr/local/bin/ollama"),
            service_url="http://localhost:11434",
            detected_at=datetime.now()
        )
        
        status = AIServiceStatus(
            service_available=True,
            ollama_available=True,
            models_loaded=5,
            cache_enabled=True,
            context_collection_enabled=True,
            ollama_status=ollama_status
        )
        
        assert status.service_available is True
        assert status.ollama_available is True
        assert status.models_loaded == 5
        assert status.cache_enabled is True
        assert status.context_collection_enabled is True
        assert status.ollama_status == ollama_status
        assert status.error_message is None


@pytest.mark.asyncio
class TestAIService:
    """Test AIService facade class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = AIServiceConfig()
        self.service = AIService(ai_config=self.config)
        
        # Mock templates
        self.mock_template = Mock(spec=Template)
        self.mock_template.name = "test_template"
        
        # Mock models
        from datetime import datetime
        self.mock_models = [
            ModelInfo(
                name="codellama:7b",
                size=3800000000,
                digest="sha256:test123",
                modified_at=datetime.fromisoformat("2023-07-21T10:00:00"),
                capabilities={ModelCapability.CODE_GENERATION},
                family="codellama",
                parameter_size="7B",
                quantization="Q4_0"
            ),
            ModelInfo(
                name="llama2:7b",
                size=3800000000,
                digest="sha256:test456",
                modified_at=datetime.fromisoformat("2023-07-21T10:00:00"),
                capabilities={ModelCapability.TEXT_GENERATION},
                family="llama",
                parameter_size="7B",
                quantization="Q4_0"
            )
        ]
    
    def test_initialization(self):
        """Test service initialization."""
        service = AIService()
        
        assert service.config.enabled is True
        assert service._initialized is False
        assert service._detector is None
        assert service._client is None
        assert service._model_manager is None
        assert service._response_generator is None
        assert service._cache_manager is None
        assert service._context_collector is None
    
    def test_initialization_with_config_manager(self):
        """Test service initialization with config manager."""
        config_manager = Mock(spec=ConfigManager)
        service = AIService(config_manager=config_manager)
        
        assert service.config_manager == config_manager
        assert service.config.enabled is True
    
    def test_initialization_with_custom_config(self):
        """Test service initialization with custom config."""
        custom_config = AIServiceConfig(
            enabled=False,
            ollama_url="http://test:8080"
        )
        service = AIService(ai_config=custom_config)
        
        assert service.config.enabled is False
        assert service.config.ollama_url == "http://test:8080"
    
    async def test_initialize_service_disabled(self):
        """Test initialization when service is disabled."""
        config = AIServiceConfig(enabled=False)
        service = AIService(ai_config=config)
        
        status = await service.initialize()
        
        assert status.service_available is False
        assert status.ollama_available is False
        assert status.models_loaded == 0
        assert status.error_message == "AI service disabled in configuration"
        assert service._initialized is True
    
    @patch('create_project.ai.ai_service.OllamaDetector')
    async def test_initialize_ollama_not_available(self, mock_detector_class):
        """Test initialization when Ollama is not available."""
        # Mock detector
        mock_detector = Mock()
        mock_detector_class.return_value = mock_detector
        
        from datetime import datetime
        mock_ollama_status = OllamaStatus(
            is_installed=False,
            is_running=False,
            version=None,
            binary_path=None,
            service_url="http://localhost:11434",
            detected_at=datetime.now(),
            error_message="Ollama not found"
        )
        mock_detector.detect.return_value = mock_ollama_status
        
        status = await self.service.initialize()
        
        assert status.service_available is False
        assert status.ollama_available is False
        assert status.models_loaded == 0
        assert "Ollama unavailable" in status.error_message
        assert status.ollama_status == mock_ollama_status
    
    @patch('create_project.ai.ai_service.OllamaDetector')
    @patch('create_project.ai.ai_service.OllamaClient')
    @patch('create_project.ai.ai_service.ModelManager')
    @patch('create_project.ai.ai_service.ResponseGenerator')
    @patch('create_project.ai.ai_service.ResponseCacheManager')
    @patch('create_project.ai.ai_service.ErrorContextCollector')
    async def test_initialize_success(
        self, mock_context_collector, mock_cache_manager, mock_response_gen,
        mock_model_manager, mock_client, mock_detector_class
    ):
        """Test successful initialization."""
        # Mock detector
        mock_detector = Mock()
        mock_detector_class.return_value = mock_detector
        
        from datetime import datetime
        mock_ollama_status = OllamaStatus(
            is_installed=True,
            is_running=True,
            version="0.1.0",
            binary_path=Path("/usr/local/bin/ollama"),
            service_url="http://localhost:11434",
            detected_at=datetime.now()
        )
        mock_detector.detect.return_value = mock_ollama_status
        
        # Mock client
        mock_client_instance = Mock()
        mock_client.get_instance.return_value = mock_client_instance
        
        # Mock model manager
        mock_model_mgr = Mock()
        mock_model_manager.return_value = mock_model_mgr
        mock_model_mgr.get_models.return_value = self.mock_models
        
        # Mock response generator
        mock_response_gen.return_value = Mock()
        
        # Mock cache manager
        mock_cache_mgr = AsyncMock()
        mock_cache_manager.return_value = mock_cache_mgr
        
        # Mock context collector
        mock_context_collector.return_value = Mock()
        
        status = await self.service.initialize()
        
        assert status.service_available is True
        assert status.ollama_available is True
        assert status.models_loaded == 2
        assert status.cache_enabled is True
        assert status.context_collection_enabled is True
        assert status.ollama_status == mock_ollama_status
        assert status.error_message is None
        
        # Verify components were created
        mock_detector_class.assert_called_once_with(service_url=self.config.ollama_url)
        mock_client.get_instance.assert_called_once()
        mock_model_manager.assert_called_once()
        mock_response_gen.assert_called_once()
        mock_cache_manager.assert_called_once()
        mock_context_collector.assert_called_once()
        
        # Verify cache was loaded
        mock_cache_mgr.load_cache.assert_called_once()
    
    @patch('create_project.ai.ai_service.OllamaDetector')
    async def test_initialize_exception_handling(self, mock_detector_class):
        """Test initialization exception handling."""
        mock_detector_class.side_effect = Exception("Initialization failed")
        
        status = await self.service.initialize()
        
        assert status.service_available is False
        assert status.ollama_available is False
        assert status.models_loaded == 0
        assert "Initialization failed" in status.error_message
    
    async def test_get_status_before_init(self):
        """Test get_status calls initialize if not done."""
        # Create a fresh service that hasn't been initialized
        fresh_service = AIService(ai_config=self.config)
        
        # Ensure the service is not initialized
        assert fresh_service._initialized is False
        
        mock_status = AIServiceStatus(
            service_available=True,
            ollama_available=True,
            models_loaded=2,
            cache_enabled=True,
            context_collection_enabled=True,
            ollama_status=None
        )
        
        async def mock_initialize():
            """Mock initialize that sets the service status."""
            fresh_service._service_status = mock_status
            fresh_service._initialized = True
            return mock_status
        
        with patch.object(fresh_service, 'initialize', side_effect=mock_initialize) as mock_init:
            status = await fresh_service.get_status()
            
            # Verify the mock was called and the status is returned
            mock_init.assert_called_once()
            assert status == mock_status
    
    async def test_get_status_after_init(self):
        """Test get_status after initialization."""
        # Mark as initialized
        self.service._initialized = True
        self.service._service_status = AIServiceStatus(
            service_available=True,
            ollama_available=True,
            models_loaded=2,
            cache_enabled=True,
            context_collection_enabled=True,
            ollama_status=None
        )
        
        with patch.object(self.service, 'initialize') as mock_init:
            status = await self.service.get_status()
            
            assert status.service_available is True
            mock_init.assert_not_called()  # Should not reinitialize
    
    async def test_is_available_true(self):
        """Test is_available when service is available."""
        with patch.object(self.service, 'get_status') as mock_get_status:
            mock_get_status.return_value = AIServiceStatus(
                service_available=True,
                ollama_available=True,
                models_loaded=2,
                cache_enabled=True,
                context_collection_enabled=True,
                ollama_status=None
            )
            
            available = await self.service.is_available()
            assert available is True
    
    async def test_is_available_false(self):
        """Test is_available when service is not available."""
        with patch.object(self.service, 'get_status') as mock_get_status:
            mock_get_status.return_value = AIServiceStatus(
                service_available=False,
                ollama_available=False,
                models_loaded=0,
                cache_enabled=False,
                context_collection_enabled=False,
                ollama_status=None,
                error_message="Service disabled"
            )
            
            available = await self.service.is_available()
            assert available is False
    
    async def test_get_available_models_service_unavailable(self):
        """Test get_available_models when service is unavailable."""
        with patch.object(self.service, 'is_available', return_value=False):
            with pytest.raises(OllamaNotFoundError, match="AI service not available"):
                await self.service.get_available_models()
    
    async def test_get_available_models_success(self):
        """Test successful get_available_models."""
        # Mock model manager
        mock_model_manager = Mock()
        mock_model_manager.get_models.return_value = self.mock_models
        self.service._model_manager = mock_model_manager
        
        with patch.object(self.service, 'is_available', return_value=True):
            models = await self.service.get_available_models()
            
            assert len(models) == 2
            assert models[0].name == "codellama:7b"
            assert models[1].name == "llama2:7b"
    
    async def test_generate_help_response_service_unavailable(self):
        """Test generate_help_response when service is unavailable."""
        error = TemplateError("Test template error")
        
        with patch.object(self.service, 'is_available', return_value=False):
            response = await self.service.generate_help_response(error, self.mock_template)
            
            assert "Template processing failed" in response
            assert "test_template" in response
            assert "TemplateError" in response
    
    async def test_generate_help_response_with_context_collection(self):
        """Test generate_help_response with context collection."""
        error = TemplateError("Test error")
        
        # Mock context collector
        mock_context_collector = Mock()
        mock_context = CompleteErrorContext(
            timestamp="2023-07-21T10:00:00",
            context_version="1.0.0",
            system=SystemContext("Linux", "5.4.0", "3.9.6", "x86_64", 100.0, "/home/user", {}),
            project=ProjectContext("test", "/home/user/test", {}, {}, [], {}),
            error=ErrorContext("TemplateError", "Test error", [], None, None, []),
            template=TemplateContext("test", "1.0.0", [], [], [], [], "valid"),
            context_size_bytes=1024,
            collection_duration_ms=50.0
        )
        mock_context_collector.collect_context.return_value = mock_context
        self.service._context_collector = mock_context_collector
        
        # Mock response generator
        mock_response_generator = AsyncMock()
        mock_response_generator.generate_response.return_value = "AI generated help response"
        self.service._response_generator = mock_response_generator
        
        # Mock cache manager
        mock_cache_manager = Mock()
        mock_cache_manager.generate_key.return_value = "cache_key"
        mock_cache_manager.get.return_value = None  # No cached response
        self.service._cache_manager = mock_cache_manager
        
        with patch.object(self.service, 'is_available', return_value=True):
            response = await self.service.generate_help_response(
                error,
                self.mock_template,
                {"var": "value"},
                Path("/test/path"),
                {"option": True},
                ["create_dir"],
                {"files": 1}
            )
            
            assert response == "AI generated help response"
            
            # Verify context collection was called
            mock_context_collector.collect_context.assert_called_once_with(
                error=error,
                template=self.mock_template,
                project_variables={"var": "value"},
                target_path=Path("/test/path"),
                options={"option": True},
                attempted_operations=["create_dir"],
                partial_results={"files": 1}
            )
            
            # Verify cache operations
            mock_cache_manager.generate_key.assert_called_once()
            mock_cache_manager.get.assert_called_once_with("cache_key")
            mock_cache_manager.put.assert_called_once_with("cache_key", "AI generated help response")
    
    async def test_generate_help_response_cached_response(self):
        """Test generate_help_response with cached response."""
        error = TemplateError("Test error")
        
        # Mock cache manager with cached response
        mock_cache_manager = Mock()
        mock_cache_manager.generate_key.return_value = "cache_key"
        mock_cache_manager.get.return_value = "Cached help response"
        self.service._cache_manager = mock_cache_manager
        
        with patch.object(self.service, 'is_available', return_value=True):
            response = await self.service.generate_help_response(error, self.mock_template)
            
            assert response == "Cached help response"
            mock_cache_manager.get.assert_called_once_with("cache_key")
    
    async def test_generate_help_response_context_collection_failure(self):
        """Test generate_help_response when context collection fails."""
        error = TemplateError("Test error")
        
        # Mock context collector that fails
        mock_context_collector = Mock()
        mock_context_collector.collect_context.side_effect = Exception("Context collection failed")
        self.service._context_collector = mock_context_collector
        
        # Mock response generator
        mock_response_generator = AsyncMock()
        mock_response_generator.generate_response.return_value = "AI response without context"
        self.service._response_generator = mock_response_generator
        
        with patch.object(self.service, 'is_available', return_value=True):
            response = await self.service.generate_help_response(error, self.mock_template)
            
            assert response == "AI response without context"
            # Should continue despite context collection failure
    
    async def test_generate_help_response_generation_failure(self):
        """Test generate_help_response when AI generation fails."""
        error = TemplateError("Test error")
        
        # Mock response generator that fails
        mock_response_generator = AsyncMock()
        mock_response_generator.generate_response.side_effect = Exception("Generation failed")
        self.service._response_generator = mock_response_generator
        
        with patch.object(self.service, 'is_available', return_value=True):
            response = await self.service.generate_help_response(error, self.mock_template)
            
            # Should fall back to static response
            assert "Template processing failed" in response
            assert "test_template" in response
    
    async def test_stream_help_response_service_unavailable(self):
        """Test stream_help_response when service is unavailable."""
        error = TemplateError("Test error")
        
        with patch.object(self.service, 'is_available', return_value=False):
            chunks = []
            async for chunk in self.service.stream_help_response(error, self.mock_template):
                chunks.append(chunk)
            
            full_response = "".join(chunks)
            assert "Template processing failed" in full_response
            assert "test_template" in full_response
    
    async def test_stream_help_response_success(self):
        """Test successful stream_help_response."""
        error = TemplateError("Test error")
        
        # Mock response generator with streaming
        mock_response_generator = AsyncMock()
        
        async def mock_stream_response(*args, **kwargs):
            for chunk in ["Streaming ", "AI ", "response"]:
                yield chunk
        
        mock_response_generator.stream_response = mock_stream_response
        self.service._response_generator = mock_response_generator
        
        # Mock cache manager
        mock_cache_manager = Mock()
        mock_cache_manager.generate_key.return_value = "cache_key"
        self.service._cache_manager = mock_cache_manager
        
        with patch.object(self.service, 'is_available', return_value=True):
            chunks = []
            async for chunk in self.service.stream_help_response(error, self.mock_template):
                chunks.append(chunk)
            
            assert chunks == ["Streaming ", "AI ", "response"]
            
            # Verify cache was updated with full response
            mock_cache_manager.put.assert_called_once_with("cache_key", "Streaming AI response")
    
    async def test_stream_help_response_generation_failure(self):
        """Test stream_help_response when generation fails."""
        error = TemplateError("Test error")
        
        # Mock response generator that fails
        mock_response_generator = AsyncMock()
        mock_response_generator.stream_response.side_effect = Exception("Streaming failed")
        self.service._response_generator = mock_response_generator
        
        with patch.object(self.service, 'is_available', return_value=True):
            chunks = []
            async for chunk in self.service.stream_help_response(error, self.mock_template):
                chunks.append(chunk)
            
            full_response = "".join(chunks)
            assert "Template processing failed" in full_response
    
    async def test_get_suggestions_service_unavailable(self):
        """Test get_suggestions when service is unavailable."""
        context = {"project_type": "web_app"}
        
        with patch.object(self.service, 'is_available', return_value=False):
            suggestions = await self.service.get_suggestions(context, "general")
            
            assert len(suggestions) == 5
            assert "Ensure all required dependencies are installed" in suggestions
    
    async def test_get_suggestions_success(self):
        """Test successful get_suggestions."""
        context = {"project_type": "web_app"}
        
        # Mock response generator
        mock_response_generator = AsyncMock()
        mock_response_generator.generate_response.return_value = """
- Use Flask or Django for web framework
- Set up virtual environment
- Configure database connection
- Implement user authentication
- Add error handling
"""
        self.service._response_generator = mock_response_generator
        
        with patch.object(self.service, 'is_available', return_value=True):
            suggestions = await self.service.get_suggestions(context, "template")
            
            assert len(suggestions) == 5
            assert "Use Flask or Django for web framework" in suggestions
            assert "Set up virtual environment" in suggestions
    
    async def test_get_suggestions_generation_failure(self):
        """Test get_suggestions when generation fails."""
        context = {"project_type": "web_app"}
        
        # Mock response generator that fails
        mock_response_generator = AsyncMock()
        mock_response_generator.generate_response.side_effect = Exception("Generation failed")
        self.service._response_generator = mock_response_generator
        
        with patch.object(self.service, 'is_available', return_value=True):
            suggestions = await self.service.get_suggestions(context, "template")
            
            # Should fall back to static suggestions
            assert len(suggestions) == 5
            assert "Check template syntax for Jinja2 errors" in suggestions
    
    async def test_cleanup(self):
        """Test service cleanup."""
        # Mock cache manager
        mock_cache_manager = AsyncMock()
        self.service._cache_manager = mock_cache_manager
        
        # Mock client
        mock_client = Mock()
        self.service._client = mock_client
        
        await self.service.cleanup()
        
        # Verify cleanup operations
        mock_cache_manager.persist_cache.assert_called_once()
        mock_client.close_clients.assert_called_once()
    
    async def test_cleanup_with_exception(self):
        """Test cleanup when operations fail."""
        # Mock cache manager that fails
        mock_cache_manager = AsyncMock()
        mock_cache_manager.persist_cache.side_effect = Exception("Persist failed")
        self.service._cache_manager = mock_cache_manager
        
        # Should not raise exception
        await self.service.cleanup()
    
    def test_get_fallback_help_response(self):
        """Test fallback help response generation."""
        error = TemplateError("Variable missing")
        
        response = self.service._get_fallback_help_response(error, self.mock_template)
        
        assert "Template processing failed" in response
        assert "test_template" in response
        assert "TemplateError" in response
        assert "Variable missing" in response
        assert "Troubleshooting Steps" in response
    
    def test_get_fallback_help_response_unknown_error(self):
        """Test fallback help response for unknown error type."""
        error = ValueError("Unknown error")
        
        response = self.service._get_fallback_help_response(error, self.mock_template)
        
        assert "An error occurred during project generation" in response
        assert "ValueError" in response
        assert "Unknown error" in response
    
    def test_get_fallback_suggestions_general(self):
        """Test fallback suggestions for general type."""
        context = {"test": "value"}
        
        suggestions = self.service._get_fallback_suggestions(context, "general")
        
        assert len(suggestions) == 5
        assert "Ensure all required dependencies are installed" in suggestions
        assert "Verify template configuration is correct" in suggestions
    
    def test_get_fallback_suggestions_template(self):
        """Test fallback suggestions for template type."""
        context = {"test": "value"}
        
        suggestions = self.service._get_fallback_suggestions(context, "template")
        
        assert len(suggestions) == 5
        assert "Check template syntax for Jinja2 errors" in suggestions
        assert "Verify all required variables are defined" in suggestions
    
    def test_get_fallback_suggestions_unknown_type(self):
        """Test fallback suggestions for unknown type."""
        context = {"test": "value"}
        
        suggestions = self.service._get_fallback_suggestions(context, "unknown")
        
        # Should default to general suggestions
        assert len(suggestions) == 5
        assert "Ensure all required dependencies are installed" in suggestions
    
    async def test_async_context_manager(self):
        """Test async context manager functionality."""
        with patch.object(self.service, 'initialize') as mock_init, \
             patch.object(self.service, 'cleanup') as mock_cleanup:
            
            mock_init.return_value = AIServiceStatus(
                service_available=True,
                ollama_available=True,
                models_loaded=2,
                cache_enabled=True,
                context_collection_enabled=True,
                ollama_status=None
            )
            
            async with self.service as service:
                assert service == self.service
                mock_init.assert_called_once()
            
            mock_cleanup.assert_called_once()