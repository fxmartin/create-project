# ABOUTME: Model discovery and management for Ollama with caching and validation
# ABOUTME: Queries available models, manages metadata, and provides filtering capabilities

import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set

from pydantic import BaseModel, Field
from structlog import get_logger

from .exceptions import AIError, ModelNotAvailableError
from .ollama_client import OllamaClient


class ModelCapability(Enum):
    """Model capabilities."""
    TEXT_GENERATION = "text_generation"
    CODE_GENERATION = "code_generation"
    CHAT = "chat"
    EMBEDDING = "embedding"
    VISION = "vision"


@dataclass
class ModelInfo:
    """Information about an Ollama model."""
    name: str
    size: int
    digest: str
    modified_at: datetime
    capabilities: Set[ModelCapability]
    family: Optional[str] = None
    parameter_size: Optional[str] = None
    quantization: Optional[str] = None


class ModelListResponse(BaseModel):
    """Pydantic model for Ollama model list response."""
    models: List[Dict[str, str]] = Field(default_factory=list)

    class Config:
        extra = "allow"


class ModelManager:
    """Manages Ollama model discovery and metadata with caching."""

    CACHE_TTL_MINUTES = 10

    # Known model families and their typical capabilities
    MODEL_FAMILIES = {
        "llama": {ModelCapability.TEXT_GENERATION, ModelCapability.CHAT, ModelCapability.CODE_GENERATION},
        "codellama": {ModelCapability.CODE_GENERATION, ModelCapability.TEXT_GENERATION, ModelCapability.CHAT},
        "mistral": {ModelCapability.TEXT_GENERATION, ModelCapability.CHAT},
        "dolphin": {ModelCapability.TEXT_GENERATION, ModelCapability.CHAT, ModelCapability.CODE_GENERATION},
        "orca": {ModelCapability.TEXT_GENERATION, ModelCapability.CHAT},
        "vicuna": {ModelCapability.TEXT_GENERATION, ModelCapability.CHAT},
        "wizardcoder": {ModelCapability.CODE_GENERATION, ModelCapability.TEXT_GENERATION},
        "starcoder": {ModelCapability.CODE_GENERATION, ModelCapability.TEXT_GENERATION},
        "deepseek": {ModelCapability.CODE_GENERATION, ModelCapability.TEXT_GENERATION, ModelCapability.CHAT},
        "phi": {ModelCapability.TEXT_GENERATION, ModelCapability.CHAT, ModelCapability.CODE_GENERATION},
        "gemma": {ModelCapability.TEXT_GENERATION, ModelCapability.CHAT},
        "qwen": {ModelCapability.TEXT_GENERATION, ModelCapability.CHAT, ModelCapability.CODE_GENERATION},
        "nomic": {ModelCapability.EMBEDDING},
        "llava": {ModelCapability.VISION, ModelCapability.TEXT_GENERATION, ModelCapability.CHAT}
    }

    def __init__(self, client: Optional[OllamaClient] = None):
        """
        Initialize model manager.
        
        Args:
            client: Ollama client instance (creates default if None)
        """
        self.client = client or OllamaClient()
        self.logger = get_logger("ai.model_manager")

        # Thread-safe caching
        self._cache: Optional[List[ModelInfo]] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_lock = threading.RLock()

        self.logger.debug("Model manager initialized")

    def get_models(self, force_refresh: bool = False) -> List[ModelInfo]:
        """
        Get list of available models with caching.
        
        Args:
            force_refresh: If True, bypass cache and fetch fresh data
            
        Returns:
            List of ModelInfo objects
            
        Raises:
            AIError: If unable to fetch models
        """
        with self._cache_lock:
            # Check cache validity
            if not force_refresh and self._is_cache_valid():
                self.logger.debug("Using cached model list")
                return self._cache.copy()

            self.logger.info("Fetching available models from Ollama")

            # Fetch fresh model data
            models = self._fetch_models()

            # Cache results
            self._cache = models
            self._cache_timestamp = datetime.now()

            self.logger.info("Model list updated", model_count=len(models))
            return models.copy()

    def _is_cache_valid(self) -> bool:
        """Check if cached model list is still valid."""
        if self._cache is None or self._cache_timestamp is None:
            return False

        cache_age = datetime.now() - self._cache_timestamp
        return cache_age < timedelta(minutes=self.CACHE_TTL_MINUTES)

    def _fetch_models(self) -> List[ModelInfo]:
        """Fetch model list from Ollama API."""
        try:
            response = self.client.get_models()

            if not response.success:
                raise AIError(f"Failed to fetch models: {response.error_message}")

            # Parse response using Pydantic
            model_list = ModelListResponse(**response.data)

            models = []
            for model_data in model_list.models:
                try:
                    model_info = self._parse_model_info(model_data)
                    models.append(model_info)
                except Exception as e:
                    self.logger.warning(
                        "Failed to parse model info",
                        model_data=model_data,
                        error=str(e)
                    )
                    continue

            return models

        except Exception as e:
            self.logger.error("Failed to fetch models", error=str(e))
            raise AIError(f"Model discovery failed: {e}")

    def _parse_model_info(self, model_data: Dict[str, str]) -> ModelInfo:
        """Parse raw model data into ModelInfo object."""
        name = model_data.get("name", "").strip()
        if not name:
            raise ValueError("Model name is required")

        # Parse size (can be string or int)
        size_str = model_data.get("size", "0")
        try:
            size = int(size_str) if isinstance(size_str, str) else size_str
        except (ValueError, TypeError):
            size = 0

        # Parse digest
        digest = model_data.get("digest", "").strip()

        # Parse modified timestamp
        modified_str = model_data.get("modified_at", "")
        try:
            if modified_str:
                # Ollama returns RFC3339 format: 2024-01-01T12:00:00Z
                modified_at = datetime.fromisoformat(modified_str.replace("Z", "+00:00"))
            else:
                modified_at = datetime.now()
        except (ValueError, TypeError):
            modified_at = datetime.now()

        # Determine capabilities and family
        family, capabilities = self._analyze_model(name)

        # Parse parameter size and quantization from name
        parameter_size, quantization = self._parse_model_name_details(name)

        return ModelInfo(
            name=name,
            size=size,
            digest=digest,
            modified_at=modified_at,
            capabilities=capabilities,
            family=family,
            parameter_size=parameter_size,
            quantization=quantization
        )

    def _analyze_model(self, model_name: str) -> tuple[Optional[str], Set[ModelCapability]]:
        """
        Analyze model name to determine family and capabilities.
        
        Args:
            model_name: Full model name (e.g., "llama2:7b-chat")
            
        Returns:
            Tuple of (family, capabilities)
        """
        name_lower = model_name.lower()

        # Special handling for specific patterns (check more specific first)
        # Embedding models
        if any(keyword in name_lower for keyword in ["embed", "embedding", "nomic"]):
            return "nomic", {ModelCapability.EMBEDDING}

        # Vision models
        if any(keyword in name_lower for keyword in ["vision", "llava", "bakllava"]):
            return "llava", {ModelCapability.VISION, ModelCapability.TEXT_GENERATION, ModelCapability.CHAT}

        # Code-specific models (before general code check)
        if "codellama" in name_lower:
            return "codellama", self.MODEL_FAMILIES["codellama"].copy()
        if "wizardcoder" in name_lower:
            return "wizardcoder", self.MODEL_FAMILIES["wizardcoder"].copy()
        if "starcoder" in name_lower:
            return "starcoder", self.MODEL_FAMILIES["starcoder"].copy()
        if "deepseek" in name_lower:
            return "deepseek", self.MODEL_FAMILIES["deepseek"].copy()

        # Try to match known families (order matters - more specific first)
        family_order = [
            "dolphin", "mistral", "orca", "vicuna", "phi", "gemma", "qwen",
            "llama"  # llama should be last since it's a substring of others
        ]

        for family in family_order:
            if family in name_lower:
                return family, self.MODEL_FAMILIES[family].copy()

        # Fallback for general code models
        if any(keyword in name_lower for keyword in ["code", "coder", "coding"]):
            return "code", {ModelCapability.CODE_GENERATION, ModelCapability.TEXT_GENERATION}

        # Default capabilities for unknown models
        default_capabilities = {ModelCapability.TEXT_GENERATION, ModelCapability.CHAT}
        return None, default_capabilities

    def _parse_model_name_details(self, model_name: str) -> tuple[Optional[str], Optional[str]]:
        """
        Parse parameter size and quantization from model name.
        
        Args:
            model_name: Full model name (e.g., "llama2:7b-chat-q4_0")
            
        Returns:
            Tuple of (parameter_size, quantization)
        """
        # Split by colon to separate name from tag
        if ":" in model_name:
            _, tag = model_name.split(":", 1)
        else:
            tag = model_name

        tag_lower = tag.lower()

        # Common parameter sizes
        parameter_size = None
        for size in ["70b", "34b", "13b", "7b", "3b", "1b", "0.5b"]:
            if size in tag_lower:
                parameter_size = size.upper()
                break

        # Common quantizations
        quantization = None
        quantization_patterns = ["q8_0", "q4_k_m", "q4_0", "q5_k_m", "q5_0", "q6_k", "fp16", "bf16"]
        for quant in quantization_patterns:
            if quant in tag_lower:
                quantization = quant.upper()
                break

        return parameter_size, quantization

    def get_model_by_name(self, model_name: str) -> Optional[ModelInfo]:
        """
        Get specific model by name.
        
        Args:
            model_name: Name of the model to find
            
        Returns:
            ModelInfo if found, None otherwise
        """
        models = self.get_models()

        for model in models:
            if model.name == model_name:
                return model

        return None

    def get_models_by_capability(self, capability: ModelCapability) -> List[ModelInfo]:
        """
        Get models that support a specific capability.
        
        Args:
            capability: Required capability
            
        Returns:
            List of models supporting the capability
        """
        models = self.get_models()

        return [model for model in models if capability in model.capabilities]

    def get_models_by_family(self, family: str) -> List[ModelInfo]:
        """
        Get models from a specific family.
        
        Args:
            family: Model family name
            
        Returns:
            List of models from the specified family
        """
        models = self.get_models()

        return [model for model in models if model.family == family]

    def validate_model_availability(self, model_name: str) -> ModelInfo:
        """
        Validate that a model is available and return its info.
        
        Args:
            model_name: Name of the model to validate
            
        Returns:
            ModelInfo for the validated model
            
        Raises:
            ModelNotAvailableError: If model is not available
        """
        model = self.get_model_by_name(model_name)

        if model is None:
            available_models = [m.name for m in self.get_models()]
            raise ModelNotAvailableError(model_name, available_models)

        self.logger.debug("Model validated", model_name=model_name, family=model.family)
        return model

    def get_best_model_for_capability(
        self,
        capability: ModelCapability,
        prefer_smaller: bool = False
    ) -> Optional[ModelInfo]:
        """
        Get the best available model for a specific capability.
        
        Args:
            capability: Required capability
            prefer_smaller: If True, prefer smaller models for faster inference
            
        Returns:
            Best model for the capability, or None if none available
        """
        models = self.get_models_by_capability(capability)

        if not models:
            return None

        # Sort by size (smaller first if prefer_smaller, larger first otherwise)
        models_sorted = sorted(models, key=lambda m: m.size, reverse=not prefer_smaller)

        # Prefer models with parameter size information (more reliable)
        models_with_params = [m for m in models_sorted if m.parameter_size]
        if models_with_params:
            return models_with_params[0]

        # Fallback to first sorted model
        return models_sorted[0]

    def clear_cache(self) -> None:
        """Clear cached model data."""
        with self._cache_lock:
            self._cache = None
            self._cache_timestamp = None
            self.logger.debug("Model cache cleared")

    def get_cache_info(self) -> Dict[str, any]:
        """
        Get information about the current cache state.
        
        Returns:
            Dictionary with cache information
        """
        with self._cache_lock:
            if self._cache is None or self._cache_timestamp is None:
                return {"cached": False, "model_count": 0, "age_minutes": 0}

            age = datetime.now() - self._cache_timestamp

            return {
                "cached": True,
                "model_count": len(self._cache),
                "age_minutes": age.total_seconds() / 60,
                "expires_in_minutes": max(0, self.CACHE_TTL_MINUTES - (age.total_seconds() / 60)),
                "cache_timestamp": self._cache_timestamp.isoformat()
            }
