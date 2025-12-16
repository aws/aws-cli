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
from botocore.exceptions import ClientError
from prompt_toolkit.application import create_app_session
from prompt_toolkit.output import DummyOutput

from awscli.customizations.ecs.expressgateway.display_strategy import (
    DisplayStrategy,
    InteractiveDisplayStrategy,
)


class TestDisplayStrategy:
    """Test base DisplayStrategy class."""

    def test_base_strategy_not_implemented(self):
        """Test base class raises NotImplementedError."""
        strategy = DisplayStrategy()
        with pytest.raises(NotImplementedError):
            strategy.execute(None, None, None)


@pytest.fixture
def app_session():
    """Fixture that creates and manages an app session for prompt_toolkit."""
    with create_app_session(output=DummyOutput()) as session:
        yield session


@pytest.fixture
def mock_display():
    """Fixture that creates a mock display for testing."""

    async def mock_run_async():
        await asyncio.sleep(0.01)

    display = Mock()
    display.display = Mock()
    display.run = Mock(return_value=mock_run_async())
    return display


class TestInteractiveDisplayStrategy:
    """Test InteractiveDisplayStrategy."""

    @patch('time.sleep')
    def test_execute_with_mock_display(
        self, mock_sleep, app_session, mock_display
    ):
        """Test strategy executes with mocked display."""
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

    @patch('time.sleep')
    def test_completion_message_on_normal_exit(
        self, mock_sleep, app_session, mock_display, capsys
    ):
        """Test displays completion message when monitoring completes normally."""
        mock_collector = Mock()
        mock_collector.get_current_view = Mock(return_value="Resources ready")

        strategy = InteractiveDisplayStrategy(
            display=mock_display, use_color=True
        )

        mock_sleep.side_effect = KeyboardInterrupt()

        start_time = time.time()
        strategy.execute(mock_collector, start_time, timeout_minutes=1)

        captured = capsys.readouterr()
        assert "Monitoring Complete!" in captured.out
        assert "Monitoring timed out!" not in captured.out

    @patch('time.sleep')
    def test_collector_output_is_displayed(
        self, mock_sleep, app_session, mock_display, capsys
    ):
        """Test that collector output appears in final output."""
        mock_collector = Mock()
        unique_output = "LoadBalancer lb-12345 ACTIVE"
        mock_collector.get_current_view = Mock(return_value=unique_output)

        strategy = InteractiveDisplayStrategy(
            display=mock_display, use_color=True
        )

        mock_sleep.side_effect = KeyboardInterrupt()

        start_time = time.time()
        strategy.execute(mock_collector, start_time, timeout_minutes=1)

        captured = capsys.readouterr()
        assert unique_output in captured.out

    @patch('time.sleep')
    def test_execute_handles_service_inactive(
        self, mock_sleep, app_session, mock_display, capsys
    ):
        """Test strategy handles service inactive error."""
        mock_collector = Mock()
        error = ClientError(
            error_response={
                'Error': {
                    'Code': 'InvalidParameterException',
                    'Message': 'Cannot call DescribeServiceRevisions for a service that is INACTIVE',
                }
            },
            operation_name='DescribeServiceRevisions',
        )
        mock_collector.get_current_view = Mock(side_effect=error)

        strategy = InteractiveDisplayStrategy(
            display=mock_display, use_color=True
        )

        mock_sleep.side_effect = KeyboardInterrupt()

        start_time = time.time()
        strategy.execute(mock_collector, start_time, timeout_minutes=1)

        # Strategy should handle the error and set output to "Service is inactive"
        captured = capsys.readouterr()
        assert "Service is inactive" in captured.out

    @patch('time.sleep')
    def test_execute_other_client_errors_propagate(
        self, mock_sleep, app_session, mock_display
    ):
        """Test strategy propagates non-service-inactive ClientErrors."""
        mock_collector = Mock()
        error = ClientError(
            error_response={
                'Error': {
                    'Code': 'AccessDeniedException',
                    'Message': 'Access denied',
                }
            },
            operation_name='DescribeServiceRevisions',
        )
        mock_collector.get_current_view = Mock(side_effect=error)

        strategy = InteractiveDisplayStrategy(
            display=mock_display, use_color=True
        )

        mock_sleep.side_effect = KeyboardInterrupt()

        start_time = time.time()

        # Other client errors should propagate
        with pytest.raises(ClientError) as exc_info:
            strategy.execute(mock_collector, start_time, timeout_minutes=1)

        assert (
            exc_info.value.response['Error']['Code'] == 'AccessDeniedException'
        )
