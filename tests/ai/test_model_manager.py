# ABOUTME: Comprehensive tests for model discovery and management with caching
# ABOUTME: Tests model parsing, capability detection, filtering, and cache behavior

import threading
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from create_project.ai.exceptions import AIError, ModelNotAvailableError
from create_project.ai.model_manager import (
    ModelCapability,
    ModelInfo,
    ModelListResponse,
    ModelManager,
)
from create_project.ai.ollama_client import OllamaClient, OllamaResponse


class TestModelCapability:
    """Test ModelCapability enum."""

    def test_capability_values(self):
        """Test that all expected capabilities exist."""
        assert ModelCapability.TEXT_GENERATION.value == "text_generation"
        assert ModelCapability.CODE_GENERATION.value == "code_generation"
        assert ModelCapability.CHAT.value == "chat"
        assert ModelCapability.EMBEDDING.value == "embedding"
        assert ModelCapability.VISION.value == "vision"


class TestModelInfo:
    """Test ModelInfo dataclass."""

    def test_model_info_creation(self):
        """Test basic ModelInfo creation."""
        capabilities = {ModelCapability.TEXT_GENERATION, ModelCapability.CHAT}
        modified_at = datetime.now()

        model = ModelInfo(
            name="llama2:7b",
            size=3826793677,
            digest="sha256:1234567890",
            modified_at=modified_at,
            capabilities=capabilities,
            family="llama",
            parameter_size="7B",
            quantization="Q4_0",
        )

        assert model.name == "llama2:7b"
        assert model.size == 3826793677
        assert model.digest == "sha256:1234567890"
        assert model.modified_at == modified_at
        assert model.capabilities == capabilities
        assert model.family == "llama"
        assert model.parameter_size == "7B"
        assert model.quantization == "Q4_0"

    def test_model_info_optional_fields(self):
        """Test ModelInfo with only required fields."""
        model = ModelInfo(
            name="unknown:latest",
            size=1000,
            digest="sha256:abcd",
            modified_at=datetime.now(),
            capabilities={ModelCapability.TEXT_GENERATION},
        )

        assert model.family is None
        assert model.parameter_size is None
        assert model.quantization is None


class TestModelListResponse:
    """Test Pydantic model for API responses."""

    def test_empty_response(self):
        """Test parsing empty model list response."""
        response = ModelListResponse()
        assert response.models == []

    def test_model_list_response(self):
        """Test parsing model list response."""
        data = {
            "models": [
                {
                    "name": "llama2:7b",
                    "size": "3826793677",
                    "digest": "sha256:1234567890",
                    "modified_at": "2024-01-01T12:00:00Z",
                }
            ]
        }

        response = ModelListResponse(**data)
        assert len(response.models) == 1
        assert response.models[0]["name"] == "llama2:7b"


class TestModelManager:
    """Test ModelManager class."""

    def test_initialization(self):
        """Test ModelManager initialization."""
        mock_client = Mock(spec=OllamaClient)
        manager = ModelManager(client=mock_client)

        assert manager.client is mock_client
        assert manager._cache is None
        assert manager._cache_timestamp is None

    def test_initialization_default_client(self):
        """Test ModelManager initialization with default client."""
        with patch("create_project.ai.model_manager.OllamaClient") as mock_client_class:
            manager = ModelManager()
            mock_client_class.assert_called_once_with()
            assert manager.client is mock_client_class.return_value


class TestModelParsing:
    """Test model information parsing."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = Mock(spec=OllamaClient)
        self.manager = ModelManager(client=self.mock_client)

    def test_parse_llama_model(self):
        """Test parsing Llama model information."""
        model_data = {
            "name": "llama2:7b-chat",
            "size": "3826793677",
            "digest": "sha256:1234567890abcdef",
            "modified_at": "2024-01-01T12:00:00Z",
        }

        model = self.manager._parse_model_info(model_data)

        assert model.name == "llama2:7b-chat"
        assert model.size == 3826793677
        assert model.digest == "sha256:1234567890abcdef"
        assert model.family == "llama"
        assert model.parameter_size == "7B"
        assert ModelCapability.TEXT_GENERATION in model.capabilities
        assert ModelCapability.CHAT in model.capabilities
        assert ModelCapability.CODE_GENERATION in model.capabilities

    def test_parse_codellama_model(self):
        """Test parsing CodeLlama model information."""
        model_data = {
            "name": "codellama:13b-instruct-q4_0",
            "size": "7365960935",
            "digest": "sha256:abcdef1234567890",
            "modified_at": "2024-01-02T10:30:00Z",
        }

        model = self.manager._parse_model_info(model_data)

        assert model.name == "codellama:13b-instruct-q4_0"
        assert model.family == "codellama"
        assert model.parameter_size == "13B"
        assert model.quantization == "Q4_0"
        assert ModelCapability.CODE_GENERATION in model.capabilities
        assert ModelCapability.TEXT_GENERATION in model.capabilities

    def test_parse_embedding_model(self):
        """Test parsing embedding model information."""
        model_data = {
            "name": "nomic-embed-text:latest",
            "size": "274301056",
            "digest": "sha256:fedcba0987654321",
            "modified_at": "2024-01-03T08:15:00Z",
        }

        model = self.manager._parse_model_info(model_data)

        assert model.name == "nomic-embed-text:latest"
        assert model.family == "nomic"
        assert ModelCapability.EMBEDDING in model.capabilities
        assert len(model.capabilities) == 1  # Should only have embedding capability

    def test_parse_vision_model(self):
        """Test parsing vision model information."""
        model_data = {
            "name": "llava:7b",
            "size": "4109109248",
            "digest": "sha256:vision123456789",
            "modified_at": "2024-01-04T14:45:00Z",
        }

        model = self.manager._parse_model_info(model_data)

        assert model.name == "llava:7b"
        assert model.family == "llava"
        assert model.parameter_size == "7B"
        assert ModelCapability.VISION in model.capabilities
        assert ModelCapability.TEXT_GENERATION in model.capabilities
        assert ModelCapability.CHAT in model.capabilities

    def test_parse_unknown_model(self):
        """Test parsing unknown model falls back to defaults."""
        model_data = {
            "name": "unknown-model:latest",
            "size": "1000000000",
            "digest": "sha256:unknown123456",
            "modified_at": "2024-01-05T16:20:00Z",
        }

        model = self.manager._parse_model_info(model_data)

        assert model.name == "unknown-model:latest"
        assert model.family is None
        assert model.parameter_size is None
        assert model.quantization is None
        assert ModelCapability.TEXT_GENERATION in model.capabilities
        assert ModelCapability.CHAT in model.capabilities

    def test_parse_invalid_model_data(self):
        """Test parsing invalid model data raises error."""
        # Missing required name field
        model_data = {
            "size": "1000000",
            "digest": "sha256:test",
            "modified_at": "2024-01-01T12:00:00Z",
        }

        with pytest.raises(ValueError, match="Model name is required"):
            self.manager._parse_model_info(model_data)

    def test_parse_model_with_invalid_size(self):
        """Test parsing model with invalid size defaults to 0."""
        model_data = {
            "name": "test:latest",
            "size": "invalid",
            "digest": "sha256:test",
            "modified_at": "2024-01-01T12:00:00Z",
        }

        model = self.manager._parse_model_info(model_data)
        assert model.size == 0

    def test_parse_model_with_invalid_timestamp(self):
        """Test parsing model with invalid timestamp uses current time."""
        model_data = {
            "name": "test:latest",
            "size": "1000000",
            "digest": "sha256:test",
            "modified_at": "invalid-timestamp",
        }

        before_parse = datetime.now()
        model = self.manager._parse_model_info(model_data)
        after_parse = datetime.now()

        # Should be close to current time
        assert before_parse <= model.modified_at <= after_parse


class TestModelFetching:
    """Test model fetching and caching."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = Mock(spec=OllamaClient)
        self.manager = ModelManager(client=self.mock_client)

    def test_fetch_models_success(self):
        """Test successful model fetching."""
        # Mock successful API response
        response_data = {
            "models": [
                {
                    "name": "llama2:7b",
                    "size": "3826793677",
                    "digest": "sha256:1234567890",
                    "modified_at": "2024-01-01T12:00:00Z",
                },
                {
                    "name": "codellama:13b",
                    "size": "7365960935",
                    "digest": "sha256:abcdef1234",
                    "modified_at": "2024-01-02T10:30:00Z",
                },
            ]
        }

        mock_response = OllamaResponse(
            success=True, status_code=200, data=response_data
        )
        self.mock_client.get_models.return_value = mock_response

        models = self.manager.get_models()

        assert len(models) == 2
        assert models[0].name == "llama2:7b"
        assert models[0].family == "llama"
        assert models[1].name == "codellama:13b"
        assert models[1].family == "codellama"

    def test_fetch_models_api_error(self):
        """Test handling of API errors during model fetching."""
        mock_response = OllamaResponse(
            success=False, status_code=500, data=None, error_message="Server error"
        )
        self.mock_client.get_models.return_value = mock_response

        with pytest.raises(AIError, match="Failed to fetch models"):
            self.manager.get_models()

    def test_fetch_models_client_exception(self):
        """Test handling of client exceptions during model fetching."""
        self.mock_client.get_models.side_effect = Exception("Connection failed")

        with pytest.raises(AIError, match="Model discovery failed"):
            self.manager.get_models()

    def test_caching_behavior(self):
        """Test that model list is cached properly."""
        # Mock successful API response
        response_data = {
            "models": [
                {
                    "name": "test:latest",
                    "size": "1000",
                    "digest": "sha256:test",
                    "modified_at": "2024-01-01T12:00:00Z",
                }
            ]
        }
        mock_response = OllamaResponse(
            success=True, status_code=200, data=response_data
        )
        self.mock_client.get_models.return_value = mock_response

        # First call should fetch from API
        models1 = self.manager.get_models()
        assert self.mock_client.get_models.call_count == 1

        # Second call should use cache
        models2 = self.manager.get_models()
        assert self.mock_client.get_models.call_count == 1  # Still 1, not called again

        # Results should be equal but different objects (copy)
        assert len(models1) == len(models2)
        assert models1[0].name == models2[0].name
        assert models1 is not models2  # Different objects due to copy()

    def test_force_refresh_bypasses_cache(self):
        """Test that force refresh bypasses cache."""
        response_data = {
            "models": [
                {
                    "name": "test:latest",
                    "size": "1000",
                    "digest": "sha256:test",
                    "modified_at": "2024-01-01T12:00:00Z",
                }
            ]
        }
        mock_response = OllamaResponse(
            success=True, status_code=200, data=response_data
        )
        self.mock_client.get_models.return_value = mock_response

        # First call
        self.manager.get_models()
        assert self.mock_client.get_models.call_count == 1

        # Force refresh should bypass cache
        self.manager.get_models(force_refresh=True)
        assert self.mock_client.get_models.call_count == 2

    def test_cache_expiry(self):
        """Test that cache expires after TTL."""
        response_data = {
            "models": [
                {
                    "name": "test:latest",
                    "size": "1000",
                    "digest": "sha256:test",
                    "modified_at": "2024-01-01T12:00:00Z",
                }
            ]
        }
        mock_response = OllamaResponse(
            success=True, status_code=200, data=response_data
        )
        self.mock_client.get_models.return_value = mock_response

        # Manually set old cache timestamp
        self.manager._cache = []
        self.manager._cache_timestamp = datetime.now() - timedelta(
            minutes=15
        )  # Expired

        # Should trigger fresh fetch due to expired cache
        self.manager.get_models()
        assert self.mock_client.get_models.call_count == 1


class TestModelQueries:
    """Test model query and filtering methods."""

    def setup_method(self):
        """Set up test fixtures with sample models."""
        self.mock_client = Mock(spec=OllamaClient)
        self.manager = ModelManager(client=self.mock_client)

        # Create sample models
        self.sample_models = [
            ModelInfo(
                name="llama2:7b",
                size=3826793677,
                digest="sha256:1234567890",
                modified_at=datetime.now(),
                capabilities={ModelCapability.TEXT_GENERATION, ModelCapability.CHAT},
                family="llama",
                parameter_size="7B",
            ),
            ModelInfo(
                name="codellama:13b",
                size=7365960935,
                digest="sha256:abcdef1234",
                modified_at=datetime.now(),
                capabilities={
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.TEXT_GENERATION,
                },
                family="codellama",
                parameter_size="13B",
            ),
            ModelInfo(
                name="nomic-embed-text:latest",
                size=274301056,
                digest="sha256:fedcba0987",
                modified_at=datetime.now(),
                capabilities={ModelCapability.EMBEDDING},
                family="nomic",
            ),
        ]

        # Mock the get_models method to return sample models
        self.manager._cache = self.sample_models
        self.manager._cache_timestamp = datetime.now()

    def test_get_model_by_name_found(self):
        """Test finding a model by name."""
        model = self.manager.get_model_by_name("llama2:7b")

        assert model is not None
        assert model.name == "llama2:7b"
        assert model.family == "llama"

    def test_get_model_by_name_not_found(self):
        """Test searching for non-existent model."""
        model = self.manager.get_model_by_name("nonexistent:model")

        assert model is None

    def test_get_models_by_capability(self):
        """Test filtering models by capability."""
        # Test TEXT_GENERATION capability
        text_models = self.manager.get_models_by_capability(
            ModelCapability.TEXT_GENERATION
        )
        assert len(text_models) == 2  # llama2 and codellama

        # Test CODE_GENERATION capability
        code_models = self.manager.get_models_by_capability(
            ModelCapability.CODE_GENERATION
        )
        assert len(code_models) == 1  # only codellama
        assert code_models[0].name == "codellama:13b"

        # Test EMBEDDING capability
        embed_models = self.manager.get_models_by_capability(ModelCapability.EMBEDDING)
        assert len(embed_models) == 1  # only nomic-embed
        assert embed_models[0].name == "nomic-embed-text:latest"

        # Test non-existent capability
        vision_models = self.manager.get_models_by_capability(ModelCapability.VISION)
        assert len(vision_models) == 0

    def test_get_models_by_family(self):
        """Test filtering models by family."""
        llama_models = self.manager.get_models_by_family("llama")
        assert len(llama_models) == 1
        assert llama_models[0].name == "llama2:7b"

        codellama_models = self.manager.get_models_by_family("codellama")
        assert len(codellama_models) == 1
        assert codellama_models[0].name == "codellama:13b"

        nonexistent_models = self.manager.get_models_by_family("nonexistent")
        assert len(nonexistent_models) == 0

    def test_validate_model_availability_success(self):
        """Test successful model validation."""
        model = self.manager.validate_model_availability("llama2:7b")

        assert model.name == "llama2:7b"
        assert model.family == "llama"

    def test_validate_model_availability_failure(self):
        """Test model validation failure."""
        with pytest.raises(ModelNotAvailableError) as exc_info:
            self.manager.validate_model_availability("nonexistent:model")

        error = exc_info.value
        assert error.model_name == "nonexistent:model"
        assert "llama2:7b" in error.available_models
        assert "codellama:13b" in error.available_models

    def test_get_best_model_for_capability_larger_preferred(self):
        """Test getting best model for capability (larger preferred)."""
        best_model = self.manager.get_best_model_for_capability(
            ModelCapability.TEXT_GENERATION, prefer_smaller=False
        )

        assert best_model is not None
        assert best_model.name == "codellama:13b"  # Larger model preferred

    def test_get_best_model_for_capability_smaller_preferred(self):
        """Test getting best model for capability (smaller preferred)."""
        best_model = self.manager.get_best_model_for_capability(
            ModelCapability.TEXT_GENERATION, prefer_smaller=True
        )

        assert best_model is not None
        assert best_model.name == "llama2:7b"  # Smaller model preferred

    def test_get_best_model_for_capability_none_available(self):
        """Test getting best model when none available."""
        best_model = self.manager.get_best_model_for_capability(ModelCapability.VISION)

        assert best_model is None


class TestCacheManagement:
    """Test cache management functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = Mock(spec=OllamaClient)
        self.manager = ModelManager(client=self.mock_client)

    def test_clear_cache(self):
        """Test cache clearing."""
        # Set up cache
        self.manager._cache = []
        self.manager._cache_timestamp = datetime.now()

        # Clear cache
        self.manager.clear_cache()

        assert self.manager._cache is None
        assert self.manager._cache_timestamp is None

    def test_get_cache_info_empty(self):
        """Test cache info when cache is empty."""
        info = self.manager.get_cache_info()

        assert info["cached"] is False
        assert info["model_count"] == 0
        assert info["age_minutes"] == 0

    def test_get_cache_info_populated(self):
        """Test cache info when cache is populated."""
        # Set up cache
        timestamp = datetime.now() - timedelta(minutes=5)
        self.manager._cache = [Mock(), Mock(), Mock()]  # 3 mock models
        self.manager._cache_timestamp = timestamp

        info = self.manager.get_cache_info()

        assert info["cached"] is True
        assert info["model_count"] == 3
        assert 4.9 <= info["age_minutes"] <= 5.1  # Approximately 5 minutes
        assert 4.9 <= info["expires_in_minutes"] <= 5.1  # Should expire in ~5 minutes
        assert info["cache_timestamp"] == timestamp.isoformat()


class TestThreadSafety:
    """Test thread safety of model manager."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = Mock(spec=OllamaClient)
        self.manager = ModelManager(client=self.mock_client)

    def test_concurrent_model_fetching(self):
        """Test concurrent model fetching is thread-safe."""

        # Mock API response with delay
        def slow_get_models():
            time.sleep(0.1)  # Simulate network delay
            return OllamaResponse(
                success=True,
                status_code=200,
                data={
                    "models": [
                        {
                            "name": "test:latest",
                            "size": "1000",
                            "digest": "sha256:test",
                            "modified_at": "2024-01-01T12:00:00Z",
                        }
                    ]
                },
            )

        self.mock_client.get_models.side_effect = slow_get_models

        results = []

        def fetch_models():
            models = self.manager.get_models()
            results.append(models)

        # Start multiple threads
        threads = [threading.Thread(target=fetch_models) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should only call API once due to caching
        assert self.mock_client.get_models.call_count == 1
        assert len(results) == 5

        # All results should have same content
        for result in results[1:]:
            assert len(result) == len(results[0])
            assert result[0].name == results[0][0].name
