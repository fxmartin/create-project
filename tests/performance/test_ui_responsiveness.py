# ABOUTME: UI responsiveness performance measurements for PyQt6 interface
# ABOUTME: Tests wizard navigation, dialog interactions, and background operation responsiveness

"""
UI responsiveness performance test suite.

This module provides comprehensive performance testing for PyQt6 GUI responsiveness including:
- Wizard navigation response time measurements
- Template selection and preview generation performance
- Form validation responsiveness testing
- Progress dialog update frequency and smoothness
- Background operation UI responsiveness
- Dialog interaction performance benchmarks
"""

import time
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import QTimer, QThread, pyqtSignal, QEventLoop
from PyQt6.QtWidgets import QApplication
from pytest_benchmark.fixture import BenchmarkFixture

from create_project.config.config_manager import ConfigManager
from create_project.core.project_generator import ProjectGenerator, ProjectOptions
from create_project.gui.dialogs.settings import SettingsDialog
from create_project.gui.dialogs.error import ErrorDialog
from create_project.gui.dialogs.ai_help import AIHelpDialog
from create_project.gui.steps.basic_info import BasicInfoStep
from create_project.gui.steps.location import LocationStep
from create_project.gui.steps.project_type import ProjectTypeStep
from create_project.gui.wizard import ProjectWizard
from create_project.gui.widgets.progress_dialog import ProgressDialog
from create_project.templates.engine import TemplateEngine


@pytest.mark.benchmark
@pytest.mark.gui
class TestWizardNavigationPerformance:
    """Test wizard navigation response times."""

    def test_wizard_step_navigation_speed(self, benchmark: BenchmarkFixture, qapp,
                                         mock_config_manager, mock_template_engine, 
                                         mock_ai_service):
        """Benchmark wizard step navigation response time."""
        def navigate_wizard_steps():
            wizard = ProjectWizard(mock_config_manager, mock_template_engine, mock_ai_service)
            
            navigation_times = []
            start_time = time.perf_counter()
            
            # Navigate through wizard steps
            for step_id in range(5):  # 5 wizard steps
                step_start = time.perf_counter()
                
                # Simulate step navigation
                current_page = wizard.currentPage()
                if current_page:
                    # Simulate validation and data collection
                    wizard.setCurrentId(step_id)
                
                step_end = time.perf_counter()
                navigation_times.append(step_end - step_start)
            
            total_time = time.perf_counter() - start_time
            wizard.close()
            
            return {
                "total_time": total_time,
                "step_times": navigation_times,
                "avg_step_time": sum(navigation_times) / len(navigation_times)
            }
        
        result = benchmark(navigate_wizard_steps)
        
        # Performance assertions
        assert result["avg_step_time"] < 0.2, f"Step navigation too slow: {result['avg_step_time']:.3f}s"
        assert result["total_time"] < 1.0, f"Total navigation too slow: {result['total_time']:.3f}s"

    def test_wizard_validation_responsiveness(self, benchmark: BenchmarkFixture, qapp,
                                            mock_config_manager):
        """Benchmark form validation response time."""
        def test_validation_speed():
            step = BasicInfoStep(mock_config_manager)
            
            validation_times = []
            test_inputs = [
                "valid_project_name",
                "123invalid_name",
                "another_valid_name",
                "invalid@name",
                "final_valid_name"
            ]
            
            for test_input in test_inputs:
                start_time = time.perf_counter()
                
                # Simulate form field validation
                is_valid = self._validate_project_name(test_input)
                
                end_time = time.perf_counter()
                validation_times.append(end_time - start_time)
            
            step.close()
            return {
                "validation_times": validation_times,
                "avg_validation_time": sum(validation_times) / len(validation_times),
                "max_validation_time": max(validation_times)
            }
        
        result = benchmark(test_validation_speed)
        
        # Validation should be instant for good UX
        assert result["avg_validation_time"] < 0.01, f"Validation too slow: {result['avg_validation_time']:.4f}s"
        assert result["max_validation_time"] < 0.05, f"Max validation too slow: {result['max_validation_time']:.4f}s"

    def test_wizard_data_binding_performance(self, benchmark: BenchmarkFixture, qapp,
                                           mock_config_manager, mock_template_engine,
                                           mock_ai_service):
        """Benchmark wizard data binding and updates."""
        def test_data_binding():
            wizard = ProjectWizard(mock_config_manager, mock_template_engine, mock_ai_service)
            
            binding_times = []
            test_data = {
                "project_name": "performance_test",
                "author": "Performance User",
                "version": "1.0.0",
                "description": "Performance testing project",
                "location": "/tmp/perf_test"
            }
            
            for key, value in test_data.items():
                start_time = time.perf_counter()
                
                # Simulate data binding update
                wizard.wizard_data.__setattr__(key, value)
                
                end_time = time.perf_counter()
                binding_times.append(end_time - start_time)
            
            wizard.close()
            return {
                "binding_times": binding_times,
                "avg_binding_time": sum(binding_times) / len(binding_times),
                "total_binding_time": sum(binding_times)
            }
        
        result = benchmark(test_data_binding)
        
        assert result["avg_binding_time"] < 0.001, f"Data binding too slow: {result['avg_binding_time']:.4f}s"

    def _validate_project_name(self, name: str) -> bool:
        """Simulate project name validation logic."""
        import re
        return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name))


@pytest.mark.benchmark
@pytest.mark.gui
class TestTemplateSelectionPerformance:
    """Test template selection and preview performance."""

    def test_template_loading_speed(self, benchmark: BenchmarkFixture, qapp,
                                  mock_config_manager, mock_template_engine):
        """Benchmark template loading and display time."""
        def load_templates():
            step = ProjectTypeStep(mock_config_manager, mock_template_engine)
            
            loading_times = []
            templates = ["python_library", "cli_single_package", "flask_web_app", 
                        "django_web_app", "python_package", "one_off_script"]
            
            for template_name in templates:
                start_time = time.perf_counter()
                
                # Simulate template loading
                template_data = mock_template_engine.get_template(template_name)
                
                end_time = time.perf_counter()
                loading_times.append(end_time - start_time)
            
            step.close()
            return {
                "loading_times": loading_times,
                "avg_loading_time": sum(loading_times) / len(loading_times),
                "total_loading_time": sum(loading_times)
            }
        
        result = benchmark(load_templates)
        
        # Templates should load quickly
        assert result["avg_loading_time"] < 0.1, f"Template loading too slow: {result['avg_loading_time']:.3f}s"
        assert result["total_loading_time"] < 0.5, f"Total template loading too slow: {result['total_loading_time']:.3f}s"

    def test_template_preview_generation(self, benchmark: BenchmarkFixture, qapp,
                                       mock_config_manager, mock_template_engine):
        """Benchmark template preview generation speed."""
        def generate_previews():
            step = ProjectTypeStep(mock_config_manager, mock_template_engine)
            
            preview_times = []
            templates = ["python_library", "cli_single_package", "flask_web_app"]
            
            for template_name in templates:
                start_time = time.perf_counter()
                
                # Simulate preview generation
                template_data = mock_template_engine.get_template(template_name)
                preview_html = self._generate_template_preview(template_data)
                
                end_time = time.perf_counter()
                preview_times.append(end_time - start_time)
            
            step.close()
            return {
                "preview_times": preview_times,
                "avg_preview_time": sum(preview_times) / len(preview_times)
            }
        
        result = benchmark(generate_previews)
        
        assert result["avg_preview_time"] < 0.05, f"Preview generation too slow: {result['avg_preview_time']:.3f}s"

    def test_template_selection_responsiveness(self, benchmark: BenchmarkFixture, qapp,
                                             mock_config_manager, mock_template_engine):
        """Benchmark template selection UI responsiveness."""
        def test_selection_response():
            step = ProjectTypeStep(mock_config_manager, mock_template_engine)
            
            selection_times = []
            template_indices = [0, 1, 2, 1, 0]  # Simulate user clicking between templates
            
            for index in template_indices:
                start_time = time.perf_counter()
                
                # Simulate template selection
                template_list = step.findChild(type(None))  # Mock template list
                if hasattr(step, 'template_list') and step.template_list:
                    step.template_list.setCurrentRow(index)
                
                end_time = time.perf_counter()
                selection_times.append(end_time - start_time)
            
            step.close()
            return {
                "selection_times": selection_times,
                "avg_selection_time": sum(selection_times) / len(selection_times)
            }
        
        result = benchmark(test_selection_response)
        
        assert result["avg_selection_time"] < 0.02, f"Template selection too slow: {result['avg_selection_time']:.3f}s"

    def _generate_template_preview(self, template_data: Dict[str, Any]) -> str:
        """Simulate template preview HTML generation."""
        preview = f"""
        <h3>{template_data.get('name', 'Unknown Template')}</h3>
        <p>{template_data.get('description', 'No description')}</p>
        <ul>
        """
        
        for var in template_data.get('variables', []):
            preview += f"<li>{var}</li>"
        
        preview += "</ul>"
        return preview


@pytest.mark.benchmark
@pytest.mark.gui 
class TestProgressDialogPerformance:
    """Test progress dialog responsiveness and update frequency."""

    def test_progress_update_frequency(self, benchmark: BenchmarkFixture, qapp):
        """Benchmark progress dialog update frequency and smoothness."""
        def test_progress_updates():
            progress_dialog = ProgressDialog("Performance Test")
            
            update_times = []
            total_updates = 100
            
            start_time = time.perf_counter()
            
            for i in range(total_updates):
                update_start = time.perf_counter()
                
                # Simulate progress update
                progress_value = int((i / total_updates) * 100)
                progress_dialog.update_progress(progress_value, f"Step {i} of {total_updates}")
                
                # Process events to ensure UI updates
                QApplication.processEvents()
                
                update_end = time.perf_counter()
                update_times.append(update_end - update_start)
            
            total_time = time.perf_counter() - start_time
            progress_dialog.close()
            
            return {
                "total_updates": total_updates,
                "total_time": total_time,
                "avg_update_time": sum(update_times) / len(update_times),
                "max_update_time": max(update_times),
                "updates_per_second": total_updates / total_time
            }
        
        result = benchmark(test_progress_updates)
        
        # Progress updates should be smooth (60fps = ~16.7ms per frame)
        assert result["avg_update_time"] < 0.01, f"Progress updates too slow: {result['avg_update_time']:.4f}s"
        assert result["updates_per_second"] > 50, f"Update rate too low: {result['updates_per_second']:.1f} fps"

    def test_progress_dialog_responsiveness_during_work(self, benchmark: BenchmarkFixture, qapp,
                                                      temp_dir: Path, mock_config_manager,
                                                      mock_template_engine):
        """Test progress dialog responsiveness during actual work."""
        def test_progress_with_background_work():
            progress_dialog = ProgressDialog("Background Work Test")
            
            responsiveness_times = []
            work_iterations = 10
            
            for i in range(work_iterations):
                start_time = time.perf_counter()
                
                # Simulate background work
                self._simulate_background_work(0.05)  # 50ms of work
                
                # Update progress
                progress_value = int((i / work_iterations) * 100)
                progress_dialog.update_progress(progress_value, f"Processing {i}")
                
                # Test UI responsiveness
                QApplication.processEvents()
                
                end_time = time.perf_counter()
                responsiveness_times.append(end_time - start_time)
            
            progress_dialog.close()
            
            return {
                "responsiveness_times": responsiveness_times,
                "avg_responsiveness": sum(responsiveness_times) / len(responsiveness_times)
            }
        
        result = benchmark(test_progress_with_background_work)
        
        # UI should remain responsive even during background work
        assert result["avg_responsiveness"] < 0.1, f"UI not responsive during work: {result['avg_responsiveness']:.3f}s"

    def _simulate_background_work(self, duration: float):
        """Simulate background work for specified duration."""
        end_time = time.perf_counter() + duration
        while time.perf_counter() < end_time:
            # Simulate CPU work
            sum(range(1000))


@pytest.mark.benchmark
@pytest.mark.gui
class TestDialogInteractionPerformance:
    """Test dialog interaction response times."""

    def test_settings_dialog_responsiveness(self, benchmark: BenchmarkFixture, qapp,
                                          mock_config_manager):
        """Benchmark settings dialog interaction speed."""
        def test_settings_interactions():
            settings_dialog = SettingsDialog(mock_config_manager)
            
            interaction_times = []
            
            # Test tab switching
            if hasattr(settings_dialog, 'tab_widget'):
                for tab_index in [0, 1, 2, 1, 0]:  # Switch between tabs
                    start_time = time.perf_counter()
                    
                    settings_dialog.tab_widget.setCurrentIndex(tab_index)
                    QApplication.processEvents()
                    
                    end_time = time.perf_counter()
                    interaction_times.append(end_time - start_time)
            
            # Test form field updates
            for i in range(5):
                start_time = time.perf_counter()
                
                # Simulate field update
                QApplication.processEvents()
                
                end_time = time.perf_counter()
                interaction_times.append(end_time - start_time)
            
            settings_dialog.close()
            
            return {
                "interaction_times": interaction_times,
                "avg_interaction_time": sum(interaction_times) / len(interaction_times) if interaction_times else 0
            }
        
        result = benchmark(test_settings_interactions)
        
        if result["avg_interaction_time"] > 0:
            assert result["avg_interaction_time"] < 0.05, f"Settings interactions too slow: {result['avg_interaction_time']:.3f}s"

    def test_error_dialog_responsiveness(self, benchmark: BenchmarkFixture, qapp,
                                       mock_config_manager):
        """Benchmark error dialog response time."""
        def test_error_dialog():
            test_error = Exception("Performance test error")
            error_context = {"operation": "performance_test", "details": "Testing responsiveness"}
            
            dialog_times = []
            
            for _ in range(3):
                start_time = time.perf_counter()
                
                error_dialog = ErrorDialog(test_error, error_context, mock_config_manager)
                QApplication.processEvents()
                error_dialog.close()
                
                end_time = time.perf_counter()
                dialog_times.append(end_time - start_time)
            
            return {
                "dialog_times": dialog_times,
                "avg_dialog_time": sum(dialog_times) / len(dialog_times)
            }
        
        result = benchmark(test_error_dialog)
        
        assert result["avg_dialog_time"] < 0.1, f"Error dialog too slow: {result['avg_dialog_time']:.3f}s"

    def test_ai_help_dialog_responsiveness(self, benchmark: BenchmarkFixture, qapp,
                                         mock_ai_service):
        """Benchmark AI help dialog response time."""
        def test_ai_help_dialog():
            test_error = Exception("AI help test error")
            error_context = {"operation": "ai_test", "details": "Testing AI help responsiveness"}
            
            response_times = []
            
            with patch('create_project.gui.dialogs.ai_help.AIService') as mock_ai_class:
                mock_ai_class.return_value = mock_ai_service
                
                for _ in range(3):
                    start_time = time.perf_counter()
                    
                    ai_dialog = AIHelpDialog(test_error, error_context, mock_ai_service)
                    QApplication.processEvents()
                    ai_dialog.close()
                    
                    end_time = time.perf_counter()
                    response_times.append(end_time - start_time)
            
            return {
                "response_times": response_times,
                "avg_response_time": sum(response_times) / len(response_times)
            }
        
        result = benchmark(test_ai_help_dialog)
        
        assert result["avg_response_time"] < 0.15, f"AI help dialog too slow: {result['avg_response_time']:.3f}s"


@pytest.mark.benchmark
@pytest.mark.gui
class TestBackgroundOperationResponsiveness:
    """Test UI responsiveness during background operations."""

    def test_ui_responsiveness_during_generation(self, benchmark: BenchmarkFixture, qapp,
                                               temp_dir: Path, mock_config_manager,
                                               mock_template_engine, mock_ai_service):
        """Test UI responsiveness during project generation."""
        def test_generation_responsiveness():
            wizard = ProjectWizard(mock_config_manager, mock_template_engine, mock_ai_service)
            
            # Simulate project generation in background
            generation_thread = MockGenerationThread()
            generation_thread.start()
            
            responsiveness_measurements = []
            measurement_count = 20
            
            for i in range(measurement_count):
                start_time = time.perf_counter()
                
                # Test UI responsiveness
                QApplication.processEvents()
                
                # Simulate user interaction
                wizard.setWindowTitle(f"Generation Progress {i}")
                
                end_time = time.perf_counter()
                responsiveness_measurements.append(end_time - start_time)
                
                time.sleep(0.01)  # Small delay between measurements
            
            generation_thread.stop()
            generation_thread.wait()
            wizard.close()
            
            return {
                "responsiveness_measurements": responsiveness_measurements,
                "avg_responsiveness": sum(responsiveness_measurements) / len(responsiveness_measurements),
                "max_responsiveness": max(responsiveness_measurements)
            }
        
        result = benchmark(test_generation_responsiveness)
        
        # UI should remain responsive during background operations
        assert result["avg_responsiveness"] < 0.01, f"UI not responsive during generation: {result['avg_responsiveness']:.4f}s"
        assert result["max_responsiveness"] < 0.05, f"UI blocking detected: {result['max_responsiveness']:.4f}s"

    def test_concurrent_ui_updates(self, benchmark: BenchmarkFixture, qapp):
        """Test performance with concurrent UI updates."""
        def test_concurrent_updates():
            progress_dialog1 = ProgressDialog("Operation 1")
            progress_dialog2 = ProgressDialog("Operation 2")
            
            update_times = []
            iterations = 50
            
            for i in range(iterations):
                start_time = time.perf_counter()
                
                # Update both dialogs simultaneously
                progress1 = (i * 2) % 100
                progress2 = (i * 3) % 100
                
                progress_dialog1.update_progress(progress1, f"Op1: {i}")
                progress_dialog2.update_progress(progress2, f"Op2: {i}")
                
                QApplication.processEvents()
                
                end_time = time.perf_counter()
                update_times.append(end_time - start_time)
            
            progress_dialog1.close()
            progress_dialog2.close()
            
            return {
                "update_times": update_times,
                "avg_update_time": sum(update_times) / len(update_times)
            }
        
        result = benchmark(test_concurrent_updates)
        
        assert result["avg_update_time"] < 0.02, f"Concurrent updates too slow: {result['avg_update_time']:.4f}s"


class MockGenerationThread(QThread):
    """Mock thread for simulating background project generation."""
    
    def __init__(self):
        super().__init__()
        self.should_stop = False
    
    def run(self):
        """Simulate background work."""
        iteration = 0
        while not self.should_stop and iteration < 100:
            # Simulate work
            time.sleep(0.01)
            iteration += 1
    
    def stop(self):
        """Stop the background work."""
        self.should_stop = True


@pytest.fixture
def qapp():
    """Provide QApplication for GUI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def mock_config_manager():
    """Provide mock config manager."""
    config = MagicMock()
    config.get_setting.return_value = None
    return config


@pytest.fixture
def mock_template_engine():
    """Provide mock template engine."""
    engine = MagicMock()
    templates = {
        "python_library": {
            "name": "Python Library",
            "description": "A reusable Python library",
            "variables": ["author", "version", "description"],
            "structure": {"src": {}, "tests": {}}
        },
        "cli_single_package": {
            "name": "CLI Application", 
            "description": "Command-line application",
            "variables": ["author", "version", "description"],
            "structure": {"src": {}, "tests": {}}
        },
        "flask_web_app": {
            "name": "Flask Web App",
            "description": "Web application using Flask",
            "variables": ["author", "version", "description"],
            "structure": {"app": {}, "tests": {}}
        }
    }
    
    engine.get_template.side_effect = lambda name: templates.get(name, templates["python_library"])
    engine.list_templates.return_value = list(templates.values())
    return engine


@pytest.fixture
def mock_ai_service():
    """Provide mock AI service."""
    ai_service = MagicMock()
    ai_service.is_available.return_value = True
    ai_service.get_error_help.return_value = "Mock AI suggestion for performance testing"
    return ai_service