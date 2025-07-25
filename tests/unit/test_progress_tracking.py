# ABOUTME: Unit tests for progress tracking utilities
# ABOUTME: Tests DetailedProgress, ProgressTracker, and StepTracker classes

"""
Unit tests for progress tracking utilities.

This module tests the progress tracking components including DetailedProgress,
ProgressTracker, and StepTracker for accurate progress calculation and reporting.
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from create_project.core.progress import DetailedProgress, ProgressTracker, StepTracker


class TestDetailedProgress:
    """Test DetailedProgress dataclass."""
    
    def test_basic_creation(self):
        """Test creating a DetailedProgress instance."""
        progress = DetailedProgress(
            percentage=50,
            message="Processing files",
            current_step=5,
            total_steps=10,
            phase="file_rendering",
            time_elapsed=30.5,
            estimated_remaining=25.0
        )
        
        assert progress.percentage == 50
        assert progress.message == "Processing files"
        assert progress.current_step == 5
        assert progress.total_steps == 10
        assert progress.phase == "file_rendering"
        assert progress.time_elapsed == 30.5
        assert progress.estimated_remaining == 25.0
        assert progress.sub_progress is None
    
    def test_percentage_clamping(self):
        """Test that percentage is clamped to 0-100 range."""
        # Test over 100
        progress = DetailedProgress(percentage=150, message="Test")
        assert progress.percentage == 100
        
        # Test under 0
        progress = DetailedProgress(percentage=-50, message="Test")
        assert progress.percentage == 0
        
        # Test normal range
        progress = DetailedProgress(percentage=75, message="Test")
        assert progress.percentage == 75


class TestProgressTracker:
    """Test ProgressTracker class."""
    
    def test_phase_management(self):
        """Test starting and completing phases."""
        tracker = ProgressTracker()
        
        # Start a phase
        tracker.start_phase("validation")
        assert tracker.current_phase == "validation"
        assert "validation" in tracker.phase_start_times
        assert tracker.phase_progress["validation"] == 0.0
        
        # Update phase progress
        tracker.update_phase_progress(0.5, "Validating inputs")
        assert tracker.phase_progress["validation"] == 0.5
        
        # Complete phase
        tracker.complete_phase()
        assert tracker.phase_progress["validation"] == 1.0
        assert "validation" in tracker.completed_phases
    
    def test_overall_progress_calculation(self):
        """Test calculation of overall progress."""
        tracker = ProgressTracker()
        
        # Complete validation phase (5% weight)
        tracker.start_phase("validation")
        tracker.complete_phase()
        
        progress = tracker.get_overall_progress()
        assert progress.percentage == 5  # 5% of total
        assert progress.phase == "validation"
        assert progress.current_step == 1
        assert progress.total_steps == 6
        
        # Partially complete directory creation (20% weight)
        tracker.start_phase("directory_creation")
        tracker.update_phase_progress(0.5)
        
        progress = tracker.get_overall_progress()
        # 5% (validation) + 10% (half of directory_creation)
        assert progress.percentage == 15
        assert progress.phase == "directory_creation"
    
    def test_time_estimation(self):
        """Test time estimation in progress tracking."""
        # Create tracker first
        tracker = ProgressTracker()
        
        # Manually set start time for testing
        tracker.start_time = 0
        
        # Simulate phases with manual time tracking
        tracker.start_phase("validation")
        tracker.phase_start_times["validation"] = 0
        tracker.complete_phase()
        
        tracker.start_phase("directory_creation")
        tracker.phase_start_times["directory_creation"] = 5
        tracker.complete_phase()
        
        # Override time for progress calculation
        with patch('create_project.core.progress.time.time', return_value=10):
            progress = tracker.get_overall_progress()
            assert progress.time_elapsed == 10
            # 25% done in 10 seconds, so ~30 seconds remaining
            assert progress.estimated_remaining is not None
            assert 25 <= progress.estimated_remaining <= 35
    
    def test_progress_callback(self):
        """Test progress callback functionality."""
        callback = MagicMock()
        tracker = ProgressTracker(progress_callback=callback)
        
        tracker.start_phase("validation")
        
        # Verify callback was called
        assert callback.call_count > 0
        progress_arg = callback.call_args[0][0]
        assert isinstance(progress_arg, DetailedProgress)
        assert "validation" in progress_arg.message.lower()


class TestStepTracker:
    """Test StepTracker class."""
    
    def test_basic_tracking(self):
        """Test basic step tracking."""
        tracker = StepTracker(total_items=10, phase_name="file_rendering")
        
        assert tracker.total_items == 10
        assert tracker.completed_items == 0
        assert tracker.get_progress() == 0.0
        
        # Complete some items
        tracker.complete_item("file1.py")
        tracker.complete_item("file2.py")
        
        assert tracker.completed_items == 2
        assert tracker.get_progress() == 0.2
    
    def test_time_tracking(self):
        """Test time tracking in StepTracker."""
        with patch('create_project.core.progress.time.time') as mock_time:
            mock_time.return_value = 0
            tracker = StepTracker(total_items=5, phase_name="test")
            
            # Complete 2 items in 10 seconds
            mock_time.return_value = 10
            tracker.complete_item()
            tracker.complete_item()
            
            assert tracker.get_elapsed_time() == 10
            
            # Should estimate 15 seconds remaining (3 items * 5 sec/item)
            remaining = tracker.estimate_remaining_time()
            assert remaining is not None
            assert 14 <= remaining <= 16
    
    def test_integration_with_progress_tracker(self):
        """Test StepTracker integration with ProgressTracker."""
        progress_tracker = ProgressTracker()
        progress_tracker.start_phase("file_rendering")
        
        step_tracker = StepTracker(
            total_items=4,
            phase_name="file_rendering",
            progress_tracker=progress_tracker
        )
        
        # Complete items
        step_tracker.complete_item("file1.py")
        assert progress_tracker.phase_progress["file_rendering"] == 0.25
        
        step_tracker.complete_item("file2.py")
        assert progress_tracker.phase_progress["file_rendering"] == 0.5
    
    def test_empty_tracker(self):
        """Test StepTracker with no items."""
        tracker = StepTracker(total_items=0, phase_name="empty")
        
        assert tracker.get_progress() == 0.0
        assert tracker.estimate_remaining_time() is None
        
        # Should handle completion gracefully
        tracker.complete_item("phantom")
        assert tracker.completed_items == 1
        assert tracker.get_progress() == 1.0  # Uses max(1, total_items)


class TestIntegration:
    """Test integration between progress tracking components."""
    
    def test_full_project_generation_tracking(self):
        """Test tracking a complete project generation."""
        progress_updates = []
        
        def capture_progress(progress: DetailedProgress):
            progress_updates.append({
                "percentage": progress.percentage,
                "phase": progress.phase,
                "message": progress.message
            })
        
        tracker = ProgressTracker(progress_callback=capture_progress)
        
        # Simulate project generation
        # 1. Validation
        tracker.start_phase("validation")
        tracker.complete_phase()
        
        # 2. Directory creation with steps
        tracker.start_phase("directory_creation")
        dir_tracker = StepTracker(3, "directory_creation", tracker)
        dir_tracker.complete_item("src")
        dir_tracker.complete_item("tests")
        dir_tracker.complete_item("docs")
        tracker.complete_phase()
        
        # 3. File rendering with steps
        tracker.start_phase("file_rendering")
        file_tracker = StepTracker(5, "file_rendering", tracker)
        for i in range(5):
            file_tracker.complete_item(f"file{i}.py")
        tracker.complete_phase()
        
        # Verify progress was tracked correctly
        assert len(progress_updates) > 0
        
        # Check final progress
        final_progress = tracker.get_overall_progress()
        assert final_progress.percentage == 70  # 5% + 20% + 45%
        assert final_progress.current_step == 3
        assert len(tracker.completed_phases) == 3
