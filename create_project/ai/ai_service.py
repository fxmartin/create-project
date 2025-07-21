# ABOUTME: AI Service Facade providing unified interface for all AI operations
# ABOUTME: Integrates Ollama detection, response generation, caching with graceful degradation

"""
AI Service Facade for unified AI operations.

This module provides the AIService class which acts as a facade for all AI-related
operations in the project generation system. It integrates Ollama detection,
response generation, caching, and error context collection into a single,
easy-to-use interface with graceful degradation when AI services are unavailable.

The facade handles:
- Automatic Ollama detection and availability checking
- Request routing to appropriate AI components
- Caching layer integration for performance
- Error context enrichment for better assistance
- Configuration management integration
- Structured logging for all operations
"""

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from structlog import get_logger

from ..config.config_manager import ConfigManager
from ..templates.schema.template import Template
from .cache_manager import ResponseCacheManager
from .context_collector import ErrorContextCollector
from .exceptions import OllamaNotFoundError
from .model_manager import ModelInfo, ModelManager
from .ollama_client import OllamaClient
from .ollama_detector import OllamaDetector, OllamaStatus
from .response_generator import GenerationConfig, ResponseGenerator

logger = get_logger(__name__)


@dataclass
class AIServiceConfig:
    """Configuration for AI service operations.
    
    Attributes:
        enabled: Whether AI service is enabled
        ollama_url: Ollama server URL
        ollama_timeout: Timeout for Ollama operations
        cache_enabled: Whether response caching is enabled
        cache_ttl_hours: Cache TTL in hours
        max_cache_entries: Maximum cache entries
        preferred_models: List of preferred models
        context_collection_enabled: Whether to collect error context
        max_context_size_kb: Maximum context size in KB
    """
    enabled: bool = True
    ollama_url: str = "http://localhost:11434"
    ollama_timeout: int = 30
    cache_enabled: bool = True
    cache_ttl_hours: int = 24
    max_cache_entries: int = 100
    preferred_models: List[str] = None
    context_collection_enabled: bool = True
    max_context_size_kb: int = 4

    def __post_init__(self):
        """Initialize default preferred models."""
        if self.preferred_models is None:
            self.preferred_models = [
                "codellama:13b",
                "llama2:13b",
                "mistral:7b",
                "codellama:7b",
                "llama2:7b"
            ]


@dataclass
class AIServiceStatus:
    """Status of AI service components.
    
    Attributes:
        service_available: Whether AI service is available overall
        ollama_available: Whether Ollama is detected and running
        models_loaded: Number of models available
        cache_enabled: Whether caching is enabled
        context_collection_enabled: Whether context collection is enabled
        ollama_status: Detailed Ollama status
        error_message: Error message if service unavailable
    """
    service_available: bool
    ollama_available: bool
    models_loaded: int
    cache_enabled: bool
    context_collection_enabled: bool
    ollama_status: Optional[OllamaStatus]
    error_message: Optional[str] = None


class AIService:
    """Unified AI service facade for project generation assistance.
    
    This class provides a single interface for all AI operations, integrating
    Ollama detection, response generation, caching, and error context collection.
    It handles graceful degradation when AI services are unavailable.
    
    The service automatically detects Ollama availability, manages model discovery,
    handles request routing with caching, and enriches requests with error context
    for better AI assistance quality.
    
    Attributes:
        config: AI service configuration
        detector: Ollama detection service
        client: HTTP client for Ollama API
        model_manager: Model discovery and management
        response_generator: AI response generation
        cache_manager: Response caching system
        context_collector: Error context collection
    """

    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        ai_config: Optional[AIServiceConfig] = None
    ) -> None:
        """Initialize the AI service facade.
        
        Args:
            config_manager: Configuration manager for settings
            ai_config: AI service specific configuration
        """
        self.logger = logger.bind(component="ai_service")
        self.config_manager = config_manager
        self.config = ai_config or AIServiceConfig()

        # Initialize service status
        self._service_status = AIServiceStatus(
            service_available=False,
            ollama_available=False,
            models_loaded=0,
            cache_enabled=False,
            context_collection_enabled=False,
            ollama_status=None
        )

        # Initialize components (lazy loading)
        self._detector: Optional[OllamaDetector] = None
        self._client: Optional[OllamaClient] = None
        self._model_manager: Optional[ModelManager] = None
        self._response_generator: Optional[ResponseGenerator] = None
        self._cache_manager: Optional[ResponseCacheManager] = None
        self._context_collector: Optional[ErrorContextCollector] = None

        # Initialization flag
        self._initialized = False

        self.logger.info(
            "AI service initialized",
            enabled=self.config.enabled,
            ollama_url=self.config.ollama_url,
            cache_enabled=self.config.cache_enabled
        )

    async def initialize(self) -> AIServiceStatus:
        """Initialize AI service components and check availability.
        
        Returns:
            AIServiceStatus with current service status
        """
        if self._initialized:
            return self._service_status

        self.logger.info("Starting AI service initialization")

        try:
            # Check if AI service is enabled
            if not self.config.enabled:
                self.logger.info("AI service disabled in configuration")
                self._service_status = AIServiceStatus(
                    service_available=False,
                    ollama_available=False,
                    models_loaded=0,
                    cache_enabled=False,
                    context_collection_enabled=False,
                    ollama_status=None,
                    error_message="AI service disabled in configuration"
                )
                self._initialized = True
                return self._service_status

            # Initialize detector and check Ollama availability
            self._detector = OllamaDetector(service_url=self.config.ollama_url)
            ollama_status = self._detector.detect()

            if not (ollama_status.is_installed and ollama_status.is_running):
                self.logger.warning(
                    "Ollama not available",
                    is_installed=ollama_status.is_installed,
                    is_running=ollama_status.is_running,
                    error=ollama_status.error_message
                )
                self._service_status = AIServiceStatus(
                    service_available=False,
                    ollama_available=False,
                    models_loaded=0,
                    cache_enabled=self.config.cache_enabled,
                    context_collection_enabled=self.config.context_collection_enabled,
                    ollama_status=ollama_status,
                    error_message=f"Ollama unavailable: {ollama_status.error_message}"
                )
                self._initialized = True
                return self._service_status

            # Initialize HTTP client
            self._client = OllamaClient.get_instance(
                base_url=self.config.ollama_url,
                timeout=self.config.ollama_timeout
            )

            # Initialize model manager and load models
            self._model_manager = ModelManager(client=self._client)
            models = self._model_manager.get_models()

            # Initialize response generator
            self._response_generator = ResponseGenerator(
                model_manager=self._model_manager,
                ollama_client=self._client
            )

            # Initialize cache manager if enabled
            if self.config.cache_enabled:
                self._cache_manager = ResponseCacheManager(
                    max_entries=self.config.max_cache_entries,
                    default_ttl_hours=self.config.cache_ttl_hours
                )
                await self._cache_manager.load_cache()

            # Initialize context collector if enabled
            if self.config.context_collection_enabled:
                self._context_collector = ErrorContextCollector()

            # Update service status
            self._service_status = AIServiceStatus(
                service_available=True,
                ollama_available=True,
                models_loaded=len(models),
                cache_enabled=self.config.cache_enabled,
                context_collection_enabled=self.config.context_collection_enabled,
                ollama_status=ollama_status
            )

            self._initialized = True

            self.logger.info(
                "AI service initialization completed",
                models_available=len(models),
                cache_enabled=self.config.cache_enabled,
                context_collection_enabled=self.config.context_collection_enabled
            )

            return self._service_status

        except Exception as e:
            self.logger.error(
                "AI service initialization failed",
                error=str(e),
                error_type=type(e).__name__
            )
            self._service_status = AIServiceStatus(
                service_available=False,
                ollama_available=False,
                models_loaded=0,
                cache_enabled=False,
                context_collection_enabled=False,
                ollama_status=None,
                error_message=f"Initialization failed: {str(e)}"
            )
            self._initialized = True
            return self._service_status

    async def get_status(self) -> AIServiceStatus:
        """Get current AI service status.
        
        Returns:
            Current service status
        """
        if not self._initialized:
            await self.initialize()
        return self._service_status

    async def is_available(self) -> bool:
        """Check if AI service is available.
        
        Returns:
            True if service is available, False otherwise
        """
        status = await self.get_status()
        return status.service_available

    async def get_available_models(self) -> List[ModelInfo]:
        """Get list of available models.
        
        Returns:
            List of available models
            
        Raises:
            OllamaNotFoundError: If Ollama is not available
        """
        if not await self.is_available():
            raise OllamaNotFoundError("AI service not available")

        return self._model_manager.get_models()

    async def generate_help_response(
        self,
        error: Exception,
        template: Optional[Template] = None,
        project_variables: Optional[Dict[str, Any]] = None,
        target_path: Optional[Path] = None,
        options: Optional[Dict[str, Any]] = None,
        attempted_operations: Optional[List[str]] = None,
        partial_results: Optional[Dict[str, Any]] = None,
        config: Optional[GenerationConfig] = None
    ) -> str:
        """Generate AI-powered help response for project generation errors.
        
        Args:
            error: The error that occurred
            template: Template being processed
            project_variables: Variables used for generation
            target_path: Target path for project
            options: Generation options
            attempted_operations: Operations that were attempted
            partial_results: Partial results from generation
            config: Generation configuration
            
        Returns:
            AI-generated help response
            
        Raises:
            AIError: If response generation fails
        """
        self.logger.info(
            "Generating help response for error",
            error_type=type(error).__name__,
            template_name=template.name if template else None
        )

        # Check if service is available
        if not await self.is_available():
            return self._get_fallback_help_response(error, template)

        try:
            # Collect error context if enabled
            context = None
            if self.config.context_collection_enabled and self._context_collector:
                try:
                    context = self._context_collector.collect_context(
                        error=error,
                        template=template,
                        project_variables=project_variables,
                        target_path=target_path,
                        options=options,
                        attempted_operations=attempted_operations,
                        partial_results=partial_results
                    )

                    self.logger.debug(
                        "Error context collected",
                        context_size_bytes=context.context_size_bytes,
                        collection_duration_ms=context.collection_duration_ms
                    )

                except Exception as ctx_error:
                    self.logger.warning(
                        "Failed to collect error context",
                        error=str(ctx_error)
                    )

            # Check cache if enabled
            cache_key = None
            if self.config.cache_enabled and self._cache_manager:
                cache_params = {
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                    "template_name": template.name if template else None,
                    "context_hash": hash(str(context)) if context else None
                }
                cache_key = self._cache_manager.generate_key(cache_params)
                cached_response = self._cache_manager.get(cache_key)

                if cached_response:
                    self.logger.debug("Using cached response")
                    return cached_response

            # Generate response using AI
            generation_config = config or GenerationConfig()
            response = await self._response_generator.generate_response(
                prompt_type="error_help",
                context={
                    "error": error,
                    "error_context": context,
                    "template": template,
                    "project_variables": project_variables,
                    "target_path": str(target_path) if target_path else None,
                    "options": options,
                    "attempted_operations": attempted_operations,
                    "partial_results": partial_results
                },
                config=generation_config
            )

            # Cache the response if enabled
            if self.config.cache_enabled and self._cache_manager and cache_key:
                self._cache_manager.put(cache_key, response)

            self.logger.info(
                "Help response generated successfully",
                response_length=len(response),
                from_cache=False
            )

            return response

        except Exception as e:
            self.logger.error(
                "Failed to generate AI help response",
                error=str(e),
                error_type=type(e).__name__
            )
            # Fallback to static help
            return self._get_fallback_help_response(error, template)

    async def stream_help_response(
        self,
        error: Exception,
        template: Optional[Template] = None,
        project_variables: Optional[Dict[str, Any]] = None,
        target_path: Optional[Path] = None,
        options: Optional[Dict[str, Any]] = None,
        attempted_operations: Optional[List[str]] = None,
        partial_results: Optional[Dict[str, Any]] = None,
        config: Optional[GenerationConfig] = None
    ) -> AsyncGenerator[str, None]:
        """Stream AI-powered help response for project generation errors.
        
        Args:
            error: The error that occurred
            template: Template being processed
            project_variables: Variables used for generation
            target_path: Target path for project
            options: Generation options
            attempted_operations: Operations that were attempted
            partial_results: Partial results from generation
            config: Generation configuration
            
        Yields:
            Chunks of AI-generated help response
        """
        self.logger.info(
            "Streaming help response for error",
            error_type=type(error).__name__,
            template_name=template.name if template else None
        )

        # Check if service is available
        if not await self.is_available():
            fallback_response = self._get_fallback_help_response(error, template)
            yield fallback_response
            return

        try:
            # Collect error context if enabled
            context = None
            if self.config.context_collection_enabled and self._context_collector:
                try:
                    context = self._context_collector.collect_context(
                        error=error,
                        template=template,
                        project_variables=project_variables,
                        target_path=target_path,
                        options=options,
                        attempted_operations=attempted_operations,
                        partial_results=partial_results
                    )
                except Exception as ctx_error:
                    self.logger.warning(
                        "Failed to collect error context for streaming",
                        error=str(ctx_error)
                    )

            # Stream response using AI
            generation_config = config or GenerationConfig()
            full_response = ""

            async for chunk in self._response_generator.stream_response(
                prompt_type="error_help",
                context={
                    "error": error,
                    "error_context": context,
                    "template": template,
                    "project_variables": project_variables,
                    "target_path": str(target_path) if target_path else None,
                    "options": options,
                    "attempted_operations": attempted_operations,
                    "partial_results": partial_results
                },
                config=generation_config
            ):
                full_response += chunk
                yield chunk

            # Cache the full response if enabled
            if self.config.cache_enabled and self._cache_manager and full_response:
                cache_params = {
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                    "template_name": template.name if template else None,
                    "context_hash": hash(str(context)) if context else None
                }
                cache_key = self._cache_manager.generate_key(cache_params)
                self._cache_manager.put(cache_key, full_response)

            self.logger.info(
                "Streamed help response completed",
                response_length=len(full_response)
            )

        except Exception as e:
            self.logger.error(
                "Failed to stream AI help response",
                error=str(e),
                error_type=type(e).__name__
            )
            # Fallback to static help
            fallback_response = self._get_fallback_help_response(error, template)
            yield fallback_response

    async def get_suggestions(
        self,
        context: Dict[str, Any],
        suggestion_type: str = "general",
        config: Optional[GenerationConfig] = None
    ) -> List[str]:
        """Get AI-powered suggestions for project generation.
        
        Args:
            context: Context information for suggestions
            suggestion_type: Type of suggestions to generate
            config: Generation configuration
            
        Returns:
            List of suggestions
        """
        self.logger.debug(
            "Generating suggestions",
            suggestion_type=suggestion_type,
            context_keys=list(context.keys())
        )

        if not await self.is_available():
            return self._get_fallback_suggestions(context, suggestion_type)

        try:
            generation_config = config or GenerationConfig()
            response = await self._response_generator.generate_response(
                prompt_type="suggestions",
                context={"suggestion_type": suggestion_type, **context},
                config=generation_config
            )

            # Parse response into list of suggestions
            suggestions = []
            for line in response.split("\n"):
                line = line.strip()
                if line and (line.startswith("-") or line.startswith("•") or line.startswith("*")):
                    suggestions.append(line[1:].strip())
                elif line and len(suggestions) < 10:  # Limit to 10 suggestions
                    suggestions.append(line)

            return suggestions[:10] if suggestions else self._get_fallback_suggestions(context, suggestion_type)

        except Exception as e:
            self.logger.error(
                "Failed to generate suggestions",
                error=str(e),
                suggestion_type=suggestion_type
            )
            return self._get_fallback_suggestions(context, suggestion_type)

    async def cleanup(self) -> None:
        """Cleanup AI service resources."""
        self.logger.info("Cleaning up AI service resources")

        try:
            # Persist cache if enabled
            if self._cache_manager and self.config.cache_enabled:
                await self._cache_manager.persist_cache()

            # Close HTTP clients
            if self._client:
                self._client.close_clients()

            self.logger.info("AI service cleanup completed")

        except Exception as e:
            self.logger.error(
                "Error during AI service cleanup",
                error=str(e)
            )

    def _get_fallback_help_response(
        self,
        error: Exception,
        template: Optional[Template] = None
    ) -> str:
        """Get fallback help response when AI is unavailable.
        
        Args:
            error: The error that occurred
            template: Template being processed
            
        Returns:
            Static fallback help response
        """
        error_type = type(error).__name__
        template_name = template.name if template else "unknown"

        fallback_responses = {
            "TemplateError": f"Template processing failed for '{template_name}'. Check that all required variables are provided and template syntax is correct.",
            "PathError": "Path-related error occurred. Verify the target directory exists and you have proper permissions.",
            "GitError": "Git operation failed. Ensure git is installed and properly configured, or disable git integration.",
            "VirtualEnvError": "Virtual environment creation failed. Check Python installation and available tools (venv, virtualenv, uv).",
            "ProjectGenerationError": f"Project generation failed for template '{template_name}'. Review the template configuration and try again.",
        }

        base_response = fallback_responses.get(error_type, f"An error occurred during project generation: {str(error)}")

        return f"""
{base_response}

Error Details:
- Error Type: {error_type}
- Template: {template_name}
- Message: {str(error)}

Troubleshooting Steps:
1. Check the error message for specific details about what went wrong
2. Verify all required template variables are provided
3. Ensure target directory permissions are correct
4. Check that all required tools are installed and accessible
5. Review template configuration for syntax errors

For more detailed assistance, ensure Ollama is installed and running to enable AI-powered help.
""".strip()

    def _get_fallback_suggestions(
        self,
        context: Dict[str, Any],
        suggestion_type: str
    ) -> List[str]:
        """Get fallback suggestions when AI is unavailable.
        
        Args:
            context: Context information
            suggestion_type: Type of suggestions
            
        Returns:
            List of static fallback suggestions
        """
        fallback_suggestions = {
            "general": [
                "Ensure all required dependencies are installed",
                "Verify template configuration is correct",
                "Check file permissions in target directory",
                "Review project variables for completeness",
                "Test with a simpler template first"
            ],
            "template": [
                "Check template syntax for Jinja2 errors",
                "Verify all required variables are defined",
                "Test template rendering with sample data",
                "Review template structure and file paths",
                "Validate template YAML configuration"
            ],
            "path": [
                "Use absolute paths when possible",
                "Avoid special characters in path names",
                "Check directory permissions",
                "Ensure parent directories exist",
                "Verify path length limitations"
            ]
        }

        return fallback_suggestions.get(suggestion_type, fallback_suggestions["general"])

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()
