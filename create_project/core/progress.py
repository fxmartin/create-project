# ABOUTME: Progress tracking utilities for detailed project generation reporting
# ABOUTME: Provides dataclasses and helpers for granular progress updates with time estimation

"""
Progress tracking utilities for project generation.

This module provides dataclasses and utilities for tracking detailed progress
during project generation, including percentage completion, time estimation,
and phase tracking.
"""

import time
from dataclasses import dataclass, field
from typing import Optional, List, Callable


@dataclass
class DetailedProgress:
    """Detailed progress information for project generation.
    
    Attributes:
        percentage: Overall completion percentage (0-100)
        message: Current status message
        current_step: Current step number
        total_steps: Total number of steps
        phase: Current phase of generation
        time_elapsed: Time elapsed since start (seconds)
        estimated_remaining: Estimated time remaining (seconds)
        sub_progress: Optional sub-progress for nested operations
    """
    percentage: int
    message: str
    current_step: int = 0
    total_steps: int = 0
    phase: str = "initializing"
    time_elapsed: float = 0.0
    estimated_remaining: Optional[float] = None
    sub_progress: Optional[str] = None
    
    def __post_init__(self):
        # Ensure percentage is within valid range
        self.percentage = max(0, min(100, self.percentage))


@dataclass
class ProgressTracker:
    """Tracks progress across multiple phases of an operation.
    
    This class helps calculate accurate progress percentages and time estimates
    across different phases of project generation.
    """
    
    # Phase weights (percentage of total time)
    phase_weights: dict[str, float] = field(default_factory=lambda: {
        "validation": 5,
        "directory_creation": 20,
        "file_rendering": 45,
        "git_initialization": 10,
        "venv_creation": 15,
        "post_commands": 5,
    })
    
    # Current state
    start_time: float = field(default_factory=time.time)
    current_phase: str = "validation"
    phase_progress: dict[str, float] = field(default_factory=dict)
    phase_start_times: dict[str, float] = field(default_factory=dict)
    completed_phases: List[str] = field(default_factory=list)
    
    # Callbacks
    progress_callback: Optional[Callable[[DetailedProgress], None]] = None
    
    def start_phase(self, phase: str) -> None:
        """Start tracking a new phase.
        
        Args:
            phase: Name of the phase to start
        """
        self.current_phase = phase
        self.phase_start_times[phase] = time.time()
        self.phase_progress[phase] = 0.0
        
        # Report phase start
        self._report_progress(f"Starting {phase.replace('_', ' ').title()}...")
    
    def update_phase_progress(self, progress: float, message: str = "") -> None:
        """Update progress within the current phase.
        
        Args:
            progress: Progress within the phase (0.0 to 1.0)
            message: Optional status message
        """
        self.phase_progress[self.current_phase] = max(0.0, min(1.0, progress))
        
        if message:
            self._report_progress(message)
        else:
            self._report_progress(f"{self.current_phase.replace('_', ' ').title()}: {int(progress * 100)}%")
    
    def complete_phase(self, phase: Optional[str] = None) -> None:
        """Mark a phase as complete.
        
        Args:
            phase: Phase to complete (defaults to current phase)
        """
        phase = phase or self.current_phase
        self.phase_progress[phase] = 1.0
        if phase not in self.completed_phases:
            self.completed_phases.append(phase)
        
        self._report_progress(f"Completed {phase.replace('_', ' ').title()}")
    
    def get_current_phase(self) -> str:
        """Get the current phase name.
        
        Returns:
            Current phase name or "unknown"
        """
        return self.current_phase
    
    def get_overall_progress(self) -> DetailedProgress:
        """Calculate overall progress across all phases.
        
        Returns:
            DetailedProgress object with current status
        """
        # Calculate weighted progress
        total_weight = sum(self.phase_weights.values())
        weighted_progress = 0.0
        
        for phase, weight in self.phase_weights.items():
            phase_prog = self.phase_progress.get(phase, 0.0)
            weighted_progress += (phase_prog * weight) / total_weight
        
        # Calculate percentage
        percentage = int(weighted_progress * 100)
        
        # Calculate time elapsed
        time_elapsed = time.time() - self.start_time
        
        # Estimate remaining time
        estimated_remaining = None
        if percentage > 0 and percentage < 100:
            estimated_total = time_elapsed / (percentage / 100.0)
            estimated_remaining = estimated_total - time_elapsed
        
        # Count completed steps
        current_step = len(self.completed_phases)
        total_steps = len(self.phase_weights)
        
        return DetailedProgress(
            percentage=percentage,
            message=f"Phase: {self.current_phase.replace('_', ' ').title()}",
            current_step=current_step,
            total_steps=total_steps,
            phase=self.current_phase,
            time_elapsed=time_elapsed,
            estimated_remaining=estimated_remaining,
        )
    
    def _report_progress(self, message: str) -> None:
        """Report progress through callback.
        
        Args:
            message: Progress message
        """
        if self.progress_callback:
            progress = self.get_overall_progress()
            progress.message = message
            self.progress_callback(progress)


class StepTracker:
    """Tracks progress for operations with discrete steps.
    
    Useful for tracking progress when processing a known number of items
    (e.g., files to render, directories to create).
    """
    
    def __init__(
        self,
        total_items: int,
        phase_name: str,
        progress_tracker: Optional[ProgressTracker] = None,
    ):
        """Initialize step tracker.
        
        Args:
            total_items: Total number of items to process
            phase_name: Name of the phase these steps belong to
            progress_tracker: Parent progress tracker
        """
        self.total_items = total_items
        self.phase_name = phase_name
        self.progress_tracker = progress_tracker
        self.completed_items = 0
        self.start_time = time.time()
    
    def complete_item(self, item_name: str = "") -> None:
        """Mark an item as complete.
        
        Args:
            item_name: Optional name of the completed item
        """
        self.completed_items += 1
        progress = self.completed_items / max(1, self.total_items)
        
        message = f"Completed {self.completed_items}/{self.total_items}"
        if item_name:
            message += f": {item_name}"
        
        if self.progress_tracker:
            self.progress_tracker.update_phase_progress(progress, message)
    
    def get_progress(self) -> float:
        """Get current progress as a fraction.
        
        Returns:
            Progress from 0.0 to 1.0
        """
        return self.completed_items / max(1, self.total_items)
    
    def get_elapsed_time(self) -> float:
        """Get elapsed time since start.
        
        Returns:
            Elapsed time in seconds
        """
        return time.time() - self.start_time
    
    def estimate_remaining_time(self) -> Optional[float]:
        """Estimate remaining time based on current progress.
        
        Returns:
            Estimated remaining time in seconds, or None if cannot estimate
        """
        if self.completed_items == 0:
            return None
        
        elapsed = self.get_elapsed_time()
        avg_time_per_item = elapsed / self.completed_items
        remaining_items = self.total_items - self.completed_items
        
        return avg_time_per_item * remaining_items
