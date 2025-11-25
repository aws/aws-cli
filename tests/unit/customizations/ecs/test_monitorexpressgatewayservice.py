# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/

import asyncio
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
            service_arn="test-arn",
            resource_view="RESOURCE",
            mode="INTERACTIVE",
            timeout=30,
        )
        parsed_globals = Mock(
            region="us-west-2",
            endpoint_url=None,
            verify_ssl=True,
            color="auto",
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
            service_arn="test-arn",
            resource_view="RESOURCE",
            mode="INTERACTIVE",
            timeout=30,
        )
        parsed_globals = Mock(
            region="us-west-2",
            endpoint_url=None,
            verify_ssl=True,
            color="auto",
        )

        with pytest.raises(ValueError):
            command._run_main(parsed_args, parsed_globals)

    @patch('sys.stdout.isatty')
    def test_interactive_mode_requires_tty(self, mock_isatty, capsys):
        """Test command fails when INTERACTIVE mode without TTY"""
        # Not in TTY
        mock_isatty.return_value = False

        mock_session = Mock()
        command = ECSMonitorExpressGatewayService(mock_session)

        parsed_args = Mock(
            service_arn="test-arn",
            resource_view="RESOURCE",
            mode="interactive",
            timeout=30,
        )
        parsed_globals = Mock(
            region="us-west-2",
            endpoint_url=None,
            verify_ssl=True,
            color="auto",
        )

        result = command._run_main(parsed_args, parsed_globals)

        captured = capsys.readouterr()
        assert result == 1
        assert "Interactive mode requires a TTY" in captured.err

    @patch('sys.stdout.isatty')
    def test_run_main_with_text_only_mode_no_tty(self, mock_isatty):
        """Test text-only mode works without TTY."""
        mock_isatty.return_value = False

        mock_session = Mock()
        mock_watcher_class = Mock()
        mock_watcher = Mock()
        mock_watcher_class.return_value = mock_watcher

        command = ECSMonitorExpressGatewayService(
            mock_session, watcher_class=mock_watcher_class
        )

        parsed_args = Mock(
            service_arn="test-arn",
            resource_view="RESOURCE",
            mode="text-only",
            timeout=30,
        )
        parsed_globals = Mock(
            region="us-west-2",
            endpoint_url=None,
            verify_ssl=True,
            color="auto",
        )

        command._run_main(parsed_args, parsed_globals)

        # Watcher should be created with text-only mode
        mock_watcher_class.assert_called_once()


class TestECSExpressGatewayServiceWatcher:
    """Test the watcher class through public interface"""

    def setup_method(self):
        self.app_session = create_app_session(output=DummyOutput())
        self.app_session.__enter__()
        self.mock_client = Mock()
        self.service_arn = (
            "arn:aws:ecs:us-west-2:123456789012:service/my-cluster/my-service"
        )

    def teardown_method(self):
        if hasattr(self, 'app_session'):
            self.app_session.__exit__(None, None, None)

    def _create_watcher_with_mocks(self, resource_view="RESOURCE", timeout=1):
        """Helper to create watcher with mocked display and collector"""

        async def mock_run_async():
            # Mock async display.run() - just wait briefly then exit
            await asyncio.sleep(0.01)

        mock_display = Mock()
        mock_display.has_terminal.return_value = True
        mock_display._check_keypress.return_value = None
        mock_display._restore_terminal.return_value = None
        mock_display.display.return_value = None
        mock_display.run.return_value = mock_run_async()

        # Mock the collector to avoid all the API complexity
        mock_collector = Mock()
        mock_collector.get_current_view = Mock(return_value="Mocked view")

        watcher = ECSExpressGatewayServiceWatcher(
            self.mock_client,
            self.service_arn,
            resource_view,
            'INTERACTIVE',
            timeout_minutes=timeout,
            display=mock_display,
            collector=mock_collector,
        )

        # Make collector accessible for tests
        watcher.mock_collector = mock_collector

        return watcher

    @patch('time.sleep')
    def test_exec_successful_all_mode_monitoring(self, mock_sleep, capsys):
        """Test successful monitoring in RESOURCE mode with resource parsing"""
        watcher = self._create_watcher_with_mocks()
        watcher.mock_collector.get_current_view.return_value = (
            "Cluster\nService\nIngressPath\nLoadBalancer\nTargetGroup"
        )
        mock_sleep.side_effect = KeyboardInterrupt()

        watcher.exec()
        captured = capsys.readouterr()
        output_text = captured.out

        assert "Cluster" in output_text

    @patch('time.sleep')
    def test_exec_successful_delta_mode_with_deployment(
        self, mock_sleep, capsys
    ):
        """Test DEPLOYMENT mode executes successfully"""
        watcher = self._create_watcher_with_mocks()
        mock_sleep.side_effect = KeyboardInterrupt()

        self.mock_client.describe_express_gateway_service.return_value = {
            "service": {
                "serviceArn": self.service_arn,
                "cluster": "my-cluster",
                "activeConfigurations": [],
            }
        }
        self.mock_client.describe_services.return_value = {
            "services": [{"events": [{"message": "Service running"}]}]
        }

        watcher.exec()
        captured = capsys.readouterr()

        # Verify DEPLOYMENT mode executes successfully
        assert captured.out


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
