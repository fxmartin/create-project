# ABOUTME: Comprehensive unit tests for OllamaClient HTTP client with singleton pattern
# ABOUTME: Tests sync/async operations, retry logic, error handling, and connection pooling

"""Unit tests for OllamaClient HTTP client."""

import asyncio
import json
import random
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx
import pytest

from create_project.ai.exceptions import (
    AIError,
    OllamaNotFoundError,
    ResponseTimeoutError,
)
from create_project.ai.ollama_client import (
    OllamaClient,
    OllamaResponse,
    RequestMethod,
    RetryConfig,
)


class TestRequestMethod:
    """Test RequestMethod enum."""

    def test_request_method_values(self):
        """Test request method enum values."""
        assert RequestMethod.GET.value == "GET"
        assert RequestMethod.POST.value == "POST"
        assert RequestMethod.PUT.value == "PUT"
        assert RequestMethod.DELETE.value == "DELETE"

    def test_request_method_comparison(self):
        """Test request method comparison."""
        assert RequestMethod.GET == RequestMethod.GET
        assert RequestMethod.GET != RequestMethod.POST


class TestRetryConfig:
    """Test RetryConfig dataclass."""

    def test_default_retry_config(self):
        """Test default retry configuration."""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 30.0
        assert config.exponential_base == 2.0
        assert config.jitter is True

    def test_custom_retry_config(self):
        """Test custom retry configuration."""
        config = RetryConfig(
            max_attempts=5,
            base_delay=0.5,
            max_delay=60.0,
            exponential_base=3.0,
            jitter=False,
        )
        assert config.max_attempts == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 60.0
        assert config.exponential_base == 3.0
        assert config.jitter is False


class TestOllamaResponse:
    """Test OllamaResponse dataclass."""

    def test_successful_response(self):
        """Test successful response creation."""
        response = OllamaResponse(
            success=True,
            status_code=200,
            data={"message": {"content": "Hello"}, "model": "llama2"},
            response_time=1.5,
        )
        assert response.success is True
        assert response.status_code == 200
        assert response.content == "Hello"
        assert response.error is None
        assert response.response_time == 1.5

    def test_failed_response(self):
        """Test failed response creation."""
        response = OllamaResponse(
            success=False,
            status_code=500,
            data=None,
            error_message="Internal server error",
        )
        assert response.success is False
        assert response.status_code == 500
        assert response.content is None
        assert response.error == "Internal server error"

    def test_content_extraction_patterns(self):
        """Test different content extraction patterns."""
        # Message content pattern
        response = OllamaResponse(
            success=True,
            status_code=200,
            data={"message": {"content": "Hello from message"}},
        )
        assert response.content == "Hello from message"

        # Response pattern
        response = OllamaResponse(
            success=True, status_code=200, data={"response": "Hello from response"}
        )
        assert response.content == "Hello from response"

        # Direct content pattern
        response = OllamaResponse(
            success=True, status_code=200, data={"content": "Hello from content"}
        )
        assert response.content == "Hello from content"

        # No matching pattern
        response = OllamaResponse(
            success=True, status_code=200, data={"other": "value"}
        )
        assert response.content is None


class TestOllamaClient:
    """Test OllamaClient class."""

    def setup_method(self):
        """Reset singleton before each test."""
        OllamaClient.reset_instance()

    def teardown_method(self):
        """Clean up after each test."""
        # Clean up any existing client instances
        if OllamaClient._instance:
            try:
                if hasattr(OllamaClient._instance, '_sync_client') and OllamaClient._instance._sync_client:
                    OllamaClient._instance._sync_client.close()
                if hasattr(OllamaClient._instance, '_async_client') and OllamaClient._instance._async_client:
                    # Can't await in teardown, just set to None
                    OllamaClient._instance._async_client = None
            except:
                pass
        OllamaClient.reset_instance()

    def test_singleton_pattern(self):
        """Test singleton pattern implementation."""
        client1 = OllamaClient(base_url="http://localhost:11434")
        client2 = OllamaClient(base_url="http://different:11434")
        
        # Should be the same instance
        assert client1 is client2
        # Base URL should not change after first initialization
        assert client1.base_url == "http://localhost:11434"
        assert client2.base_url == "http://localhost:11434"

    def test_initialization(self):
        """Test client initialization."""
        retry_config = RetryConfig(max_attempts=5)
        client = OllamaClient(
            base_url="http://test:11434", timeout=60.0, retry_config=retry_config
        )

        assert client.base_url == "http://test:11434"
        assert client.timeout == 60.0
        assert client.retry_config.max_attempts == 5
        assert client._initialized is True

    def test_default_initialization(self):
        """Test client with default values."""
        client = OllamaClient()
        
        assert client.base_url == "http://localhost:11434"
        assert client.timeout == OllamaClient.DEFAULT_TIMEOUT
        assert isinstance(client.retry_config, RetryConfig)

    @patch("create_project.ai.ollama_client.OllamaDetector")
    def test_is_available(self, mock_detector_class):
        """Test is_available property."""
        mock_detector = Mock()
        mock_status = Mock()
        mock_status.is_installed = True
        mock_status.is_running = True
        mock_detector.detect.return_value = mock_status
        mock_detector_class.return_value = mock_detector

        client = OllamaClient()
        assert client.is_available is True
        mock_detector.detect.assert_called_once()

    def test_sync_client_lazy_creation(self):
        """Test lazy creation of sync HTTP client."""
        client = OllamaClient()
        assert client._sync_client is None

        # Access sync_client property
        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            sync_client = client.sync_client
            assert sync_client is mock_client
            assert client._sync_client is mock_client

            # Subsequent access should return same client
            sync_client2 = client.sync_client
            assert sync_client2 is mock_client
            mock_client_class.assert_called_once()

    def test_async_client_lazy_creation(self):
        """Test lazy creation of async HTTP client."""
        client = OllamaClient()
        assert client._async_client is None

        # Access async_client property
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            async_client = client.async_client
            assert async_client is mock_client
            assert client._async_client is mock_client

            # Subsequent access should return same client
            async_client2 = client.async_client
            assert async_client2 is mock_client
            mock_client_class.assert_called_once()

    def test_calculate_delay(self):
        """Test delay calculation for retries."""
        client = OllamaClient()
        
        # Test with jitter enabled
        client.retry_config.jitter = True
        with patch("random.random", return_value=0.0):  # This will result in 0.5 multiplier
            delay = client._calculate_delay(0)
            # base_delay * (exponential_base ^ attempt) * (0.5 + random() * 0.5)
            # 1.0 * (2.0 ^ 0) * (0.5 + 0.0 * 0.5) = 0.5
            assert delay == 0.5

        # Test with jitter disabled
        client.retry_config.jitter = False
        delay = client._calculate_delay(2)
        # 1.0 * (2.0 ^ 2) = 4.0
        assert delay == 4.0

        # Test max delay capping
        delay = client._calculate_delay(10)
        assert delay == client.retry_config.max_delay

    def test_should_retry(self):
        """Test retry decision logic."""
        client = OllamaClient()

        # Should retry on connection error
        assert client._should_retry(None, httpx.ConnectError("Connection failed")) is True

        # Should retry on timeout
        assert client._should_retry(None, httpx.TimeoutException("Timeout")) is True

        # Should retry on 5xx status codes
        response = Mock(status_code=503)
        assert client._should_retry(response, None) is True

        # Should not retry on 4xx status codes
        response = Mock(status_code=404)
        assert client._should_retry(response, None) is False

        # Should not retry on other exceptions
        assert client._should_retry(None, ValueError("Other error")) is False

    @patch("httpx.Client.get")
    def test_synchronous_request_success(self, mock_get):
        """Test successful synchronous request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_response.content = b'{"result": "success"}'
        mock_get.return_value = mock_response

        client = OllamaClient()
        response = client.request(RequestMethod.GET, "test")

        assert response.success is True
        assert response.status_code == 200
        assert response.data == {"result": "success"}
        assert response.error is None
        mock_get.assert_called_once_with("/api/test", params=None, timeout=30.0)

    @patch("httpx.Client.get")
    def test_synchronous_request_with_retry(self, mock_get):
        """Test synchronous request with retry on failure."""
        # First attempt fails, second succeeds
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_response.content = b'{"result": "success"}'
        
        mock_get.side_effect = [
            httpx.ConnectError("Connection failed"),
            mock_response,
        ]

        client = OllamaClient()
        with patch("time.sleep"):  # Mock sleep to speed up test
            response = client.request(RequestMethod.GET, "test")

        assert response.success is True
        assert response.status_code == 200
        assert mock_get.call_count == 2

    @patch("httpx.Client.get")
    def test_synchronous_request_all_retries_fail(self, mock_get):
        """Test synchronous request when all retries fail."""
        mock_get.side_effect = httpx.ConnectError("Connection failed")

        client = OllamaClient()
        client.retry_config.max_attempts = 2

        with patch("time.sleep"):  # Mock sleep to speed up test
            with pytest.raises(OllamaNotFoundError) as exc_info:
                client.request(RequestMethod.GET, "test")

        assert str(exc_info.value) == "Unable to connect to Ollama service"
        assert mock_get.call_count == 2

    @patch("httpx.Client.get")
    def test_synchronous_request_json_error(self, mock_get):
        """Test synchronous request with JSON parsing error."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.text = "Invalid JSON response"
        mock_response.content = b"Invalid JSON response"
        mock_get.return_value = mock_response

        client = OllamaClient()
        response = client.request(RequestMethod.GET, "test")

        assert response.success is True  # Status code < 400 means success
        assert response.data == {"content": "Invalid JSON response"}

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_asynchronous_request_success(self, mock_get):
        """Test successful asynchronous request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={"result": "success"})
        mock_response.content = b'{"result": "success"}'
        mock_get.return_value = mock_response

        client = OllamaClient()
        response = await client.request_async(RequestMethod.GET, "test")

        assert response.success is True
        assert response.status_code == 200
        assert response.data == {"result": "success"}
        mock_get.assert_called_once_with("/api/test", params=None, timeout=30.0)

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_asynchronous_request_with_retry(self, mock_get):
        """Test asynchronous request with retry."""
        # First attempt fails, second succeeds
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={"result": "success"})
        mock_response.content = b'{"result": "success"}'
        
        mock_get.side_effect = [
            httpx.TimeoutException("Timeout"),
            mock_response,
        ]

        client = OllamaClient()
        with patch("asyncio.sleep"):  # Mock sleep to speed up test
            response = await client.request_async(RequestMethod.GET, "test")

        assert response.success is True
        assert response.status_code == 200
        assert mock_get.call_count == 2

    def test_get_models(self):
        """Test get_models synchronous method."""
        client = OllamaClient()
        
        with patch.object(client, "request") as mock_request:
            mock_request.return_value = OllamaResponse(
                success=True,
                status_code=200,
                data={"models": [{"name": "llama2"}]},
            )

            response = client.get_models()
            assert response.success is True
            assert response.data["models"][0]["name"] == "llama2"
            mock_request.assert_called_once_with(RequestMethod.GET, "tags")

    @pytest.mark.asyncio
    async def test_get_models_async(self):
        """Test get_models asynchronous method."""
        client = OllamaClient()
        
        with patch.object(client, "request_async") as mock_request:
            mock_request.return_value = OllamaResponse(
                success=True,
                status_code=200,
                data={"models": [{"name": "llama2"}]},
            )

            response = await client.get_models_async()
            assert response.success is True
            mock_request.assert_called_once_with(RequestMethod.GET, "tags")

    def test_generate_completion(self):
        """Test generate_completion synchronous method."""
        client = OllamaClient()
        
        with patch.object(client, "request") as mock_request:
            mock_request.return_value = OllamaResponse(
                success=True,
                status_code=200,
                data={"response": "Generated text"},
            )

            response = client.generate_completion(
                model="llama2",
                prompt="Test prompt",
                temperature=0.7,
                max_tokens=100,
            )
            
            assert response.success is True
            assert response.content == "Generated text"
            
            # Check request parameters
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[0] == (RequestMethod.POST, "generate")
            
            # The generate_completion method passes data as a dict, not json parameter
            data = call_args[1]["data"]
            assert data["model"] == "llama2"
            assert data["prompt"] == "Test prompt"
            assert data["temperature"] == 0.7
            assert data["max_tokens"] == 100

    @pytest.mark.asyncio
    async def test_generate_completion_async(self):
        """Test generate_completion asynchronous method."""
        client = OllamaClient()
        
        with patch.object(client, "request_async") as mock_request:
            mock_request.return_value = OllamaResponse(
                success=True,
                status_code=200,
                data={"response": "Generated text"},
            )

            response = await client.generate_completion_async(
                model="llama2", prompt="Test prompt"
            )
            
            assert response.success is True
            mock_request.assert_called_once()


    def test_chat_completion(self):
        """Test chat_completion synchronous method."""
        client = OllamaClient()
        
        messages = [{"role": "user", "content": "Hello"}]
        
        with patch.object(client, "request") as mock_request:
            mock_request.return_value = OllamaResponse(
                success=True,
                status_code=200,
                data={"message": {"content": "Hi there!"}},
            )

            response = client.chat_completion(model="llama2", messages=messages)
            
            assert response.success is True
            assert response.content == "Hi there!"
            
            # Check request parameters
            call_args = mock_request.call_args
            assert call_args[0] == (RequestMethod.POST, "chat")
            assert call_args[1]["data"]["messages"] == messages

    @pytest.mark.asyncio
    async def test_chat_completion_async(self):
        """Test chat_completion asynchronous method."""
        client = OllamaClient()
        
        messages = [{"role": "user", "content": "Hello"}]
        
        with patch.object(client, "request_async") as mock_request:
            mock_request.return_value = OllamaResponse(
                success=True,
                status_code=200,
                data={"message": {"content": "Hi there!"}},
            )

            response = await client.chat_completion_async(
                model="llama2", messages=messages
            )
            
            assert response.success is True
            mock_request.assert_called_once()

    def test_close(self):
        """Test close method."""
        client = OllamaClient()
        
        # Create mock clients
        mock_sync_client = Mock()
        mock_async_client = AsyncMock()
        mock_async_client.aclose = AsyncMock()
        
        client._sync_client = mock_sync_client
        client._async_client = mock_async_client
        
        client.close()
        
        mock_sync_client.close.assert_called_once()
        assert client._sync_client is None
        # Async client should be closed in sync close method
        mock_async_client.aclose.assert_called_once()
        assert client._async_client is None

    @pytest.mark.asyncio
    async def test_close_async(self):
        """Test close_async method."""
        client = OllamaClient()
        
        # Create mock clients
        mock_sync_client = Mock()
        mock_async_client = AsyncMock()
        
        client._sync_client = mock_sync_client
        client._async_client = mock_async_client
        
        await client.close_async()
        
        mock_async_client.aclose.assert_called_once()
        assert client._async_client is None
        mock_sync_client.close.assert_called_once()
        assert client._sync_client is None

    def test_del_method(self):
        """Test __del__ cleanup method."""
        client = OllamaClient()
        
        # Create mock clients
        mock_sync_client = Mock()
        mock_async_client = Mock()
        
        client._sync_client = mock_sync_client
        client._async_client = mock_async_client
        
        # Call __del__
        client.__del__()
        
        mock_sync_client.close.assert_called_once()
        # Async client close should be attempted but might fail

    def test_reset_instance(self):
        """Test reset_instance class method."""
        # Create instance
        client1 = OllamaClient()
        assert OllamaClient._instance is client1
        assert client1._initialized is True
        
        # Close any clients before resetting
        if client1._sync_client:
            client1._sync_client.close()
        client1._sync_client = None
        client1._async_client = None
        
        # Reset instance
        OllamaClient.reset_instance()
        assert OllamaClient._instance is None
        assert OllamaClient._initialized is False
        
        # New instance should be different
        client2 = OllamaClient()
        assert client2 is not client1


    @patch("httpx.Client.get")
    def test_request_with_params(self, mock_get):
        """Test request with query parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True}
        mock_response.content = b'{"ok": true}'
        mock_get.return_value = mock_response

        client = OllamaClient()
        params = {"key": "value", "limit": 10}
        
        response = client.request(
            RequestMethod.GET, "test", params=params
        )
        
        assert response.success is True
        mock_get.assert_called_once_with("/api/test", params=params, timeout=30.0)

    @patch("httpx.Client.get")
    def test_request_timeout_handling(self, mock_get):
        """Test timeout error handling."""
        mock_get.side_effect = httpx.TimeoutException("Request timed out")

        client = OllamaClient()
        client.retry_config.max_attempts = 1
        
        with pytest.raises(ResponseTimeoutError) as exc_info:
            client.request(RequestMethod.GET, "test")
        
        assert "30 seconds" in str(exc_info.value)

    @patch("httpx.Client.get") 
    def test_request_5xx_error_handling(self, mock_get):
        """Test 5xx server error handling."""
        mock_response = Mock()
        mock_response.status_code = 503
        mock_response.json.return_value = {"error": "Service unavailable"}
        mock_response.text = "Service unavailable"
        mock_response.content = b'{"error": "Service unavailable"}'
        mock_get.return_value = mock_response

        client = OllamaClient()
        client.retry_config.max_attempts = 1
        
        response = client.request(RequestMethod.GET, "test")
        
        assert response.success is False
        # When all retries fail, status_code is 0
        assert response.status_code == 0
        assert "HTTP 503: Service unavailable" in response.error_message

    def test_content_property_edge_cases(self):
        """Test OllamaResponse content property edge cases."""
        # Empty data
        response = OllamaResponse(success=True, status_code=200, data={})
        assert response.content is None
        
        # Message not a dict
        response = OllamaResponse(
            success=True, status_code=200, data={"message": "string message"}
        )
        assert response.content is None
        
        # Nested content structures
        response = OllamaResponse(
            success=True,
            status_code=200,
            data={"message": {"role": "assistant", "content": "Nested content"}},
        )
        assert response.content == "Nested content"