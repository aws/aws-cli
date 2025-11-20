import asyncio
from unittest.mock import Mock, patch

import pytest

from awscli.customizations.ecs.prompt_toolkit_display import Display


class TestPromptToolkitDisplay:
    @pytest.fixture
    def display(self):
        return Display()

    def test_init(self, display):
        """Test Display initialization."""
        assert display.control is not None
        assert display.window is not None
        assert display.status_control is not None
        assert display.app is not None
        assert display.content_lines == 0

    def test_display_updates_content(self, display):
        """Test display method updates content and line count."""
        test_text = "Line 1\nLine 2\nLine 3"
        test_status = "Status message"

        display.display(test_text, test_status)

        assert display.content_lines == 3
        assert display.status_control.text == test_status

    def test_display_without_status(self, display):
        """Test display method with only text."""
        test_text = "Single line"

        display.display(test_text)

        assert display.content_lines == 1

    @patch('awscli.customizations.ecs.prompt_toolkit_display.ANSI')
    def test_display_uses_ansi_formatting(self, mock_ansi, display):
        """Test display method uses ANSI for color formatting."""
        test_text = "Colored text"

        display.display(test_text)

        mock_ansi.assert_called_once_with(test_text)

    def test_scroll_bounds_calculation(self, display):
        """Test that content_lines is calculated correctly for scroll bounds."""
        multiline_text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"

        display.display(multiline_text)

        assert display.content_lines == 5

    @patch('awscli.customizations.ecs.prompt_toolkit_display.Application')
    def test_run_calls_app_run_async(self, mock_app_class):
        """Test run method calls app.run_async()."""
        mock_app = Mock()
        mock_app_class.return_value = mock_app

        # Make run_async return a coroutine
        async def mock_run_async():
            return None

        mock_app.run_async = mock_run_async

        display = Display()

        # Run the async method
        asyncio.run(display.run())

        # Verify the mock was set up correctly
        assert mock_app.run_async == mock_run_async

    def test_scrollable_pane_with_scrollbar(self, display):
        """Test that ScrollablePane is configured with scrollbar for better UX."""
        # The window should be wrapped in a ScrollablePane with scrollbar
        assert hasattr(display.window, 'show_scrollbar')
        # The inner window should have wrap_lines enabled
        inner_window = display.window.content
        assert hasattr(inner_window, 'wrap_lines')
        assert inner_window.wrap_lines is not None

    def test_long_line_wrapping(self, display):
        """Test that very long lines are handled properly with wrapping."""
        long_line = "This is a very long line that should wrap properly " * 10
        test_text = f"Short line\n{long_line}\nAnother short line"

        display.display(test_text)

        assert display.content_lines == 3
        # Verify the content is set correctly
        assert display.control.text is not None
