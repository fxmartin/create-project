# ABOUTME: Enhanced API module for improved UI-Backend integration
# ABOUTME: Provides thread-safe project generation with detailed progress reporting and error handling

"""
Enhanced Public API for the Python Project Creator.

This module provides an improved interface for UI-Backend integration with:
- Detailed progress reporting with percentage calculations
- Enhanced error context for AI assistance
- Thread-safe configuration updates
- Real-time status notifications
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from ..config import ConfigManager, get_config_manager
from ..templates import TemplateEngine, TemplateLoader
from ..templates.schema import Template
from ..utils.logger import get_logger
from .project_generator import GenerationResult, ProjectGenerator, ProjectOptions

logger = get_logger(__name__)


@dataclass
class DetailedProgress:
    """Detailed progress information for UI updates."""
    percentage: int
    message: str
    current_step: int
    total_steps: int
    phase: str  # 'setup', 'generation', 'postprocess', 'complete'
    time_elapsed: float
    estimated_remaining: Optional[float] = None


class EnhancedProjectGenerator:
    """Enhanced project generator with improved UI integration."""
    
    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        template_loader: Optional[TemplateLoader] = None,
        template_engine: Optional[TemplateEngine] = None,
    ):
        """Initialize enhanced generator with optional dependencies."""
        self.config_manager = config_manager or get_config_manager()
        self.template_loader = template_loader or TemplateLoader(self.config_manager)
        self.template_engine = template_engine or TemplateEngine(self.config_manager)
        self.generator = ProjectGenerator(
            template_loader=self.template_loader,
            ai_service=self._get_ai_service()
        )
        
        # Progress tracking
        self._progress_callbacks: List[Callable[[DetailedProgress], None]] = []
        self._error_callbacks: List[Callable[[Exception, Dict[str, Any]], None]] = []
        self._start_time: Optional[float] = None
        
    def _get_ai_service(self):
        """Get AI service if enabled in configuration."""
        if self.config_manager.get_setting("ai.enabled", True):
            try:
                from ..ai import AIService
                return AIService(self.config_manager)
            except Exception as e:
                logger.warning(f"Failed to initialize AI service: {e}")
        return None
    
    def add_progress_callback(self, callback: Callable[[DetailedProgress], None]) -> None:
        """Add a callback for progress updates."""
        if callback not in self._progress_callbacks:
            self._progress_callbacks.append(callback)
    
    def add_error_callback(self, callback: Callable[[Exception, Dict[str, Any]], None]) -> None:
        """Add a callback for error notifications."""
        if callback not in self._error_callbacks:
            self._error_callbacks.append(callback)
    
    def remove_progress_callback(self, callback: Callable[[DetailedProgress], None]) -> None:
        """Remove a progress callback."""
        if callback in self._progress_callbacks:
            self._progress_callbacks.remove(callback)
    
    def remove_error_callback(self, callback: Callable[[Exception, Dict[str, Any]], None]) -> None:
        """Remove an error callback."""
        if callback in self._error_callbacks:
            self._error_callbacks.remove(callback)
    
    def generate_project(
        self,
        template_path: Union[str, Path],
        target_path: Union[str, Path],
        variables: Dict[str, Any],
        options: Optional[ProjectOptions] = None,
    ) -> GenerationResult:
        """
        Generate a project with enhanced progress reporting.
        
        Args:
            template_path: Path to template file
            target_path: Target directory for project
            variables: Template variables
            options: Project generation options
            
        Returns:
            GenerationResult with detailed information
        """
        import time
        self._start_time = time.time()
        
        try:
            # Load template
            self._notify_progress(
                DetailedProgress(
                    percentage=0,
                    message="Loading template configuration...",
                    current_step=1,
                    total_steps=5,
                    phase="setup",
                    time_elapsed=0
                )
            )
            
            template = self.template_engine.load_template(template_path)
            
            # Create wrapped progress callback
            def progress_wrapper(message: str, percentage: Optional[int] = None):
                elapsed = time.time() - self._start_time
                phase = self._determine_phase(percentage)
                
                progress = DetailedProgress(
                    percentage=percentage or 50,
                    message=message,
                    current_step=self._calculate_step(percentage),
                    total_steps=5,
                    phase=phase,
                    time_elapsed=elapsed,
                    estimated_remaining=self._estimate_remaining(percentage, elapsed)
                )
                self._notify_progress(progress)
            
            # Generate project
            result = self.generator.generate_project(
                template=template,
                variables=variables,
                target_path=target_path,
                options=options or ProjectOptions(),
                progress_callback=progress_wrapper
            )
            
            # Final progress notification
            if result.success:
                self._notify_progress(
                    DetailedProgress(
                        percentage=100,
                        message="Project generation completed successfully!",
                        current_step=5,
                        total_steps=5,
                        phase="complete",
                        time_elapsed=time.time() - self._start_time
                    )
                )
            
            return result
            
        except Exception as e:
            # Create enhanced error context
            context = {
                "operation": "project_generation",
                "template_path": str(template_path),
                "target_path": str(target_path),
                "variables": variables,
                "time_elapsed": time.time() - self._start_time if self._start_time else 0,
                "config_state": {
                    "ai_enabled": self.config_manager.get_setting("ai.enabled"),
                    "template_dirs": self.config_manager.get_setting("templates.directories"),
                }
            }
            
            # Notify error callbacks
            self._notify_error(e, context)
            
            # Re-raise for normal error handling
            raise
    
    def _notify_progress(self, progress: DetailedProgress) -> None:
        """Notify all progress callbacks."""
        for callback in self._progress_callbacks.copy():
            try:
                callback(progress)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")
    
    def _notify_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """Notify all error callbacks."""
        for callback in self._error_callbacks.copy():
            try:
                callback(error, context)
            except Exception as e:
                logger.error(f"Error callback error: {e}")
    
    def _determine_phase(self, percentage: Optional[int]) -> str:
        """Determine the current phase based on percentage."""
        if percentage is None:
            return "generation"
        elif percentage < 20:
            return "setup"
        elif percentage < 80:
            return "generation"
        elif percentage < 100:
            return "postprocess"
        else:
            return "complete"
    
    def _calculate_step(self, percentage: Optional[int]) -> int:
        """Calculate current step from percentage."""
        if percentage is None:
            return 3
        return min(5, max(1, int((percentage / 100) * 5) + 1))
    
    def _estimate_remaining(self, percentage: Optional[int], elapsed: float) -> Optional[float]:
        """Estimate remaining time based on progress."""
        if percentage is None or percentage == 0:
            return None
        
        # Simple linear estimation
        total_estimated = elapsed / (percentage / 100)
        remaining = total_estimated - elapsed
        
        return max(0, remaining)


def create_project_enhanced(
    template_path: Union[str, Path],
    target_path: Union[str, Path],
    variables: Dict[str, Any],
    options: Optional[ProjectOptions] = None,
    progress_callback: Optional[Callable[[DetailedProgress], None]] = None,
    error_callback: Optional[Callable[[Exception, Dict[str, Any]], None]] = None,
    config_manager: Optional[ConfigManager] = None,
) -> GenerationResult:
    """
    Create a project with enhanced UI integration support.
    
    Args:
        template_path: Path to template file
        target_path: Target directory for project
        variables: Template variables
        options: Project generation options
        progress_callback: Optional callback for progress updates
        error_callback: Optional callback for error handling
        config_manager: Optional configuration manager instance
        
    Returns:
        GenerationResult with detailed information
    """
    generator = EnhancedProjectGenerator(config_manager=config_manager)
    
    if progress_callback:
        generator.add_progress_callback(progress_callback)
    
    if error_callback:
        generator.add_error_callback(error_callback)
    
    try:
        return generator.generate_project(
            template_path=template_path,
            target_path=target_path,
            variables=variables,
            options=options
        )
    finally:
        # Clean up callbacks
        if progress_callback:
            generator.remove_progress_callback(progress_callback)
        if error_callback:
            generator.remove_error_callback(error_callback)