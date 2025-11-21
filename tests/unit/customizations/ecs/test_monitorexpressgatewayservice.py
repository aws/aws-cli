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
        """Helper to create watcher with mocked display"""
        mock_display = Mock()
        mock_display.has_terminal.return_value = True
        mock_display._check_keypress.return_value = None
        mock_display._restore_terminal.return_value = None
        mock_display.display.return_value = None

        watcher = ECSExpressGatewayServiceWatcher(
            self.mock_client,
            self.service_arn,
            resource_view,
            timeout_minutes=timeout,
            display=mock_display,
        )

        # Mock exec to call the monitoring method once and print output
        original_monitor = watcher._monitor_express_gateway_service

        def mock_exec():
            try:
                output = original_monitor("⠋", self.service_arn, resource_view)
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
    def test_exec_combined_view_multiple_revisions(self, mock_sleep, capsys):
        """Test RESOURCE mode combines multiple service revisions correctly"""
        watcher = self._create_watcher_with_mocks()
        mock_sleep.side_effect = KeyboardInterrupt()

        # Multiple active configurations (combined view)
        self.mock_client.describe_express_gateway_service.return_value = {
            "service": {
                "serviceArn": self.service_arn,
                "cluster": "my-cluster",
                "activeConfigurations": [
                    {"serviceRevisionArn": "rev-1"},
                    {"serviceRevisionArn": "rev-2"},
                ],
            }
        }

        # Mock multiple revisions with different resources
        self.mock_client.describe_service_revisions.return_value = {
            "serviceRevisions": [
                {
                    "arn": "rev-1",
                    "ecsManagedResources": {
                        "ingressPaths": [
                            {
                                "endpoint": "https://api.example.com",
                                "loadBalancer": {
                                    "arn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/api-lb/1234",
                                    "status": "ACTIVE",
                                },
                            }
                        ],
                        "serviceSecurityGroups": [
                            {
                                "arn": "arn:aws:ec2:us-west-2:123456789012:security-group/sg-api123",
                                "status": "ACTIVE",
                            }
                        ],
                    },
                },
                {
                    "arn": "rev-2",
                    "ecsManagedResources": {
                        "ingressPaths": [
                            {
                                "endpoint": "https://web.example.com",
                                "loadBalancer": {
                                    "arn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/web-lb/5678",
                                    "status": "CREATING",
                                },
                            }
                        ],
                        "logGroups": [
                            {
                                "arn": "arn:aws:logs:us-west-2:123456789012:log-group:/aws/ecs/web-logs",
                                "status": "ACTIVE",
                            }
                        ],
                    },
                },
            ]
        }

        self.mock_client.describe_services.return_value = {
            "services": [
                {"events": [{"message": "Multiple revisions active"}]}
            ]
        }

        watcher.exec()
        captured = capsys.readouterr()
        output_text = captured.out

        # Verify combined view shows resources from both revisions
        # Resource types from both revisions
        assert "IngressPath" in output_text
        assert "LoadBalancer" in output_text
        assert "SecurityGroup" in output_text  # From rev-1
        assert "LogGroup" in output_text  # From rev-2

        # Specific identifiers from both revisions
        assert "https://api.example.com" in output_text  # From rev-1
        assert "https://web.example.com" in output_text  # From rev-2
        assert "api-lb" in output_text  # From rev-1
        assert "web-lb" in output_text  # From rev-2
        assert "sg-api123" in output_text  # From rev-1
        assert "/aws/ecs/web-logs" in output_text  # From rev-2

        # Status values from both revisions
        assert "ACTIVE" in output_text  # From both revisions
        assert "CREATING" in output_text  # From rev-2

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

    @patch('time.sleep')
    def test_exec_with_inactive_service_handled_gracefully(
        self, mock_sleep, capsys
    ):
        """Test exec() handles inactive service gracefully"""
        watcher = self._create_watcher_with_mocks()
        mock_sleep.side_effect = KeyboardInterrupt()

        self.mock_client.describe_express_gateway_service.side_effect = ClientError(
            error_response={
                'Error': {
                    'Code': 'InvalidParameterException',
                    'Message': 'Cannot call DescribeServiceRevisions for a service that is INACTIVE',
                }
            },
            operation_name='DescribeExpressGatewayService',
        )
        self.mock_client.describe_services.return_value = {
            "services": [{"events": [{"message": "Service is inactive"}]}]
        }

        watcher.exec()
        captured = capsys.readouterr()

        # Verify inactive service is handled and appropriate message shown
        assert "inactive" in captured.out.lower()

    @patch('time.sleep')
    def test_exec_with_empty_resources(self, mock_sleep, capsys):
        """Test parsing edge case: empty/null resources"""
        watcher = self._create_watcher_with_mocks()
        mock_sleep.side_effect = KeyboardInterrupt()

        self.mock_client.describe_express_gateway_service.return_value = {
            "service": {
                "serviceArn": self.service_arn,
                "cluster": "my-cluster",
                "activeConfigurations": [{"serviceRevisionArn": "rev-arn"}],
            }
        }
        # Empty ecsManagedResources
        self.mock_client.describe_service_revisions.return_value = {
            "serviceRevisions": [{"arn": "rev-arn", "ecsManagedResources": {}}]
        }
        self.mock_client.describe_services.return_value = {
            "services": [{"events": [{"message": "No resources"}]}]
        }

        watcher.exec()
        captured = capsys.readouterr()
        output_text = captured.out

        # Should handle empty resources gracefully but still show basic structure
        assert "Cluster" in output_text
        assert "Service" in output_text
        # Should NOT contain resource types since ecsManagedResources is empty
        assert "IngressPath" not in output_text
        assert "LoadBalancer" not in output_text

    @patch('time.sleep')
    def test_exec_with_autoscaling_resources(self, mock_sleep, capsys):
        """Test autoscaling resource parsing with scalableTarget and policies"""
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
                        "autoScaling": {
                            "scalableTarget": {
                                "arn": "arn:aws:application-autoscaling:us-west-2:123456789012:scalable-target/1234567890abcdef",
                                "status": "ACTIVE",
                            },
                            "applicationAutoScalingPolicies": [
                                {
                                    "arn": "arn:aws:application-autoscaling:us-west-2:123456789012:scaling-policy/cpu-policy",
                                    "status": "ACTIVE",
                                },
                                {
                                    "arn": "arn:aws:application-autoscaling:us-west-2:123456789012:scaling-policy/memory-policy",
                                    "status": "ACTIVE",
                                },
                            ],
                        }
                    },
                }
            ]
        }
        self.mock_client.describe_services.return_value = {
            "services": [{"events": [{"message": "Autoscaling active"}]}]
        }

        watcher.exec()
        captured = capsys.readouterr()
        output_text = captured.out

        assert "AutoScaling" in output_text
        assert "ScalableTarget" in output_text
        assert "AutoScalingPolicy" in output_text
        # ScalableTarget identifier
        assert "1234567890abcdef" in output_text
        # Policy identifiers
        assert "cpu-policy" in output_text
        assert "memory-policy" in output_text

    @patch('time.sleep')
    def test_exec_with_malformed_resource_data(self, mock_sleep, capsys):
        """Test parsing edge case: malformed resource data"""
        watcher = self._create_watcher_with_mocks()
        mock_sleep.side_effect = KeyboardInterrupt()

        self.mock_client.describe_express_gateway_service.return_value = {
            "service": {
                "serviceArn": self.service_arn,
                "cluster": "my-cluster",
                "activeConfigurations": [{"serviceRevisionArn": "rev-arn"}],
            }
        }
        # Malformed resources - missing required fields
        self.mock_client.describe_service_revisions.return_value = {
            "serviceRevisions": [
                {
                    "arn": "rev-arn",
                    "ecsManagedResources": {
                        "ingressPaths": [
                            {"endpoint": "https://example.com"}
                        ],  # Missing loadBalancer
                        "serviceSecurityGroups": [
                            {"status": "ACTIVE"}
                        ],  # Missing arn
                    },
                }
            ]
        }
        self.mock_client.describe_services.return_value = {
            "services": [{"events": [{"message": "Malformed data"}]}]
        }

        watcher.exec()
        captured = capsys.readouterr()
        output_text = captured.out

        # Should handle malformed data gracefully and show what it can parse
        assert "IngressPath" in output_text
        assert "https://example.com" in output_text
        # Should show SecurityGroup type even with missing arn
        assert "SecurityGroup" in output_text
        # Should NOT show LoadBalancer since it's missing from IngressPath
        assert "LoadBalancer" not in output_text

    @patch('time.sleep')
    def test_exec_eventually_consistent_missing_deployment(
        self, mock_sleep, capsys
    ):
        """Test eventually consistent behavior: deployment missing after list"""
        watcher = self._create_watcher_with_mocks()
        mock_sleep.side_effect = KeyboardInterrupt()

        self.mock_client.describe_express_gateway_service.return_value = {
            "service": {
                "serviceArn": self.service_arn,
                "cluster": "my-cluster",
                "activeConfigurations": [],
            }
        }
        # List shows deployment exists
        self.mock_client.list_service_deployments.return_value = {
            "serviceDeployments": [{"serviceDeploymentArn": "deploy-arn"}]
        }
        # But describe fails (eventually consistent)
        self.mock_client.describe_service_deployments.return_value = {
            "serviceDeployments": [],
            "failures": [{"arn": "deploy-arn", "reason": "MISSING"}],
        }
        self.mock_client.describe_services.return_value = {
            "services": [{"events": [{"message": "Eventually consistent"}]}]
        }

        watcher.exec()
        captured = capsys.readouterr()
        output_text = captured.out

        # Should handle eventually consistent missing deployment gracefully
        # Should show waiting state when deployment is missing
        assert "Trying to describe gateway service" in output_text
        assert "Monitoring Complete" in output_text

    @patch('time.sleep')
    def test_exec_eventually_consistent_missing_revision(
        self, mock_sleep, capsys
    ):
        """Test eventually consistent behavior: service revision missing after deployment describe"""
        watcher = self._create_watcher_with_mocks()
        mock_sleep.side_effect = KeyboardInterrupt()

        self.mock_client.describe_express_gateway_service.return_value = {
            "service": {
                "serviceArn": self.service_arn,
                "cluster": "my-cluster",
                "activeConfigurations": [],
            }
        }
        self.mock_client.list_service_deployments.return_value = {
            "serviceDeployments": [{"serviceDeploymentArn": "deploy-arn"}]
        }
        self.mock_client.describe_service_deployments.return_value = {
            "serviceDeployments": [
                {
                    "serviceDeploymentArn": "deploy-arn",
                    "status": "IN_PROGRESS",
                    "targetServiceRevision": {"arn": "target-rev"},
                }
            ]
        }
        # Service revision missing (eventually consistent)
        self.mock_client.describe_service_revisions.return_value = {
            "serviceRevisions": [],
            "failures": [{"arn": "target-rev", "reason": "MISSING"}],
        }
        self.mock_client.describe_services.return_value = {
            "services": [{"events": [{"message": "Revision missing"}]}]
        }

        watcher.exec()
        captured = capsys.readouterr()
        output_text = captured.out

        # Should handle eventually consistent missing revision gracefully
        # Should show waiting state when revision is missing
        assert "Trying to describe gateway service" in output_text
        assert "Monitoring Complete" in output_text

    @patch('time.sleep')
    def test_exec_with_api_failures(self, mock_sleep):
        """Test failure parsing: API returns failures"""
        watcher = self._create_watcher_with_mocks()
        mock_sleep.side_effect = KeyboardInterrupt()

        self.mock_client.describe_express_gateway_service.return_value = {
            "service": {
                "serviceArn": self.service_arn,
                "cluster": "my-cluster",
                "activeConfigurations": [{"serviceRevisionArn": "rev-arn"}],
            }
        }
        # API returns failures
        self.mock_client.describe_service_revisions.return_value = {
            "serviceRevisions": [],
            "failures": [{"arn": "rev-arn", "reason": "ServiceNotFound"}],
        }

        with pytest.raises(MonitoringError) as exc_info:
            watcher.exec()

        # Should raise MonitoringError with failure details
        error_message = str(exc_info.value)
        assert "DescribeServiceRevisions" in error_message
        assert "rev-arn" in error_message
        assert "ServiceNotFound" in error_message

    @patch('time.sleep')
    def test_exec_with_malformed_api_failures(self, mock_sleep):
        """Test failure parsing: malformed failure responses"""
        watcher = self._create_watcher_with_mocks()
        mock_sleep.side_effect = KeyboardInterrupt()

        self.mock_client.describe_express_gateway_service.return_value = {
            "service": {
                "serviceArn": self.service_arn,
                "cluster": "my-cluster",
                "activeConfigurations": [{"serviceRevisionArn": "rev-arn"}],
            }
        }
        # Malformed failures - missing arn or reason
        self.mock_client.describe_service_revisions.return_value = {
            "serviceRevisions": [],
            "failures": [{"reason": "ServiceNotFound"}],  # Missing arn
        }

        with pytest.raises(MonitoringError) as exc_info:
            watcher.exec()

        # Should raise MonitoringError about invalid failure response
        error_message = str(exc_info.value)
        assert "Invalid failure response" in error_message
        assert "missing arn or reason" in error_message

    @patch('time.sleep')
    def test_exec_with_missing_response_fields(self, mock_sleep):
        """Test response validation: missing required fields"""
        watcher = self._create_watcher_with_mocks()
        mock_sleep.side_effect = KeyboardInterrupt()

        self.mock_client.describe_express_gateway_service.return_value = {
            "service": {
                "serviceArn": self.service_arn,
                "cluster": "my-cluster",
                "activeConfigurations": [{"serviceRevisionArn": "rev-arn"}],
            }
        }
        # Missing serviceRevisions field
        self.mock_client.describe_service_revisions.return_value = {}

        with pytest.raises(MonitoringError) as exc_info:
            watcher.exec()

        # Should raise MonitoringError about empty response
        error_message = str(exc_info.value)
        assert "DescribeServiceRevisions" in error_message
        assert "empty" in error_message


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
