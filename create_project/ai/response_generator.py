# ABOUTME: AI response generator for creating contextual help and suggestions
# ABOUTME: Handles prompt templating, response streaming, and quality validation

import asyncio
from typing import Dict, Any, Optional, AsyncIterator, List, Union, Protocol
from dataclasses import dataclass, field
from enum import Enum
import structlog
from jinja2 import Environment, DictLoader, select_autoescape

from .ollama_client import OllamaClient, OllamaResponse
from .model_manager import ModelManager, ModelCapability
from .exceptions import AIError, ResponseTimeoutError, ModelNotAvailableError

logger = structlog.get_logger(__name__)


class PromptType(Enum):
    """Types of AI prompts supported by the response generator."""
    ERROR_HELP = "error_help"
    SUGGESTIONS = "suggestions" 
    EXPLANATION = "explanation"
    GENERIC_HELP = "generic_help"


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
    stream_response: bool = True
    timeout_seconds: int = 30
    quality_filter: ResponseQuality = field(default_factory=ResponseQuality)
    retry_attempts: int = 2


class PromptTemplate(Protocol):
    """Protocol for prompt template rendering."""
    
    def render(self, **kwargs: Any) -> str:
        """Render template with provided variables."""
        ...


class ResponseGenerator:
    """
    Generates contextual AI responses for project creation assistance.
    
    Provides intelligent help suggestions, error explanations, and general guidance
    using Ollama models with quality filtering and streaming support.
    """
    
    # Default prompt templates
    _DEFAULT_TEMPLATES = {
        "error_help": """You are an expert Python developer helping troubleshoot project creation errors.

Context:
- Error: {{ error_message }}
- Project Type: {{ project_type | default("Unknown") }}
- Template: {{ template_name | default("Unknown") }}
- System: {{ system_info | default("Unknown") }}

Please provide:
1. A brief explanation of what likely went wrong
2. 2-3 specific actionable steps to resolve the issue
3. One alternative approach if the main solution doesn't work

Keep your response concise (under 300 words) and practical. Focus on solutions, not just descriptions of the problem.""",

        "suggestions": """You are a helpful Python project assistant providing creative suggestions.

Context:
- User Goal: {{ user_goal }}
- Project Type: {{ project_type | default("Python project") }}
- Current Templates: {{ available_templates | join(", ") if available_templates else "Standard templates" }}

Suggest 3 different approaches for this project, considering:
- Different project structures that might fit
- Useful libraries or tools to include
- Best practices for this type of project

Keep suggestions practical and explain why each approach would be beneficial.""",

        "explanation": """You are a knowledgeable Python educator explaining project concepts.

Context:
- Topic: {{ topic }}
- User Level: {{ user_level | default("intermediate") }}
- Specific Question: {{ question | default("General explanation requested") }}

Provide a clear explanation that:
1. Explains the concept in simple terms
2. Shows a practical example if relevant  
3. Mentions common pitfalls to avoid

Tailor your explanation to be educational but not overwhelming.""",

        "generic_help": """You are a friendly Python project creation assistant.

The user needs help with: {{ request }}

Context: {{ context | default("No additional context provided") }}

Provide helpful, actionable advice. Be encouraging and practical."""
    }
    
    def __init__(self, 
                 ollama_client: Optional[OllamaClient] = None,
                 model_manager: Optional[ModelManager] = None):
        """
        Initialize the response generator.
        
        Args:
            ollama_client: Client for Ollama API communication
            model_manager: Manager for model discovery and selection
        """
        self._client = ollama_client or OllamaClient()
        self._model_manager = model_manager or ModelManager()
        self._template_env = self._setup_templates()
        self._fallback_responses: Dict[PromptType, List[str]] = self._load_fallback_responses()
        
        logger.info("Response generator initialized", 
                   client_available=self._client.is_available,
                   templates_count=len(self._DEFAULT_TEMPLATES))
    
    def _setup_templates(self) -> Environment:
        """Set up Jinja2 template environment with default templates."""
        env = Environment(
            loader=DictLoader(self._DEFAULT_TEMPLATES),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        return env
    
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
                "Think about including testing frameworks, linting tools, and CI/CD setup from the start."
            ],
            PromptType.EXPLANATION: [
                "This concept involves understanding Python project structure and organization principles.",
                "Consider reviewing Python packaging and project management best practices.",
                "Look into established patterns used by the Python community for similar projects."
            ],
            PromptType.GENERIC_HELP: [
                "Check the documentation for detailed guidance on project creation options.",
                "Ensure your development environment is properly configured with required tools.",
                "Consider starting with a simpler template and adding complexity gradually."
            ]
        }
    
    async def generate_response(self, 
                              prompt_type: PromptType,
                              context: Dict[str, Any],
                              config: Optional[GenerationConfig] = None) -> str:
        """
        Generate an AI response for the given prompt and context.
        
        Args:
            prompt_type: Type of prompt to generate
            context: Context variables for template rendering
            config: Generation configuration options
            
        Returns:
            Generated response text
            
        Raises:
            AIError: If response generation fails
            ResponseTimeoutError: If generation times out
            ModelNotAvailableError: If no suitable model is available
        """
        config = config or GenerationConfig()
        
        # Check if AI is available
        if not self._client.is_available:
            logger.warning("Ollama client unavailable, using fallback response",
                          prompt_type=prompt_type.value)
            return self._get_fallback_response(prompt_type, context)
        
        try:
            # Render prompt template
            prompt = self._render_prompt(prompt_type, context)
            
            # Select appropriate model
            model = await self._select_model(config.model_preference)
            
            # Generate response
            if config.stream_response:
                response_text = ""
                async for chunk in self._stream_generate(prompt, model, config):
                    response_text += chunk
            else:
                response_text = await self._generate_single(prompt, model, config)
            
            # Validate response quality
            if self._validate_response_quality(response_text, config.quality_filter):
                logger.info("AI response generated successfully",
                           prompt_type=prompt_type.value,
                           response_length=len(response_text),
                           model=model)
                return response_text
            else:
                logger.warning("AI response failed quality check, using fallback",
                              prompt_type=prompt_type.value)
                return self._get_fallback_response(prompt_type, context)
                
        except Exception as e:
            logger.error("AI response generation failed",
                        prompt_type=prompt_type.value,
                        error=str(e),
                        exc_info=True)
            
            if config.retry_attempts > 0:
                config.retry_attempts -= 1
                logger.info("Retrying response generation", attempts_remaining=config.retry_attempts)
                return await self.generate_response(prompt_type, context, config)
            
            # Fall back to static response
            return self._get_fallback_response(prompt_type, context)
    
    async def stream_response(self,
                            prompt_type: PromptType,
                            context: Dict[str, Any],
                            config: Optional[GenerationConfig] = None) -> AsyncIterator[str]:
        """
        Stream AI response generation for better UX.
        
        Args:
            prompt_type: Type of prompt to generate
            context: Context variables for template rendering
            config: Generation configuration options
            
        Yields:
            Response chunks as they are generated
        """
        config = config or GenerationConfig(stream_response=True)
        
        if not self._client.is_available:
            # Yield fallback response in chunks
            fallback = self._get_fallback_response(prompt_type, context)
            chunk_size = 50
            for i in range(0, len(fallback), chunk_size):
                yield fallback[i:i + chunk_size]
                await asyncio.sleep(0.1)  # Simulate streaming delay
            return
        
        try:
            prompt = self._render_prompt(prompt_type, context)
            model = await self._select_model(config.model_preference)
            
            async for chunk in self._stream_generate(prompt, model, config):
                yield chunk
                
        except Exception as e:
            logger.error("Streaming response generation failed",
                        prompt_type=prompt_type.value,
                        error=str(e))
            
            # Fall back to static response streaming
            fallback = self._get_fallback_response(prompt_type, context)
            chunk_size = 50
            for i in range(0, len(fallback), chunk_size):
                yield fallback[i:i + chunk_size]
                await asyncio.sleep(0.1)
    
    def _render_prompt(self, prompt_type: PromptType, context: Dict[str, Any]) -> str:
        """Render prompt template with context variables."""
        try:
            template = self._template_env.get_template(prompt_type.value)
            return template.render(**context)
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
            ]
            
            if not suitable_models:
                raise ModelNotAvailableError("No models available for text generation")
            
            # Prefer models with better capabilities, larger size generally better
            def model_priority(model):
                # Convert parameter size to numeric for comparison
                param_size = 0
                if model.parameter_size:
                    try:
                        # Extract numeric part from strings like "7b", "3b", etc.
                        size_str = model.parameter_size.lower().replace('b', '')
                        param_size = float(size_str)
                    except (ValueError, AttributeError):
                        param_size = 0
                
                return (len(model.capabilities), param_size)
            
            best_model = max(suitable_models, key=model_priority)
            
            return best_model.name
            
        except ModelNotAvailableError:
            # Re-raise ModelNotAvailableError directly
            raise
        except Exception as e:
            logger.error("Model selection failed", error=str(e))
            # Try to use any available model as last resort
            try:
                models = await self._model_manager.get_available_models()
                if models:
                    return models[0].name
            except Exception:
                pass  # Continue to final error
            raise ModelNotAvailableError("No models available for response generation")
    
    async def _generate_single(self, prompt: str, model: str, config: GenerationConfig) -> str:
        """Generate a single complete response."""
        response = await self._client.chat_completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=config.max_tokens,
            temperature=config.temperature,
            timeout=config.timeout_seconds
        )
        
        if not response.success:
            raise AIError(f"Response generation failed: {response.error}")
        
        return response.content
    
    async def _stream_generate(self, prompt: str, model: str, config: GenerationConfig) -> AsyncIterator[str]:
        """Generate streaming response chunks."""
        # For now, simulate streaming by yielding single response in chunks
        # This can be enhanced when Ollama streaming API is implemented
        response_text = await self._generate_single(prompt, model, config)
        
        # Yield in chunks for streaming effect
        chunk_size = 20
        for i in range(0, len(response_text), chunk_size):
            yield response_text[i:i + chunk_size]
            await asyncio.sleep(0.05)  # Small delay for streaming effect
    
    def _validate_response_quality(self, response: str, quality: ResponseQuality) -> bool:
        """Validate if response meets quality standards."""
        if not response or not response.strip():
            return False
        
        response = response.strip()
        
        # Check length requirements
        if len(response) < quality.min_length or len(response) > quality.max_length:
            return False
        
        # Basic coherence checks
        if quality.requires_actionable_advice:
            # Look for action words/phrases indicating actionable advice
            action_indicators = [
                "try", "check", "verify", "ensure", "consider", "use", "install",
                "run", "create", "add", "remove", "update", "configure", "set",
                "step", "solution", "fix", "resolve"
            ]
            
            response_lower = response.lower()
            has_action = any(indicator in response_lower for indicator in action_indicators)
            
            if not has_action:
                return False
        
        # Check for minimal structure (sentences, not just fragments)
        if '.' not in response and '!' not in response and '?' not in response:
            return False
        
        return True
    
    def _get_fallback_response(self, prompt_type: PromptType, context: Dict[str, Any]) -> str:
        """Get a fallback response when AI is unavailable."""
        fallback_options = self._fallback_responses.get(prompt_type, [])
        
        if not fallback_options:
            return "I'm unable to provide specific guidance at the moment. Please check the documentation or try a simpler approach."
        
        # Select most relevant fallback based on context
        if context.get('error_message'):
            # For errors, prefer diagnostic fallbacks
            diagnostic_fallbacks = [fb for fb in fallback_options if 'check' in fb.lower() or 'verify' in fb.lower()]
            if diagnostic_fallbacks:
                return diagnostic_fallbacks[0]
        
        return fallback_options[0]
    
    def get_supported_models(self) -> List[str]:
        """Get list of supported model names."""
        try:
            models = asyncio.run(self._model_manager.get_available_models())
            return [model.name for model in models]
        except Exception:
            return []
    
    def is_available(self) -> bool:
        """Check if the response generator is available for use."""
        return self._client.is_available