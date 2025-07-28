# ABOUTME: Comprehensive Ollama mock implementations for testing
# ABOUTME: Includes client, detector, and response mocks with various scenarios

"""Ollama mock implementations for testing."""

import asyncio
import time
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

from create_project.ai.exceptions import (
    AIError,
    ModelNotAvailableError,
    OllamaNotFoundError,
    ResponseTimeoutError,
)
from create_project.ai.model_manager import ModelCapability, ModelInfo
from create_project.ai.ollama_detector import OllamaStatus


# Mock OllamaResponse
@dataclass
class MockOllamaResponse:
    """Mock OllamaResponse for testing."""
    success: bool
    status_code: int
    data: Optional[Dict[str, Any]]
    error_message: Optional[str] = None
    response_time: Optional[float] = None


class OllamaMockScenario(Enum):
    """Predefined mock scenarios for testing."""
    
    SUCCESS = "success"
    CONNECTION_ERROR = "connection_error"
    TIMEOUT_ERROR = "timeout_error"
    MODEL_NOT_FOUND = "model_not_found"
    INVALID_RESPONSE = "invalid_response"
    SLOW_RESPONSE = "slow_response"
    PARTIAL_RESPONSE = "partial_response"
    EMPTY_MODELS = "empty_models"
    RATE_LIMITED = "rate_limited"
    SERVER_ERROR = "server_error"


@dataclass
class MockOllamaResponse:
    """Mock response for Ollama API calls."""
    
    model: str = "codellama:13b"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    response: str = "This is a mock response"
    done: bool = True
    context: Optional[List[int]] = None
    total_duration: int = 1000000000  # 1 second in nanoseconds
    load_duration: int = 500000000
    prompt_eval_count: int = 10
    prompt_eval_duration: int = 100000000
    eval_count: int = 20
    eval_duration: int = 400000000
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format matching Ollama API."""
        return {
            "model": self.model,
            "created_at": self.created_at,
            "response": self.response,
            "done": self.done,
            "context": self.context or [],
            "total_duration": self.total_duration,
            "load_duration": self.load_duration,
            "prompt_eval_count": self.prompt_eval_count,
            "prompt_eval_duration": self.prompt_eval_duration,
            "eval_count": self.eval_count,
            "eval_duration": self.eval_duration,
        }


def create_mock_model_info(
    name: str = "codellama:13b",
    size: int = 7365960935,
    modified_at: Optional[datetime] = None,
    digest: Optional[str] = None,
    family: Optional[str] = "llama",
    parameter_size: Optional[str] = "13B",
    quantization: Optional[str] = "Q4_0",
    capabilities: Optional[set] = None,
) -> ModelInfo:
    """Create a mock ModelInfo object."""
    if modified_at is None:
        modified_at = datetime.now()
    
    if digest is None:
        digest = f"sha256:{'a' * 64}"
    
    if capabilities is None:
        # Default capabilities based on model type
        if "code" in name.lower():
            capabilities = {ModelCapability.CODE_GENERATION, ModelCapability.TEXT_GENERATION}
        elif "embed" in name.lower():
            capabilities = {ModelCapability.EMBEDDING}
        else:
            capabilities = {ModelCapability.TEXT_GENERATION, ModelCapability.CHAT}
    
    return ModelInfo(
        name=name,
        size=size,
        digest=digest,
        modified_at=modified_at,
        capabilities=capabilities,
        family=family,
        parameter_size=parameter_size,
        quantization=quantization,
    )


def create_mock_ollama_status(
    is_installed: bool = True,
    is_running: bool = True,
    binary_path: Optional[str] = "/usr/local/bin/ollama",
    version: Optional[str] = "0.1.24",
    service_url: str = "http://localhost:11434",
    error_message: Optional[str] = None,
) -> OllamaStatus:
    """Create a mock OllamaStatus object."""
    return OllamaStatus(
        is_installed=is_installed,
        is_running=is_running,
        version=version,
        binary_path=Path(binary_path) if binary_path else None,
        service_url=service_url,
        detected_at=datetime.now(),
        error_message=error_message,
    )


class MockOllamaClient:
    """Mock implementation of OllamaClient for testing."""
    
    def __init__(
        self,
        scenario: OllamaMockScenario = OllamaMockScenario.SUCCESS,
        models: Optional[List[ModelInfo]] = None,
        response_delay: float = 0.0,
        streaming_chunks: int = 5,
    ):
        """Initialize mock client with scenario."""
        self.scenario = scenario
        self.models = models or [
            create_mock_model_info("codellama:13b"),
            create_mock_model_info("llama2:7b", size=3826793677),
            create_mock_model_info("mistral:7b", size=4109856768),
        ]
        self.response_delay = response_delay
        self.streaming_chunks = streaming_chunks
        self.call_count = 0
        self.last_prompt = None
        self.last_model = None
        
    async def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        template: Optional[str] = None,
        context: Optional[List[int]] = None,
        stream: bool = False,
        raw: bool = False,
        format: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        keep_alive: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Mock generate method."""
        self.call_count += 1
        self.last_prompt = prompt
        self.last_model = model
        
        # Simulate delay if configured
        if self.response_delay > 0:
            await asyncio.sleep(self.response_delay)
        
        # Handle different scenarios
        if self.scenario == OllamaMockScenario.CONNECTION_ERROR:
            raise AIError("Mock connection error")
        
        elif self.scenario == OllamaMockScenario.TIMEOUT_ERROR:
            raise ResponseTimeoutError(30)
        
        elif self.scenario == OllamaMockScenario.MODEL_NOT_FOUND:
            raise ModelNotAvailableError(model, available_models=["codellama:13b", "llama2:7b"])
        
        elif self.scenario == OllamaMockScenario.RATE_LIMITED:
            raise AIError("Rate limit exceeded")
        
        elif self.scenario == OllamaMockScenario.SERVER_ERROR:
            raise AIError("Internal server error")
        
        elif self.scenario == OllamaMockScenario.INVALID_RESPONSE:
            yield {"invalid": "response", "missing": "required_fields"}
            return
        
        elif self.scenario == OllamaMockScenario.SLOW_RESPONSE:
            # Simulate slow streaming
            for i in range(self.streaming_chunks):
                await asyncio.sleep(0.5)
                yield {
                    "model": model,
                    "created_at": datetime.now().isoformat(),
                    "response": f"Chunk {i+1} of slow response. ",
                    "done": i == self.streaming_chunks - 1,
                }
            return
        
        elif self.scenario == OllamaMockScenario.PARTIAL_RESPONSE:
            # Simulate incomplete response
            yield {
                "model": model,
                "created_at": datetime.now().isoformat(),
                "response": "This is a partial",
                "done": False,
            }
            # Don't send done=True
            return
        
        # Default success scenario
        if stream:
            # Simulate streaming response
            response_parts = [
                "This is ",
                "a mock ",
                "streaming ",
                "response ",
                "for testing.",
            ]
            for i, part in enumerate(response_parts):
                yield {
                    "model": model,
                    "created_at": datetime.now().isoformat(),
                    "response": part,
                    "done": i == len(response_parts) - 1,
                }
        else:
            # Single response
            mock_response = MockOllamaResponse(
                model=model,
                response=f"Mock response for prompt: {prompt[:50]}...",
            )
            yield mock_response.to_dict()
    
    async def list_models(self) -> Dict[str, Any]:
        """Mock list_models method."""
        if self.scenario == OllamaMockScenario.CONNECTION_ERROR:
            raise AIError("Mock connection error")
        
        elif self.scenario == OllamaMockScenario.EMPTY_MODELS:
            return {"models": []}
        
        # Return mock models
        return {
            "models": [
                {
                    "name": model.name,
                    "size": str(model.size),  # ModelListResponse expects string
                    "digest": model.digest,
                    "modified_at": model.modified_at.isoformat() if model.modified_at else None,
                    "details": getattr(model, 'details', {}),
                }
                for model in self.models
            ]
        }
    
    async def show_model_info(self, model: str) -> Dict[str, Any]:
        """Mock show_model_info method."""
        if self.scenario == OllamaMockScenario.MODEL_NOT_FOUND:
            raise ModelNotAvailableError(model)
        
        # Find model in list
        for m in self.models:
            if m.name == model:
                return {
                    "name": m.name,
                    "modelfile": f"FROM {m.name}\nPARAMETER temperature 0.7",
                    "parameters": "temperature 0.7\nstop [INST]",
                    "template": "{{ .System }}\n{{ .Prompt }}",
                    "details": m.details,
                }
        
        raise ModelNotAvailableError(model)
    
    async def pull_model(self, model: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Mock pull_model method."""
        if self.scenario == OllamaMockScenario.CONNECTION_ERROR:
            raise AIError("Mock connection error")
        
        # Simulate pulling progress
        stages = [
            {"status": "pulling manifest"},
            {"status": "pulling model", "digest": "sha256:abc123", "total": 1000000},
            {"status": "pulling model", "digest": "sha256:abc123", "completed": 500000, "total": 1000000},
            {"status": "pulling model", "digest": "sha256:abc123", "completed": 1000000, "total": 1000000},
            {"status": "verifying sha256 digest"},
            {"status": "writing manifest"},
            {"status": "success"},
        ]
        
        for stage in stages:
            yield stage
            await asyncio.sleep(0.1)
    
    def close(self) -> None:
        """Mock close method."""
        pass
    
    def is_available(self) -> bool:
        """Mock is_available method."""
        if self.scenario in [OllamaMockScenario.CONNECTION_ERROR, OllamaMockScenario.SERVER_ERROR]:
            return False
        return True
    
    def get_models(self) -> MockOllamaResponse:
        """Mock synchronous get_models method."""
        # Return a mock response directly
        if self.scenario == OllamaMockScenario.CONNECTION_ERROR:
            return MockOllamaResponse(
                success=False,
                status_code=500,
                data=None,
                error_message="Mock connection error",
                response_time=0.1
            )
        elif self.scenario == OllamaMockScenario.EMPTY_MODELS:
            return MockOllamaResponse(
                success=True,
                status_code=200,
                data={"models": []},
                response_time=0.1
            )
        
        # Return mock models
        model_data = {
            "models": [
                {
                    "name": model.name,
                    "size": str(model.size),  # ModelListResponse expects string
                    "digest": model.digest,
                    "modified_at": model.modified_at.isoformat() if model.modified_at else None,
                }
                for model in self.models
            ]
        }
        
        return MockOllamaResponse(
            success=True,
            status_code=200,
            data=model_data,
            response_time=0.1
        )


class MockOllamaDetector:
    """Mock implementation of OllamaDetector."""
    
    def __init__(
        self,
        is_installed: bool = True,
        is_running: bool = True,
        is_serving: bool = True,
        version: str = "0.1.24",
        service_url: str = "http://localhost:11434",
        error_message: Optional[str] = None,
    ):
        """Initialize mock detector."""
        self.is_installed = is_installed
        self.is_running = is_running
        self.is_serving = is_serving
        self.version = version
        self.service_url = service_url
        self.error_message = error_message
        self.detect_called = False
        
    def detect(self) -> OllamaStatus:
        """Mock detect method."""
        self.detect_called = True
        
        return OllamaStatus(
            is_installed=self.is_installed,
            is_running=self.is_running,
            version=self.version if self.is_installed else None,
            binary_path=Path("/usr/local/bin/ollama") if self.is_installed else None,
            service_url=self.service_url,
            detected_at=datetime.now(),
            error_message=self.error_message,
        )
    
    def _check_service_endpoint(self) -> bool:
        """Mock service endpoint check."""
        return self.is_serving