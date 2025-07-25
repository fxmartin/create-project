# ABOUTME: GUI tests for enhanced progress dialog functionality
# ABOUTME: Tests detailed progress updates, time estimation, and phase tracking

"""
GUI tests for enhanced progress dialog.

This module tests the enhanced progress dialog features including detailed
progress updates, time estimation, and phase tracking.
"""

import pytest
from PyQt6.QtWidgets import QApplication

from create_project.core.progress import DetailedProgress
from create_project.gui.widgets.progress_dialog import ProgressDialog


class TestEnhancedProgressDialog:
    """Test enhanced ProgressDialog features."""

    def test_detailed_progress_update(self, qtbot):
        """Test updating dialog with DetailedProgress."""
        dialog = ProgressDialog()
        qtbot.addWidget(dialog)
        dialog.show()

        # Create detailed progress
        progress = DetailedProgress(
            percentage=45,
            message="Rendering template files...",
            current_step=3,
            total_steps=6,
            phase="file_rendering",
            time_elapsed=15.5,
            estimated_remaining=18.2,
            sub_progress="Processing README.md"
        )

        # Update dialog
        dialog.update_detailed_progress(progress)

        # Verify updates
        assert dialog.progress_bar.value() == 45
        assert "Rendering template files" in dialog.status_label.text()
        assert "File Rendering" in dialog.phase_label.text()
        assert "0:15" in dialog.time_label.text()
        assert "0:18" in dialog.remaining_label.text()
        assert "(45%)" in dialog.windowTitle()

    def test_phase_formatting(self, qtbot):
        """Test phase name formatting."""
        dialog = ProgressDialog()
        qtbot.addWidget(dialog)

        test_cases = [
            ("validation", "Validation"),
            ("directory_creation", "Directory Creation"),
            ("file_rendering", "File Rendering"),
            ("git_initialization", "Git Initialization"),
            ("venv_creation", "Venv Creation"),
            ("post_commands", "Post Commands")
        ]

        for phase_id, expected_text in test_cases:
            progress = DetailedProgress(
                percentage=50,
                message="Test",
                phase=phase_id
            )
            dialog.update_detailed_progress(progress)
            assert expected_text in dialog.phase_label.text()

    def test_time_formatting(self, qtbot):
        """Test time display formatting."""
        dialog = ProgressDialog()
        qtbot.addWidget(dialog)

        # Test various time values
        test_cases = [
            (0, "0:00"),
            (59, "0:59"),
            (60, "1:00"),
            (125, "2:05"),
            (3661, "61:01")  # Over an hour
        ]

        for elapsed_seconds, expected_display in test_cases:
            progress = DetailedProgress(
                percentage=50,
                message="Test",
                time_elapsed=elapsed_seconds
            )
            dialog.update_detailed_progress(progress)
            assert expected_display in dialog.time_label.text()

    def test_no_remaining_time(self, qtbot):
        """Test display when no remaining time estimate."""
        dialog = ProgressDialog()
        qtbot.addWidget(dialog)

        progress = DetailedProgress(
            percentage=10,
            message="Starting...",
            time_elapsed=5,
            estimated_remaining=None
        )

        dialog.update_detailed_progress(progress)
        assert "--:--" in dialog.remaining_label.text()

    def test_sub_progress_logging(self, qtbot):
        """Test sub-progress entries in log."""
        dialog = ProgressDialog()
        qtbot.addWidget(dialog)

        # Update with sub-progress
        progress = DetailedProgress(
            percentage=50,
            message="Main task",
            sub_progress="Processing file 3 of 10"
        )

        dialog.update_detailed_progress(progress)

        log_text = dialog.log_display.toPlainText()
        assert "→ Processing file 3 of 10" in log_text

    def test_progress_during_cancellation(self, qtbot):
        """Test that progress updates are ignored after cancellation."""
        dialog = ProgressDialog()
        qtbot.addWidget(dialog)
        dialog.show()

        # Set cancelled state
        dialog._cancelled = True

        # Try to update
        progress = DetailedProgress(
            percentage=75,
            message="Should not appear"
        )

        dialog.update_detailed_progress(progress)

        # Progress should not update
        assert dialog.progress_bar.value() != 75
        assert "Should not appear" not in dialog.status_label.text()

    @pytest.mark.skipif(
        not hasattr(QApplication, "setHighDpiScaleFactorRoundingPolicy"),
        reason="High DPI features not available"
    )
    def test_high_dpi_rendering(self, qtbot):
        """Test dialog renders correctly on high DPI displays."""
        dialog = ProgressDialog()
        qtbot.addWidget(dialog)
        dialog.show()

        # Update with detailed progress
        progress = DetailedProgress(
            percentage=60,
            message="Testing high DPI",
            phase="validation",
            time_elapsed=10,
            estimated_remaining=15
        )

        dialog.update_detailed_progress(progress)

        # Verify all elements are visible
        assert dialog.phase_label.isVisible()
        assert dialog.time_label.isVisible()
        assert dialog.remaining_label.isVisible()

        # Check font sizes are readable
        phase_font = dialog.phase_label.font()
        assert phase_font.pointSize() >= 10 or phase_font.pixelSize() >= 10
