# ABOUTME: Tests for AI response generator covering prompt templating and quality validation
# ABOUTME: Includes async testing, mock responses, and streaming functionality validation

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass
from typing import List

from create_project.ai.response_generator import (
    ResponseGenerator,
    PromptType,
    GenerationConfig,
    ResponseQuality
)
from create_project.ai.ollama_client import OllamaResponse
from create_project.ai.model_manager import ModelInfo, ModelCapability
from create_project.ai.exceptions import AIError, ModelNotAvailableError, ResponseTimeoutError


class TestResponseGenerator:
    """Test suite for ResponseGenerator class."""
    
    @pytest.fixture
    def mock_client(self):
        """Mock Ollama client."""
        client = Mock()
        client.is_available = True
        client.chat_completion = AsyncMock()
        return client
    
    @pytest.fixture
    def mock_model_manager(self):
        """Mock model manager."""
        manager = Mock()
        manager.get_available_models = AsyncMock()
        return manager
    
    @pytest.fixture
    def sample_models(self):
        """Sample model data for testing."""
        from datetime import datetime
        
        return [
            ModelInfo(
                name="llama3.2:3b",
                size=2_000_000_000,
                digest="sha256:abc123",
                modified_at=datetime.now(),
                family="llama",
                parameter_size="3b",
                capabilities={ModelCapability.TEXT_GENERATION, ModelCapability.CHAT}
            ),
            ModelInfo(
                name="codellama:7b",
                size=4_000_000_000,
                digest="sha256:def456",
                modified_at=datetime.now(),
                family="codellama",
                parameter_size="7b",
                capabilities={ModelCapability.TEXT_GENERATION, ModelCapability.CODE_GENERATION}
            )
        ]
    
    @pytest.fixture
    def generator(self, mock_client, mock_model_manager):
        """ResponseGenerator instance with mocked dependencies."""
        return ResponseGenerator(
            ollama_client=mock_client,
            model_manager=mock_model_manager
        )
    
    def test_init_default_dependencies(self):
        """Test initialization with default dependencies."""
        with patch('create_project.ai.response_generator.OllamaClient') as mock_client_class, \
             patch('create_project.ai.response_generator.ModelManager') as mock_manager_class:
            
            mock_client = Mock()
            mock_manager = Mock()
            mock_client_class.return_value = mock_client
            mock_manager_class.return_value = mock_manager
            
            generator = ResponseGenerator()
            
            assert generator._client == mock_client
            assert generator._model_manager == mock_manager
            mock_client_class.assert_called_once()
            mock_manager_class.assert_called_once()
    
    def test_template_setup(self, generator):
        """Test that templates are properly set up."""
        assert generator._template_env is not None
        
        # Check that all default templates are loaded
        expected_templates = {"error_help", "suggestions", "explanation", "generic_help"}
        loaded_templates = set(generator._template_env.list_templates())
        assert expected_templates == loaded_templates
    
    def test_fallback_responses_loaded(self, generator):
        """Test that fallback responses are properly loaded."""
        assert len(generator._fallback_responses) == 4
        
        for prompt_type in PromptType:
            assert prompt_type in generator._fallback_responses
            assert len(generator._fallback_responses[prompt_type]) > 0
    
    def test_render_prompt_success(self, generator):
        """Test successful prompt template rendering."""
        context = {
            "error_message": "Template not found",
            "project_type": "FastAPI",
            "template_name": "api_template"
        }
        
        prompt = generator._render_prompt(PromptType.ERROR_HELP, context)
        
        assert "Template not found" in prompt
        assert "FastAPI" in prompt
        assert "api_template" in prompt
        assert "troubleshoot" in prompt.lower()
    
    def test_render_prompt_missing_context(self, generator):
        """Test prompt rendering with minimal context."""
        context = {"error_message": "Unknown error"}
        
        prompt = generator._render_prompt(PromptType.ERROR_HELP, context)
        
        assert "Unknown error" in prompt
        assert "Unknown" in prompt  # Default values should be used
    
    def test_render_prompt_failure_fallback(self, generator):
        """Test prompt rendering failure fallback."""
        # Use invalid template name to trigger error
        invalid_type = Mock()
        invalid_type.value = "nonexistent_template"
        
        context = {"request": "help with project"}
        
        prompt = generator._render_prompt(invalid_type, context)
        
        assert "help with project" in prompt
        assert "Please help with:" in prompt
    
    @pytest.mark.asyncio
    async def test_select_model_with_preference(self, generator, mock_model_manager, sample_models):
        """Test model selection with user preference."""
        mock_model_manager.get_available_models.return_value = sample_models
        
        model = await generator._select_model("llama3.2:3b")
        
        assert model == "llama3.2:3b"
    
    @pytest.mark.asyncio
    async def test_select_model_best_available(self, generator, mock_model_manager, sample_models):
        """Test model selection choosing best available."""
        mock_model_manager.get_available_models.return_value = sample_models
        
        model = await generator._select_model(None)
        
        # Should select codellama:7b (larger parameter size)
        assert model == "codellama:7b"
    
    @pytest.mark.asyncio
    async def test_select_model_no_suitable_models(self, generator, mock_model_manager):
        """Test model selection when no suitable models available."""
        from datetime import datetime
        
        models_without_text_gen = [
            ModelInfo(
                name="vision:1b",
                size=1_000_000_000,
                digest="sha256:vision123",
                modified_at=datetime.now(),
                family="vision",
                capabilities={ModelCapability.VISION}
            )
        ]
        mock_model_manager.get_available_models.return_value = models_without_text_gen
        
        with pytest.raises(ModelNotAvailableError):
            await generator._select_model(None)
    
    @pytest.mark.asyncio
    async def test_select_model_fallback_any_available(self, generator, mock_model_manager, sample_models):
        """Test model selection fallback to any available model."""
        # First call fails, second call returns models
        mock_model_manager.get_available_models.side_effect = [
            Exception("Model capability check failed"),
            sample_models
        ]
        
        model = await generator._select_model(None)
        
        assert model == sample_models[0].name
    
    def test_validate_response_quality_valid(self, generator):
        """Test response quality validation for valid responses."""
        quality = ResponseQuality(min_length=20, requires_actionable_advice=True)
        
        valid_response = "You should try checking your configuration file and ensure all dependencies are properly installed."
        
        assert generator._validate_response_quality(valid_response, quality) is True
    
    def test_validate_response_quality_too_short(self, generator):
        """Test response quality validation for too short responses."""
        quality = ResponseQuality(min_length=50)
        
        short_response = "Check config."
        
        assert generator._validate_response_quality(short_response, quality) is False
    
    def test_validate_response_quality_too_long(self, generator):
        """Test response quality validation for too long responses."""
        quality = ResponseQuality(max_length=100)
        
        long_response = "x" * 200
        
        assert generator._validate_response_quality(long_response, quality) is False
    
    def test_validate_response_quality_no_actionable_advice(self, generator):
        """Test response quality validation for responses without actionable advice."""
        quality = ResponseQuality(requires_actionable_advice=True)
        
        non_actionable = "This is a very long description of what the error means and the various ways this problem manifests itself in different circumstances."
        
        assert generator._validate_response_quality(non_actionable, quality) is False
    
    def test_validate_response_quality_no_sentence_structure(self, generator):
        """Test response quality validation for responses without proper structure."""
        quality = ResponseQuality()
        
        fragment_response = "error happened configuration wrong dependencies missing system problem"
        
        assert generator._validate_response_quality(fragment_response, quality) is False
    
    @pytest.mark.asyncio
    async def test_generate_single_success(self, generator, mock_client):
        """Test successful single response generation."""
        mock_response = OllamaResponse(
            success=True,
            status_code=200,
            data={"message": {"content": "Try updating your project template configuration."}}
        )
        mock_client.chat_completion.return_value = mock_response
        
        config = GenerationConfig(max_tokens=500, temperature=0.5)
        
        result = await generator._generate_single("test prompt", "llama3.2:3b", config)
        
        assert result == "Try updating your project template configuration."
        mock_client.chat_completion.assert_called_once_with(
            model="llama3.2:3b",
            messages=[{"role": "user", "content": "test prompt"}],
            max_tokens=500,
            temperature=0.5,
            timeout=30
        )
    
    @pytest.mark.asyncio
    async def test_generate_single_failure(self, generator, mock_client):
        """Test single response generation failure."""
        mock_response = OllamaResponse(
            success=False,
            status_code=404,
            data=None,
            error_message="Model not available"
        )
        mock_client.chat_completion.return_value = mock_response
        
        config = GenerationConfig()
        
        with pytest.raises(AIError, match="Response generation failed"):
            await generator._generate_single("test prompt", "llama3.2:3b", config)
    
    @pytest.mark.asyncio
    async def test_stream_generate(self, generator, mock_client):
        """Test streaming response generation."""
        mock_response = OllamaResponse(
            success=True,
            status_code=200,
            data={"message": {"content": "This is a test response for streaming."}}
        )
        mock_client.chat_completion.return_value = mock_response
        
        config = GenerationConfig()
        chunks = []
        
        async for chunk in generator._stream_generate("test prompt", "llama3.2:3b", config):
            chunks.append(chunk)
        
        full_response = "".join(chunks)
        assert full_response == "This is a test response for streaming."
        assert len(chunks) > 1  # Should be split into chunks
    
    def test_get_fallback_response_basic(self, generator):
        """Test getting basic fallback response."""
        context = {}
        
        response = generator._get_fallback_response(PromptType.SUGGESTIONS, context)
        
        assert len(response) > 0
        assert any(word in response.lower() for word in ["template", "project", "structure"])
    
    def test_get_fallback_response_error_context(self, generator):
        """Test fallback response selection based on error context."""
        context = {"error_message": "Permission denied"}
        
        response = generator._get_fallback_response(PromptType.ERROR_HELP, context)
        
        assert len(response) > 0
        # Should prefer diagnostic fallbacks for errors
        assert any(word in response.lower() for word in ["check", "verify"])
    
    @pytest.mark.asyncio
    async def test_generate_response_success(self, generator, mock_client, mock_model_manager, sample_models):
        """Test complete successful response generation."""
        # Setup mocks
        mock_model_manager.get_available_models.return_value = sample_models
        mock_response = OllamaResponse(
            success=True,
            status_code=200,
            data={"message": {"content": "You should check your template configuration and verify all dependencies are installed correctly."}}
        )
        mock_client.chat_completion.return_value = mock_response
        
        context = {
            "error_message": "Template not found",
            "project_type": "FastAPI"
        }
        
        result = await generator.generate_response(PromptType.ERROR_HELP, context)
        
        assert "check your template configuration" in result
        assert "verify all dependencies" in result
    
    @pytest.mark.asyncio
    async def test_generate_response_client_unavailable(self, generator, mock_client):
        """Test response generation when client is unavailable."""
        mock_client.is_available = False
        
        context = {"error_message": "Test error"}
        
        result = await generator.generate_response(PromptType.ERROR_HELP, context)
        
        # Should return fallback response
        assert len(result) > 0
        assert any(word in result.lower() for word in ["check", "try", "verify"])
    
    @pytest.mark.asyncio
    async def test_generate_response_quality_failure_fallback(self, generator, mock_client, mock_model_manager, sample_models):
        """Test fallback when AI response fails quality check."""
        # Setup mocks
        mock_model_manager.get_available_models.return_value = sample_models
        mock_response = OllamaResponse(
            success=True,
            status_code=200,
            data={"message": {"content": "Bad response."}}  # Too short, no actionable advice
        )
        mock_client.chat_completion.return_value = mock_response
        
        context = {"error_message": "Test error"}
        
        result = await generator.generate_response(PromptType.ERROR_HELP, context)
        
        # Should return fallback response due to quality failure
        assert len(result) > len("Bad response.")
        assert result != "Bad response."
    
    @pytest.mark.asyncio
    async def test_generate_response_with_retry(self, generator, mock_client, mock_model_manager, sample_models):
        """Test response generation with retry on failure."""
        # Setup mocks - first call fails, second succeeds
        mock_model_manager.get_available_models.return_value = sample_models
        mock_client.chat_completion.side_effect = [
            Exception("Temporary failure"),
            OllamaResponse(
                success=True,
                status_code=200,
                data={"message": {"content": "Try checking your configuration and ensure dependencies are properly installed."}}
            )
        ]
        
        context = {"error_message": "Test error"}
        config = GenerationConfig(retry_attempts=1)
        
        result = await generator.generate_response(PromptType.ERROR_HELP, context, config)
        
        assert "Try checking your configuration" in result
        assert mock_client.chat_completion.call_count == 2
    
    @pytest.mark.asyncio
    async def test_stream_response_success(self, generator, mock_client, mock_model_manager, sample_models):
        """Test streaming response generation."""
        # Setup mocks
        mock_model_manager.get_available_models.return_value = sample_models
        mock_response = OllamaResponse(
            success=True,
            status_code=200,
            data={"message": {"content": "This is a streaming response for testing purposes."}}
        )
        mock_client.chat_completion.return_value = mock_response
        
        context = {"request": "Help with project"}
        chunks = []
        
        async for chunk in generator.stream_response(PromptType.GENERIC_HELP, context):
            chunks.append(chunk)
        
        full_response = "".join(chunks)
        assert "This is a streaming response" in full_response
        assert len(chunks) > 1  # Should be streamed in chunks
    
    @pytest.mark.asyncio
    async def test_stream_response_client_unavailable(self, generator, mock_client):
        """Test streaming response when client is unavailable."""
        mock_client.is_available = False
        
        context = {"request": "Help needed"}
        chunks = []
        
        async for chunk in generator.stream_response(PromptType.GENERIC_HELP, context):
            chunks.append(chunk)
        
        full_response = "".join(chunks)
        assert len(full_response) > 0
        assert len(chunks) > 1  # Should be streamed even for fallback
    
    def test_get_supported_models_success(self, generator, mock_model_manager, sample_models):
        """Test getting list of supported models."""
        with patch('asyncio.run') as mock_run:
            mock_run.return_value = sample_models
            
            models = generator.get_supported_models()
            
            assert models == ["llama3.2:3b", "codellama:7b"]
    
    def test_get_supported_models_failure(self, generator, mock_model_manager):
        """Test getting supported models when operation fails."""
        with patch('asyncio.run', side_effect=Exception("Model fetch failed")):
            
            models = generator.get_supported_models()
            
            assert models == []
    
    def test_is_available(self, generator, mock_client):
        """Test availability check."""
        mock_client.is_available = True
        assert generator.is_available() is True
        
        mock_client.is_available = False
        assert generator.is_available() is False


class TestGenerationConfig:
    """Test suite for GenerationConfig dataclass."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = GenerationConfig()
        
        assert config.model_preference is None
        assert config.max_tokens == 1000
        assert config.temperature == 0.7
        assert config.stream_response is True
        assert config.timeout_seconds == 30
        assert config.retry_attempts == 2
        assert isinstance(config.quality_filter, ResponseQuality)
    
    def test_custom_values(self):
        """Test configuration with custom values."""
        quality = ResponseQuality(min_length=100, requires_actionable_advice=False)
        config = GenerationConfig(
            model_preference="llama3.2:3b",
            max_tokens=500,
            temperature=0.5,
            stream_response=False,
            timeout_seconds=60,
            retry_attempts=5,
            quality_filter=quality
        )
        
        assert config.model_preference == "llama3.2:3b"
        assert config.max_tokens == 500
        assert config.temperature == 0.5
        assert config.stream_response is False
        assert config.timeout_seconds == 60
        assert config.retry_attempts == 5
        assert config.quality_filter == quality


class TestResponseQuality:
    """Test suite for ResponseQuality dataclass."""
    
    def test_default_values(self):
        """Test default quality settings."""
        quality = ResponseQuality()
        
        assert quality.min_length == 50
        assert quality.max_length == 2000
        assert quality.min_coherence_score == 0.7
        assert quality.requires_actionable_advice is True
    
    def test_custom_values(self):
        """Test quality settings with custom values."""
        quality = ResponseQuality(
            min_length=100,
            max_length=500,
            min_coherence_score=0.8,
            requires_actionable_advice=False
        )
        
        assert quality.min_length == 100
        assert quality.max_length == 500
        assert quality.min_coherence_score == 0.8
        assert quality.requires_actionable_advice is False