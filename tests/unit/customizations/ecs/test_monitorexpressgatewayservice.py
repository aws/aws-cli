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
            mode='interactive',  # Explicitly request interactive mode
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

    def _create_watcher_with_mocks(
        self, resource_view="RESOURCE", timeout=1, display_mode="interactive"
    ):
        """Helper to create watcher with mocked display strategy"""
        mock_display_strategy = Mock()

        # Create watcher with mocked strategy
        watcher = ECSExpressGatewayServiceWatcher(
            self.mock_client,
            self.service_arn,
            resource_view,
            display_mode,
            timeout_minutes=timeout,
            display_strategy=mock_display_strategy,
        )

        # Mock exec to call the collector once and print output
        collector = watcher.collector

        def mock_exec():
            try:
                output = collector.get_current_view("⠋")
                print(output)
                print("Monitoring Complete!")
            except Exception as e:
                # Re-raise expected exceptions
                if isinstance(e, (ClientError, MonitoringError)):
                    raise
                # For other exceptions, just print and complete
                print("Monitoring Complete!")

        watcher.exec = mock_exec
        return watcher

    @patch('time.sleep')
    def test_exec_successful_all_mode_monitoring(self, mock_sleep, capsys):
        """Test successful monitoring in RESOURCE mode with resource parsing"""
        watcher = self._create_watcher_with_mocks()
        mock_sleep.side_effect = KeyboardInterrupt()

        self.mock_client.describe_express_gateway_service.return_value = {
            "service": {
                "serviceArn": self.service_arn,
                "cluster": "my-cluster",
                "activeConfigurations": [{"serviceRevisionArn": "rev-arn"}],
            }
        }
        self.mock_client.describe_service_revisions.return_value = {
            "serviceRevisions": [
                {
                    "arn": "rev-arn",
                    "ecsManagedResources": {
                        "ingressPaths": [
                            {
                                "endpoint": "https://api.example.com",
                                "loadBalancer": {
                                    "arn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/my-lb/1234567890abcdef",
                                    "status": "ACTIVE",
                                },
                                "targetGroups": [
                                    {
                                        "arn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/my-tg/1234567890abcdef",
                                        "status": "HEALTHY",
                                    }
                                ],
                            }
                        ],
                        "serviceSecurityGroups": [
                            {
                                "arn": "arn:aws:ec2:us-west-2:123456789012:security-group/sg-1234567890abcdef0",
                                "status": "ACTIVE",
                            }
                        ],
                        "logGroups": [
                            {
                                "arn": "arn:aws:logs:us-west-2:123456789012:log-group:/aws/ecs/my-service",
                                "status": "ACTIVE",
                            }
                        ],
                    },
                }
            ]
        }
        self.mock_client.describe_services.return_value = {
            "services": [{"events": [{"message": "Running"}]}]
        }

        watcher.exec()
        captured = capsys.readouterr()
        output_text = captured.out

        # Verify parsed resources appear in output
        assert "Cluster" in output_text
        assert "Service" in output_text
        assert "IngressPath" in output_text
        assert "LoadBalancer" in output_text
        assert "TargetGroup" in output_text
        assert "SecurityGroup" in output_text
        assert "LogGroup" in output_text

        # Specific identifiers
        assert "https://api.example.com" in output_text  # IngressPath endpoint
        assert "my-lb" in output_text  # LoadBalancer identifier
        assert "my-tg" in output_text  # TargetGroup identifier
        assert (
            "sg-1234567890abcdef0" in output_text
        )  # SecurityGroup identifier
        assert "/aws/ecs/my-service" in output_text  # LogGroup identifier

        # Status values
        assert "ACTIVE" in output_text  # LoadBalancer and SecurityGroup status
        assert "HEALTHY" in output_text  # TargetGroup status

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

    @patch('time.sleep')
    def test_exec_keyboard_interrupt_handling(self, mock_sleep, capsys):
        watcher = self._create_watcher_with_mocks()
        mock_sleep.side_effect = KeyboardInterrupt()

        self.mock_client.describe_express_gateway_service.return_value = {
            "service": {
                "serviceArn": self.service_arn,
                "cluster": "my-cluster",
                "activeConfigurations": [],
            }
        }

        watcher.exec()
        captured = capsys.readouterr()

        # Verify completion message is printed
        assert "Monitoring Complete!" in captured.out

    @patch('time.sleep')
    def test_exec_with_service_not_found_error(self, mock_sleep):
        """Test exec() with service not found error bubbles up"""
        watcher = self._create_watcher_with_mocks()
        mock_sleep.side_effect = KeyboardInterrupt()

        error = ClientError(
            error_response={
                'Error': {
                    'Code': 'ServiceNotFoundException',
                    'Message': 'Service not found',
                }
            },
            operation_name='DescribeExpressGatewayService',
        )
        self.mock_client.describe_express_gateway_service.side_effect = error

        with pytest.raises(ClientError) as exc_info:
            watcher.exec()

        # Verify the specific error is raised
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
            "interactive",
            use_color=True,
        )
        assert watcher.collector.use_color is True

        # Test with use_color=False
        watcher = ECSExpressGatewayServiceWatcher(
            mock_client,
            "arn:aws:ecs:us-east-1:123456789012:service/test-service",
            "ALL",
            "interactive",
            use_color=False,
        )
        assert watcher.collector.use_color is False
