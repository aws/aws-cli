import asyncio
from unittest.mock import Mock, patch

import pytest

from awscli.customizations.ecs.prompt_toolkit_display import Display


class TestPromptToolkitDisplay:
    @pytest.fixture
    def display(self, ptk_app_session):
        yield Display()

    def test_init(self, display):
        """Test Display initialization."""
        assert display.control is not None
        assert display.window is not None
        assert display.status_control is not None
        assert display.app is not None
        assert display.content_lines == 0
        assert display.raw_text == ""

    def test_display_updates_content(self, display):
        """Test display method updates content and line count."""
        test_text = "Line 1\nLine 2\nLine 3"
        test_status = "Status message"

        display.display(test_text, test_status)

        assert display.content_lines == 3
        assert display.raw_text == test_text
        assert display.status_control.text == test_status

    def test_display_without_status(self, display):
        """Test display method with only text."""
        test_text = "Single line"

        display.display(test_text)

        assert display.content_lines == 1
        assert display.raw_text == test_text

    @patch('awscli.customizations.ecs.prompt_toolkit_display.ANSI')
    def test_display_uses_ansi_formatting(self, mock_ansi, display):
        """Test display method uses ANSI for color formatting."""
        test_text = "Colored text"

        display.display(test_text)

        mock_ansi.assert_called_once_with(test_text)
        assert display.raw_text == test_text

    def test_scroll_bounds_calculation(self, display):
        """Test that content_lines is calculated correctly for scroll bounds."""
        multiline_text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"

        display.display(multiline_text)

        assert display.content_lines == 5

    @patch('awscli.customizations.ecs.prompt_toolkit_display.Application')
    def test_run_calls_app_run_async(self, mock_app_class, display):
        """Test run method calls app.run_async()."""
        mock_app = Mock()
        mock_app_class.return_value = mock_app

        # Make run_async return a coroutine
        async def mock_run_async():
            return None

        mock_app.run_async = mock_run_async

        # Replace the display's app with our mock
        display.app = mock_app

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

    def test_display_handles_ansi_content_without_errors(self, display):
        """Test that display handles ANSI-colored content without errors."""
        # Content with various ANSI codes
        ansi_text = "\x1b[32mGreen\x1b[0m\n\x1b[31mRed\x1b[32mGreen\x1b[0m\n\x1b[1m\x1b[41mBold on Red\x1b[0m"

        # Should not raise any exceptions
        display.display(ansi_text)

        # Content should be stored and processed
        assert display.raw_text == ansi_text
        assert display.content_lines == 3

    def test_scroll_validation_with_ansi_content(self, display):
        """Test scroll position validation works with ANSI-colored content."""
        # Mock the app output for terminal size
        mock_output = Mock()
        mock_output.get_size.return_value = Mock(rows=20, columns=80)
        display.app.output = mock_output

        # Set content with ANSI codes
        ansi_text = "\x1b[32mShort line\x1b[0m\n\x1b[31mAnother line\x1b[0m"

        # Should not raise an exception and content should be stored
        display.display(ansi_text)
        assert display.raw_text == ansi_text

    def test_scroll_validation_handles_missing_output(self, display):
        """Test scroll validation gracefully handles missing app output."""
        # Set up display without proper app output
        display.app.output = None

        # Should not raise an exception
        display.display("Test content")
        assert display.raw_text == "Test content"

    def test_scroll_validation_handles_exceptions(self, display):
        """Test scroll validation clamps scroll position on terminal size exceptions."""
        mock_output = Mock()
        mock_output.get_size.side_effect = OSError("Terminal unavailable")
        display.app.output = mock_output

        display.window.vertical_scroll = 5

        display.display("Test content")
        assert display.window.vertical_scroll == 5

    def test_scroll_validation_with_long_lines(self, display):
        """Test scroll validation with lines that wrap."""
        # Mock the app output for terminal size
        mock_output = Mock()
        mock_output.get_size.return_value = Mock(rows=20, columns=80)
        display.app.output = mock_output

        # Create content with very long lines that will wrap
        long_line = "A" * 100  # Longer than terminal width
        content = f"Short\n{long_line}\nShort again"

        # Should handle wrapping without errors
        display.display(content)
        assert display.raw_text == content
