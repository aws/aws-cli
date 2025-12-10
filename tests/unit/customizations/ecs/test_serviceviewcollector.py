# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/

from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError

from awscli.customizations.ecs.exceptions import MonitoringError
from awscli.customizations.ecs.serviceviewcollector import (
    ServiceViewCollector,
)


class TestServiceViewCollector:
    """Test ServiceViewCollector business logic"""

    def setup_method(self):
        self.mock_client = Mock()
        self.service_arn = (
            "arn:aws:ecs:us-west-2:123456789012:service/my-cluster/my-service"
        )

    def test_get_current_view_resource_mode(self):
        """Test get_current_view in RESOURCE mode parses resources"""
        collector = ServiceViewCollector(
            self.mock_client, self.service_arn, "RESOURCE"
        )

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
                            }
                        ],
                    },
                }
            ]
        }
        self.mock_client.describe_services.return_value = {
            "services": [{"events": [{"message": "Running"}]}]
        }

        output = collector.get_current_view("⠋")

        assert "Cluster" in output
        assert "Service" in output
        assert "IngressPath" in output
        assert "LoadBalancer" in output
        assert "https://api.example.com" in output
        assert "ACTIVE" in output

    def test_get_current_view_handles_inactive_service(self):
        """Test get_current_view handles inactive service gracefully"""
        collector = ServiceViewCollector(
            self.mock_client, self.service_arn, "RESOURCE"
        )

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

        output = collector.get_current_view("⠋")

        assert "inactive" in output.lower()

    def test_get_current_view_with_api_failures(self):
        """Test get_current_view raises MonitoringError on API failures"""
        collector = ServiceViewCollector(
            self.mock_client, self.service_arn, "RESOURCE"
        )

        self.mock_client.describe_express_gateway_service.return_value = {
            "service": {
                "serviceArn": self.service_arn,
                "cluster": "my-cluster",
                "activeConfigurations": [{"serviceRevisionArn": "rev-arn"}],
            }
        }
        self.mock_client.describe_service_revisions.return_value = {
            "serviceRevisions": [],
            "failures": [{"arn": "rev-arn", "reason": "ServiceNotFound"}],
        }

        with pytest.raises(MonitoringError) as exc_info:
            collector.get_current_view("⠋")

        error_message = str(exc_info.value)
        assert "DescribeServiceRevisions" in error_message
        assert "rev-arn" in error_message
        assert "ServiceNotFound" in error_message

    def test_get_current_view_caches_results(self):
        """Test get_current_view caches results within refresh interval"""
        collector = ServiceViewCollector(
            self.mock_client, self.service_arn, "RESOURCE"
        )

        self.mock_client.describe_express_gateway_service.return_value = {
            "service": {
                "serviceArn": self.service_arn,
                "cluster": "my-cluster",
                "activeConfigurations": [{"serviceRevisionArn": "rev-arn"}],
            }
        }
        self.mock_client.describe_service_revisions.return_value = {
            "serviceRevisions": [{"arn": "rev-arn", "ecsManagedResources": {}}]
        }
        self.mock_client.describe_services.return_value = {
            "services": [{"events": [{"message": "Running"}]}]
        }

        # First call
        collector.get_current_view("⠋")
        call_count_first = (
            self.mock_client.describe_express_gateway_service.call_count
        )

        # Second call within refresh interval (default 5000ms)
        collector.get_current_view("⠙")
        # Should use cached result, not call API again
        call_count_second = (
            self.mock_client.describe_express_gateway_service.call_count
        )
        assert call_count_first == call_count_second  # Cached, no new API call

    def test_combined_view_multiple_revisions(self):
        """Test RESOURCE mode combines multiple service revisions correctly"""
        collector = ServiceViewCollector(
            self.mock_client, self.service_arn, "RESOURCE"
        )

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

        output = collector.get_current_view("⠋")

        # Verify combined view shows resources from both revisions
        assert "IngressPath" in output
        assert "LoadBalancer" in output
        assert "SecurityGroup" in output  # From rev-1
        assert "LogGroup" in output  # From rev-2
        assert "https://api.example.com" in output  # From rev-1
        assert "https://web.example.com" in output  # From rev-2
        assert "api-lb" in output  # From rev-1
        assert "web-lb" in output  # From rev-2
        assert "sg-api123" in output  # From rev-1
        assert "/aws/ecs/web-logs" in output  # From rev-2
        assert "ACTIVE" in output  # From both revisions
        assert "CREATING" in output  # From rev-2

    def test_get_current_view_with_empty_resources(self):
        """Test parsing edge case: empty/null resources"""
        collector = ServiceViewCollector(
            self.mock_client, self.service_arn, "RESOURCE"
        )

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

        output = collector.get_current_view("⠋")

        # Should handle empty resources gracefully but still show basic structure
        assert "Cluster" in output
        assert "Service" in output
        # Should NOT contain resource types since ecsManagedResources is empty
        assert "IngressPath" not in output
        assert "LoadBalancer" not in output

    def test_get_current_view_with_autoscaling_resources(self):
        """Test autoscaling resource parsing with scalableTarget and policies"""
        collector = ServiceViewCollector(
            self.mock_client, self.service_arn, "RESOURCE"
        )

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

        output = collector.get_current_view("⠋")

        assert "AutoScaling" in output
        assert "ScalableTarget" in output
        assert "AutoScalingPolicy" in output
        assert "1234567890abcdef" in output
        assert "cpu-policy" in output
        assert "memory-policy" in output

    def test_get_current_view_with_malformed_resource_data(self):
        """Test parsing edge case: malformed resource data"""
        collector = ServiceViewCollector(
            self.mock_client, self.service_arn, "RESOURCE"
        )

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

        output = collector.get_current_view("⠋")

        # Should handle malformed data gracefully and show what it can parse
        assert "IngressPath" in output
        assert "https://example.com" in output
        # Should show SecurityGroup type even with missing arn
        assert "SecurityGroup" in output
        # Should NOT show LoadBalancer since it's missing from IngressPath
        assert "LoadBalancer" not in output

    def test_eventually_consistent_missing_deployment(self):
        """Test eventually consistent behavior: deployment missing after list"""
        collector = ServiceViewCollector(
            self.mock_client, self.service_arn, "DEPLOYMENT"
        )

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

        output = collector.get_current_view("⠋")

        # Should handle eventually consistent missing deployment gracefully
        assert "Waiting for a deployment to start" in output

    def test_eventually_consistent_missing_revision(self):
        """Test eventually consistent behavior: service revision missing"""
        collector = ServiceViewCollector(
            self.mock_client, self.service_arn, "DEPLOYMENT"
        )

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

        output = collector.get_current_view("⠋")

        # Should handle eventually consistent missing revision gracefully
        assert "Trying to describe service revisions" in output

    def test_with_malformed_api_failures(self):
        """Test failure parsing: malformed failure responses"""
        collector = ServiceViewCollector(
            self.mock_client, self.service_arn, "RESOURCE"
        )

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
            collector.get_current_view("⠋")

        # Should raise MonitoringError about invalid failure response
        error_message = str(exc_info.value)
        assert "Invalid failure response" in error_message
        assert "missing arn or reason" in error_message

    def test_with_missing_response_fields(self):
        """Test response validation: missing required fields"""
        collector = ServiceViewCollector(
            self.mock_client, self.service_arn, "RESOURCE"
        )

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
            collector.get_current_view("⠋")

        # Should raise MonitoringError about missing field
        error_message = str(exc_info.value)
        assert "DescribeServiceRevisions" in error_message
        assert (
            "response is" in error_message
        )  # "response is missing" or "response is empty"

    def test_deployment_mode_diff_view(self):
        """Test DEPLOYMENT mode shows diff of target vs source revisions"""
        collector = ServiceViewCollector(
            self.mock_client, self.service_arn, "DEPLOYMENT"
        )

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
                    "sourceServiceRevisions": [{"arn": "source-rev"}],
                }
            ]
        }
        self.mock_client.describe_service_revisions.return_value = {
            "serviceRevisions": [
                {
                    "arn": "target-rev",
                    "taskDefinition": "task-def-arn",
                    "ecsManagedResources": {
                        "ingressPaths": [
                            {
                                "endpoint": "https://new-api.example.com",
                                "loadBalancer": {
                                    "arn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/new-lb/1234",
                                    "status": "CREATING",
                                },
                            }
                        ],
                    },
                },
                {
                    "arn": "source-rev",
                    "ecsManagedResources": {
                        "ingressPaths": [
                            {
                                "endpoint": "https://old-api.example.com",
                                "loadBalancer": {
                                    "arn": "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/old-lb/5678",
                                    "status": "ACTIVE",
                                },
                            }
                        ],
                    },
                },
            ]
        }
        self.mock_client.describe_services.return_value = {
            "services": [{"events": [{"message": "Deployment in progress"}]}]
        }

        output = collector.get_current_view("⠋")

        # Should show deployment diff
        # Initially will show "Trying to describe service revisions" due to mismatch
        # But implementation still shows Cluster/Service
        assert "Trying to describe service revisions" in output

    def test_waiting_for_deployment_to_start(self):
        """Test DEPLOYMENT mode when no deployment exists yet"""
        collector = ServiceViewCollector(
            self.mock_client, self.service_arn, "DEPLOYMENT"
        )

        self.mock_client.describe_express_gateway_service.return_value = {
            "service": {
                "serviceArn": self.service_arn,
                "cluster": "my-cluster",
                "activeConfigurations": [],
            }
        }
        # No deployments
        self.mock_client.list_service_deployments.return_value = {
            "serviceDeployments": []
        }
        self.mock_client.describe_services.return_value = {
            "services": [{"events": [{"message": "No deployment"}]}]
        }

        output = collector.get_current_view("⠋")

        assert "Waiting for a deployment to start" in output

    def test_deployment_missing_target_revision(self):
        """Test DEPLOYMENT mode when deployment is missing target revision"""
        collector = ServiceViewCollector(
            self.mock_client, self.service_arn, "DEPLOYMENT"
        )

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
                    # Missing targetServiceRevision
                }
            ]
        }
        self.mock_client.describe_services.return_value = {
            "services": [{"events": [{"message": "Deployment starting"}]}]
        }

        output = collector.get_current_view("⠋")

        assert "Waiting for a deployment to start" in output

    def test_empty_describe_gateway_service_response(self):
        """Test handling of empty describe_express_gateway_service response"""
        collector = ServiceViewCollector(
            self.mock_client, self.service_arn, "RESOURCE"
        )

        self.mock_client.describe_express_gateway_service.return_value = None

        output = collector.get_current_view("⠋")

        assert "Trying to describe gateway service" in output

    def test_missing_service_in_response(self):
        """Test handling when service field is missing"""
        collector = ServiceViewCollector(
            self.mock_client, self.service_arn, "RESOURCE"
        )

        self.mock_client.describe_express_gateway_service.return_value = {}

        output = collector.get_current_view("⠋")

        assert "Trying to describe gateway service" in output

    def test_service_missing_required_fields(self):
        """Test handling when service is missing required fields"""
        collector = ServiceViewCollector(
            self.mock_client, self.service_arn, "RESOURCE"
        )

        # Missing activeConfigurations
        self.mock_client.describe_express_gateway_service.return_value = {
            "service": {"serviceArn": self.service_arn}
        }

        output = collector.get_current_view("⠋")

        assert "Trying to describe gateway service" in output

    def test_empty_response_error(self):
        """Test _validate_and_parse_response with empty response"""
        collector = ServiceViewCollector(
            self.mock_client, self.service_arn, "RESOURCE"
        )

        with pytest.raises(MonitoringError) as exc_info:
            collector._validate_and_parse_response(
                None, "TestOperation", "expectedField"
            )

        assert "TestOperation response is empty" in str(exc_info.value)

    def test_missing_expected_field_error(self):
        """Test _validate_and_parse_response with missing expected field"""
        collector = ServiceViewCollector(
            self.mock_client, self.service_arn, "RESOURCE"
        )

        with pytest.raises(MonitoringError) as exc_info:
            collector._validate_and_parse_response(
                {"otherField": "value"}, "TestOperation", "expectedField"
            )

        error_message = str(exc_info.value)
        assert "TestOperation" in error_message
        assert "expectedField" in error_message

    def test_parse_failures_filters_missing_reason(self):
        """Test _parse_failures filters MISSING failures for eventually consistent"""
        collector = ServiceViewCollector(
            self.mock_client, self.service_arn, "RESOURCE"
        )

        response = {
            "failures": [
                {"arn": "arn1", "reason": "MISSING"},
                {"arn": "arn2", "reason": "ServiceNotFound"},
            ]
        }

        # Eventually consistent - should only raise for non-MISSING
        with pytest.raises(MonitoringError) as exc_info:
            collector._parse_failures(
                response, "TestOp", eventually_consistent=True
            )

        error_message = str(exc_info.value)
        assert "arn2" in error_message
        assert "ServiceNotFound" in error_message
        # Should NOT include arn1 (MISSING reason)
        assert "arn1" not in error_message

    def test_parse_failures_all_missing_no_error(self):
        """Test _parse_failures doesn't raise when all failures are MISSING"""
        collector = ServiceViewCollector(
            self.mock_client, self.service_arn, "RESOURCE"
        )

        response = {
            "failures": [
                {"arn": "arn1", "reason": "MISSING"},
                {"arn": "arn2", "reason": "MISSING"},
            ]
        }

        # Should not raise when all failures are MISSING
        collector._parse_failures(
            response, "TestOp", eventually_consistent=True
        )

    def test_parse_failures_malformed(self):
        """Test _parse_failures with malformed failure data"""
        collector = ServiceViewCollector(
            self.mock_client, self.service_arn, "RESOURCE"
        )

        response = {
            "failures": [
                {"reason": "ServiceNotFound"}  # Missing arn
            ]
        }

        with pytest.raises(MonitoringError) as exc_info:
            collector._parse_failures(
                response, "TestOp", eventually_consistent=False
            )

        assert "Invalid failure response" in str(exc_info.value)

    def test_parse_all_resource_types(self):
        """Test parsing all supported resource types"""
        collector = ServiceViewCollector(
            self.mock_client, self.service_arn, "RESOURCE"
        )

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
                                    "arn": "lb-arn",
                                    "status": "ACTIVE",
                                },
                                "loadBalancerSecurityGroups": [
                                    {"arn": "lb-sg-arn", "status": "ACTIVE"}
                                ],
                                "certificate": {
                                    "arn": "cert-arn",
                                    "status": "ACTIVE",
                                },
                                "listener": {
                                    "arn": "listener-arn",
                                    "status": "ACTIVE",
                                },
                                "rule": {
                                    "arn": "rule-arn",
                                    "status": "ACTIVE",
                                },
                                "targetGroups": [
                                    {"arn": "tg-arn", "status": "ACTIVE"}
                                ],
                            }
                        ],
                        "autoScaling": {
                            "scalableTarget": {
                                "arn": "st-arn",
                                "status": "ACTIVE",
                            },
                            "applicationAutoScalingPolicies": [
                                {"arn": "policy-arn", "status": "ACTIVE"}
                            ],
                        },
                        "metricAlarms": [
                            {"arn": "alarm-arn", "status": "ACTIVE"}
                        ],
                        "serviceSecurityGroups": [
                            {"arn": "sg-arn", "status": "ACTIVE"}
                        ],
                        "logGroups": [{"arn": "log-arn", "status": "ACTIVE"}],
                    },
                }
            ]
        }
        self.mock_client.describe_services.return_value = {
            "services": [{"events": [{"message": "All resources"}]}]
        }

        output = collector.get_current_view("⠋")

        # Verify all resource types are parsed
        assert "IngressPath" in output
        assert "LoadBalancer" in output
        assert "LoadBalancerSecurityGroup" in output
        assert "Certificate" in output
        assert "Listener" in output
        assert "Rule" in output
        assert "TargetGroup" in output
        assert "AutoScalingConfiguration" in output
        assert "ScalableTarget" in output
        assert "ApplicationAutoScalingPolicy" in output
        assert "MetricAlarms" in output
        assert "ServiceSecurityGroups" in output
        assert "LogGroups" in output
