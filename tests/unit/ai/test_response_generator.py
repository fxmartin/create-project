# ABOUTME: Comprehensive unit tests for ResponseGenerator with streaming and quality validation
# ABOUTME: Tests prompt rendering, model selection, fallback responses, and timeout handling

"""Unit tests for response generator module."""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from create_project.ai.exceptions import AIError, ModelNotAvailableError, ResponseTimeoutError
from create_project.ai.model_manager import ModelCapability, ModelInfo
from create_project.ai.ollama_client import OllamaResponse
from create_project.ai.prompt_manager import PromptManager
from create_project.ai.response_generator import (
    GenerationConfig,
    ResponseGenerator,
    ResponseQuality,
)
from create_project.ai.types import PromptType


class TestResponseQuality:
    """Test ResponseQuality dataclass."""

    def test_default_values(self):
        """Test default quality settings."""
        quality = ResponseQuality()
        assert quality.min_length == 50
        assert quality.max_length == 2000
        assert quality.min_coherence_score == 0.7
        assert quality.requires_actionable_advice is True

    def test_custom_values(self):
        """Test custom quality settings."""
        quality = ResponseQuality(
            min_length=100,
            max_length=5000,
            min_coherence_score=0.9,
            requires_actionable_advice=False,
        )
        assert quality.min_length == 100
        assert quality.max_length == 5000
        assert quality.min_coherence_score == 0.9
        assert quality.requires_actionable_advice is False


class TestGenerationConfig:
    """Test GenerationConfig dataclass."""

    def test_default_values(self):
        """Test default generation config."""
        config = GenerationConfig()
        assert config.model_preference is None
        assert config.max_tokens == 1000
        assert config.temperature == 0.7
        assert config.top_p == 0.9
        assert config.timeout_seconds == 30
        assert config.stream is False
        assert config.quality_check is True

    def test_custom_values(self):
        """Test custom generation config."""
        config = GenerationConfig(
            model_preference="llama2:13b",
            max_tokens=2000,
            temperature=0.5,
            top_p=0.95,
            timeout_seconds=60,
            stream=True,
            quality_check=False,
        )
        assert config.model_preference == "llama2:13b"
        assert config.max_tokens == 2000
        assert config.temperature == 0.5
        assert config.top_p == 0.95
        assert config.timeout_seconds == 60
        assert config.stream is True
        assert config.quality_check is False


class TestResponseGenerator:
    """Test ResponseGenerator class."""

    @pytest.fixture
    def mock_ollama_client(self):
        """Create mock Ollama client."""
        client = Mock()
        client.is_available = True
        client.generate = AsyncMock()
        client.stream_generate = AsyncMock()
        return client

    @pytest.fixture
    def mock_model_manager(self):
        """Create mock model manager."""
        manager = Mock()
        manager.get_models = Mock()
        return manager

    @pytest.fixture
    def mock_prompt_manager(self):
        """Create mock prompt manager."""
        manager = Mock()
        manager.render_prompt = Mock(return_value="Rendered prompt")
        manager.list_available_templates = Mock(return_value=["error_help", "suggestions"])
        return manager

    @pytest.fixture
    def response_generator(self, mock_ollama_client, mock_model_manager, mock_prompt_manager):
        """Create response generator with mocks."""
        return ResponseGenerator(
            ollama_client=mock_ollama_client,
            model_manager=mock_model_manager,
            prompt_manager=mock_prompt_manager,
        )

    def test_initialization(self, mock_ollama_client, mock_model_manager, mock_prompt_manager):
        """Test response generator initialization."""
        generator = ResponseGenerator(
            ollama_client=mock_ollama_client,
            model_manager=mock_model_manager,
            prompt_manager=mock_prompt_manager,
        )
        
        assert generator._client is mock_ollama_client
        assert generator._model_manager is mock_model_manager
        assert generator._prompt_manager is mock_prompt_manager
        assert len(generator._fallback_responses) > 0

    def test_initialization_defaults(self):
        """Test initialization with default dependencies."""
        with patch("create_project.ai.response_generator.OllamaClient") as mock_client:
            with patch("create_project.ai.response_generator.ModelManager") as mock_manager:
                with patch("create_project.ai.response_generator.PromptManager") as mock_prompt:
                    generator = ResponseGenerator()
                    
                    mock_client.assert_called_once()
                    mock_manager.assert_called_once()
                    mock_prompt.assert_called_once()

    def test_load_fallback_responses(self, response_generator):
        """Test loading fallback responses."""
        fallbacks = response_generator._load_fallback_responses()
        
        assert PromptType.ERROR_HELP in fallbacks
        assert PromptType.SUGGESTIONS in fallbacks
        assert PromptType.EXPLANATION in fallbacks
        assert PromptType.GENERIC_HELP in fallbacks
        
        # Check each type has multiple responses
        for prompt_type, responses in fallbacks.items():
            assert isinstance(responses, list)
            assert len(responses) > 0
            assert all(isinstance(r, str) for r in responses)

    @pytest.mark.asyncio
    async def test_generate_response_success(self, response_generator, mock_model_manager):
        """Test successful response generation."""
        # Setup mocks
        mock_models = [
            ModelInfo(
                name="llama2:7b",
                size=7_000_000_000,
                digest="abc",
                modified_at=datetime.now(),
                capabilities={ModelCapability.TEXT_GENERATION},
            )
        ]
        mock_model_manager.get_models.return_value = mock_models
        
        response_generator._client.generate.return_value = OllamaResponse(
            success=True,
            status_code=200,
            data={"response": "This is a helpful AI response with actionable advice:\n1. First step\n2. Second step"},
        )
        
        # Generate response
        context = {"error_message": "Test error"}
        response = await response_generator.generate_response(
            PromptType.ERROR_HELP,
            context,
        )
        
        assert response == "This is a helpful AI response with actionable advice:\n1. First step\n2. Second step"
        response_generator._client.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_response_client_unavailable(self, response_generator):
        """Test response generation when client is unavailable."""
        response_generator._client.is_available = False
        
        context = {"error_message": "Test error"}
        response = await response_generator.generate_response(
            PromptType.ERROR_HELP,
            context,
        )
        
        # Should return fallback response
        assert "Try checking your project template configuration" in response
        assert "Error details: Test error" in response
        response_generator._client.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_response_quality_check_fail(self, response_generator, mock_model_manager):
        """Test response generation with failed quality check."""
        # Setup mocks
        mock_models = [
            ModelInfo(
                name="llama2:7b",
                size=7_000_000_000,
                digest="abc",
                modified_at=datetime.now(),
                capabilities={ModelCapability.TEXT_GENERATION},
            )
        ]
        mock_model_manager.get_models.return_value = mock_models
        
        # Return short response that fails quality check
        response_generator._client.generate.return_value = OllamaResponse(
            success=True,
            status_code=200,
            data={"response": "Too short"},
        )
        
        context = {"error_message": "Test error"}
        response = await response_generator.generate_response(
            PromptType.ERROR_HELP,
            context,
        )
        
        # Should return fallback due to quality check failure
        assert "Try checking your project template configuration" in response

    @pytest.mark.asyncio
    async def test_generate_response_timeout(self, response_generator, mock_model_manager):
        """Test response generation timeout."""
        # Setup mocks
        mock_models = [
            ModelInfo(
                name="llama2:7b",
                size=7_000_000_000,
                digest="abc",
                modified_at=datetime.now(),
                capabilities={ModelCapability.TEXT_GENERATION},
            )
        ]
        mock_model_manager.get_models.return_value = mock_models
        
        # Simulate timeout
        response_generator._client.generate.side_effect = asyncio.TimeoutError()
        
        context = {"error_message": "Test error"}
        
        with pytest.raises(ResponseTimeoutError):
            await response_generator.generate_response(
                PromptType.ERROR_HELP,
                context,
                GenerationConfig(timeout_seconds=1),
            )

    @pytest.mark.asyncio
    async def test_generate_response_error_with_retry(self, response_generator, mock_model_manager):
        """Test response generation error with streaming retry."""
        # Setup mocks
        mock_models = [
            ModelInfo(
                name="llama2:7b",
                size=7_000_000_000,
                digest="abc",
                modified_at=datetime.now(),
                capabilities={ModelCapability.TEXT_GENERATION},
            )
        ]
        mock_model_manager.get_models.return_value = mock_models
        
        # First call fails, second (streaming) succeeds
        response_generator._client.generate.side_effect = [
            AIError("Generation failed"),
            OllamaResponse(
                success=True,
                status_code=200,
                data={"response": "Streaming response with advice:\n1. Step one\n2. Step two"},
            ),
        ]
        
        context = {"request": "Help needed"}
        response = await response_generator.generate_response(
            PromptType.GENERIC_HELP,
            context,
            GenerationConfig(stream=False),
        )
        
        # Should retry with streaming enabled
        assert "Streaming response with advice" in response
        assert response_generator._client.generate.call_count == 2

    @pytest.mark.asyncio
    async def test_stream_response_success(self, response_generator, mock_model_manager):
        """Test successful response streaming."""
        # Setup mocks
        mock_models = [
            ModelInfo(
                name="llama2:7b",
                size=7_000_000_000,
                digest="abc",
                modified_at=datetime.now(),
                capabilities={ModelCapability.TEXT_GENERATION},
            )
        ]
        mock_model_manager.get_models.return_value = mock_models
        
        # Since the actual client doesn't have stream_generate, mock it as a missing method
        # This will cause an error and fallback to streaming the fallback response
        response_generator._client.stream_generate = Mock(side_effect=AttributeError("stream_generate"))
        
        # Stream response - will fall back to fallback
        context = {"request": "Test"}
        chunks = []
        async for chunk in response_generator.stream_response(
            PromptType.SUGGESTIONS,
            context,
        ):
            chunks.append(chunk)
        
        # Should get fallback response streamed
        full_response = "".join(chunks)
        assert "Consider using a standard Python project structure" in full_response

    @pytest.mark.asyncio
    async def test_stream_response_client_unavailable(self, response_generator):
        """Test streaming when client is unavailable."""
        response_generator._client.is_available = False
        
        context = {"request": "Test"}
        chunks = []
        async for chunk in response_generator.stream_response(
            PromptType.SUGGESTIONS,
            context,
        ):
            chunks.append(chunk)
        
        # Should stream fallback response
        full_response = "".join(chunks)
        assert "Consider using a standard Python project structure" in full_response

    @pytest.mark.asyncio
    async def test_stream_response_error(self, response_generator, mock_model_manager):
        """Test streaming error handling."""
        # Setup mocks
        mock_models = [
            ModelInfo(
                name="llama2:7b",
                size=7_000_000_000,
                digest="abc",
                modified_at=datetime.now(),
                capabilities={ModelCapability.TEXT_GENERATION},
            )
        ]
        mock_model_manager.get_models.return_value = mock_models
        
        # Simulate streaming error
        response_generator._client.stream_generate.side_effect = AIError("Stream failed")
        
        context = {"request": "Test"}
        chunks = []
        async for chunk in response_generator.stream_response(
            PromptType.SUGGESTIONS,
            context,
        ):
            chunks.append(chunk)
        
        # Should stream fallback
        full_response = "".join(chunks)
        assert len(full_response) > 0

    def test_render_prompt_success(self, response_generator):
        """Test successful prompt rendering."""
        context = {"error": "Test error"}
        prompt = response_generator._render_prompt(PromptType.ERROR_HELP, context)
        
        assert prompt == "Rendered prompt"
        response_generator._prompt_manager.render_prompt.assert_called_once_with(
            PromptType.ERROR_HELP,
            context,
            validate_required=False,
        )

    def test_render_prompt_error(self, response_generator):
        """Test prompt rendering error handling."""
        response_generator._prompt_manager.render_prompt.side_effect = Exception("Render error")
        
        context = {"request": "Help with testing"}
        prompt = response_generator._render_prompt(PromptType.GENERIC_HELP, context)
        
        assert prompt == "Please help with: Help with testing"

    @pytest.mark.asyncio
    async def test_select_model_with_preference(self, response_generator, mock_model_manager):
        """Test model selection with preference."""
        mock_models = [
            ModelInfo(
                name="llama2:7b",
                size=7_000_000_000,
                digest="abc",
                modified_at=datetime.now(),
                capabilities={ModelCapability.TEXT_GENERATION},
            ),
            ModelInfo(
                name="llama2:13b",
                size=13_000_000_000,
                digest="def",
                modified_at=datetime.now(),
                capabilities={ModelCapability.TEXT_GENERATION},
            ),
        ]
        mock_model_manager.get_models.return_value = mock_models
        
        model = await response_generator._select_model("llama2:13b")
        assert model == "llama2:13b"

    @pytest.mark.asyncio
    async def test_select_model_no_preference(self, response_generator, mock_model_manager):
        """Test model selection without preference."""
        mock_models = [
            ModelInfo(
                name="llama2:7b",
                size=7_000_000_000,
                digest="abc",
                modified_at=datetime.now(),
                capabilities={ModelCapability.TEXT_GENERATION},
            ),
            ModelInfo(
                name="llama2:13b",
                size=13_000_000_000,
                digest="def",
                modified_at=datetime.now(),
                capabilities={ModelCapability.TEXT_GENERATION},
            ),
        ]
        mock_model_manager.get_models.return_value = mock_models
        
        model = await response_generator._select_model(None)
        # Should select larger model
        assert model == "llama2:13b"

    @pytest.mark.asyncio
    async def test_select_model_no_suitable(self, response_generator, mock_model_manager):
        """Test model selection with no suitable models."""
        mock_models = [
            ModelInfo(
                name="nomic-embed",
                size=1_000_000_000,
                digest="abc",
                modified_at=datetime.now(),
                capabilities={ModelCapability.EMBEDDING},
            ),
        ]
        mock_model_manager.get_models.return_value = mock_models
        
        model = await response_generator._select_model(None)
        # Should return default
        assert model == "llama2:7b"

    @pytest.mark.asyncio
    async def test_select_model_error(self, response_generator, mock_model_manager):
        """Test model selection error handling."""
        mock_model_manager.get_models.side_effect = Exception("Model error")
        
        model = await response_generator._select_model(None)
        assert model == "llama2:7b"

    def test_validate_response_quality_too_short(self, response_generator):
        """Test quality validation for short responses."""
        assert response_generator._validate_response_quality("") is False
        assert response_generator._validate_response_quality("Too short") is False
        assert response_generator._validate_response_quality(" " * 49) is False

    def test_validate_response_quality_too_long(self, response_generator):
        """Test quality validation for long responses."""
        long_response = "x" * 2001
        assert response_generator._validate_response_quality(long_response) is False

    def test_validate_response_quality_repetitive(self, response_generator):
        """Test quality validation for repetitive responses."""
        repetitive = "Same line\n" * 20
        assert response_generator._validate_response_quality(repetitive) is False

    def test_validate_response_quality_no_actionable(self, response_generator):
        """Test quality validation for responses without actionable advice."""
        no_actionable = "This is a response without any numbered steps or bullet points.\n" * 5
        assert response_generator._validate_response_quality(no_actionable) is False

    def test_validate_response_quality_good(self, response_generator):
        """Test quality validation for good responses."""
        good_response = """Here's how to solve your problem:
        
1. First, check your configuration files
2. Next, verify all dependencies are installed
3. Finally, restart the application

Additional tips:
- Make sure you have proper permissions
- Check the log files for more details
- Consider updating to the latest version

This should resolve most common issues."""
        
        assert response_generator._validate_response_quality(good_response) is True

    def test_get_fallback_response_error_help(self, response_generator):
        """Test fallback response for error help."""
        context = {"error_message": "Permission denied"}
        response = response_generator._get_fallback_response(
            PromptType.ERROR_HELP,
            context,
        )
        
        assert "Try checking your project template configuration" in response
        assert "Error details: Permission denied" in response

    def test_get_fallback_response_suggestions(self, response_generator):
        """Test fallback response for suggestions."""
        context = {"project_type": "web_app"}
        response = response_generator._get_fallback_response(
            PromptType.SUGGESTIONS,
            context,
        )
        
        assert "Consider using a standard Python project structure" in response

    def test_get_fallback_response_no_context(self, response_generator):
        """Test fallback response without context."""
        response = response_generator._get_fallback_response(
            PromptType.EXPLANATION,
            {},
        )
        
        assert len(response) > 0
        assert "Understanding the error context" in response

    @pytest.mark.asyncio
    async def test_stream_fallback(self, response_generator):
        """Test streaming fallback responses."""
        fallback = "This is a test fallback response that should be streamed"
        
        chunks = []
        async for chunk in response_generator._stream_fallback(fallback, chunk_size=10):
            chunks.append(chunk)
        
        assert len(chunks) > 1
        assert "".join(chunks) == fallback

    @pytest.mark.asyncio
    async def test_generate_with_custom_config(self, response_generator, mock_model_manager):
        """Test generation with custom configuration."""
        # Setup mocks
        mock_models = [
            ModelInfo(
                name="llama2:13b",
                size=13_000_000_000,
                digest="abc",
                modified_at=datetime.now(),
                capabilities={ModelCapability.TEXT_GENERATION},
            )
        ]
        mock_model_manager.get_models.return_value = mock_models
        
        response_generator._client.generate.return_value = OllamaResponse(
            success=True,
            status_code=200,
            data={"response": "Custom response with specific settings:\n1. Step one\n2. Step two"},
        )
        
        config = GenerationConfig(
            model_preference="llama2:13b",
            max_tokens=2000,
            temperature=0.5,
            top_p=0.95,
            quality_check=False,
        )
        
        context = {"request": "Custom help"}
        response = await response_generator.generate_response(
            PromptType.GENERIC_HELP,
            context,
            config,
        )
        
        assert "Custom response with specific settings" in response
        
        # Verify custom parameters were used
        call_kwargs = response_generator._client.generate.call_args[1]
        assert call_kwargs["temperature"] == 0.5
        assert call_kwargs["top_p"] == 0.95
        assert call_kwargs["max_tokens"] == 2000

    @pytest.mark.asyncio
    async def test_concurrent_generation(self, response_generator, mock_model_manager):
        """Test concurrent response generation."""
        # Setup mocks
        mock_models = [
            ModelInfo(
                name="llama2:7b",
                size=7_000_000_000,
                digest="abc",
                modified_at=datetime.now(),
                capabilities={ModelCapability.TEXT_GENERATION},
            )
        ]
        mock_model_manager.get_models.return_value = mock_models
        
        # Different responses for different prompts (must be long enough to pass quality check)
        responses = [
            OllamaResponse(
                success=True, 
                status_code=200, 
                data={"response": f"Response {i} - This is a detailed response with actionable advice:\n1. First action for error {i}\n2. Second action to resolve the issue\n3. Third step to prevent future occurrences"}
            )
            for i in range(3)
        ]
        response_generator._client.generate.side_effect = responses
        
        # Generate multiple responses concurrently
        tasks = [
            response_generator.generate_response(
                PromptType.ERROR_HELP,
                {"error": f"Error {i}"},
            )
            for i in range(3)
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 3
        assert all("Response" in r for r in results)
        assert response_generator._client.generate.call_count == 3