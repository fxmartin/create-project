# ABOUTME: Unit tests for wizard base step validation and data logic 
# ABOUTME: Tests non-Qt dependent functionality like validation functions and data management

"""Unit tests for base wizard step validation logic."""

import sys
from unittest.mock import Mock, patch, MagicMock
from typing import Optional, List, Callable, Dict, Any

import pytest

# Mock PyQt6 completely to test only the logic
sys.modules['PyQt6'] = Mock()
sys.modules['PyQt6.QtCore'] = Mock()
sys.modules['PyQt6.QtWidgets'] = Mock()

# Configure signal mock
signal_mock = Mock()
sys.modules['PyQt6.QtCore'].pyqtSignal = Mock(return_value=signal_mock)

# Create mock base classes
class MockQWizardPage:
    """Mock QWizardPage for testing."""
    def __init__(self, parent=None):
        self.parent = parent
        self._title = ""
        self._subtitle = ""
        
    def setTitle(self, title: str):
        self._title = title
        
    def setSubTitle(self, subtitle: str):
        self._subtitle = subtitle
        
    def setLayout(self, layout):
        self._layout = layout
        
    def title(self):
        return self._title

class MockQVBoxLayout:
    """Mock QVBoxLayout for testing."""
    def __init__(self):
        self._widgets = []
        
    def addWidget(self, widget):
        self._widgets.append(widget)

class MockQLabelWidget:
    """Mock QLabel for testing."""
    def __init__(self):
        self._text = ""
        self._object_name = ""
        self._word_wrap = False
        self._visible = True
        
    def setObjectName(self, name: str):
        self._object_name = name
        
    def setWordWrap(self, wrap: bool):
        self._word_wrap = wrap
        
    def hide(self):
        self._visible = False
        
    def show(self):
        self._visible = True
        
    def setText(self, text: str):
        self._text = text
        
    def clear(self):
        self._text = ""

class MockQMessageBox:
    """Mock QMessageBox for testing."""
    StandardButton = Mock()
    StandardButton.Yes = 16384
    StandardButton.No = 65536
    
    @staticmethod
    def information(parent, title: str, message: str):
        return None
        
    @staticmethod  
    def warning(parent, title: str, message: str):
        return None
        
    @staticmethod
    def question(parent, title: str, message: str, buttons, default_button):
        return MockQMessageBox.StandardButton.Yes

# Set up the mocks
sys.modules['PyQt6.QtWidgets'].QWizardPage = MockQWizardPage
sys.modules['PyQt6.QtWidgets'].QVBoxLayout = MockQVBoxLayout
sys.modules['PyQt6.QtWidgets'].QLabel = MockQLabelWidget
sys.modules['PyQt6.QtWidgets'].QMessageBox = MockQMessageBox

# Now import the actual module
from create_project.gui.wizard.base_step import WizardStep


class TestableWizardStep(WizardStep):
    """Concrete implementation of WizardStep for testing."""
    
    def __init__(self, title: str, subtitle: str = "", parent=None):
        # Initialize internal state before calling super().__init__
        self._test_data = {}
        self._custom_validation_error = None
        super().__init__(title, subtitle, parent)
        
    def _setup_ui(self) -> None:
        """Mock UI setup - we don't need actual UI for logic testing."""
        pass
        
    def validate(self) -> Optional[str]:
        """Custom validation for testing."""
        return self._custom_validation_error
        
    def get_data(self) -> Dict[str, Any]:
        """Get test data."""
        return self._test_data.copy()
        
    def set_data(self, data: Dict[str, Any]) -> None:
        """Set test data."""
        if data:
            self._test_data.update(data)
            
    def set_custom_validation_error(self, error: Optional[str]):
        """Set custom validation error for testing."""
        self._custom_validation_error = error


class TestWizardStepValidationLogic:
    """Test validation logic functionality."""

    @pytest.fixture
    def wizard_step(self):
        """Create a testable wizard step."""
        return TestableWizardStep("Test Step", "Test subtitle")

    def test_initialization_sets_title_and_subtitle(self):
        """Test that initialization properly sets title and subtitle."""
        step = TestableWizardStep("My Title", "My Subtitle")
        
        assert step.title() == "My Title"
        # Note: We can't easily test subtitle without more Qt mocking

    def test_validators_list_initialization(self, wizard_step):
        """Test that validators list is properly initialized."""
        assert hasattr(wizard_step, '_validators')
        assert isinstance(wizard_step._validators, list)
        assert len(wizard_step._validators) == 0

    def test_add_single_validator(self, wizard_step):
        """Test adding a single validator function."""
        def test_validator() -> Optional[str]:
            return None
            
        wizard_step.add_validator(test_validator)
        
        assert len(wizard_step._validators) == 1
        assert wizard_step._validators[0] is test_validator

    def test_add_multiple_validators(self, wizard_step):
        """Test adding multiple validator functions."""
        def validator1() -> Optional[str]:
            return None
            
        def validator2() -> Optional[str]:
            return None
            
        def validator3() -> Optional[str]:
            return "Error"
            
        wizard_step.add_validator(validator1)
        wizard_step.add_validator(validator2)
        wizard_step.add_validator(validator3)
        
        assert len(wizard_step._validators) == 3
        assert wizard_step._validators[0] is validator1
        assert wizard_step._validators[1] is validator2
        assert wizard_step._validators[2] is validator3

    def test_validate_page_no_validators_success(self, wizard_step):
        """Test validatePage with no validators passes."""
        result = wizard_step.validatePage()
        assert result is True

    def test_validate_page_passing_validators(self, wizard_step):
        """Test validatePage with validators that all pass."""
        def passing_validator1() -> Optional[str]:
            return None
            
        def passing_validator2() -> Optional[str]:
            return None
            
        wizard_step.add_validator(passing_validator1)
        wizard_step.add_validator(passing_validator2)
        
        result = wizard_step.validatePage()
        assert result is True

    def test_validate_page_failing_validator(self, wizard_step):
        """Test validatePage with a failing validator."""
        error_message = "Validation failed"
        
        def failing_validator() -> Optional[str]:
            return error_message
            
        wizard_step.add_validator(failing_validator)
        
        result = wizard_step.validatePage()
        assert result is False

    def test_validate_page_stops_at_first_failure(self, wizard_step):
        """Test that validatePage stops at the first failing validator."""
        call_count = 0
        
        def counting_validator() -> Optional[str]:
            nonlocal call_count
            call_count += 1
            return None
            
        def failing_validator() -> Optional[str]:
            nonlocal call_count
            call_count += 1
            return "Failed"
            
        def should_not_be_called() -> Optional[str]:
            nonlocal call_count
            call_count += 1
            pytest.fail("This validator should not be called")
            
        wizard_step.add_validator(counting_validator)
        wizard_step.add_validator(failing_validator) 
        wizard_step.add_validator(should_not_be_called)
        
        result = wizard_step.validatePage()
        
        assert result is False
        assert call_count == 2  # Only first two validators should be called

    def test_validate_page_custom_validation_failure(self, wizard_step):
        """Test validatePage with custom validation failure."""
        custom_error = "Custom validation error"
        wizard_step.set_custom_validation_error(custom_error)
        
        result = wizard_step.validatePage()
        assert result is False

    def test_validate_page_validators_pass_custom_fails(self, wizard_step):
        """Test validatePage where validators pass but custom validation fails."""
        def passing_validator() -> Optional[str]:
            return None
            
        wizard_step.add_validator(passing_validator)
        wizard_step.set_custom_validation_error("Custom error")
        
        result = wizard_step.validatePage()
        assert result is False

    def test_default_validate_implementation(self, wizard_step):
        """Test that default validate() returns None."""
        # Reset custom validation error
        wizard_step.set_custom_validation_error(None)
        result = wizard_step.validate()
        assert result is None

    def test_default_is_complete_implementation(self, wizard_step):
        """Test that default isComplete() returns True."""
        result = wizard_step.isComplete()
        assert result is True


class TestWizardStepDataManagement:
    """Test data management functionality."""

    @pytest.fixture
    def wizard_step(self):
        """Create a testable wizard step."""
        return TestableWizardStep("Data Step")

    def test_get_data_initially_empty(self, wizard_step):
        """Test that get_data initially returns empty dict."""
        result = wizard_step.get_data()
        assert result == {}

    def test_set_and_get_data(self, wizard_step):
        """Test setting and getting data."""
        test_data = {
            "field1": "value1",
            "field2": "value2", 
            "field3": 123
        }
        
        wizard_step.set_data(test_data)
        result = wizard_step.get_data()
        
        assert result == test_data

    def test_update_existing_data(self, wizard_step):
        """Test updating existing data."""
        initial_data = {"field1": "initial", "field2": "value2"}
        update_data = {"field1": "updated", "field3": "new"}
        
        wizard_step.set_data(initial_data)
        wizard_step.set_data(update_data)
        
        result = wizard_step.get_data()
        expected = {"field1": "updated", "field2": "value2", "field3": "new"}
        
        assert result == expected

    def test_get_data_returns_copy(self, wizard_step):
        """Test that get_data returns a copy, not reference."""
        original_data = {"field1": "value1"}
        wizard_step.set_data(original_data)
        
        returned_data = wizard_step.get_data()
        returned_data["field1"] = "modified"
        
        # Original data should be unchanged
        assert wizard_step.get_data()["field1"] == "value1"

    def test_set_data_with_none(self, wizard_step):
        """Test set_data handles None gracefully."""
        wizard_step.set_data(None)  # Should not crash
        result = wizard_step.get_data()
        assert result == {}

    def test_set_data_with_empty_dict(self, wizard_step):
        """Test set_data with empty dictionary."""
        wizard_step.set_data({})
        result = wizard_step.get_data()
        assert result == {}


class TestWizardStepErrorHandling:
    """Test error handling and display functionality."""

    @pytest.fixture  
    def wizard_step(self):
        """Create a testable wizard step."""
        return TestableWizardStep("Error Step")

    def test_show_error_sets_error_label_text(self, wizard_step):
        """Test that show_error sets the error label text."""
        error_message = "Test error message"
        wizard_step.show_error(error_message)
        
        # Check that error label text was set with emoji prefix
        expected_text = f"❌ {error_message}"
        assert wizard_step.error_label._text == expected_text

    def test_show_error_makes_label_visible(self, wizard_step):
        """Test that show_error makes the error label visible."""
        wizard_step.error_label._visible = False
        wizard_step.show_error("Test error")
        
        assert wizard_step.error_label._visible is True

    def test_clear_error_hides_label(self, wizard_step):
        """Test that clear_error hides the error label."""
        wizard_step.error_label._visible = True
        wizard_step.clear_error()
        
        assert wizard_step.error_label._visible is False

    def test_clear_error_clears_text(self, wizard_step):
        """Test that clear_error clears the error text."""
        wizard_step.error_label._text = "Some error"
        wizard_step.clear_error()
        
        assert wizard_step.error_label._text == ""

    def test_show_error_with_empty_string(self, wizard_step):
        """Test show_error with empty string."""
        wizard_step.show_error("")
        assert wizard_step.error_label._text == "❌ "

    def test_multiple_show_error_calls(self, wizard_step):
        """Test multiple consecutive show_error calls."""
        wizard_step.show_error("First error")
        assert wizard_step.error_label._text == "❌ First error"
        
        wizard_step.show_error("Second error")
        assert wizard_step.error_label._text == "❌ Second error"


class TestWizardStepHelpSystem:
    """Test help system functionality."""

    @pytest.fixture
    def wizard_step(self):
        """Create a testable wizard step."""
        return TestableWizardStep("Help Step")

    def test_get_help_context_default(self, wizard_step):
        """Test default help context generation."""
        result = wizard_step._get_help_context()
        expected = f"Help for: {wizard_step.title()}"
        assert result == expected

    def test_request_help_emits_signal(self, wizard_step):
        """Test that request_help emits help_requested signal."""
        # Mock the signal emission
        emitted_contexts = []
        
        def mock_emit(context):
            emitted_contexts.append(context)
            
        wizard_step.help_requested.emit = mock_emit
        
        wizard_step.request_help()
        
        assert len(emitted_contexts) == 1
        expected_context = f"Help for: {wizard_step.title()}"
        assert emitted_contexts[0] == expected_context


class TestWizardStepComplexValidationScenarios:
    """Test complex validation scenarios."""

    @pytest.fixture
    def wizard_step(self):
        """Create a testable wizard step."""
        return TestableWizardStep("Complex Step")

    def test_validation_with_exception_in_validator(self, wizard_step):
        """Test that exceptions in validators are handled."""
        def exception_validator() -> Optional[str]:
            raise ValueError("Validator exception")
            
        wizard_step.add_validator(exception_validator)
        
        # Should propagate the exception (this is expected behavior)
        with pytest.raises(ValueError, match="Validator exception"):
            wizard_step.validatePage()

    def test_complex_validation_all_pass(self, wizard_step):
        """Test complex validation scenario where all validations pass."""
        def validator1() -> Optional[str]:
            return None
            
        def validator2() -> Optional[str]:
            return None
            
        def validator3() -> Optional[str]:
            return None
            
        wizard_step.add_validator(validator1)
        wizard_step.add_validator(validator2) 
        wizard_step.add_validator(validator3)
        wizard_step.set_custom_validation_error(None)
        
        result = wizard_step.validatePage()
        assert result is True

    def test_validation_state_tracking(self, wizard_step):
        """Test that validation state is properly tracked."""
        emitted_errors = []
        
        def mock_emit(error):
            emitted_errors.append(error)
            
        wizard_step.validation_error.emit = mock_emit
        
        def failing_validator() -> Optional[str]:
            return "Tracked error"
            
        wizard_step.add_validator(failing_validator)
        
        result = wizard_step.validatePage()
        
        assert result is False
        assert len(emitted_errors) == 1
        assert emitted_errors[0] == "Tracked error"

    def test_validator_execution_order(self, wizard_step):
        """Test that validators are executed in the order they were added."""
        execution_order = []
        
        def validator1() -> Optional[str]:
            execution_order.append(1)
            return None
            
        def validator2() -> Optional[str]:
            execution_order.append(2)
            return None
            
        def validator3() -> Optional[str]:
            execution_order.append(3)
            return None
            
        wizard_step.add_validator(validator1)
        wizard_step.add_validator(validator2)
        wizard_step.add_validator(validator3)
        
        wizard_step.validatePage()
        
        assert execution_order == [1, 2, 3]

    def test_validator_with_non_string_return(self, wizard_step):
        """Test validator returning non-string error value."""
        def non_string_validator() -> Optional[str]:
            return 123  # Return integer instead of string
            
        wizard_step.add_validator(non_string_validator)
        
        result = wizard_step.validatePage()
        assert result is False
        # The error should still be handled (converted to string)


class TestWizardStepInitializationAndCleanup:
    """Test initialization and cleanup functionality."""

    @pytest.fixture
    def wizard_step(self):
        """Create a testable wizard step."""
        return TestableWizardStep("Lifecycle Step")

    def test_initialize_page_clears_errors(self, wizard_step):
        """Test that initializePage clears existing errors."""
        # Set an error first
        wizard_step.show_error("Previous error")
        assert wizard_step.error_label._visible is True
        
        # Initialize page should clear the error
        wizard_step.initializePage()
        assert wizard_step.error_label._visible is False

    def test_cleanup_page_clears_errors(self, wizard_step):
        """Test that cleanupPage clears existing errors."""
        # Set an error first
        wizard_step.show_error("Error to clean")
        assert wizard_step.error_label._visible is True
        
        # Cleanup should clear the error
        wizard_step.cleanupPage()
        assert wizard_step.error_label._visible is False

    def test_initialization_with_title_only(self):
        """Test initialization with title only."""
        step = TestableWizardStep("Title Only")
        assert step.title() == "Title Only"

    def test_initialization_with_title_and_subtitle(self):
        """Test initialization with title and subtitle."""
        step = TestableWizardStep("Title", "Subtitle")
        assert step.title() == "Title"
        # Subtitle testing would require more Qt mocking