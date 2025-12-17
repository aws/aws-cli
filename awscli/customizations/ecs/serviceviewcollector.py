# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

"""Service view collector for ECS Express Gateway Service monitoring.

This module provides business logic for collecting and formatting
ECS Express Gateway Service monitoring data.
"""

import time
from functools import reduce

from botocore.exceptions import ClientError

from awscli.customizations.ecs.exceptions import MonitoringError
from awscli.customizations.ecs.expressgateway.managedresource import (
    ManagedResource,
)
from awscli.customizations.ecs.expressgateway.managedresourcegroup import (
    ManagedResourceGroup,
)


class ServiceViewCollector:
    """Collects and formats ECS Express Gateway Service monitoring data.

    Responsible for:
    - Making ECS API calls
    - Parsing resource data
    - Formatting output strings
    - Caching responses

    Args:
        client: ECS client for API calls
        service_arn (str): ARN of the service to monitor
        mode (str): Monitoring mode - 'RESOURCE' or 'DEPLOYMENT'
        use_color (bool): Whether to use color in output
    """

    def __init__(self, client, service_arn, mode, use_color=True):
        self._client = client
        self.service_arn = service_arn
        self.mode = mode
        self.use_color = use_color
        self.last_described_gateway_service_response = None
        self.last_execution_time = 0
        self.cached_monitor_result = None

    def get_current_view(
        self, spinner_char="{SPINNER}", execution_refresh_millis=5000
    ):
        """Get current monitoring view as formatted string.

        Args:
            spinner_char (str): Character for progress indication
            execution_refresh_millis (int): Refresh interval in milliseconds

        Returns:
            str: Formatted monitoring output
        """
        current_time = time.time()

        if (
            current_time - self.last_execution_time
            >= execution_refresh_millis / 1000.0
        ):
            try:
                describe_gateway_service_response = (
                    self._client.describe_express_gateway_service(
                        serviceArn=self.service_arn
                    )
                )
                if not describe_gateway_service_response:
                    self.cached_monitor_result = (
                        None,
                        "Trying to describe gateway service",
                    )
                elif (
                    not (
                        service := describe_gateway_service_response.get(
                            "service"
                        )
                    )
                    or not service.get("serviceArn")
                    or service.get("activeConfigurations") is None
                ):
                    self.cached_monitor_result = (
                        None,
                        "Trying to describe gateway service",
                    )
                else:
                    self.last_described_gateway_service_response = (
                        describe_gateway_service_response
                    )
                    described_gateway_service = (
                        describe_gateway_service_response.get("service")
                    )

                    if self.mode == "DEPLOYMENT":
                        managed_resources, info = self._diff_service_view(
                            described_gateway_service
                        )
                    else:
                        managed_resources, info = self._combined_service_view(
                            described_gateway_service
                        )

                    service_resources = [
                        self._parse_cluster(described_gateway_service),
                        self._parse_service(described_gateway_service),
                    ]
                    if managed_resources:
                        service_resources.append(managed_resources)
                    service_resource = ManagedResourceGroup(
                        resources=service_resources
                    )
                    self._update_cached_monitor_results(service_resource, info)
            except ClientError as e:
                if (
                    e.response.get('Error', {}).get('Code')
                    == 'InvalidParameterException'
                ):
                    error_message = e.response.get('Error', {}).get(
                        'Message', ''
                    )
                    if (
                        "Cannot call DescribeServiceRevisions for a service that is INACTIVE"
                        in error_message
                    ):
                        empty_resource_group = ManagedResourceGroup()
                        self._update_cached_monitor_results(
                            empty_resource_group, "Service is inactive"
                        )
                    else:
                        raise
                else:
                    raise

            self.last_execution_time = current_time

        if not self.cached_monitor_result:
            return "Waiting for initial data"
        else:
            service_resource, info = self.cached_monitor_result
            status_string = (
                service_resource.get_status_string(
                    spinner_char=spinner_char, use_color=self.use_color
                )
                if service_resource
                else None
            )

            output = "\n".join([x for x in [status_string, info] if x])
            return output

    def _diff_service_view(self, describe_gateway_service_response):
        """Generate diff view showing changes in the latest deployment."""
        service_arn = describe_gateway_service_response.get("serviceArn")
        list_service_deployments_response = (
            self._client.list_service_deployments(
                service=service_arn, maxResults=1
            )
        )
        listed_service_deployments = self._validate_and_parse_response(
            list_service_deployments_response,
            "ListServiceDeployments",
            expected_field="serviceDeployments",
        )
        if (
            not listed_service_deployments
            or "serviceDeploymentArn" not in listed_service_deployments[0]
        ):
            return (
                None,
                "Waiting for a deployment to start",
            )

        deployment_arn = listed_service_deployments[0].get(
            "serviceDeploymentArn"
        )

        describe_service_deployments_response = (
            self._client.describe_service_deployments(
                serviceDeploymentArns=[deployment_arn]
            )
        )
        described_service_deployments = self._validate_and_parse_response(
            describe_service_deployments_response,
            "DescribeServiceDeployments",
            expected_field="serviceDeployments",
            eventually_consistent=True,
        )
        if not described_service_deployments:
            return (None, "Waiting for a deployment to start")

        described_service_deployment = described_service_deployments[0]
        if (
            not described_service_deployment
            or not described_service_deployment.get("targetServiceRevision")
        ):
            return (
                None,
                "Waiting for a deployment to start",
            )

        target_sr = described_service_deployment.get(
            "targetServiceRevision"
        ).get("arn")

        target_sr_resources_list, described_target_sr_list = (
            self._describe_and_parse_service_revisions([target_sr])
        )
        if len(target_sr_resources_list) != 1:
            return (None, "Trying to describe service revisions")
        target_sr_resources = target_sr_resources_list[0]
        described_target_sr = described_target_sr_list[0]

        task_def_arn = described_target_sr.get("taskDefinition")
        if "sourceServiceRevisions" in described_service_deployment:
            source_sr_resources, _ = (
                self._describe_and_parse_service_revisions(
                    [
                        sr.get("arn")
                        for sr in described_service_deployment.get(
                            "sourceServiceRevisions"
                        )
                    ]
                )
            )
            if len(source_sr_resources) != len(
                described_service_deployment.get("sourceServiceRevisions")
            ):
                return (None, "Trying to describe service revisions")
            source_sr_resources_combined = reduce(
                lambda x, y: x.combine(y), source_sr_resources
            )
        else:
            source_sr_resources_combined = ManagedResourceGroup()

        updating_resources, disassociating_resources = (
            target_sr_resources.diff(source_sr_resources_combined)
        )
        updating_resources.resource_type = "Updating"
        disassociating_resources.resource_type = "Disassociating"
        service_resources = ManagedResourceGroup(
            resource_type="Deployment",
            identifier=deployment_arn,
            status=described_service_deployment.get("status"),
            reason=described_service_deployment.get("statusReason"),
            resources=[
                ManagedResource(
                    resource_type="TargetServiceRevision", identifier=target_sr
                ),
                ManagedResource(
                    resource_type="TaskDefinition", identifier=task_def_arn
                ),
                updating_resources,
                disassociating_resources,
            ],
        )
        return service_resources, None

    def _combined_service_view(self, describe_gateway_service_response):
        """Generate combined view of all active service resources."""
        service_revision_arns = [
            config.get("serviceRevisionArn")
            for config in describe_gateway_service_response.get(
                "activeConfigurations"
            )
        ]
        service_revision_resources, _ = (
            self._describe_and_parse_service_revisions(service_revision_arns)
        )

        # If empty, we're still waiting for active configurations
        if not service_revision_resources or len(
            service_revision_resources
        ) != len(service_revision_arns):
            return (None, "Trying to describe service revisions")

        service_resource = reduce(
            lambda x, y: x.combine(y), service_revision_resources
        )

        return service_resource, None

    def _update_cached_monitor_results(self, resource, info):
        """Update cached monitoring results with new data."""
        if not self.cached_monitor_result:
            self.cached_monitor_result = (resource, info)
        else:
            self.cached_monitor_result = (
                resource or self.cached_monitor_result[0],
                info,
            )

    def _validate_and_parse_response(
        self,
        response,
        operation_name,
        expected_field=None,
        eventually_consistent=False,
    ):
        """Validate API response and extract expected field."""
        if not response:
            raise MonitoringError(f"{operation_name} response is empty")

        self._parse_failures(response, operation_name, eventually_consistent)

        if not expected_field:
            return None

        if response.get(expected_field) is None:
            raise MonitoringError(
                f"{operation_name} response is missing {expected_field}"
            )
        return response.get(expected_field)

    def _parse_failures(self, response, operation_name, eventually_consistent):
        """Parse and raise errors for API response failures."""
        failures = response.get("failures")

        if not failures:
            return

        if any(not f.get('arn') or not f.get('reason') for f in failures):
            raise MonitoringError(
                "Invalid failure response: missing arn or reason"
            )

        if eventually_consistent:
            failures = [
                failure
                for failure in failures
                if failure.get("reason") != "MISSING"
            ]

        if not failures:
            return

        failure_msgs = [
            f"{f['arn']} failed with {f['reason']}" for f in failures
        ]
        joined_msgs = '\n'.join(failure_msgs)
        raise MonitoringError(f"{operation_name}:\n{joined_msgs}")

    def _describe_and_parse_service_revisions(self, arns):
        """Describe and parse service revisions into managed resources."""
        describe_service_revisions_response = (
            self._client.describe_service_revisions(serviceRevisionArns=arns)
        )
        described_service_revisions = self._validate_and_parse_response(
            describe_service_revisions_response,
            "DescribeServiceRevisions",
            expected_field="serviceRevisions",
            eventually_consistent=True,
        )

        return [
            self._parse_ecs_managed_resources(sr)
            for sr in described_service_revisions
        ], described_service_revisions

    def _parse_cluster(self, service):
        return ManagedResource("Cluster", service.get("cluster"))

    def _parse_service(self, service):
        service_arn = service.get("serviceArn")
        cluster = service.get("cluster")
        describe_service_response = self._client.describe_services(
            cluster=cluster, services=[service_arn]
        )
        described_service = self._validate_and_parse_response(
            describe_service_response, "DescribeServices", "services"
        )[0]
        return ManagedResource(
            "Service",
            service.get("serviceArn"),
            additional_info=described_service
            and described_service.get("events")[0].get("message")
            if described_service.get("events")
            else None,
        )

    def _parse_ecs_managed_resources(self, service_revision):
        managed_resources = service_revision.get("ecsManagedResources")
        if not managed_resources:
            return ManagedResourceGroup()

        parsed_resources = []
        if "ingressPaths" in managed_resources:
            parsed_resources.append(
                ManagedResourceGroup(
                    resource_type="IngressPaths",
                    resources=[
                        self._parse_ingress_path_resources(ingress_path)
                        for ingress_path in managed_resources.get(
                            "ingressPaths"
                        )
                    ],
                )
            )
        if "autoScaling" in managed_resources:
            parsed_resources.append(
                self._parse_auto_scaling_configuration(
                    managed_resources.get("autoScaling")
                )
            )
        if "metricAlarms" in managed_resources:
            parsed_resources.append(
                self._parse_metric_alarms(
                    managed_resources.get("metricAlarms")
                )
            )
        if "serviceSecurityGroups" in managed_resources:
            parsed_resources.append(
                self._parse_service_security_groups(
                    managed_resources.get("serviceSecurityGroups")
                )
            )
        if "logGroups" in managed_resources:
            parsed_resources.append(
                self._parse_log_groups(managed_resources.get("logGroups"))
            )
        return ManagedResourceGroup(resources=parsed_resources)

    def _parse_ingress_path_resources(self, ingress_path):
        resources = []
        if ingress_path.get("loadBalancer"):
            resources.append(
                self._parse_managed_resource(
                    ingress_path.get("loadBalancer"), "LoadBalancer"
                )
            )
        if ingress_path.get("loadBalancerSecurityGroups"):
            resources.extend(
                self._parse_managed_resource_list(
                    ingress_path.get("loadBalancerSecurityGroups"),
                    "LoadBalancerSecurityGroup",
                )
            )
        if ingress_path.get("certificate"):
            resources.append(
                self._parse_managed_resource(
                    ingress_path.get("certificate"), "Certificate"
                )
            )
        if ingress_path.get("listener"):
            resources.append(
                self._parse_managed_resource(
                    ingress_path.get("listener"), "Listener"
                )
            )
        if ingress_path.get("rule"):
            resources.append(
                self._parse_managed_resource(ingress_path.get("rule"), "Rule")
            )
        if ingress_path.get("targetGroups"):
            resources.extend(
                self._parse_managed_resource_list(
                    ingress_path.get("targetGroups"), "TargetGroup"
                )
            )
        return ManagedResourceGroup(
            resource_type="IngressPath",
            identifier=ingress_path.get("endpoint"),
            resources=resources,
        )

    def _parse_auto_scaling_configuration(self, auto_scaling_configuration):
        resources = []
        if auto_scaling_configuration.get("scalableTarget"):
            resources.append(
                self._parse_managed_resource(
                    auto_scaling_configuration.get("scalableTarget"),
                    "ScalableTarget",
                )
            )
        if auto_scaling_configuration.get("applicationAutoScalingPolicies"):
            resources.extend(
                self._parse_managed_resource_list(
                    auto_scaling_configuration.get(
                        "applicationAutoScalingPolicies"
                    ),
                    "ApplicationAutoScalingPolicy",
                )
            )
        return ManagedResourceGroup(
            resource_type="AutoScalingConfiguration", resources=resources
        )

    def _parse_metric_alarms(self, metric_alarms):
        return ManagedResourceGroup(
            resource_type="MetricAlarms",
            resources=self._parse_managed_resource_list(
                metric_alarms, "MetricAlarm"
            ),
        )

    def _parse_service_security_groups(self, service_security_groups):
        return ManagedResourceGroup(
            resource_type="ServiceSecurityGroups",
            resources=self._parse_managed_resource_list(
                service_security_groups, "SecurityGroup"
            ),
        )

    def _parse_log_groups(self, logs_groups):
        return ManagedResourceGroup(
            resource_type="LogGroups",
            resources=self._parse_managed_resource_list(
                logs_groups, "LogGroup"
            ),
        )

    def _parse_managed_resource(self, resource, resource_type):
        return ManagedResource(
            resource_type,
            resource.get("arn"),
            status=resource.get("status"),
            updated_at=resource.get("updatedAt"),
            reason=resource.get("statusReason"),
        )

    def _parse_managed_resource_list(self, data_list, resource_type):
        return [
            self._parse_managed_resource(data, resource_type)
            for data in data_list
        ]
