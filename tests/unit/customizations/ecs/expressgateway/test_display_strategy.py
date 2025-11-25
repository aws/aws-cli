# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/

import asyncio
import time
from unittest.mock import Mock, patch

import pytest
from prompt_toolkit.application import create_app_session
from prompt_toolkit.output import DummyOutput

from awscli.customizations.ecs.expressgateway.display_strategy import (
    DisplayStrategy,
    InteractiveDisplayStrategy,
    TextOnlyDisplayStrategy,
)


class TestDisplayStrategy:
    """Test base DisplayStrategy class."""

    def test_base_strategy_not_implemented(self):
        """Test base class raises NotImplementedError."""
        strategy = DisplayStrategy()
        with pytest.raises(NotImplementedError):
            strategy.execute(None, None, None)


class TestInteractiveDisplayStrategy:
    """Test InteractiveDisplayStrategy."""

    def setup_method(self):
        self.app_session = create_app_session(output=DummyOutput())
        self.app_session.__enter__()

    def teardown_method(self):
        if hasattr(self, 'app_session'):
            self.app_session.__exit__(None, None, None)

    @patch('time.sleep')
    def test_execute_with_mock_display(self, mock_sleep):
        """Test strategy executes with mocked display."""

        async def mock_run_async():
            await asyncio.sleep(0.01)

        mock_display = Mock()
        mock_display.display = Mock()
        mock_display.run = Mock(return_value=mock_run_async())

        mock_collector = Mock()
        mock_collector.get_current_view = Mock(
            return_value="Test output {SPINNER}"
        )

        strategy = InteractiveDisplayStrategy(
            display=mock_display, use_color=True
        )

        mock_sleep.side_effect = KeyboardInterrupt()

        start_time = time.time()
        strategy.execute(mock_collector, start_time, timeout_minutes=1)

        # Verify display was called
        assert mock_display.display.called
        assert mock_display.run.called

    def test_strategy_uses_provided_color_setting(self):
        """Test strategy respects use_color parameter."""
        mock_display = Mock()

        strategy_with_color = InteractiveDisplayStrategy(
            display=mock_display, use_color=True
        )
        assert strategy_with_color.use_color is True

        strategy_no_color = InteractiveDisplayStrategy(
            display=mock_display, use_color=False
        )
        assert strategy_no_color.use_color is False


class TestTextOnlyDisplayStrategy:
    """Test TextOnlyDisplayStrategy."""

    @patch('time.sleep')
    def test_execute_with_mock_collector(self, mock_sleep, capsys):
        """Test strategy executes sync loop with text output."""
        mock_collector = Mock()
        mock_collector.get_current_view = Mock(return_value="Test output")
        mock_collector.cached_monitor_result = (None, "Test info")

        strategy = TextOnlyDisplayStrategy(use_color=True)

        # Make sleep raise to exit loop after first iteration
        mock_sleep.side_effect = KeyboardInterrupt()

        start_time = time.time()
        strategy.execute(mock_collector, start_time, timeout_minutes=1)

        output = capsys.readouterr().out
        printed_output = output
        assert "Starting monitoring" in printed_output
        assert "Polling for updates" in printed_output
        assert "stopped by user" in printed_output
        assert "complete" in printed_output

    @patch('time.sleep')
    @patch('time.time')
    def test_execute_handles_timeout(self, mock_time, mock_sleep, capsys):
        """Test strategy handles timeout correctly."""
        mock_collector = Mock()
        mock_collector.get_current_view = Mock(return_value="Test output")
        mock_collector.cached_monitor_result = (None, None)

        strategy = TextOnlyDisplayStrategy(use_color=True)

        # Simulate timeout after first poll
        start_time = 1000.0
        mock_time.side_effect = [
            1000.0,  # First check - within timeout
            2000.0,  # Second check - exceeded timeout
        ]

        strategy.execute(mock_collector, start_time, timeout_minutes=1)

        output = capsys.readouterr().out
        printed_output = output
        assert "timeout reached" in printed_output.lower()

    def test_strategy_uses_provided_color_setting(self):
        """Test strategy respects use_color parameter."""
        strategy_with_color = TextOnlyDisplayStrategy(use_color=True)
        assert strategy_with_color.stream_display.use_color is True

        strategy_no_color = TextOnlyDisplayStrategy(use_color=False)
        assert strategy_no_color.stream_display.use_color is False


# Suppress thread exception warnings for these async tests
pytestmark = pytest.mark.filterwarnings(
    "ignore::pytest.PytestUnhandledThreadExceptionWarning"
)
