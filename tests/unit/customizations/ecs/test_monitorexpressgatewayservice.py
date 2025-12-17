# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/

from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError
from prompt_toolkit.application import create_app_session
from prompt_toolkit.output import DummyOutput

from awscli.customizations.ecs.exceptions import MonitoringError
from awscli.customizations.ecs.monitorexpressgatewayservice import (
    ECSExpressGatewayServiceWatcher,
    ECSMonitorExpressGatewayService,
)


class TestECSMonitorExpressGatewayServiceCommand:
    """Test the command class through public interface"""

    @patch('sys.stdout.isatty')
    def test_monitoring_error_handled_gracefully(self, mock_isatty, capsys):
        """Test MonitoringError is caught and printed"""
        # Mock TTY for interactive mode
        mock_isatty.return_value = True

        mock_session = Mock()
        mock_client = Mock()
        mock_session.create_client.return_value = mock_client

        mock_watcher_class = Mock()
        mock_watcher = Mock()
        mock_watcher.exec.side_effect = MonitoringError("Test error")
        mock_watcher_class.return_value = mock_watcher

        command = ECSMonitorExpressGatewayService(
            mock_session, watcher_class=mock_watcher_class
        )

        parsed_args = Mock(
            service_arn="test-arn", resource_view="RESOURCE", timeout=30
        )
        parsed_globals = Mock(
            region="us-west-2", endpoint_url=None, verify_ssl=True
        )

        command._run_main(parsed_args, parsed_globals)

        captured = capsys.readouterr()
        assert "Error monitoring service: Test error" in captured.err

    @patch('sys.stdout.isatty')
    def test_non_monitoring_error_bubbles_up(self, mock_isatty):
        """Test non-MonitoringError exceptions are not caught"""
        # Mock TTY for interactive mode
        mock_isatty.return_value = True

        mock_session = Mock()
        command = ECSMonitorExpressGatewayService(mock_session)

        mock_session.create_client.side_effect = ValueError("Unexpected error")

        parsed_args = Mock(
            service_arn="test-arn", resource_view="RESOURCE", timeout=30
        )
        parsed_globals = Mock(
            region="us-west-2", endpoint_url=None, verify_ssl=True
        )

        with pytest.raises(ValueError):
            command._run_main(parsed_args, parsed_globals)

    @patch('sys.stdout.isatty')
    def test_interactive_mode_requires_tty(self, mock_isatty, capsys):
        """Test interactive mode fails without TTY"""
        # Not in TTY
        mock_isatty.return_value = False

        mock_session = Mock()
        mock_client = Mock()
        mock_session.create_client.return_value = mock_client

        command = ECSMonitorExpressGatewayService(mock_session)

        parsed_args = Mock(
            service_arn="test-arn",
            resource_view="RESOURCE",
            timeout=30,
            mode='INTERACTIVE',
        )
        parsed_globals = Mock(
            region="us-west-2",
            endpoint_url=None,
            verify_ssl=True,
            color='auto',
        )

        result = command._run_main(parsed_args, parsed_globals)

        captured = capsys.readouterr()
        assert "Interactive mode requires a TTY" in captured.err
        assert result == 1

    @patch('sys.stdout.isatty')
    def test_text_only_mode_without_tty(self, mock_isatty, capsys):
        """Test command uses text-only mode when not in TTY"""
        # Not in TTY
        mock_isatty.return_value = False

        mock_session = Mock()
        mock_client = Mock()
        mock_session.create_client.return_value = mock_client

        mock_watcher_class = Mock()
        mock_watcher = Mock()
        mock_watcher_class.return_value = mock_watcher

        command = ECSMonitorExpressGatewayService(
            mock_session, watcher_class=mock_watcher_class
        )

        parsed_args = Mock(
            service_arn="test-arn",
            resource_view="RESOURCE",
            timeout=30,
            mode=None,
        )
        parsed_globals = Mock(
            region="us-west-2", endpoint_url=None, verify_ssl=True
        )

        command._run_main(parsed_args, parsed_globals)


@pytest.fixture
def watcher_app_session():
    """Fixture that creates and manages an app session for watcher tests."""
    with create_app_session(output=DummyOutput()) as session:
        yield session


@pytest.fixture
def service_arn():
    """Fixture that provides a test service ARN."""
    return "arn:aws:ecs:us-west-2:123456789012:service/my-cluster/my-service"


class TestECSExpressGatewayServiceWatcher:
    """Test the watcher class through public interface"""

    def test_init_creates_collector_with_correct_parameters(self):
        """Test watcher creates collector with correct client, service_arn, resource_view, use_color"""
        mock_client = Mock()
        service_arn = "arn:aws:ecs:us-west-2:123456789012:service/test-service"

        watcher = ECSExpressGatewayServiceWatcher(
            mock_client,
            service_arn,
            resource_view="DEPLOYMENT",
            display_mode="TEXT-ONLY",
            use_color=False,
        )

        # Verify collector was created with correct parameters
        assert watcher.collector is not None
        assert watcher.collector._client == mock_client
        assert watcher.collector.service_arn == service_arn
        assert watcher.collector.mode == "DEPLOYMENT"
        assert watcher.collector.use_color is False

    def test_init_uses_injected_collector(self):
        """Test watcher uses injected collector instead of creating one"""
        mock_collector = Mock()

        watcher = ECSExpressGatewayServiceWatcher(
            Mock(),
            "arn:aws:ecs:us-west-2:123456789012:service/test-service",
            "RESOURCE",
            "INTERACTIVE",
            collector=mock_collector,
        )

        assert watcher.collector == mock_collector

    def test_exec_calls_display_strategy_with_correct_parameters(
        self, watcher_app_session
    ):
        """Test exec() calls display strategy with collector, start_time, and timeout"""
        mock_collector = Mock()
        mock_display_strategy = Mock()

        watcher = ECSExpressGatewayServiceWatcher(
            Mock(),
            "arn:aws:ecs:us-west-2:123456789012:service/test-service",
            "RESOURCE",
            "INTERACTIVE",
            timeout_minutes=15,
            display_strategy=mock_display_strategy,
            collector=mock_collector,
        )

        watcher.exec()

        # Verify display strategy was called once
        mock_display_strategy.execute_monitoring.assert_called_once()

        # Verify correct parameters were passed
        call_args = mock_display_strategy.execute_monitoring.call_args
        assert call_args.kwargs['collector'] == mock_collector
        assert call_args.kwargs['start_time'] == watcher.start_time
        assert call_args.kwargs['timeout_minutes'] == 15

    def test_exec_propagates_exceptions_from_display_strategy(
        self, watcher_app_session
    ):
        """Test exec() propagates exceptions from display strategy"""
        mock_display_strategy = Mock()
        mock_display_strategy.execute_monitoring.side_effect = ClientError(
            error_response={
                'Error': {
                    'Code': 'ServiceNotFoundException',
                    'Message': 'Service not found',
                }
            },
            operation_name='DescribeExpressGatewayService',
        )

        watcher = ECSExpressGatewayServiceWatcher(
            Mock(),
            "arn:aws:ecs:us-west-2:123456789012:service/test-service",
            "RESOURCE",
            "INTERACTIVE",
            display_strategy=mock_display_strategy,
            collector=Mock(),
        )

        with pytest.raises(ClientError) as exc_info:
            watcher.exec()

        assert (
            exc_info.value.response['Error']['Code']
            == 'ServiceNotFoundException'
        )
        assert (
            exc_info.value.response['Error']['Message'] == 'Service not found'
        )


class TestMonitoringError:
    """Test MonitoringError exception class"""

    def test_monitoring_error_creation(self):
        """Test MonitoringError can be created with message"""
        error = MonitoringError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"


class TestColorSupport:
    """Test color support functionality"""

    def test_should_use_color_on(self):
        """Test _should_use_color returns True when color is 'on'"""
        command = ECSMonitorExpressGatewayService(Mock())
        parsed_globals = Mock()
        parsed_globals.color = 'on'

        assert command._should_use_color(parsed_globals) is True

    def test_should_use_color_off(self):
        """Test _should_use_color returns False when color is 'off'"""
        command = ECSMonitorExpressGatewayService(Mock())
        parsed_globals = Mock()
        parsed_globals.color = 'off'

        assert command._should_use_color(parsed_globals) is False

    @patch('sys.stdout.isatty')
    def test_should_use_color_auto_tty(self, mock_isatty):
        """Test _should_use_color returns True for 'auto' when stdout is TTY"""
        mock_isatty.return_value = True
        command = ECSMonitorExpressGatewayService(Mock())
        parsed_globals = Mock()
        parsed_globals.color = 'auto'

        assert command._should_use_color(parsed_globals) is True

    @patch('sys.stdout.isatty')
    def test_should_use_color_auto_no_tty(self, mock_isatty):
        """Test _should_use_color returns False for 'auto' when stdout is not TTY"""
        mock_isatty.return_value = False
        command = ECSMonitorExpressGatewayService(Mock())
        parsed_globals = Mock()
        parsed_globals.color = 'auto'

        assert command._should_use_color(parsed_globals) is False

    def test_watcher_accepts_use_color_parameter(self, watcher_app_session):
        """Test ECSExpressGatewayServiceWatcher accepts use_color parameter"""
        mock_client = Mock()

        # Test with use_color=True
        watcher = ECSExpressGatewayServiceWatcher(
            mock_client,
            "arn:aws:ecs:us-east-1:123456789012:service/test-service",
            "ALL",
            "INTERACTIVE",
            use_color=True,
        )
        assert watcher.collector.use_color is True

        # Test with use_color=False
        watcher = ECSExpressGatewayServiceWatcher(
            mock_client,
            "arn:aws:ecs:us-east-1:123456789012:service/test-service",
            "ALL",
            "INTERACTIVE",
            use_color=False,
        )
        assert watcher.collector.use_color is False

    def test_invalid_display_mode_raises_error(self):
        """Test that invalid display mode raises ValueError"""
        mock_client = Mock()

        with pytest.raises(ValueError) as exc_info:
            ECSExpressGatewayServiceWatcher(
                mock_client,
                "arn:aws:ecs:us-east-1:123456789012:service/test-service",
                "RESOURCE",
                "INVALID_MODE",
            )
        assert "Invalid display mode: INVALID_MODE" in str(exc_info.value)
