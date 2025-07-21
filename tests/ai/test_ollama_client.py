# ABOUTME: Comprehensive tests for Ollama HTTP client with async/sync support and retry logic
# ABOUTME: Tests singleton pattern, timeout handling, retry behavior, and API methods

import asyncio
import json
import time
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

import httpx
import pytest

from create_project.ai.ollama_client import (
    OllamaClient, 
    RequestMethod, 
    RetryConfig, 
    OllamaResponse
)
from create_project.ai.exceptions import OllamaNotFoundError, ResponseTimeoutError, AIError


class TestRetryConfig:
    """Test RetryConfig dataclass."""
    
    def test_default_config(self):
        """Test default retry configuration."""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 30.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
        
    def test_custom_config(self):
        """Test custom retry configuration."""
        config = RetryConfig(
            max_attempts=5,
            base_delay=0.5,
            max_delay=60.0,
            exponential_base=1.5,
            jitter=False
        )
        assert config.max_attempts == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 60.0
        assert config.exponential_base == 1.5
        assert config.jitter is False


class TestOllamaResponse:
    """Test OllamaResponse dataclass."""
    
    def test_successful_response(self):
        """Test successful response creation."""
        response = OllamaResponse(
            success=True,
            status_code=200,
            data={"models": []},
            response_time=0.5
        )
        
        assert response.success is True
        assert response.status_code == 200
        assert response.data == {"models": []}
        assert response.error_message is None
        assert response.response_time == 0.5
        
    def test_error_response(self):
        """Test error response creation."""
        response = OllamaResponse(
            success=False,
            status_code=500,
            data=None,
            error_message="Server error",
            response_time=1.0
        )
        
        assert response.success is False
        assert response.status_code == 500
        assert response.data is None
        assert response.error_message == "Server error"
        assert response.response_time == 1.0


class TestOllamaClientSingleton:
    """Test singleton pattern behavior."""
    
    def teardown_method(self):
        """Reset singleton after each test."""
        OllamaClient.reset_instance()
    
    def test_singleton_behavior(self):
        """Test that OllamaClient is a singleton."""
        client1 = OllamaClient()
        client2 = OllamaClient()
        
        assert client1 is client2
        assert OllamaClient._instance is client1
        
    def test_singleton_initialization(self):
        """Test singleton initializes only once."""
        client1 = OllamaClient(base_url="http://localhost:11434")
        client2 = OllamaClient(base_url="http://different:8080")
        
        # Both should have the same base_url from first initialization
        assert client1.base_url == "http://localhost:11434"
        assert client2.base_url == "http://localhost:11434"
        assert client1 is client2
        
    def test_reset_instance(self):
        """Test singleton reset functionality."""
        client1 = OllamaClient()
        OllamaClient.reset_instance()
        client2 = OllamaClient()
        
        assert client1 is not client2
        assert OllamaClient._instance is client2


class TestOllamaClientInitialization:
    """Test client initialization."""
    
    def teardown_method(self):
        """Reset singleton after each test."""
        OllamaClient.reset_instance()
    
    def test_default_initialization(self):
        """Test client initialization with defaults."""
        client = OllamaClient()
        
        assert client.base_url == "http://localhost:11434"
        assert client.timeout == 30.0
        assert client.retry_config.max_attempts == 3
        
    def test_custom_initialization(self):
        """Test client initialization with custom parameters."""
        retry_config = RetryConfig(max_attempts=5, base_delay=0.5)
        client = OllamaClient(
            base_url="http://custom:8080",
            timeout=60.0,
            retry_config=retry_config
        )
        
        assert client.base_url == "http://custom:8080"
        assert client.timeout == 60.0
        assert client.retry_config.max_attempts == 5
        assert client.retry_config.base_delay == 0.5


class TestOllamaClientProperties:
    """Test client property methods."""
    
    def teardown_method(self):
        """Reset singleton after each test."""
        OllamaClient.reset_instance()
    
    def test_sync_client_creation(self):
        """Test synchronous client creation."""
        client = OllamaClient()
        sync_client = client.sync_client
        
        assert isinstance(sync_client, httpx.Client)
        assert sync_client.base_url == "http://localhost:11434"
        assert sync_client is client.sync_client  # Should return same instance
        
    def test_async_client_creation(self):
        """Test asynchronous client creation."""
        client = OllamaClient()
        async_client = client.async_client
        
        assert isinstance(async_client, httpx.AsyncClient)
        assert async_client.base_url == "http://localhost:11434"
        assert async_client is client.async_client  # Should return same instance


class TestRetryLogic:
    """Test retry logic and delay calculations."""
    
    def teardown_method(self):
        """Reset singleton after each test."""
        OllamaClient.reset_instance()
    
    def test_calculate_delay_exponential(self):
        """Test exponential backoff delay calculation."""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)
        client = OllamaClient(retry_config=config)
        
        assert client._calculate_delay(0) == 1.0  # 1.0 * 2^0
        assert client._calculate_delay(1) == 2.0  # 1.0 * 2^1
        assert client._calculate_delay(2) == 4.0  # 1.0 * 2^2
        
    def test_calculate_delay_max_limit(self):
        """Test delay respects maximum limit."""
        config = RetryConfig(base_delay=10.0, max_delay=15.0, jitter=False)
        client = OllamaClient(retry_config=config)
        
        # Should be capped at max_delay
        assert client._calculate_delay(2) == 15.0
        
    def test_calculate_delay_with_jitter(self):
        """Test delay calculation with jitter."""
        config = RetryConfig(base_delay=2.0, exponential_base=1.0, jitter=True)
        client = OllamaClient(retry_config=config)
        
        # With jitter, delay should be between 1.0 and 2.0
        delay = client._calculate_delay(0)
        assert 1.0 <= delay <= 2.0
        
    def test_should_retry_connection_error(self):
        """Test retry decision for connection errors."""
        client = OllamaClient()
        
        assert client._should_retry(None, httpx.ConnectError("Connection failed"))
        assert client._should_retry(None, httpx.TimeoutException("Timeout"))
        assert client._should_retry(None, httpx.ReadTimeout("Read timeout"))
        
    def test_should_retry_http_status(self):
        """Test retry decision for HTTP status codes."""
        client = OllamaClient()
        
        # Mock responses
        server_error = Mock()
        server_error.status_code = 500
        
        client_error = Mock()
        client_error.status_code = 404
        
        success = Mock()
        success.status_code = 200
        
        assert client._should_retry(server_error, None) is True
        assert client._should_retry(client_error, None) is False
        assert client._should_retry(success, None) is False
        
    def test_should_not_retry_other_exceptions(self):
        """Test retry decision for non-retryable exceptions."""
        client = OllamaClient()
        
        assert client._should_retry(None, ValueError("Invalid data")) is False
        assert client._should_retry(None, KeyError("Missing key")) is False


class TestSynchronousRequests:
    """Test synchronous HTTP requests."""
    
    def teardown_method(self):
        """Reset singleton after each test."""
        OllamaClient.reset_instance()
    
    @patch('httpx.Client')
    def test_successful_get_request(self, mock_client_class):
        """Test successful GET request."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": []}
        mock_response.content = b'{"models": []}'
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        client = OllamaClient()
        client._sync_client = mock_client  # Bypass property
        
        response = client.request(RequestMethod.GET, "tags")
        
        assert response.success is True
        assert response.status_code == 200
        assert response.data == {"models": []}
        assert response.error_message is None
        
    @patch('httpx.Client')
    def test_successful_post_request(self, mock_client_class):
        """Test successful POST request."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Generated text"}
        mock_response.content = b'{"response": "Generated text"}'
        
        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        client = OllamaClient()
        client._sync_client = mock_client
        
        data = {"model": "llama2", "prompt": "Hello"}
        response = client.request(RequestMethod.POST, "generate", data=data)
        
        assert response.success is True
        assert response.status_code == 200
        assert response.data == {"response": "Generated text"}
        
        # Verify POST was called with correct data
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert json.loads(call_args.kwargs['content']) == data
        
    @patch('httpx.Client')
    def test_client_error_response(self, mock_client_class):
        """Test handling of client error (4xx) responses."""
        # Mock 404 response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Model not found"
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        client = OllamaClient()
        client._sync_client = mock_client
        
        response = client.request(RequestMethod.GET, "unknown")
        
        assert response.success is False
        assert response.status_code == 404
        assert "Model not found" in response.error_message
        
    @patch('httpx.Client')
    @patch('time.sleep')  # Mock sleep to speed up tests
    def test_retry_on_server_error(self, mock_sleep, mock_client_class):
        """Test retry behavior on server errors."""
        # Mock server error on first two attempts, success on third
        responses = [
            Mock(status_code=500, text="Server error"),
            Mock(status_code=500, text="Server error"),
            Mock(status_code=200, json=lambda: {"success": True}, content=b'{"success": true}')
        ]
        
        mock_client = Mock()
        mock_client.get.side_effect = responses
        mock_client_class.return_value = mock_client
        
        client = OllamaClient()
        client._sync_client = mock_client
        
        response = client.request(RequestMethod.GET, "tags")
        
        assert response.success is True
        assert response.status_code == 200
        assert mock_client.get.call_count == 3  # Should have retried twice
        assert mock_sleep.call_count == 2  # Should have slept between retries
        
    @patch('httpx.Client')
    def test_connection_error_raises_exception(self, mock_client_class):
        """Test that connection errors raise OllamaNotFoundError."""
        mock_client = Mock()
        mock_client.get.side_effect = httpx.ConnectError("Connection failed")
        mock_client_class.return_value = mock_client
        
        client = OllamaClient(retry_config=RetryConfig(max_attempts=1))  # No retries
        client._sync_client = mock_client
        
        with pytest.raises(OllamaNotFoundError):
            client.request(RequestMethod.GET, "tags")
            
    @patch('httpx.Client')
    def test_timeout_raises_exception(self, mock_client_class):
        """Test that timeouts raise ResponseTimeoutError."""
        mock_client = Mock()
        mock_client.get.side_effect = httpx.TimeoutException("Request timeout")
        mock_client_class.return_value = mock_client
        
        client = OllamaClient(retry_config=RetryConfig(max_attempts=1))  # No retries
        client._sync_client = mock_client
        
        with pytest.raises(ResponseTimeoutError):
            client.request(RequestMethod.GET, "tags")


class TestAsynchronousRequests:
    """Test asynchronous HTTP requests."""
    
    def teardown_method(self):
        """Reset singleton after each test."""
        OllamaClient.reset_instance()
    
    @patch('httpx.AsyncClient')
    @pytest.mark.asyncio
    async def test_successful_async_get_request(self, mock_client_class):
        """Test successful async GET request."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": []}
        mock_response.content = b'{"models": []}'
        
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        client = OllamaClient()
        client._async_client = mock_client  # Bypass property
        
        response = await client.request_async(RequestMethod.GET, "tags")
        
        assert response.success is True
        assert response.status_code == 200
        assert response.data == {"models": []}
        
    @patch('httpx.AsyncClient')
    @pytest.mark.asyncio
    async def test_async_retry_behavior(self, mock_client_class):
        """Test async retry behavior."""
        # Mock server error on first attempt, success on second
        responses = [
            Mock(status_code=500, text="Server error"),
            Mock(status_code=200, json=lambda: {"success": True}, content=b'{"success": true}')
        ]
        
        mock_client = AsyncMock()
        mock_client.get.side_effect = responses
        mock_client_class.return_value = mock_client
        
        client = OllamaClient()
        client._async_client = mock_client
        
        with patch('asyncio.sleep') as mock_sleep:  # Mock async sleep
            response = await client.request_async(RequestMethod.GET, "tags")
            
        assert response.success is True
        assert response.status_code == 200
        assert mock_client.get.call_count == 2
        mock_sleep.assert_called_once()  # Should have slept once between retries


class TestAPIHelperMethods:
    """Test API helper methods."""
    
    def teardown_method(self):
        """Reset singleton after each test."""
        OllamaClient.reset_instance()
    
    @patch.object(OllamaClient, 'request')
    def test_get_models(self, mock_request):
        """Test get_models helper method."""
        mock_response = OllamaResponse(True, 200, {"models": []})
        mock_request.return_value = mock_response
        
        client = OllamaClient()
        response = client.get_models()
        
        assert response is mock_response
        mock_request.assert_called_once_with(RequestMethod.GET, "tags")
        
    @patch.object(OllamaClient, 'request_async')
    @pytest.mark.asyncio
    async def test_get_models_async(self, mock_request):
        """Test async get_models helper method."""
        mock_response = OllamaResponse(True, 200, {"models": []})
        mock_request.return_value = mock_response
        
        client = OllamaClient()
        response = await client.get_models_async()
        
        assert response is mock_response
        mock_request.assert_called_once_with(RequestMethod.GET, "tags")
        
    @patch.object(OllamaClient, 'request')
    def test_generate_completion(self, mock_request):
        """Test generate_completion helper method."""
        mock_response = OllamaResponse(True, 200, {"response": "Generated"})
        mock_request.return_value = mock_response
        
        client = OllamaClient()
        response = client.generate_completion(
            model="llama2",
            prompt="Hello",
            temperature=0.8
        )
        
        expected_data = {
            "model": "llama2",
            "prompt": "Hello",
            "stream": False,
            "temperature": 0.8
        }
        
        assert response is mock_response
        mock_request.assert_called_once_with(RequestMethod.POST, "generate", data=expected_data)
        
    @patch.object(OllamaClient, 'request')
    def test_chat_completion(self, mock_request):
        """Test chat_completion helper method."""
        mock_response = OllamaResponse(True, 200, {"message": {"content": "Reply"}})
        mock_request.return_value = mock_response
        
        client = OllamaClient()
        messages = [{"role": "user", "content": "Hello"}]
        response = client.chat_completion(model="llama2", messages=messages)
        
        expected_data = {
            "model": "llama2", 
            "messages": messages,
            "stream": False
        }
        
        assert response is mock_response
        mock_request.assert_called_once_with(RequestMethod.POST, "chat", data=expected_data)


class TestClientCleanup:
    """Test client cleanup and resource management."""
    
    def teardown_method(self):
        """Reset singleton after each test."""
        OllamaClient.reset_instance()
    
    def test_close_clients(self):
        """Test synchronous client cleanup."""
        client = OllamaClient()
        
        # Create mock clients
        sync_client = Mock()
        async_client = Mock()
        
        client._sync_client = sync_client
        client._async_client = async_client
        
        # Mock event loop for async client cleanup
        with patch('asyncio.get_event_loop') as mock_get_loop:
            mock_loop = Mock()
            mock_get_loop.return_value = mock_loop
            
            client.close()
            
            sync_client.close.assert_called_once()
            mock_loop.run_until_complete.assert_called_once()
            
        assert client._sync_client is None
        assert client._async_client is None
        
    @pytest.mark.asyncio
    async def test_close_clients_async(self):
        """Test asynchronous client cleanup."""
        client = OllamaClient()
        
        # Create mock clients
        sync_client = Mock()
        async_client = AsyncMock()
        
        client._sync_client = sync_client
        client._async_client = async_client
        
        await client.close_async()
        
        sync_client.close.assert_called_once()
        async_client.aclose.assert_called_once()
        
        assert client._sync_client is None
        assert client._async_client is None