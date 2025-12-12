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

# Suppress thread exception warnings - tests use KeyboardInterrupt to exit monitoring loops,
# which causes expected exceptions in background threads
pytestmark = pytest.mark.filterwarnings(
    "ignore::pytest.PytestUnhandledThreadExceptionWarning"
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
        """Test command fails when not in TTY"""
        # Not in TTY
        mock_isatty.return_value = False

        mock_session = Mock()
        command = ECSMonitorExpressGatewayService(mock_session)

        parsed_args = Mock(
            service_arn="test-arn", resource_view="RESOURCE", timeout=30
        )
        parsed_globals = Mock(
            region="us-west-2", endpoint_url=None, verify_ssl=True
        )

        result = command._run_main(parsed_args, parsed_globals)

        captured = capsys.readouterr()
        assert result == 1
        assert "This command requires a TTY" in captured.err


class TestECSExpressGatewayServiceWatcher:
    """Test the watcher class through public interface"""

    @patch('sys.stdout.isatty')
    def test_is_monitoring_available_with_tty(self, mock_isatty):
        """Test is_monitoring_available returns True when TTY is available"""
        mock_isatty.return_value = True
        assert (
            ECSExpressGatewayServiceWatcher.is_monitoring_available() is True
        )

    @patch('sys.stdout.isatty')
    def test_is_monitoring_available_without_tty(self, mock_isatty):
        """Test is_monitoring_available returns False when TTY is not available"""
        mock_isatty.return_value = False
        assert (
            ECSExpressGatewayServiceWatcher.is_monitoring_available() is False
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

    def setup_method(self):
        self.app_session = create_app_session(output=DummyOutput())
        self.app_session.__enter__()

    def teardown_method(self):
        if hasattr(self, 'app_session'):
            self.app_session.__exit__(None, None, None)

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

    def test_watcher_accepts_use_color_parameter(self):
        """Test ECSExpressGatewayServiceWatcher accepts use_color parameter"""
        mock_client = Mock()

        # Test with use_color=True
        watcher = ECSExpressGatewayServiceWatcher(
            mock_client,
            "arn:aws:ecs:us-east-1:123456789012:service/test-service",
            "ALL",
            use_color=True,
        )
        assert watcher.use_color is True

        # Test with use_color=False
        watcher = ECSExpressGatewayServiceWatcher(
            mock_client,
            "arn:aws:ecs:us-east-1:123456789012:service/test-service",
            "ALL",
            use_color=False,
        )
        assert watcher.use_color is False
