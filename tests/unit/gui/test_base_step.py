# ABOUTME: Comprehensive unit tests for wizard base step functionality
# ABOUTME: Tests validation logic, error handling, data management, and non-Qt dependent features

"""Unit tests for base wizard step module."""

import sys
from unittest.mock import Mock, patch, MagicMock
from typing import Optional

import pytest

# Mock PyQt6 modules before importing
sys.modules['PyQt6'] = Mock()
sys.modules['PyQt6.QtCore'] = Mock()
sys.modules['PyQt6.QtWidgets'] = Mock()

# Configure the mocks
pyqt_signal_mock = Mock()
sys.modules['PyQt6.QtCore'].pyqtSignal = Mock(return_value=pyqt_signal_mock)

# Mock Qt widgets
qwizard_page_mock = Mock()
qvbox_layout_mock = Mock() 
qlabel_mock = Mock()
qmessage_box_mock = Mock()

sys.modules['PyQt6.QtWidgets'].QWizardPage = qwizard_page_mock
sys.modules['PyQt6.QtWidgets'].QVBoxLayout = qvbox_layout_mock
sys.modules['PyQt6.QtWidgets'].QLabel = qlabel_mock
sys.modules['PyQt6.QtWidgets'].QMessageBox = qmessage_box_mock

# Mock QMessageBox static methods and constants
qmessage_box_mock.StandardButton = Mock()
qmessage_box_mock.StandardButton.Yes = 'Yes'
qmessage_box_mock.StandardButton.No = 'No'
qmessage_box_mock.question = Mock(return_value='Yes')
qmessage_box_mock.information = Mock()
qmessage_box_mock.warning = Mock()

# Now import the module
from create_project.gui.wizard.base_step import WizardStep


class TestWizardStep:
    """Test WizardStep class."""

    @pytest.fixture
    def mock_wizard_step_class(self):
        """Create a concrete implementation of WizardStep for testing."""
        class TestWizardStep(WizardStep):
            def _setup_ui(self):
                """Mock UI setup."""
                pass
                
        return TestWizardStep

    @pytest.fixture
    def wizard_step(self, mock_wizard_step_class):
        """Create a test wizard step instance."""
        with patch.object(mock_wizard_step_class, 'setTitle'), \
             patch.object(mock_wizard_step_class, 'setSubTitle'), \
             patch.object(mock_wizard_step_class, 'setLayout'):
            
            step = mock_wizard_step_class("Test Step", "Test subtitle")
            
            # Mock the Qt components
            step.error_label = Mock()
            step.layout = Mock()
            step.validation_error = Mock()
            step.help_requested = Mock()
            
            return step

    def test_initialization_with_title_only(self, mock_wizard_step_class):
        """Test wizard step initialization with title only."""
        with patch.object(mock_wizard_step_class, 'setTitle') as mock_set_title, \
             patch.object(mock_wizard_step_class, 'setSubTitle') as mock_set_subtitle, \
             patch.object(mock_wizard_step_class, 'setLayout'):
            
            step = mock_wizard_step_class("Test Title")
            
            mock_set_title.assert_called_once_with("Test Title")
            mock_set_subtitle.assert_not_called()

    def test_initialization_with_title_and_subtitle(self, mock_wizard_step_class):
        """Test wizard step initialization with title and subtitle."""
        with patch.object(mock_wizard_step_class, 'setTitle') as mock_set_title, \
             patch.object(mock_wizard_step_class, 'setSubTitle') as mock_set_subtitle, \
             patch.object(mock_wizard_step_class, 'setLayout'):
            
            step = mock_wizard_step_class("Test Title", "Test Subtitle")
            
            mock_set_title.assert_called_once_with("Test Title")
            mock_set_subtitle.assert_called_once_with("Test Subtitle")

    def test_validators_list_initialization(self, wizard_step):
        """Test that validators list is properly initialized."""
        assert hasattr(wizard_step, '_validators')
        assert isinstance(wizard_step._validators, list)
        assert len(wizard_step._validators) == 0

    def test_add_validator_single(self, wizard_step):
        """Test adding a single validator function."""
        def test_validator():
            return None
            
        wizard_step.add_validator(test_validator)
        
        assert len(wizard_step._validators) == 1
        assert wizard_step._validators[0] is test_validator

    def test_add_validator_multiple(self, wizard_step):
        """Test adding multiple validator functions."""
        def validator1():
            return None
            
        def validator2():
            return None
            
        def validator3():
            return "Error message"
            
        wizard_step.add_validator(validator1)
        wizard_step.add_validator(validator2)
        wizard_step.add_validator(validator3)
        
        assert len(wizard_step._validators) == 3
        assert wizard_step._validators[0] is validator1
        assert wizard_step._validators[1] is validator2
        assert wizard_step._validators[2] is validator3

    def test_validate_page_no_validators_success(self, wizard_step):
        """Test validatePage with no validators (should pass)."""
        with patch.object(wizard_step, 'clear_error') as mock_clear, \
             patch.object(wizard_step, 'validate', return_value=None) as mock_validate, \
             patch.object(wizard_step, 'title', return_value="Test Step"):
            
            result = wizard_step.validatePage()
            
            assert result is True
            mock_clear.assert_called_once()
            mock_validate.assert_called_once()

    def test_validate_page_validators_pass(self, wizard_step):
        """Test validatePage with validators that pass."""
        def passing_validator1():
            return None
            
        def passing_validator2():
            return None
            
        wizard_step.add_validator(passing_validator1)
        wizard_step.add_validator(passing_validator2)
        
        with patch.object(wizard_step, 'clear_error') as mock_clear, \
             patch.object(wizard_step, 'validate', return_value=None) as mock_validate, \
             patch.object(wizard_step, 'title', return_value="Test Step"):
            
            result = wizard_step.validatePage()
            
            assert result is True
            mock_clear.assert_called_once()
            mock_validate.assert_called_once()

    def test_validate_page_validator_fails(self, wizard_step):
        """Test validatePage with a failing validator."""
        error_message = "Validation failed"
        
        def failing_validator():
            return error_message
            
        wizard_step.add_validator(failing_validator)
        
        with patch.object(wizard_step, 'clear_error') as mock_clear, \
             patch.object(wizard_step, 'show_error') as mock_show_error, \
             patch.object(wizard_step, 'title', return_value="Test Step"):
            
            result = wizard_step.validatePage()
            
            assert result is False
            mock_clear.assert_called_once()
            mock_show_error.assert_called_once_with(error_message)
            wizard_step.validation_error.emit.assert_called_once_with(error_message)

    def test_validate_page_first_validator_fails_stops_execution(self, wizard_step):
        """Test that validatePage stops at first failing validator."""
        def failing_validator():
            return "First error"
            
        def should_not_run_validator():
            pytest.fail("This validator should not be called")
            
        wizard_step.add_validator(failing_validator)
        wizard_step.add_validator(should_not_run_validator)
        
        with patch.object(wizard_step, 'clear_error'), \
             patch.object(wizard_step, 'show_error'), \
             patch.object(wizard_step, 'title', return_value="Test Step"):
            
            result = wizard_step.validatePage()
            assert result is False

    def test_validate_page_custom_validation_fails(self, wizard_step):
        """Test validatePage with custom validation failure."""
        custom_error = "Custom validation error"
        
        with patch.object(wizard_step, 'clear_error') as mock_clear, \
             patch.object(wizard_step, 'validate', return_value=custom_error) as mock_validate, \
             patch.object(wizard_step, 'show_error') as mock_show_error, \
             patch.object(wizard_step, 'title', return_value="Test Step"):
            
            result = wizard_step.validatePage()
            
            assert result is False
            mock_validate.assert_called_once()
            mock_show_error.assert_called_once_with(custom_error)
            wizard_step.validation_error.emit.assert_called_once_with(custom_error)

    def test_validate_page_validator_passes_custom_fails(self, wizard_step):
        """Test validatePage where validators pass but custom validation fails."""
        def passing_validator():
            return None
            
        wizard_step.add_validator(passing_validator)
        custom_error = "Custom error"
        
        with patch.object(wizard_step, 'clear_error'), \
             patch.object(wizard_step, 'validate', return_value=custom_error), \
             patch.object(wizard_step, 'show_error') as mock_show_error, \
             patch.object(wizard_step, 'title', return_value="Test Step"):
            
            result = wizard_step.validatePage()
            
            assert result is False
            mock_show_error.assert_called_once_with(custom_error)

    def test_validate_default_implementation(self, wizard_step):
        """Test that default validate() method returns None."""
        result = wizard_step.validate()
        assert result is None

    def test_show_error(self, wizard_step):
        """Test show_error method."""
        error_message = "Test error message"
        
        wizard_step.show_error(error_message)
        
        wizard_step.error_label.setText.assert_called_once_with(f"❌ {error_message}")
        wizard_step.error_label.show.assert_called_once()

    def test_clear_error(self, wizard_step):
        """Test clear_error method."""
        wizard_step.clear_error()
        
        wizard_step.error_label.hide.assert_called_once()
        wizard_step.error_label.clear.assert_called_once()

    def test_get_data_default_implementation(self, wizard_step):
        """Test that default get_data() method returns empty dict."""
        result = wizard_step.get_data()
        assert result == {}
        assert isinstance(result, dict)

    def test_set_data_default_implementation(self, wizard_step):
        """Test that default set_data() method doesn't raise errors."""
        test_data = {"field1": "value1", "field2": "value2"}
        
        # Should not raise any exceptions
        wizard_step.set_data(test_data)

    def test_initialize_page(self, wizard_step):
        """Test initializePage method."""
        with patch.object(wizard_step, 'clear_error') as mock_clear, \
             patch.object(wizard_step, 'title', return_value="Test Step"):
            
            wizard_step.initializePage()
            mock_clear.assert_called_once()

    def test_cleanup_page(self, wizard_step):
        """Test cleanupPage method."""
        with patch.object(wizard_step, 'clear_error') as mock_clear, \
             patch.object(wizard_step, 'title', return_value="Test Step"):
            
            wizard_step.cleanupPage()
            mock_clear.assert_called_once()

    def test_is_complete_default_implementation(self, wizard_step):
        """Test that default isComplete() method returns True."""
        result = wizard_step.isComplete()
        assert result is True

    def test_request_help(self, wizard_step):
        """Test request_help method."""
        test_context = "Help context for Test Step"
        
        with patch.object(wizard_step, '_get_help_context', return_value=test_context) as mock_get_context, \
             patch.object(wizard_step, 'title', return_value="Test Step"):
            
            wizard_step.request_help()
            
            mock_get_context.assert_called_once()
            wizard_step.help_requested.emit.assert_called_once_with(test_context)

    def test_get_help_context_default_implementation(self, wizard_step):
        """Test default _get_help_context method."""
        with patch.object(wizard_step, 'title', return_value="Test Step"):
            result = wizard_step._get_help_context()
            assert result == "Help for: Test Step"

    def test_show_info_calls_message_box(self, wizard_step):
        """Test show_info method calls QMessageBox.information."""
        with patch('create_project.gui.wizard.base_step.QMessageBox') as mock_msg_box:
            title = "Info Title"
            message = "Info message"
            
            wizard_step.show_info(title, message)
            
            mock_msg_box.information.assert_called_once_with(wizard_step, title, message)

    def test_show_warning_calls_message_box(self, wizard_step):
        """Test show_warning method calls QMessageBox.warning."""
        with patch('create_project.gui.wizard.base_step.QMessageBox') as mock_msg_box:
            title = "Warning Title"
            message = "Warning message"
            
            wizard_step.show_warning(title, message)
            
            mock_msg_box.warning.assert_called_once_with(wizard_step, title, message)

    def test_confirm_action_returns_true_for_yes(self, wizard_step):
        """Test confirm_action returns True when user clicks Yes."""
        with patch('create_project.gui.wizard.base_step.QMessageBox') as mock_msg_box:
            mock_msg_box.StandardButton.Yes = 'Yes'
            mock_msg_box.StandardButton.No = 'No'
            mock_msg_box.question.return_value = 'Yes'
            
            title = "Confirm Title"
            message = "Confirm message"
            
            result = wizard_step.confirm_action(title, message)
            
            assert result is True
            mock_msg_box.question.assert_called_once()

    def test_confirm_action_returns_false_for_no(self, wizard_step):
        """Test confirm_action returns False when user clicks No."""
        with patch('create_project.gui.wizard.base_step.QMessageBox') as mock_msg_box:
            mock_msg_box.StandardButton.Yes = 'Yes'
            mock_msg_box.StandardButton.No = 'No'
            mock_msg_box.question.return_value = 'No'
            
            title = "Confirm Title"
            message = "Confirm message"
            
            result = wizard_step.confirm_action(title, message)
            
            assert result is False


class TestWizardStepValidationScenarios:
    """Test various validation scenarios for WizardStep."""

    @pytest.fixture
    def mock_wizard_step_class(self):
        """Create a concrete implementation with custom validation."""
        class CustomValidationStep(WizardStep):
            def __init__(self, title, subtitle="", custom_validation_result=None):
                self.custom_validation_result = custom_validation_result
                super().__init__(title, subtitle)
                
            def _setup_ui(self):
                pass
                
            def validate(self):
                return self.custom_validation_result
                
        return CustomValidationStep

    @pytest.fixture
    def validation_step(self, mock_wizard_step_class):
        """Create a step with custom validation."""
        with patch.object(mock_wizard_step_class, 'setTitle'), \
             patch.object(mock_wizard_step_class, 'setSubTitle'), \
             patch.object(mock_wizard_step_class, 'setLayout'):
            
            step = mock_wizard_step_class("Validation Step")
            step.error_label = Mock()
            step.layout = Mock()
            step.validation_error = Mock()
            step.help_requested = Mock()
            
            return step

    def test_complex_validation_scenario_all_pass(self, mock_wizard_step_class):
        """Test complex validation with multiple validators and custom validation passing."""
        with patch.object(mock_wizard_step_class, 'setTitle'), \
             patch.object(mock_wizard_step_class, 'setSubTitle'), \
             patch.object(mock_wizard_step_class, 'setLayout'):
            
            step = mock_wizard_step_class("Test", custom_validation_result=None)
            step.error_label = Mock()
            step.validation_error = Mock()
            
            # Add multiple validators
            step.add_validator(lambda: None)  # Pass
            step.add_validator(lambda: None)  # Pass
            step.add_validator(lambda: None)  # Pass
            
            with patch.object(step, 'clear_error'), \
                 patch.object(step, 'title', return_value="Test"):
                
                result = step.validatePage()
                assert result is True

    def test_complex_validation_scenario_middle_validator_fails(self, mock_wizard_step_class):
        """Test validation stops at middle failing validator."""
        with patch.object(mock_wizard_step_class, 'setTitle'), \
             patch.object(mock_wizard_step_class, 'setSubTitle'), \
             patch.object(mock_wizard_step_class, 'setLayout'):
            
            step = mock_wizard_step_class("Test")
            step.error_label = Mock()
            step.validation_error = Mock()
            
            call_count = 0
            def counting_validator_pass():
                nonlocal call_count
                call_count += 1
                return None
                
            def counting_validator_fail():
                nonlocal call_count
                call_count += 1
                return "Middle validator failed"
                
            def should_not_be_called():
                nonlocal call_count
                call_count += 1
                pytest.fail("This validator should not be called")
            
            step.add_validator(counting_validator_pass)  # Should be called
            step.add_validator(counting_validator_fail)  # Should be called and fail
            step.add_validator(should_not_be_called)     # Should NOT be called
            
            with patch.object(step, 'clear_error'), \
                 patch.object(step, 'show_error'), \
                 patch.object(step, 'title', return_value="Test"):
                
                result = step.validatePage()
                
                assert result is False
                assert call_count == 2  # Only first two validators called

    def test_validation_with_exception_in_validator(self, validation_step):
        """Test validation handles exceptions in validator functions."""
        def exception_validator():
            raise ValueError("Validator exception")
            
        validation_step.add_validator(exception_validator)
        
        with patch.object(validation_step, 'clear_error'), \
             patch.object(validation_step, 'title', return_value="Test"):
            
            # Should not crash, exception should be handled gracefully
            with pytest.raises(ValueError):
                validation_step.validatePage()

    def test_validation_state_tracking(self, validation_step):
        """Test that validation properly tracks and reports state."""
        error_messages = []
        
        def capture_error(message):
            error_messages.append(message)
            
        validation_step.validation_error.emit.side_effect = capture_error
        
        # Test failing validation
        validation_step.add_validator(lambda: "First error")
        
        with patch.object(validation_step, 'clear_error'), \
             patch.object(validation_step, 'show_error'), \
             patch.object(validation_step, 'title', return_value="Test"):
            
            result = validation_step.validatePage()
            
            assert result is False
            assert len(error_messages) == 1
            assert error_messages[0] == "First error"


class TestWizardStepDataManagement:
    """Test data management features of WizardStep."""

    @pytest.fixture
    def data_step_class(self):
        """Create a step class with data management."""
        class DataManagementStep(WizardStep):
            def __init__(self, title, subtitle=""):
                super().__init__(title, subtitle)
                self._data = {}
                
            def _setup_ui(self):
                pass
                
            def get_data(self):
                return self._data.copy()
                
            def set_data(self, data):
                self._data.update(data)
                
        return DataManagementStep

    @pytest.fixture
    def data_step(self, data_step_class):
        """Create a data management step instance."""
        with patch.object(data_step_class, 'setTitle'), \
             patch.object(data_step_class, 'setSubTitle'), \
             patch.object(data_step_class, 'setLayout'):
            
            step = data_step_class("Data Step")
            step.error_label = Mock()
            step.layout = Mock()
            step.validation_error = Mock()
            step.help_requested = Mock()
            
            return step

    def test_data_management_get_empty(self, data_step):
        """Test getting data when no data has been set."""
        result = data_step.get_data()
        assert result == {}

    def test_data_management_set_and_get(self, data_step):
        """Test setting and getting data."""
        test_data = {
            "field1": "value1",
            "field2": "value2",
            "field3": 123
        }
        
        data_step.set_data(test_data)
        result = data_step.get_data()
        
        assert result == test_data

    def test_data_management_update_existing(self, data_step):
        """Test updating existing data."""
        initial_data = {"field1": "initial", "field2": "value2"}
        update_data = {"field1": "updated", "field3": "new"}
        
        data_step.set_data(initial_data)
        data_step.set_data(update_data)
        
        result = data_step.get_data()
        expected = {"field1": "updated", "field2": "value2", "field3": "new"}
        
        assert result == expected

    def test_data_management_immutable_return(self, data_step):
        """Test that get_data returns a copy, not reference."""
        original_data = {"field1": "value1"}
        data_step.set_data(original_data)
        
        returned_data = data_step.get_data()
        returned_data["field1"] = "modified"
        
        # Original data in step should be unchanged
        assert data_step.get_data()["field1"] == "value1"


class TestWizardStepHelpers:
    """Test helper methods and utilities."""

    @pytest.fixture
    def helper_step_class(self):
        """Create a step with custom help context."""
        class HelperStep(WizardStep):
            def __init__(self, title, help_context=None):
                self.custom_help_context = help_context
                super().__init__(title)
                
            def _setup_ui(self):
                pass
                
            def _get_help_context(self):
                if self.custom_help_context:
                    return self.custom_help_context
                return super()._get_help_context()
                
        return HelperStep

    @pytest.fixture
    def helper_step(self, helper_step_class):
        """Create helper step instance."""
        with patch.object(helper_step_class, 'setTitle'), \
             patch.object(helper_step_class, 'setLayout'):
            
            step = helper_step_class("Helper Step", "Custom help context")
            step.error_label = Mock()
            step.layout = Mock()
            step.validation_error = Mock()
            step.help_requested = Mock()
            
            return step

    def test_custom_help_context(self, helper_step):
        """Test custom help context implementation."""
        result = helper_step._get_help_context()
        assert result == "Custom help context"

    def test_help_request_with_custom_context(self, helper_step):
        """Test help request with custom context."""
        with patch.object(helper_step, 'title', return_value="Helper Step"):
            helper_step.request_help()
            
            helper_step.help_requested.emit.assert_called_once_with("Custom help context")

    def test_error_display_workflow(self, helper_step):
        """Test complete error display workflow."""
        error_message = "Test error for workflow"
        
        # Show error
        helper_step.show_error(error_message)
        helper_step.error_label.setText.assert_called_with(f"❌ {error_message}")
        helper_step.error_label.show.assert_called()
        
        # Clear error
        helper_step.clear_error()
        helper_step.error_label.hide.assert_called()
        helper_step.error_label.clear.assert_called()

    def test_validation_integration_with_signals(self, helper_step):
        """Test that validation properly integrates with Qt signals."""
        def failing_validator():
            return "Integration test error"
            
        helper_step.add_validator(failing_validator)
        
        with patch.object(helper_step, 'clear_error'), \
             patch.object(helper_step, 'show_error'), \
             patch.object(helper_step, 'title', return_value="Helper Step"):
            
            result = helper_step.validatePage()
            
            assert result is False
            helper_step.validation_error.emit.assert_called_once_with("Integration test error")


class TestWizardStepEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def edge_case_step_class(self):
        """Create step class for edge case testing."""
        class EdgeCaseStep(WizardStep):
            def _setup_ui(self):
                pass
                
        return EdgeCaseStep

    @pytest.fixture
    def edge_step(self, edge_case_step_class):
        """Create edge case step instance."""
        with patch.object(edge_case_step_class, 'setTitle'), \
             patch.object(edge_case_step_class, 'setLayout'):
            
            step = edge_case_step_class("Edge Case Step")
            step.error_label = Mock()
            step.layout = Mock()
            step.validation_error = Mock()
            step.help_requested = Mock()
            
            return step

    def test_empty_string_error_message(self, edge_step):
        """Test showing empty string as error message."""
        edge_step.show_error("")
        edge_step.error_label.setText.assert_called_once_with("❌ ")

    def test_none_values_in_data(self, edge_step):
        """Test handling None values in data operations."""
        # Default implementations should handle None gracefully
        edge_step.set_data(None)  # Should not crash
        
        result = edge_step.get_data()
        assert result == {}  # Default implementation returns empty dict

    def test_validator_returning_non_string_error(self, edge_step):
        """Test validator returning non-string error value."""
        def non_string_validator():
            return 123  # Return number instead of string
            
        edge_step.add_validator(non_string_validator)
        
        with patch.object(edge_step, 'clear_error'), \
             patch.object(edge_step, 'show_error') as mock_show_error, \
             patch.object(edge_step, 'title', return_value="Edge Step"):
            
            result = edge_step.validatePage()
            
            assert result is False
            # Should still work, converting to string
            mock_show_error.assert_called_once_with(123)

    def test_multiple_error_display_calls(self, edge_step):
        """Test multiple consecutive error display calls."""
        edge_step.show_error("First error")
        edge_step.show_error("Second error")
        edge_step.show_error("Third error")
        
        # Should handle multiple calls gracefully
        assert edge_step.error_label.setText.call_count == 3
        assert edge_step.error_label.show.call_count == 3

    def test_clear_error_when_no_error_shown(self, edge_step):
        """Test clearing error when no error is currently shown."""
        # Should not crash even if no error was shown
        edge_step.clear_error()
        
        edge_step.error_label.hide.assert_called_once()
        edge_step.error_label.clear.assert_called_once()

    def test_validation_with_no_title(self, edge_step):
        """Test validation when title returns None or empty."""
        with patch.object(edge_step, 'title', return_value=None), \
             patch.object(edge_step, 'clear_error'):
            
            # Should not crash
            result = edge_step.validatePage()
            assert result is True  # No validators, should pass