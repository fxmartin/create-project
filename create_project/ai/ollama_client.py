# ABOUTME: HTTP client for Ollama API with async/sync support and retry logic
# ABOUTME: Singleton pattern with connection pooling and comprehensive error handling

"""HTTP client for Ollama API communication.

This module provides a robust HTTP client for interacting with the Ollama API,
supporting both synchronous and asynchronous operations. It implements a
singleton pattern for efficient resource management and includes sophisticated
retry logic with exponential backoff.

Key Features:
    - Singleton pattern ensuring single client instance
    - Both sync and async API support with httpx
    - Connection pooling for efficient HTTP communication
    - Exponential backoff retry with configurable parameters
    - Automatic retry on connection errors and timeouts
    - Structured response objects with error handling
    - Support for all Ollama API endpoints
    - Graceful cleanup and resource management
    - Request/response timing and performance metrics

Main Classes:
    - RequestMethod: Enum for HTTP methods
    - RetryConfig: Configuration for retry behavior
    - OllamaResponse: Standardized API response wrapper
    - OllamaClient: Main client class (singleton)

Usage Example:
    ```python
    from create_project.ai.ollama_client import OllamaClient, RetryConfig

    # Get singleton instance
    client = OllamaClient(
        base_url="http://localhost:11434",
        timeout=30.0,
        retry_config=RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            exponential_base=2.0
        )
    )

    # Synchronous API calls
    # List available models
    response = client.get_models()
    if response.success:
        models = response.data.get("models", [])
        for model in models:
            print(f"Model: {model['name']}")

    # Generate completion
    response = client.generate_completion(
        model="llama2:7b",
        prompt="Explain Python decorators",
        temperature=0.7,
        max_tokens=500
    )
    if response.success:
        print(response.content)

    # Asynchronous API calls
    import asyncio

    async def async_example():
        # Chat completion
        messages = [
            {"role": "user", "content": "What is recursion?"}
        ]
        response = await client.chat_completion_async(
            model="llama2:7b",
            messages=messages
        )
        if response.success:
            print(response.content)

        # Cleanup
        await client.close_async()

    asyncio.run(async_example())
    ```

The client automatically handles connection errors, timeouts, and server
errors with configurable retry logic. It maintains persistent HTTP connections
for improved performance across multiple requests.
"""

import asyncio
import json
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Union

import httpx
from structlog import get_logger

from .exceptions import AIError, OllamaNotFoundError, ResponseTimeoutError
from .ollama_detector import OllamaDetector


class RequestMethod(Enum):
    """HTTP request methods."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 30.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True


@dataclass
class OllamaResponse:
    """Standardized response from Ollama API."""

    success: bool
    status_code: int
    data: Optional[Dict[str, Any]]
    error_message: Optional[str] = None
    response_time: Optional[float] = None

    @property
    def content(self) -> Optional[str]:
        """Extract content from response data."""
        if not self.success or not self.data:
            return None

        # Try different content extraction patterns
        if "message" in self.data and isinstance(self.data["message"], dict):
            return self.data["message"].get("content")
        elif "response" in self.data:
            return self.data["response"]
        elif "content" in self.data:
            return self.data["content"]

        return None

    @property
    def error(self) -> Optional[str]:
        """Get error message for failed requests."""
        return self.error_message if not self.success else None


class OllamaClient:
    """HTTP client for Ollama API with singleton pattern and connection pooling."""

    _instance: Optional["OllamaClient"] = None
    _initialized: bool = False

    DEFAULT_TIMEOUT = 30.0
    CONNECTION_TIMEOUT = 5.0

    def __new__(cls, *args, **kwargs) -> "OllamaClient":
        """Singleton pattern implementation."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        retry_config: Optional[RetryConfig] = None,
    ):
        """
        Initialize Ollama HTTP client (singleton).

        Args:
            base_url: Base URL for Ollama service
            timeout: Default request timeout in seconds
            retry_config: Retry configuration
        """
        # Only initialize once due to singleton pattern
        if self._initialized:
            return

        self.detector = OllamaDetector(service_url=base_url)
        self.base_url = base_url or "http://localhost:11434"
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self.retry_config = retry_config or RetryConfig()

        self.logger = get_logger("ai.ollama_client")

        # HTTP clients (created lazily)
        self._sync_client: Optional[httpx.Client] = None
        self._async_client: Optional[httpx.AsyncClient] = None

        self._initialized = True

        self.logger.info(
            "Ollama client initialized",
            base_url=self.base_url,
            timeout=self.timeout,
            max_attempts=self.retry_config.max_attempts,
        )

    @property
    def sync_client(self) -> httpx.Client:
        """Get or create synchronous HTTP client."""
        if self._sync_client is None:
            self._sync_client = httpx.Client(
                base_url=self.base_url,
                timeout=httpx.Timeout(
                    connect=self.CONNECTION_TIMEOUT,
                    read=self.timeout,
                    write=self.timeout,
                    pool=self.timeout,
                ),
                headers={"Content-Type": "application/json"},
            )
            self.logger.debug("Created synchronous HTTP client")
        return self._sync_client

    @property
    def async_client(self) -> httpx.AsyncClient:
        """Get or create asynchronous HTTP client."""
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(
                    connect=self.CONNECTION_TIMEOUT,
                    read=self.timeout,
                    write=self.timeout,
                    pool=self.timeout,
                ),
                headers={"Content-Type": "application/json"},
            )
            self.logger.debug("Created asynchronous HTTP client")
        return self._async_client

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for exponential backoff with jitter."""
        delay = min(
            self.retry_config.base_delay
            * (self.retry_config.exponential_base**attempt),
            self.retry_config.max_delay,
        )

        if self.retry_config.jitter:
            import random

            delay *= 0.5 + random.random() * 0.5  # Add 0-50% jitter

        return delay

    def _should_retry(
        self, response: Optional[httpx.Response], exception: Optional[Exception]
    ) -> bool:
        """Determine if request should be retried."""
        if exception:
            # Retry on connection errors and timeouts
            return isinstance(
                exception,
                (httpx.ConnectError, httpx.TimeoutException, httpx.ReadTimeout),
            )

        if response:
            # Retry on server errors (5xx) but not client errors (4xx)
            return response.status_code >= 500

        return False

    def request(
        self,
        method: Union[RequestMethod, str],
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> OllamaResponse:
        """
        Make synchronous HTTP request with retry logic.

        Args:
            method: HTTP method
            endpoint: API endpoint (without base URL)
            data: JSON data for request body
            params: URL parameters
            timeout: Request timeout override

        Returns:
            OllamaResponse with results
        """
        if isinstance(method, RequestMethod):
            method = method.value

        url = f"/api/{endpoint.lstrip('/')}"
        request_timeout = timeout or self.timeout

        self.logger.debug(
            "Making synchronous request",
            method=method,
            endpoint=endpoint,
            timeout=request_timeout,
        )

        last_exception = None
        start_time = time.time()

        for attempt in range(self.retry_config.max_attempts):
            try:
                # Make the request
                if method.upper() == "GET":
                    response = self.sync_client.get(
                        url, params=params, timeout=request_timeout
                    )
                elif method.upper() == "POST":
                    json_data = json.dumps(data) if data else None
                    response = self.sync_client.post(
                        url, content=json_data, params=params, timeout=request_timeout
                    )
                elif method.upper() == "PUT":
                    json_data = json.dumps(data) if data else None
                    response = self.sync_client.put(
                        url, content=json_data, params=params, timeout=request_timeout
                    )
                elif method.upper() == "DELETE":
                    response = self.sync_client.delete(
                        url, params=params, timeout=request_timeout
                    )
                else:
                    raise AIError(f"Unsupported HTTP method: {method}")

                # Parse response
                response_time = time.time() - start_time

                if response.status_code < 400:
                    try:
                        response_data = response.json() if response.content else {}
                    except json.JSONDecodeError:
                        response_data = {"content": response.text}

                    self.logger.debug(
                        "Request successful",
                        status_code=response.status_code,
                        response_time=response_time,
                        attempt=attempt + 1,
                    )

                    return OllamaResponse(
                        success=True,
                        status_code=response.status_code,
                        data=response_data,
                        response_time=response_time,
                    )

                # Handle client/server errors
                if not self._should_retry(response, None):
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    self.logger.warning(
                        "Request failed (not retryable)", error=error_msg
                    )

                    return OllamaResponse(
                        success=False,
                        status_code=response.status_code,
                        data=None,
                        error_message=error_msg,
                        response_time=time.time() - start_time,
                    )

                last_exception = AIError(
                    f"HTTP {response.status_code}: {response.text}"
                )

            except Exception as e:
                last_exception = e

                if not self._should_retry(None, e):
                    break

            # Log retry attempt
            if attempt < self.retry_config.max_attempts - 1:
                delay = self._calculate_delay(attempt)
                self.logger.warning(
                    "Request failed, retrying",
                    attempt=attempt + 1,
                    max_attempts=self.retry_config.max_attempts,
                    delay=delay,
                    error=str(last_exception),
                )
                time.sleep(delay)

        # All retry attempts failed
        error_msg = f"Request failed after {self.retry_config.max_attempts} attempts: {last_exception}"
        self.logger.error("Request exhausted retries", error=error_msg)

        if isinstance(last_exception, (httpx.TimeoutException, httpx.ReadTimeout)):
            raise ResponseTimeoutError(int(request_timeout))
        elif isinstance(last_exception, httpx.ConnectError):
            raise OllamaNotFoundError("Unable to connect to Ollama service")

        return OllamaResponse(
            success=False,
            status_code=0,
            data=None,
            error_message=error_msg,
            response_time=time.time() - start_time,
        )

    async def request_async(
        self,
        method: Union[RequestMethod, str],
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> OllamaResponse:
        """
        Make asynchronous HTTP request with retry logic.

        Args:
            method: HTTP method
            endpoint: API endpoint (without base URL)
            data: JSON data for request body
            params: URL parameters
            timeout: Request timeout override

        Returns:
            OllamaResponse with results
        """
        if isinstance(method, RequestMethod):
            method = method.value

        url = f"/api/{endpoint.lstrip('/')}"
        request_timeout = timeout or self.timeout

        self.logger.debug(
            "Making asynchronous request",
            method=method,
            endpoint=endpoint,
            timeout=request_timeout,
        )

        last_exception = None
        start_time = time.time()

        for attempt in range(self.retry_config.max_attempts):
            try:
                # Make the request
                if method.upper() == "GET":
                    response = await self.async_client.get(
                        url, params=params, timeout=request_timeout
                    )
                elif method.upper() == "POST":
                    json_data = json.dumps(data) if data else None
                    response = await self.async_client.post(
                        url, content=json_data, params=params, timeout=request_timeout
                    )
                elif method.upper() == "PUT":
                    json_data = json.dumps(data) if data else None
                    response = await self.async_client.put(
                        url, content=json_data, params=params, timeout=request_timeout
                    )
                elif method.upper() == "DELETE":
                    response = await self.async_client.delete(
                        url, params=params, timeout=request_timeout
                    )
                else:
                    raise AIError(f"Unsupported HTTP method: {method}")

                # Parse response
                response_time = time.time() - start_time

                if response.status_code < 400:
                    try:
                        response_data = response.json() if response.content else {}
                    except json.JSONDecodeError:
                        response_data = {"content": response.text}

                    self.logger.debug(
                        "Async request successful",
                        status_code=response.status_code,
                        response_time=response_time,
                        attempt=attempt + 1,
                    )

                    return OllamaResponse(
                        success=True,
                        status_code=response.status_code,
                        data=response_data,
                        response_time=response_time,
                    )

                # Handle client/server errors
                if not self._should_retry(response, None):
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    self.logger.warning(
                        "Async request failed (not retryable)", error=error_msg
                    )

                    return OllamaResponse(
                        success=False,
                        status_code=response.status_code,
                        data=None,
                        error_message=error_msg,
                        response_time=time.time() - start_time,
                    )

                last_exception = AIError(
                    f"HTTP {response.status_code}: {response.text}"
                )

            except Exception as e:
                last_exception = e

                if not self._should_retry(None, e):
                    break

            # Log retry attempt
            if attempt < self.retry_config.max_attempts - 1:
                delay = self._calculate_delay(attempt)
                self.logger.warning(
                    "Async request failed, retrying",
                    attempt=attempt + 1,
                    max_attempts=self.retry_config.max_attempts,
                    delay=delay,
                    error=str(last_exception),
                )
                await asyncio.sleep(delay)

        # All retry attempts failed
        error_msg = f"Async request failed after {self.retry_config.max_attempts} attempts: {last_exception}"
        self.logger.error("Async request exhausted retries", error=error_msg)

        if isinstance(last_exception, (httpx.TimeoutException, httpx.ReadTimeout)):
            raise ResponseTimeoutError(int(request_timeout))
        elif isinstance(last_exception, httpx.ConnectError):
            raise OllamaNotFoundError("Unable to connect to Ollama service")

        return OllamaResponse(
            success=False,
            status_code=0,
            data=None,
            error_message=error_msg,
            response_time=time.time() - start_time,
        )

    def get_models(self) -> OllamaResponse:
        """Get list of available models."""
        return self.request(RequestMethod.GET, "tags")

    async def get_models_async(self) -> OllamaResponse:
        """Get list of available models (async)."""
        return await self.request_async(RequestMethod.GET, "tags")

    def generate_completion(
        self, model: str, prompt: str, stream: bool = False, **kwargs
    ) -> OllamaResponse:
        """
        Generate completion from model.

        Args:
            model: Model name
            prompt: Input prompt
            stream: Whether to stream response
            **kwargs: Additional parameters for generation

        Returns:
            OllamaResponse with completion
        """
        data = {"model": model, "prompt": prompt, "stream": stream, **kwargs}

        return self.request(RequestMethod.POST, "generate", data=data)

    async def generate_completion_async(
        self, model: str, prompt: str, stream: bool = False, **kwargs
    ) -> OllamaResponse:
        """
        Generate completion from model (async).

        Args:
            model: Model name
            prompt: Input prompt
            stream: Whether to stream response
            **kwargs: Additional parameters for generation

        Returns:
            OllamaResponse with completion
        """
        data = {"model": model, "prompt": prompt, "stream": stream, **kwargs}

        return await self.request_async(RequestMethod.POST, "generate", data=data)

    def chat_completion(
        self, model: str, messages: list, stream: bool = False, **kwargs
    ) -> OllamaResponse:
        """
        Generate chat completion from model.

        Args:
            model: Model name
            messages: List of chat messages
            stream: Whether to stream response
            **kwargs: Additional parameters

        Returns:
            OllamaResponse with chat completion
        """
        data = {"model": model, "messages": messages, "stream": stream, **kwargs}

        return self.request(RequestMethod.POST, "chat", data=data)

    async def chat_completion_async(
        self, model: str, messages: list, stream: bool = False, **kwargs
    ) -> OllamaResponse:
        """
        Generate chat completion from model (async).

        Args:
            model: Model name
            messages: List of chat messages
            stream: Whether to stream response
            **kwargs: Additional parameters

        Returns:
            OllamaResponse with chat completion
        """
        data = {"model": model, "messages": messages, "stream": stream, **kwargs}

        return await self.request_async(RequestMethod.POST, "chat", data=data)

    def close(self) -> None:
        """Close HTTP clients and cleanup resources."""
        if self._sync_client:
            self._sync_client.close()
            self._sync_client = None

        if self._async_client:
            # Note: async client should be closed with await client.aclose()
            # This is a synchronous close, which may not be ideal
            try:
                asyncio.get_event_loop().run_until_complete(self._async_client.aclose())
            except RuntimeError:
                # If no event loop is running, we can't properly close async client
                pass
            self._async_client = None

        self.logger.debug("HTTP clients closed")

    async def close_async(self) -> None:
        """Close HTTP clients asynchronously."""
        if self._sync_client:
            self._sync_client.close()
            self._sync_client = None

        if self._async_client:
            await self._async_client.aclose()
            self._async_client = None

        self.logger.debug("HTTP clients closed (async)")

    def __del__(self):
        """Cleanup on destruction."""
        try:
            self.close()
        except Exception:
            # Ignore errors during cleanup
            pass

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (mainly for testing)."""
        if cls._instance:
            cls._instance.close()
        cls._instance = None
        cls._initialized = False
