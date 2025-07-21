# ABOUTME: Ollama installation detection with cross-platform support and caching
# ABOUTME: Auto-detects Ollama binary, checks service status, and provides version information

import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta

import httpx
from structlog import get_logger

from .exceptions import OllamaNotFoundError


@dataclass
class OllamaStatus:
    """Status information about Ollama installation."""
    
    is_installed: bool
    is_running: bool
    version: Optional[str]
    binary_path: Optional[Path]
    service_url: str
    detected_at: datetime
    error_message: Optional[str] = None


class OllamaDetector:
    """Cross-platform Ollama installation detector with caching."""
    
    DEFAULT_SERVICE_URL = "http://localhost:11434"
    CACHE_TTL_MINUTES = 5
    COMMON_INSTALL_PATHS = [
        "/usr/local/bin/ollama",
        "/usr/bin/ollama", 
        "/opt/homebrew/bin/ollama",
        "~/.local/bin/ollama",
        "/Applications/Ollama.app/Contents/Resources/ollama",  # macOS app
    ]
    
    def __init__(self, service_url: Optional[str] = None):
        """Initialize detector with optional custom service URL."""
        self.service_url = service_url or self.DEFAULT_SERVICE_URL
        self.logger = get_logger("ai.ollama_detector")
        self._cache: Optional[OllamaStatus] = None
        self._cache_lock = threading.RLock()
        
    def detect(self, force_refresh: bool = False) -> OllamaStatus:
        """
        Detect Ollama installation status with caching.
        
        Args:
            force_refresh: If True, bypass cache and re-detect
            
        Returns:
            OllamaStatus with detection results
        """
        with self._cache_lock:
            # Check cache validity
            if not force_refresh and self._is_cache_valid():
                self.logger.debug("Using cached Ollama status")
                return self._cache
                
            self.logger.info("Detecting Ollama installation", service_url=self.service_url)
            
            # Perform fresh detection
            status = self._detect_ollama()
            
            # Cache results
            self._cache = status
            
            self.logger.info(
                "Ollama detection complete",
                is_installed=status.is_installed,
                is_running=status.is_running,
                version=status.version,
                binary_path=str(status.binary_path) if status.binary_path else None
            )
            
            return status
            
    def _is_cache_valid(self) -> bool:
        """Check if cached status is still valid."""
        if self._cache is None:
            return False
            
        cache_age = datetime.now() - self._cache.detected_at
        return cache_age < timedelta(minutes=self.CACHE_TTL_MINUTES)
        
    def _detect_ollama(self) -> OllamaStatus:
        """Perform actual Ollama detection."""
        binary_path = self._find_binary()
        version = None
        is_installed = binary_path is not None
        error_message = None
        
        # Get version if binary found
        if is_installed:
            try:
                version = self._get_version(binary_path)
            except Exception as e:
                self.logger.warning("Failed to get Ollama version", error=str(e))
                error_message = f"Version detection failed: {e}"
        else:
            error_message = "Ollama binary not found in PATH or common locations"
            
        # Check if service is running
        is_running = self._check_service_health()
        
        return OllamaStatus(
            is_installed=is_installed,
            is_running=is_running,
            version=version,
            binary_path=binary_path,
            service_url=self.service_url,
            detected_at=datetime.now(),
            error_message=error_message
        )
        
    def _find_binary(self) -> Optional[Path]:
        """Find Ollama binary in PATH and common locations."""
        # First check PATH
        binary_path = shutil.which("ollama")
        if binary_path:
            self.logger.debug("Found Ollama in PATH", path=binary_path)
            return Path(binary_path)
            
        # Check common installation locations
        for path_str in self.COMMON_INSTALL_PATHS:
            path = Path(path_str).expanduser()
            if path.exists() and path.is_file():
                # Check if executable
                try:
                    if path.stat().st_mode & 0o111:  # Has execute permission
                        self.logger.debug("Found Ollama at common location", path=str(path))
                        return path
                except OSError:
                    continue
                    
        self.logger.debug("Ollama binary not found")
        return None
        
    def _get_version(self, binary_path: Path) -> Optional[str]:
        """Get Ollama version from binary."""
        try:
            result = subprocess.run(
                [str(binary_path), "--version"],
                capture_output=True,
                text=True,
                timeout=10  # 10 second timeout
            )
            
            if result.returncode == 0:
                # Parse version from output (usually "ollama version x.y.z")
                version_line = result.stdout.strip()
                if version_line:
                    parts = version_line.split()
                    if len(parts) >= 3 and parts[0] == "ollama" and parts[1] == "version":
                        return parts[2]
                    # Fallback: return full line
                    return version_line
                    
            self.logger.warning(
                "Ollama version command failed",
                returncode=result.returncode,
                stderr=result.stderr
            )
            return None
            
        except subprocess.TimeoutExpired:
            self.logger.warning("Ollama version command timed out")
            return None
        except Exception as e:
            self.logger.warning("Failed to execute Ollama version command", error=str(e))
            return None
            
    def _check_service_health(self) -> bool:
        """Check if Ollama service is running via HTTP health check."""
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.service_url}/api/tags")
                
                # Service is running if we get any response (even error responses)
                # The /api/tags endpoint should exist even with no models
                is_running = response.status_code in [200, 404]
                
                if is_running:
                    self.logger.debug("Ollama service is running", status_code=response.status_code)
                else:
                    self.logger.debug("Ollama service returned unexpected status", status_code=response.status_code)
                    
                return is_running
                
        except httpx.ConnectError:
            self.logger.debug("Ollama service not reachable", url=self.service_url)
            return False
        except httpx.TimeoutException:
            self.logger.warning("Ollama service health check timed out")
            return False
        except Exception as e:
            self.logger.warning("Ollama service health check failed", error=str(e))
            return False
            
    def ensure_available(self) -> OllamaStatus:
        """
        Ensure Ollama is available, raising exception if not.
        
        Returns:
            OllamaStatus if available
            
        Raises:
            OllamaNotFoundError: If Ollama is not installed or not running
        """
        status = self.detect()
        
        if not status.is_installed:
            raise OllamaNotFoundError(
                "Ollama is not installed. Please install Ollama from https://ollama.ai/"
            )
            
        if not status.is_running:
            raise OllamaNotFoundError(
                "Ollama is installed but not running. Please start the Ollama service."
            )
            
        return status
        
    def clear_cache(self) -> None:
        """Clear cached detection results."""
        with self._cache_lock:
            self._cache = None
            self.logger.debug("Cleared Ollama detection cache")