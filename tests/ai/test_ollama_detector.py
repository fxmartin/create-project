# ABOUTME: Comprehensive tests for Ollama detection with mocking and cross-platform scenarios
# ABOUTME: Tests binary detection, service health checks, caching, and error conditions

import subprocess
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from typing import Optional

import httpx
import pytest

from create_project.ai.ollama_detector import OllamaDetector, OllamaStatus
from create_project.ai.exceptions import OllamaNotFoundError


class TestOllamaStatus:
    """Test OllamaStatus dataclass."""
    
    def test_status_creation(self):
        """Test basic status object creation."""
        status = OllamaStatus(
            is_installed=True,
            is_running=True,
            version="0.1.0",
            binary_path=Path("/usr/local/bin/ollama"),
            service_url="http://localhost:11434",
            detected_at=datetime.now()
        )
        
        assert status.is_installed is True
        assert status.is_running is True
        assert status.version == "0.1.0"
        assert status.binary_path == Path("/usr/local/bin/ollama")
        assert status.service_url == "http://localhost:11434"
        assert status.error_message is None


class TestOllamaDetector:
    """Test OllamaDetector class."""
    
    def test_initialization_default_url(self):
        """Test detector initialization with default URL."""
        detector = OllamaDetector()
        assert detector.service_url == "http://localhost:11434"
        assert detector._cache is None
        
    def test_initialization_custom_url(self):
        """Test detector initialization with custom URL."""
        custom_url = "http://custom-host:8080"
        detector = OllamaDetector(service_url=custom_url)
        assert detector.service_url == custom_url
        
    @patch('shutil.which')
    @patch.object(OllamaDetector, '_get_version')
    @patch.object(OllamaDetector, '_check_service_health')
    def test_detect_ollama_in_path(self, mock_health, mock_version, mock_which):
        """Test detection when Ollama is in PATH."""
        # Setup mocks
        mock_which.return_value = "/usr/local/bin/ollama"
        mock_version.return_value = "0.1.0" 
        mock_health.return_value = True
        
        detector = OllamaDetector()
        status = detector.detect()
        
        assert status.is_installed is True
        assert status.is_running is True
        assert status.version == "0.1.0"
        assert status.binary_path == Path("/usr/local/bin/ollama")
        assert status.error_message is None
        
    @patch('shutil.which')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_file')
    @patch('pathlib.Path.stat')
    @patch.object(OllamaDetector, '_get_version')
    @patch.object(OllamaDetector, '_check_service_health')
    def test_detect_ollama_common_location(self, mock_health, mock_version, 
                                         mock_stat, mock_is_file, mock_exists, mock_which):
        """Test detection from common installation locations."""
        # Setup mocks - not in PATH
        mock_which.return_value = None
        
        # Mock file checks for first common path
        mock_exists.side_effect = lambda: True if mock_exists.call_count == 1 else False
        mock_is_file.return_value = True
        
        # Mock file permissions (executable)
        mock_stat.return_value.st_mode = 0o755
        
        mock_version.return_value = "0.1.0"
        mock_health.return_value = True
        
        detector = OllamaDetector()
        status = detector.detect()
        
        assert status.is_installed is True
        assert status.binary_path == Path("/usr/local/bin/ollama")
        
    @patch('shutil.which')
    @patch('pathlib.Path.exists')
    @patch.object(OllamaDetector, '_check_service_health')
    def test_detect_ollama_not_found(self, mock_health, mock_exists, mock_which):
        """Test detection when Ollama is not found."""
        # Setup mocks - not found anywhere
        mock_which.return_value = None
        mock_exists.return_value = False
        mock_health.return_value = False
        
        detector = OllamaDetector()
        status = detector.detect()
        
        assert status.is_installed is False
        assert status.is_running is False
        assert status.version is None
        assert status.binary_path is None
        assert "not found" in status.error_message
        
    @patch.object(OllamaDetector, '_detect_ollama')
    def test_caching_behavior(self, mock_detect):
        """Test that detection results are cached properly."""
        # Create mock status
        mock_status = OllamaStatus(
            is_installed=True,
            is_running=True,
            version="0.1.0",
            binary_path=Path("/usr/local/bin/ollama"),
            service_url="http://localhost:11434",
            detected_at=datetime.now()
        )
        mock_detect.return_value = mock_status
        
        detector = OllamaDetector()
        
        # First call should trigger detection
        status1 = detector.detect()
        assert mock_detect.call_count == 1
        
        # Second call should use cache
        status2 = detector.detect()
        assert mock_detect.call_count == 1  # Still 1, not called again
        assert status1 is status2  # Same object from cache
        
    @patch.object(OllamaDetector, '_detect_ollama')
    def test_cache_expiry(self, mock_detect):
        """Test that cache expires after TTL."""
        # Create mock status with old timestamp
        old_time = datetime.now() - timedelta(minutes=10)
        mock_status = OllamaStatus(
            is_installed=True,
            is_running=True, 
            version="0.1.0",
            binary_path=Path("/usr/local/bin/ollama"),
            service_url="http://localhost:11434",
            detected_at=old_time
        )
        mock_detect.return_value = mock_status
        
        detector = OllamaDetector()
        detector._cache = mock_status  # Manually set old cache
        
        # Should trigger fresh detection due to expired cache
        detector.detect()
        assert mock_detect.call_count == 1
        
    @patch.object(OllamaDetector, '_detect_ollama')
    def test_force_refresh(self, mock_detect):
        """Test force refresh bypasses cache."""
        mock_status = OllamaStatus(
            is_installed=True,
            is_running=True,
            version="0.1.0", 
            binary_path=Path("/usr/local/bin/ollama"),
            service_url="http://localhost:11434",
            detected_at=datetime.now()
        )
        mock_detect.return_value = mock_status
        
        detector = OllamaDetector()
        
        # First call
        detector.detect()
        assert mock_detect.call_count == 1
        
        # Force refresh should trigger new detection
        detector.detect(force_refresh=True)
        assert mock_detect.call_count == 2
        
    def test_clear_cache(self):
        """Test cache clearing functionality."""
        detector = OllamaDetector()
        
        # Set some cache data
        detector._cache = Mock()
        
        # Clear cache
        detector.clear_cache()
        
        assert detector._cache is None


class TestOllamaVersionDetection:
    """Test version detection functionality."""
    
    @patch('subprocess.run')
    def test_get_version_success(self, mock_run):
        """Test successful version extraction."""
        # Mock successful subprocess call
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "ollama version 0.1.0\n"
        mock_run.return_value = mock_result
        
        detector = OllamaDetector()
        version = detector._get_version(Path("/usr/local/bin/ollama"))
        
        assert version == "0.1.0"
        
    @patch('subprocess.run')
    def test_get_version_failure(self, mock_run):
        """Test version detection failure."""
        # Mock failed subprocess call
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "command not found"
        mock_run.return_value = mock_result
        
        detector = OllamaDetector()
        version = detector._get_version(Path("/usr/local/bin/ollama"))
        
        assert version is None
        
    @patch('subprocess.run')
    def test_get_version_timeout(self, mock_run):
        """Test version detection timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("ollama", 10)
        
        detector = OllamaDetector()
        version = detector._get_version(Path("/usr/local/bin/ollama"))
        
        assert version is None
        
    @patch('subprocess.run')
    def test_get_version_exception(self, mock_run):
        """Test version detection with general exception."""
        mock_run.side_effect = OSError("Permission denied")
        
        detector = OllamaDetector()
        version = detector._get_version(Path("/usr/local/bin/ollama"))
        
        assert version is None


class TestOllamaServiceHealthCheck:
    """Test service health check functionality."""
    
    @patch('httpx.Client')
    def test_service_running_success(self, mock_client_class):
        """Test successful service health check."""
        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client
        
        detector = OllamaDetector()
        is_running = detector._check_service_health()
        
        assert is_running is True
        
    @patch('httpx.Client')
    def test_service_running_404(self, mock_client_class):
        """Test service health check with 404 (acceptable)."""
        # Mock 404 response (service running, no models)
        mock_response = Mock()
        mock_response.status_code = 404
        
        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client
        
        detector = OllamaDetector()
        is_running = detector._check_service_health()
        
        assert is_running is True
        
    @patch('httpx.Client')
    def test_service_connection_error(self, mock_client_class):
        """Test service connection error."""
        mock_client = Mock()
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client
        
        detector = OllamaDetector()
        is_running = detector._check_service_health()
        
        assert is_running is False
        
    @patch('httpx.Client')
    def test_service_timeout(self, mock_client_class):
        """Test service timeout."""
        mock_client = Mock()
        mock_client.get.side_effect = httpx.TimeoutException("Request timeout")
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_class.return_value = mock_client
        
        detector = OllamaDetector()
        is_running = detector._check_service_health()
        
        assert is_running is False


class TestOllamaEnsureAvailable:
    """Test ensure_available functionality."""
    
    @patch.object(OllamaDetector, 'detect')
    def test_ensure_available_success(self, mock_detect):
        """Test ensure_available when Ollama is available."""
        mock_status = OllamaStatus(
            is_installed=True,
            is_running=True,
            version="0.1.0",
            binary_path=Path("/usr/local/bin/ollama"),
            service_url="http://localhost:11434",
            detected_at=datetime.now()
        )
        mock_detect.return_value = mock_status
        
        detector = OllamaDetector()
        status = detector.ensure_available()
        
        assert status is mock_status
        
    @patch.object(OllamaDetector, 'detect')
    def test_ensure_available_not_installed(self, mock_detect):
        """Test ensure_available when Ollama is not installed."""
        mock_status = OllamaStatus(
            is_installed=False,
            is_running=False,
            version=None,
            binary_path=None,
            service_url="http://localhost:11434",
            detected_at=datetime.now()
        )
        mock_detect.return_value = mock_status
        
        detector = OllamaDetector()
        
        with pytest.raises(OllamaNotFoundError) as exc_info:
            detector.ensure_available()
            
        assert "not installed" in str(exc_info.value)
        
    @patch.object(OllamaDetector, 'detect')
    def test_ensure_available_not_running(self, mock_detect):
        """Test ensure_available when Ollama is installed but not running."""
        mock_status = OllamaStatus(
            is_installed=True,
            is_running=False,
            version="0.1.0",
            binary_path=Path("/usr/local/bin/ollama"),
            service_url="http://localhost:11434",
            detected_at=datetime.now()
        )
        mock_detect.return_value = mock_status
        
        detector = OllamaDetector()
        
        with pytest.raises(OllamaNotFoundError) as exc_info:
            detector.ensure_available()
            
        assert "not running" in str(exc_info.value)


class TestThreadSafety:
    """Test thread safety of detector."""
    
    @patch.object(OllamaDetector, '_detect_ollama')
    def test_concurrent_detection(self, mock_detect):
        """Test concurrent detection calls are thread-safe."""
        # Mock detection with delay to simulate real detection
        def slow_detect():
            time.sleep(0.1)  # Small delay
            return OllamaStatus(
                is_installed=True,
                is_running=True,
                version="0.1.0",
                binary_path=Path("/usr/local/bin/ollama"),
                service_url="http://localhost:11434",
                detected_at=datetime.now()
            )
            
        mock_detect.side_effect = slow_detect
        
        detector = OllamaDetector()
        results = []
        
        def detect_worker():
            results.append(detector.detect())
            
        # Start multiple threads
        threads = [threading.Thread(target=detect_worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
            
        # Should only detect once due to caching
        assert mock_detect.call_count == 1
        assert len(results) == 5
        # All results should be the same object (from cache)
        assert all(r is results[0] for r in results[1:])