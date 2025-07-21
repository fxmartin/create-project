# ABOUTME: AI response generator for creating contextual help and suggestions
# ABOUTME: Handles prompt templating, response streaming, and quality validation

"""AI response generation system for intelligent project creation assistance.

This module provides the core response generation functionality for the AI
assistant, supporting both synchronous and streaming responses. It handles
prompt rendering, model selection, quality validation, and graceful fallback
when AI services are unavailable.

Key Features:
    - Multiple prompt types (error help, suggestions, explanations)
    - Automatic model selection based on capabilities
    - Response quality validation with configurable thresholds
    - Streaming support for real-time response display
    - Fallback responses when AI is unavailable
    - Timeout handling to prevent blocking
    - Configurable generation parameters (temperature, tokens, etc.)
    - Automatic retry with streaming if direct generation fails

Main Classes:
    - ResponseQuality: Configuration for response quality validation
    - GenerationConfig: Parameters for AI response generation
    - ResponseGenerator: Main generator class for AI responses

Usage Example:
    ```python
    from create_project.ai import ResponseGenerator, GenerationConfig
    from create_project.ai.types import PromptType
    import asyncio
    
    # Initialize generator
    generator = ResponseGenerator()
    
    # Generate error help
    async def get_error_help():
        config = GenerationConfig(
            model_preference="llama2:7b",
            temperature=0.5,  # Lower for more focused responses
            max_tokens=500,
            quality_check=True
        )
        
        context = {
            "error_message": "Permission denied: cannot create directory",
            "error_type": "PermissionError",
            "operation": "Creating project structure"
        }
        
        response = await generator.generate_response(
            PromptType.ERROR_HELP,
            context,
            config
        )
        print(response)
    
    # Stream suggestions for better UX
    async def stream_suggestions():
        context = {
            "project_type": "web_app",
            "technologies": ["FastAPI", "PostgreSQL", "Redis"]
        }
        
        async for chunk in generator.stream_response(
            PromptType.SUGGESTIONS,
            context
        ):
            print(chunk, end='', flush=True)
    
    # Run examples
    asyncio.run(get_error_help())
    asyncio.run(stream_suggestions())
    ```

The generator automatically handles model availability checks, falls back to
pre-configured responses when AI is unavailable, and validates response
quality to ensure helpful and actionable advice.
"""

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import structlog

from .exceptions import AIError, ModelNotAvailableError, ResponseTimeoutError
from .model_manager import ModelCapability, ModelManager
from .ollama_client import OllamaClient
from .prompt_manager import PromptManager
from .types import PromptType

logger = structlog.get_logger(__name__)


@dataclass
class ResponseQuality:
    """Quality metrics for AI responses."""
    min_length: int = 50
    max_length: int = 2000
    min_coherence_score: float = 0.7
    requires_actionable_advice: bool = True


@dataclass
class GenerationConfig:
    """Configuration for AI response generation."""
    model_preference: Optional[str] = None
    max_tokens: int = 1000
    temperature: float = 0.7
    top_p: float = 0.9
    timeout_seconds: int = 30
    stream: bool = False
    quality_check: bool = True


class ResponseGenerator:
    """
    AI response generator for project creation assistance.
    
    This class generates helpful AI responses for various scenarios including
    error help, suggestions, and explanations. It uses Ollama models to provide
    context-aware assistance with fallback mechanisms when AI is unavailable.
    
    The generator supports:
    - Multiple prompt types (error help, suggestions, explanations)
    - Streaming responses for better UX
    - Quality validation of generated responses
    - Fallback responses when AI is unavailable
    - Configurable model selection
    
    Provides intelligent help suggestions, error explanations, and general guidance
    using Ollama models with quality filtering and streaming support.
    """

    def __init__(self,
                 ollama_client: Optional[OllamaClient] = None,
                 model_manager: Optional[ModelManager] = None,
                 prompt_manager: Optional[PromptManager] = None):
        """
        Initialize the response generator.
        
        Args:
            ollama_client: Client for Ollama API communication
            model_manager: Manager for model discovery and selection
            prompt_manager: Manager for prompt templates
        """
        self._client = ollama_client or OllamaClient()
        self._model_manager = model_manager or ModelManager()
        self._prompt_manager = prompt_manager or PromptManager()
        self._fallback_responses: Dict[PromptType, List[str]] = self._load_fallback_responses()

        logger.info("Response generator initialized",
                   client_available=self._client.is_available,
                   templates_available=len(self._prompt_manager.list_available_templates()))

    def _load_fallback_responses(self) -> Dict[PromptType, List[str]]:
        """Load fallback responses for when AI is unavailable."""
        return {
            PromptType.ERROR_HELP: [
                "Try checking your project template configuration and ensure all required dependencies are installed.",
                "Verify that your system has sufficient permissions and disk space for project creation.",
                "Review the error message for specific file paths or permission issues that need attention."
            ],
            PromptType.SUGGESTIONS: [
                "Consider using a standard Python project structure with src/ layout for better organization.",
                "Look into popular project templates that match your use case and requirements.",
                "Review successful projects similar to yours for inspiration and best practices."
            ],
            PromptType.EXPLANATION: [
                "Understanding the error context is key to finding the right solution.",
                "Break down complex issues into smaller, manageable parts for easier troubleshooting.",
                "Consult documentation and community resources for additional guidance."
            ],
            PromptType.GENERIC_HELP: [
                "Double-check your project configuration and template settings.",
                "Ensure all required tools and dependencies are properly installed.",
                "Consider starting with a simpler template to isolate the issue."
            ]
        }

    async def generate_response(self,
                              prompt_type: PromptType,
                              context: Dict[str, Any],
                              config: Optional[GenerationConfig] = None) -> str:
        """
        Generate an AI response for the given prompt type and context.
        
        Args:
            prompt_type: Type of prompt to generate
            context: Context variables for prompt rendering
            config: Generation configuration options
            
        Returns:
            Generated AI response or fallback message
            
        Raises:
            ResponseTimeoutError: If generation times out
            AIError: For other generation failures
        """
        config = config or GenerationConfig()

        # Validate client availability
        if not self._client.is_available:
            logger.warning("Ollama client not available, using fallback",
                          prompt_type=prompt_type.value)
            return self._get_fallback_response(prompt_type, context)

        try:
            # Render prompt template
            prompt = self._render_prompt(prompt_type, context)

            # Select appropriate model
            model = await self._select_model(config.model_preference)

            # Generate response
            response = await self._generate_with_timeout(
                model=model,
                prompt=prompt,
                config=config
            )

            # Validate response quality if enabled
            if config.quality_check and not self._validate_response_quality(response):
                logger.warning("Response failed quality check, using fallback",
                              prompt_type=prompt_type.value,
                              response_length=len(response))
                return self._get_fallback_response(prompt_type, context)

            logger.info("Response generated successfully",
                       prompt_type=prompt_type.value,
                       model=model,
                       response_length=len(response))

            return response

        except ResponseTimeoutError:
            logger.error("Response generation timed out",
                        prompt_type=prompt_type.value)
            raise
        except Exception as e:
            logger.error("Response generation failed",
                        prompt_type=prompt_type.value,
                        error=str(e))
            # Try streaming as fallback if direct generation fails
            if not config.stream:
                config.stream = True
                return await self.generate_response(prompt_type, context, config)
            # Otherwise use static fallback
            return self._get_fallback_response(prompt_type, context)

    async def stream_response(self,
                            prompt_type: PromptType,
                            context: Dict[str, Any],
                            config: Optional[GenerationConfig] = None) -> AsyncIterator[str]:
        """
        Stream an AI response for the given prompt type and context.
        
        Args:
            prompt_type: Type of prompt to generate
            context: Context variables for prompt rendering
            config: Generation configuration options
            
        Yields:
            Chunks of the generated response
            
        Raises:
            ResponseTimeoutError: If generation times out
            AIError: For other generation failures
        """
        config = config or GenerationConfig()
        config.stream = True  # Force streaming mode

        # Check client availability
        if not self._client.is_available:
            logger.warning("Ollama client not available, streaming fallback",
                          prompt_type=prompt_type.value)
            fallback = self._get_fallback_response(prompt_type, context)
            # Stream the fallback in chunks
            async for chunk in self._stream_fallback(fallback):
                yield chunk
            return

        try:
            # Render prompt and select model
            prompt = self._render_prompt(prompt_type, context)
            model = await self._select_model(config.model_preference)

            # Stream the response
            response_chunks = []
            async for chunk in self._stream_with_timeout(model, prompt, config):
                response_chunks.append(chunk)
                yield chunk

            # Validate complete response if quality check enabled
            if config.quality_check:
                complete_response = "".join(response_chunks)
                if not self._validate_response_quality(complete_response):
                    logger.warning("Streamed response failed quality check",
                                 prompt_type=prompt_type.value,
                                 response_length=len(complete_response))

        except Exception as e:
            logger.error("Response streaming failed",
                        prompt_type=prompt_type.value,
                        error=str(e))
            # Stream fallback on error
            fallback = self._get_fallback_response(prompt_type, context)
            async for chunk in self._stream_fallback(fallback):
                yield chunk

    async def _stream_fallback(self, fallback: str, chunk_size: int = 100) -> AsyncIterator[str]:
        """Stream a fallback response in chunks."""
        for i in range(0, len(fallback), chunk_size):
            yield fallback[i:i + chunk_size]
            await asyncio.sleep(0.1)

    def _render_prompt(self, prompt_type: PromptType, context: Dict[str, Any]) -> str:
        """Render prompt template with context variables."""
        try:
            return self._prompt_manager.render_prompt(prompt_type, context, validate_required=False)
        except Exception as e:
            logger.error("Template rendering failed",
                        prompt_type=prompt_type.value,
                        error=str(e))
            # Return basic prompt as fallback
            return f"Please help with: {context.get('request', 'general assistance')}"

    async def _select_model(self, preference: Optional[str]) -> str:
        """Select the best available model for text generation."""
        try:
            models = await self._model_manager.get_available_models()

            # Use preference if specified and available
            if preference and any(model.name == preference for model in models):
                return preference

            # Filter models suitable for text generation
            suitable_models = [
                model for model in models
                if ModelCapability.TEXT_GENERATION in model.capabilities
                or ModelCapability.CHAT in model.capabilities
            ]

            if not suitable_models:
                raise ModelNotAvailableError("No suitable text generation models available", [])

            # Prefer larger models for better quality
            suitable_models.sort(key=lambda m: m.size, reverse=True)

            return suitable_models[0].name

        except Exception as e:
            logger.error("Model selection failed", error=str(e))
            # Default to a common model
            return "llama2:7b"

    async def _generate_with_timeout(self,
                                   model: str,
                                   prompt: str,
                                   config: GenerationConfig) -> str:
        """Generate response with timeout handling."""
        try:
            response = await asyncio.wait_for(
                self._client.generate(
                    model=model,
                    prompt=prompt,
                    temperature=config.temperature,
                    top_p=config.top_p,
                    max_tokens=config.max_tokens,
                    stream=False
                ),
                timeout=config.timeout_seconds
            )

            if response.success and response.data.get("response"):
                return response.data["response"]
            else:
                raise AIError(f"Generation failed: {response.error_message}")

        except asyncio.TimeoutError:
            raise ResponseTimeoutError(f"Response generation timed out after {config.timeout_seconds}s")

    async def _stream_with_timeout(self,
                                 model: str,
                                 prompt: str,
                                 config: GenerationConfig) -> AsyncIterator[str]:
        """Stream response with timeout handling."""
        try:
            # Create streaming task
            stream_task = asyncio.create_task(
                self._client.stream_generate(
                    model=model,
                    prompt=prompt,
                    temperature=config.temperature,
                    top_p=config.top_p,
                    max_tokens=config.max_tokens
                )
            )

            # Stream with timeout
            start_time = asyncio.get_event_loop().time()
            async for response in stream_task:
                # Check timeout
                if asyncio.get_event_loop().time() - start_time > config.timeout_seconds:
                    stream_task.cancel()
                    raise ResponseTimeoutError(f"Streaming timed out after {config.timeout_seconds}s")

                if response.success and response.data.get("response"):
                    yield response.data["response"]

        except asyncio.CancelledError:
            logger.warning("Stream generation cancelled")
            raise
        except Exception as e:
            logger.error("Stream generation error", error=str(e))
            raise

    def _validate_response_quality(self, response: str) -> bool:
        """Validate the quality of a generated response."""
        # Basic quality checks
        if not response or len(response.strip()) < ResponseQuality.min_length:
            return False

        if len(response) > ResponseQuality.max_length:
            return False

        # Check for repetitive content
        lines = response.split("\n")
        unique_lines = set(lines)
        if len(unique_lines) < len(lines) * 0.5:  # Too many repeated lines
            return False

        # Check for actionable content (should have numbered lists or bullet points)
        if ResponseQuality.requires_actionable_advice:
            has_actionable = any(
                line.strip().startswith(("1.", "2.", "3.", "-", "*", "•"))
                for line in lines
            )
            if not has_actionable:
                return False

        return True

    def _get_fallback_response(self, prompt_type: PromptType, context: Dict[str, Any]) -> str:
        """Get an appropriate fallback response for the prompt type."""
        fallback_list = self._fallback_responses.get(prompt_type, [])

        # Try to make response somewhat contextual
        if prompt_type == PromptType.ERROR_HELP and "error_message" in context:
            error_msg = str(context["error_message"])
            base_response = fallback_list[0] if fallback_list else "Please check your configuration."
            return f"{base_response}\n\nError details: {error_msg}"

        # Return first fallback or generic message
        return fallback_list[0] if fallback_list else "Please try checking your project configuration and try again."
