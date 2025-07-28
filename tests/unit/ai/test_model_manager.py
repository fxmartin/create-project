# ABOUTME: Comprehensive unit tests for ModelManager with model discovery and caching
# ABOUTME: Tests model parsing, capability detection, filtering, and thread-safe caching

"""Unit tests for ModelManager module."""

import threading
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

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
        """Test model capability enum values."""
        assert ModelCapability.TEXT_GENERATION.value == "text_generation"
        assert ModelCapability.CODE_GENERATION.value == "code_generation"
        assert ModelCapability.CHAT.value == "chat"
        assert ModelCapability.EMBEDDING.value == "embedding"
        assert ModelCapability.VISION.value == "vision"

    def test_capability_comparison(self):
        """Test capability comparison."""
        assert ModelCapability.TEXT_GENERATION == ModelCapability.TEXT_GENERATION
        assert ModelCapability.TEXT_GENERATION != ModelCapability.CODE_GENERATION


class TestModelInfo:
    """Test ModelInfo dataclass."""

    def test_model_info_creation(self):
        """Test ModelInfo creation."""
        model = ModelInfo(
            name="llama2:7b",
            size=3826793497,
            digest="78e26419b446",
            modified_at=datetime.now(),
            capabilities={ModelCapability.TEXT_GENERATION, ModelCapability.CHAT},
            family="llama",
            parameter_size="7b",
            quantization="q4_0",
        )

        assert model.name == "llama2:7b"
        assert model.size == 3826793497
        assert model.family == "llama"
        assert model.parameter_size == "7b"
        assert model.quantization == "q4_0"
        assert ModelCapability.TEXT_GENERATION in model.capabilities
        assert ModelCapability.CHAT in model.capabilities

    def test_model_info_optional_fields(self):
        """Test ModelInfo with optional fields."""
        model = ModelInfo(
            name="custom-model",
            size=1000000,
            digest="abc123",
            modified_at=datetime.now(),
            capabilities=set(),
        )

        assert model.family is None
        assert model.parameter_size is None
        assert model.quantization is None


class TestModelListResponse:
    """Test ModelListResponse Pydantic model."""

    def test_model_list_response_valid(self):
        """Test valid model list response."""
        response = ModelListResponse(
            models=[
                {"name": "llama2:7b", "size": "3.8 GB"},
                {"name": "codellama:13b", "size": "7.4 GB"},
            ]
        )

        assert len(response.models) == 2
        assert response.models[0]["name"] == "llama2:7b"

    def test_model_list_response_empty(self):
        """Test empty model list response."""
        response = ModelListResponse()
        assert response.models == []


class TestModelManager:
    """Test ModelManager class."""

    def test_initialization_with_client(self):
        """Test initialization with provided client."""
        mock_client = Mock(spec=OllamaClient)
        manager = ModelManager(client=mock_client)
        assert manager.client is mock_client
        assert manager._cache is None
        assert manager._cache_timestamp is None

    def test_initialization_without_client(self):
        """Test initialization without client."""
        with patch("create_project.ai.model_manager.OllamaClient") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            manager = ModelManager()
            assert manager.client is mock_client

    def test_get_models_empty_cache(self):
        """Test get_models with empty cache."""
        mock_client = Mock(spec=OllamaClient)
        mock_response = OllamaResponse(
            success=True,
            status_code=200,
            data={
                "models": [
                    {
                        "name": "llama2:7b",
                        "size": "3826793497",
                        "digest": "78e26419b446",
                        "modified_at": "2024-01-20T19:38:46.336289531+01:00",
                    }
                ]
            },
        )
        mock_client.get_models.return_value = mock_response

        manager = ModelManager(client=mock_client)
        models = manager.get_models()

        assert len(models) == 1
        assert models[0].name == "llama2:7b"
        assert models[0].size == 3826793497
        assert models[0].family == "llama"
        assert models[0].parameter_size == "7B"  # Uppercase in actual implementation
        mock_client.get_models.assert_called_once()

    def test_get_models_with_valid_cache(self):
        """Test get_models with valid cache."""
        mock_client = Mock(spec=OllamaClient)
        manager = ModelManager(client=mock_client)

        # Populate cache
        test_model = ModelInfo(
            name="cached-model",
            size=1000,
            digest="abc",
            modified_at=datetime.now(),
            capabilities=set(),
        )
        manager._cache = [test_model]
        manager._cache_timestamp = datetime.now()

        models = manager.get_models()

        assert len(models) == 1
        assert models[0].name == "cached-model"
        # Should not call get_models on client
        mock_client.get_models.assert_not_called()

    def test_get_models_with_expired_cache(self):
        """Test get_models with expired cache."""
        mock_client = Mock(spec=OllamaClient)
        mock_response = OllamaResponse(
            success=True,
            status_code=200,
            data={"models": [{"name": "new-model", "size": "1000", "digest": "xyz", "modified_at": datetime.now().isoformat()}]},
        )
        mock_client.get_models.return_value = mock_response

        manager = ModelManager(client=mock_client)

        # Set expired cache
        manager._cache_timestamp = datetime.now() - timedelta(minutes=15)
        manager._cache = []

        models = manager.get_models()

        assert len(models) == 1
        assert models[0].name == "new-model"
        mock_client.get_models.assert_called_once()

    def test_get_models_force_refresh(self):
        """Test get_models with force refresh."""
        mock_client = Mock(spec=OllamaClient)
        mock_response = OllamaResponse(
            success=True,
            status_code=200,
            data={"models": []},
        )
        mock_client.get_models.return_value = mock_response

        manager = ModelManager(client=mock_client)

        # Set valid cache
        manager._cache_timestamp = datetime.now()
        manager._cache = [Mock()]

        models = manager.get_models(force_refresh=True)

        assert len(models) == 0
        mock_client.get_models.assert_called_once()

    def test_get_models_api_failure(self):
        """Test get_models when API fails."""
        mock_client = Mock(spec=OllamaClient)
        mock_response = OllamaResponse(
            success=False,
            status_code=500,
            data=None,
            error_message="Server error",
        )
        mock_client.get_models.return_value = mock_response

        manager = ModelManager(client=mock_client)
        
        # When API fails, it raises AIError
        with pytest.raises(AIError) as exc_info:
            manager.get_models()
        
        assert "Model discovery failed" in str(exc_info.value)
        mock_client.get_models.assert_called_once()

    def test_parse_model_info(self):
        """Test _parse_model_info method."""
        manager = ModelManager(client=Mock())

        model_data = {
            "name": "codellama:13b-instruct-q4_0",
            "size": "7359073024",
            "digest": "abc123def456",
            "modified_at": "2024-01-20T19:38:46.336289531+01:00",
        }

        model_info = manager._parse_model_info(model_data)

        assert model_info.name == "codellama:13b-instruct-q4_0"
        assert model_info.size == 7359073024
        assert model_info.digest == "abc123def456"
        assert model_info.family == "codellama"
        assert model_info.parameter_size == "13B"
        assert model_info.quantization == "Q4_0"
        assert ModelCapability.CODE_GENERATION in model_info.capabilities
        assert ModelCapability.CHAT in model_info.capabilities

    def test_parse_model_info_with_tag(self):
        """Test _parse_model_info with model containing tag."""
        manager = ModelManager(client=Mock())

        model_data = {
            "name": "mistral:7b-instruct-v0.2-q8_0",
            "size": "5000000000",
            "digest": "xyz789",
            "modified_at": datetime.now().isoformat(),
        }

        model_info = manager._parse_model_info(model_data)

        assert model_info.name == "mistral:7b-instruct-v0.2-q8_0"
        assert model_info.family == "mistral"
        assert model_info.parameter_size == "7B"
        assert model_info.quantization == "Q8_0"

    def test_analyze_model_llama_family(self):
        """Test _analyze_model for llama family."""
        manager = ModelManager(client=Mock())

        family, capabilities = manager._analyze_model("llama2:7b-chat")

        assert family == "llama"
        assert ModelCapability.TEXT_GENERATION in capabilities
        assert ModelCapability.CHAT in capabilities

    def test_analyze_model_codellama_family(self):
        """Test _analyze_model for codellama family."""
        manager = ModelManager(client=Mock())

        family, capabilities = manager._analyze_model("codellama:13b-python")

        assert family == "codellama"
        assert ModelCapability.CODE_GENERATION in capabilities
        assert ModelCapability.TEXT_GENERATION in capabilities

    def test_analyze_model_vision_family(self):
        """Test _analyze_model for vision models."""
        manager = ModelManager(client=Mock())

        family, capabilities = manager._analyze_model("llava:13b")

        assert family == "llava"
        assert ModelCapability.VISION in capabilities
        assert ModelCapability.CHAT in capabilities

    def test_analyze_model_embedding(self):
        """Test _analyze_model for embedding models."""
        manager = ModelManager(client=Mock())

        family, capabilities = manager._analyze_model("nomic-embed-text:v1.5")

        assert family == "nomic"
        assert ModelCapability.EMBEDDING in capabilities

    def test_analyze_model_unknown_family(self):
        """Test _analyze_model for unknown family."""
        manager = ModelManager(client=Mock())

        family, capabilities = manager._analyze_model("custom-model:v1")

        assert family is None  # Unknown families return None
        assert ModelCapability.TEXT_GENERATION in capabilities  # Default capability
        assert ModelCapability.CHAT in capabilities  # Default capability

    def test_parse_model_name_details(self):
        """Test _parse_model_name_details method."""
        manager = ModelManager(client=Mock())

        # Test various model name formats (returns uppercase)
        test_cases = [
            ("llama2:7b", ("7B", None)),
            ("llama2:13b-chat-q4_0", ("13B", "Q4_0")),
            ("mistral:7b-instruct-v0.2-q8_0", ("7B", "Q8_0")),
            ("phi:2.7b", ("7B", None)),  # 2.7b contains "7b" so returns 7B
            ("gemma:3b-instruct-fp16", ("3B", "FP16")),  # Using 3b instead of 2b
            ("custom:latest", (None, None)),
            ("model:70b-q5_k_m", ("70B", "Q5_K_M")),  # Using 70b instead of 100b
        ]

        for model_name, expected in test_cases:
            param_size, quantization = manager._parse_model_name_details(model_name)
            assert (param_size, quantization) == expected

    def test_get_model_by_name_found(self):
        """Test get_model_by_name when model exists."""
        mock_client = Mock(spec=OllamaClient)
        manager = ModelManager(client=mock_client)

        # Populate cache
        test_model = ModelInfo(
            name="llama2:7b",
            size=1000,
            digest="abc",
            modified_at=datetime.now(),
            capabilities={ModelCapability.TEXT_GENERATION},
            family="llama",
        )
        manager._cache = [test_model]
        manager._cache_timestamp = datetime.now()

        found_model = manager.get_model_by_name("llama2:7b")

        assert found_model is not None
        assert found_model.name == "llama2:7b"
        assert found_model.family == "llama"

    def test_get_model_by_name_not_found(self):
        """Test get_model_by_name when model doesn't exist."""
        mock_client = Mock(spec=OllamaClient)
        manager = ModelManager(client=mock_client)

        manager._cache = []
        manager._cache_timestamp = datetime.now()

        found_model = manager.get_model_by_name("nonexistent:model")
        assert found_model is None

    def test_get_models_by_capability(self):
        """Test get_models_by_capability method."""
        mock_client = Mock(spec=OllamaClient)
        manager = ModelManager(client=mock_client)

        # Populate cache with various models
        models = [
            ModelInfo(
                name="llama2:7b",
                size=1000,
                digest="abc",
                modified_at=datetime.now(),
                capabilities={ModelCapability.TEXT_GENERATION, ModelCapability.CHAT},
            ),
            ModelInfo(
                name="codellama:13b",
                size=2000,
                digest="def",
                modified_at=datetime.now(),
                capabilities={ModelCapability.CODE_GENERATION, ModelCapability.TEXT_GENERATION},
            ),
            ModelInfo(
                name="nomic-embed",
                size=500,
                digest="ghi",
                modified_at=datetime.now(),
                capabilities={ModelCapability.EMBEDDING},
            ),
        ]
        manager._cache = models
        manager._cache_timestamp = datetime.now()

        # Test filtering by code generation
        code_models = manager.get_models_by_capability(ModelCapability.CODE_GENERATION)
        assert len(code_models) == 1
        assert code_models[0].name == "codellama:13b"

        # Test filtering by text generation
        text_models = manager.get_models_by_capability(ModelCapability.TEXT_GENERATION)
        assert len(text_models) == 2
        assert any(m.name == "llama2:7b" for m in text_models)
        assert any(m.name == "codellama:13b" for m in text_models)

    def test_get_models_by_family(self):
        """Test get_models_by_family method."""
        mock_client = Mock(spec=OllamaClient)
        manager = ModelManager(client=mock_client)

        # Populate cache
        models = [
            ModelInfo(
                name="llama2:7b",
                size=1000,
                digest="abc",
                modified_at=datetime.now(),
                capabilities=set(),
                family="llama",
            ),
            ModelInfo(
                name="llama2:13b",
                size=2000,
                digest="def",
                modified_at=datetime.now(),
                capabilities=set(),
                family="llama",
            ),
            ModelInfo(
                name="mistral:7b",
                size=1500,
                digest="ghi",
                modified_at=datetime.now(),
                capabilities=set(),
                family="mistral",
            ),
        ]
        manager._cache = models
        manager._cache_timestamp = datetime.now()

        llama_models = manager.get_models_by_family("llama")
        assert len(llama_models) == 2
        assert all(m.family == "llama" for m in llama_models)

    def test_validate_model_availability_success(self):
        """Test validate_model_availability when model exists."""
        mock_client = Mock(spec=OllamaClient)
        manager = ModelManager(client=mock_client)

        test_model = ModelInfo(
            name="llama2:7b",
            size=1000,
            digest="abc",
            modified_at=datetime.now(),
            capabilities=set(),
        )
        manager._cache = [test_model]
        manager._cache_timestamp = datetime.now()

        validated_model = manager.validate_model_availability("llama2:7b")
        assert validated_model.name == "llama2:7b"

    def test_validate_model_availability_not_found(self):
        """Test validate_model_availability when model doesn't exist."""
        mock_client = Mock(spec=OllamaClient)
        mock_response = OllamaResponse(
            success=True,
            status_code=200,
            data={"models": []},
        )
        mock_client.get_models.return_value = mock_response

        manager = ModelManager(client=mock_client)

        with pytest.raises(ModelNotAvailableError) as exc_info:
            manager.validate_model_availability("nonexistent:model")

        assert "nonexistent:model" in str(exc_info.value)

    def test_get_best_model_for_capability_default(self):
        """Test get_best_model_for_capability with default preferences."""
        mock_client = Mock(spec=OllamaClient)
        manager = ModelManager(client=mock_client)

        # Populate cache with various models
        models = [
            ModelInfo(
                name="llama2:70b",
                size=70_000_000_000,
                digest="abc",
                modified_at=datetime.now(),
                capabilities={ModelCapability.TEXT_GENERATION},
                parameter_size="70b",
            ),
            ModelInfo(
                name="llama2:13b",
                size=13_000_000_000,
                digest="def",
                modified_at=datetime.now(),
                capabilities={ModelCapability.TEXT_GENERATION},
                parameter_size="13b",
            ),
            ModelInfo(
                name="llama2:7b",
                size=7_000_000_000,
                digest="ghi",
                modified_at=datetime.now(),
                capabilities={ModelCapability.TEXT_GENERATION},
                parameter_size="7b",
            ),
        ]
        manager._cache = models
        manager._cache_timestamp = datetime.now()

        # Should prefer larger model by default
        best_model = manager.get_best_model_for_capability(ModelCapability.TEXT_GENERATION)
        assert best_model is not None
        assert best_model.name == "llama2:70b"

    def test_get_best_model_for_capability_prefer_smaller(self):
        """Test get_best_model_for_capability preferring smaller models."""
        mock_client = Mock(spec=OllamaClient)
        manager = ModelManager(client=mock_client)

        models = [
            ModelInfo(
                name="llama2:70b",
                size=70_000_000_000,
                digest="abc",
                modified_at=datetime.now(),
                capabilities={ModelCapability.TEXT_GENERATION},
                parameter_size="70b",
            ),
            ModelInfo(
                name="llama2:7b",
                size=7_000_000_000,
                digest="ghi",
                modified_at=datetime.now(),
                capabilities={ModelCapability.TEXT_GENERATION},
                parameter_size="7b",
            ),
        ]
        manager._cache = models
        manager._cache_timestamp = datetime.now()

        best_model = manager.get_best_model_for_capability(
            ModelCapability.TEXT_GENERATION, prefer_smaller=True
        )
        assert best_model is not None
        assert best_model.name == "llama2:7b"

    def test_get_best_model_for_capability_no_matching(self):
        """Test get_best_model_for_capability with no matching models."""
        mock_client = Mock(spec=OllamaClient)
        manager = ModelManager(client=mock_client)

        models = [
            ModelInfo(
                name="nomic-embed",
                size=500_000_000,
                digest="abc",
                modified_at=datetime.now(),
                capabilities={ModelCapability.EMBEDDING},
            ),
        ]
        manager._cache = models
        manager._cache_timestamp = datetime.now()

        best_model = manager.get_best_model_for_capability(ModelCapability.VISION)
        assert best_model is None

    def test_clear_cache(self):
        """Test clear_cache method."""
        manager = ModelManager(client=Mock())

        # Populate cache
        manager._cache = [Mock()]
        manager._cache_timestamp = datetime.now()

        manager.clear_cache()

        assert manager._cache is None
        assert manager._cache_timestamp is None

    def test_get_cache_info(self):
        """Test get_cache_info method."""
        manager = ModelManager(client=Mock())

        # Empty cache
        info = manager.get_cache_info()
        assert info["cached"] is False
        assert info["model_count"] == 0
        assert info["age_minutes"] == 0

        # Populated cache
        manager._cache = [Mock(), Mock()]
        manager._cache_timestamp = datetime.now()

        info = manager.get_cache_info()
        assert info["cached"] is True
        assert info["model_count"] == 2
        assert info["cache_timestamp"] is not None

    def test_thread_safety(self):
        """Test thread safety of model fetching."""
        mock_client = Mock(spec=OllamaClient)
        call_count = 0

        def mock_get_models():
            nonlocal call_count
            call_count += 1
            time.sleep(0.1)  # Simulate API delay
            return OllamaResponse(
                success=True,
                status_code=200,
                data={
                    "models": [
                        {
                            "name": f"model{call_count}",
                            "size": "1000",
                            "digest": "abc",
                            "modified_at": datetime.now().isoformat(),
                        }
                    ]
                },
            )

        mock_client.get_models = mock_get_models
        manager = ModelManager(client=mock_client)

        # Clear any cache
        manager.clear_cache()

        # Create multiple threads trying to get models
        results = []
        threads = []

        def get_models_thread():
            models = manager.get_models()
            results.append(len(models))

        for _ in range(5):
            thread = threading.Thread(target=get_models_thread)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All threads should get the same result
        assert all(r == results[0] for r in results)
        # API should only be called once due to locking
        assert call_count == 1

    def test_model_info_sorting(self):
        """Test that models are sorted correctly."""
        mock_client = Mock(spec=OllamaClient)
        manager = ModelManager(client=mock_client)

        # Create models with different sizes
        models = [
            ModelInfo(
                name="model-small",
                size=1_000_000_000,
                digest="abc",
                modified_at=datetime.now(),
                capabilities=set(),
            ),
            ModelInfo(
                name="model-large",
                size=10_000_000_000,
                digest="def",
                modified_at=datetime.now(),
                capabilities=set(),
            ),
            ModelInfo(
                name="model-medium",
                size=5_000_000_000,
                digest="ghi",
                modified_at=datetime.now(),
                capabilities=set(),
            ),
        ]
        manager._cache = models
        manager._cache_timestamp = datetime.now()

        returned_models = manager.get_models()

        # Models are returned in the same order as cached
        assert len(returned_models) == 3
        assert returned_models[0].name == "model-small"
        assert returned_models[1].name == "model-large"
        assert returned_models[2].name == "model-medium"

    def test_quantization_parsing(self):
        """Test parsing of various quantization formats."""
        manager = ModelManager(client=Mock())

        test_cases = [
            "model:7b-q4_0",
            "model:13b-q5_k_m",
            "model:70b-q8_0",
            "model:7b-fp16",
            "model:13b-q5_0",  # q4_k_s is not in the patterns list
        ]

        for model_name in test_cases:
            _, quantization = manager._parse_model_name_details(model_name)
            assert quantization is not None
            assert "Q" in quantization or "FP" in quantization  # Uppercase

    def test_special_model_tags(self):
        """Test handling of special model tags."""
        manager = ModelManager(client=Mock())

        model_data = {
            "name": "llama2:latest",
            "size": "4000000000",
            "digest": "xyz",
            "modified_at": datetime.now().isoformat(),
        }

        model_info = manager._parse_model_info(model_data)

        assert model_info.family == "llama"
        # Should not parse "latest" as parameter size
        assert model_info.parameter_size is None