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

"""
AWS CLI ECS Express Gateway Service Monitoring Module.

This module provides real-time monitoring capabilities for Amazon ECS Express Gateway Services,
allowing users to track resource creation progress, deployment status, and service health through
an interactive command-line interface with live updates and visual indicators.

The module implements two primary monitoring modes:
- RESOURCE: Displays all resources associated with the service
- DEPLOYMENT: Shows resources that have changed in the most recent deployment

Key Features:
- Real-time progress monitoring with spinner animations
- Diff-based resource tracking for deployment changes
- Comprehensive resource parsing (load balancers, security groups, auto-scaling, etc.)
- Graceful keyboard interrupt handling

Classes:
    ECSMonitorExpressGatewayService: Main CLI command class for service monitoring
    ECSExpressGatewayServiceWatcher: Core monitoring logic and resource tracking

Usage:
    aws ecs monitor-express-gateway-service --service-arn <arn> [--resource-view RESOURCE|DEPLOYMENT]
"""

import asyncio
import sys
import threading
import time
from functools import reduce

from botocore.exceptions import ClientError

from awscli.customizations.commands import BasicCommand
from awscli.customizations.ecs.exceptions import MonitoringError
from awscli.customizations.ecs.expressgateway.managedresource import (
    ManagedResource,
)
from awscli.customizations.ecs.expressgateway.managedresourcegroup import (
    ManagedResourceGroup,
)
from awscli.customizations.ecs.prompt_toolkit_display import Display
from awscli.customizations.utils import uni_print

TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class ECSMonitorExpressGatewayService(BasicCommand):
    """AWS CLI command for monitoring ECS Express Gateway Service deployments.

    Provides real-time monitoring of service resource creation and deployment
    progress with interactive output and status updates.
    """

    NAME = 'monitor-express-gateway-service'

    DESCRIPTION = (
        "Monitors the progress of resource creation for an ECS Express Gateway Service. "
        "This command provides real-time monitoring of service deployments with interactive "
        "progress display, showing the status of load balancers, security groups, auto-scaling "
        "configurations, and other AWS resources as they are created or updated. "
        "Use ``--resource-view RESOURCE`` to view all service resources, or ``--resource-view DEPLOYMENT`` to track only "
        "resources that have changed in the most recent deployment. "
        "The command requires a terminal (TTY) to run and the monitoring session continues "
        "until manually stopped by the user or the specified timeout is reached. "
        "Use keyboard shortcuts to navigate: up/down to scroll through resources, 'q' to quit monitoring."
    )

    ARG_TABLE = [
        {
            'name': 'service-arn',
            'help_text': (
                "The short name or full Amazon Resource Name "
                "(ARN) of the service to monitor."
            ),
            'required': True,
        },
        {
            'name': 'resource-view',
            'help_text': (
                "Specifies which resources to display during monitoring. "
                "RESOURCE (default) - Combines resources from all active configurations of the service "
                "and displays the live status of load balancers, security groups, target groups, etc. "
                "DEPLOYMENT - Determines the resources that are being added or removed as part of the "
                "latest service deployment, and displays their live statuses."
            ),
            'required': False,
            'default': 'RESOURCE',
            'choices': ['RESOURCE', 'DEPLOYMENT'],
        },
        {
            'name': 'timeout',
            'help_text': (
                "Maximum time in minutes to monitor the service. "
                "Default is 30 minutes."
            ),
            'required': False,
            'default': 30,
            'cli_type_name': 'integer',
        },
    ]

    def __init__(self, session, watcher_class=None):
        """Initialize the command with optional dependency injection.

        Args:
            session: AWS session
            watcher_class: Optional watcher class for dependency injection (for testing)
        """
        super().__init__(session)
        self._watcher_class = watcher_class or ECSExpressGatewayServiceWatcher

    def _run_main(self, parsed_args, parsed_globals):
        """Execute the monitoring command with parsed arguments.

        Args:
            parsed_args: Command line arguments including service-arn, resource_view, and timeout
            parsed_globals: Global CLI configuration including region and endpoint
        """
        try:
            # Check if running in a TTY for interactive display
            if not sys.stdout.isatty():
                uni_print(
                    "Error: This command requires a TTY. "
                    "Please run this command in a terminal.",
                    sys.stderr,
                )
                return 1

            self._client = self._session.create_client(
                'ecs',
                region_name=parsed_globals.region,
                endpoint_url=parsed_globals.endpoint_url,
                verify=parsed_globals.verify_ssl,
            )

            # Determine if color should be used
            use_color = self._should_use_color(parsed_globals)

            self._watcher_class(
                self._client,
                parsed_args.service_arn,
                parsed_args.resource_view,
                timeout_minutes=parsed_args.timeout,
                use_color=use_color,
            ).exec()
        except MonitoringError as e:
            uni_print(f"Error monitoring service: {e}", sys.stderr)

    def _should_use_color(self, parsed_globals):
        """Determine if color output should be used based on global settings."""
        if parsed_globals.color == 'on':
            return True
        elif parsed_globals.color == 'off':
            return False
        # Default 'auto' behavior - use color if output is a TTY
        return sys.stdout.isatty()


class ECSExpressGatewayServiceWatcher:
    """Monitors ECS Express Gateway Service deployments and resource changes.

    Provides real-time tracking of service deployments with support for different
    monitoring modes (RESOURCE/DEPLOYMENT) and handles resource parsing, status updates,
    and output formatting.

    Args:
        client: ECS client for API calls
        service_arn (str): ARN of the service to monitor
        mode (str): Monitoring mode - 'RESOURCE' or 'DEPLOYMENT'
        timeout_minutes (int): Maximum monitoring time in minutes (default: 30)
        exit_hook (callable): Optional callback function on exit
    """

    def __init__(
        self,
        client,
        service_arn,
        mode,
        timeout_minutes=30,
        exit_hook=None,
        display=None,
        use_color=True,
    ):
        self._client = client
        self.service_arn = service_arn
        self.mode = mode
        self.timeout_minutes = timeout_minutes
        self.exit_hook = exit_hook or self._default_exit_hook
        self.last_described_gateway_service_response = None
        self.last_execution_time = 0
        self.cached_monitor_result = None
        self.start_time = time.time()
        self.use_color = use_color
        self.display = display or Display()

    def _default_exit_hook(self, x):
        return x

    def exec(self):
        """Start monitoring the express gateway service with progress display."""

        def monitor_service(spinner_char):
            return self._monitor_express_gateway_service(
                spinner_char, self.service_arn, self.mode
            )

        asyncio.run(self._execute_with_progress_async(monitor_service, 100))

    async def _execute_with_progress_async(
        self, execution, progress_refresh_millis, execution_refresh_millis=5000
    ):
        """Execute monitoring loop with animated progress display."""
        spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        spinner_index = 0
        current_output = "Waiting for initial data"

        async def update_data():
            nonlocal current_output
            while True:
                current_time = time.time()
                if current_time - self.start_time > self.timeout_minutes * 60:
                    break
                try:
                    loop = asyncio.get_event_loop()
                    new_output = await loop.run_in_executor(
                        None, execution, "{SPINNER}"
                    )
                    current_output = new_output
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
                            current_output = "Service is inactive"
                        else:
                            raise
                    else:
                        raise
                await asyncio.sleep(execution_refresh_millis / 1000.0)

        async def update_spinner():
            nonlocal spinner_index
            while True:
                spinner_char = spinner_chars[spinner_index]
                display_output = current_output.replace(
                    "{SPINNER}", spinner_char
                )
                status_text = f"Getting updates... {spinner_char} | up/down to scroll, q to quit"
                self.display.display(display_output, status_text)
                spinner_index = (spinner_index + 1) % len(spinner_chars)
                await asyncio.sleep(progress_refresh_millis / 1000.0)

        # Start both tasks
        data_task = asyncio.create_task(update_data())
        spinner_task = asyncio.create_task(update_spinner())

        try:
            await self.display.run()
        finally:
            data_task.cancel()
            spinner_task.cancel()
            final_output = current_output.replace("{SPINNER}", "")
            uni_print(final_output + "\nMonitoring Complete!\n")

    def _monitor_express_gateway_service(
        self, spinner_char, service_arn, mode, execution_refresh_millis=5000
    ):
        """Monitor service status and return formatted output.

        Args:
            spinner_char (char): Character to print representing progress (unused with single spinner)
            execution_refresh_millis (int): Refresh interval in milliseconds
            service_arn (str): Service ARN to monitor
            mode (str): Monitoring mode ('RESOURCE' or 'DEPLOYMENT')

        Returns:
            str: Formatted status output
        """
        current_time = time.time()

        if (
            current_time - self.last_execution_time
            >= execution_refresh_millis / 1000.0
        ):
            try:
                describe_gateway_service_response = (
                    self._client.describe_express_gateway_service(
                        serviceArn=service_arn
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
                    or not service.get("activeConfigurations")
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

                    if mode == "DEPLOYMENT":
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
            # Generate the output every iteration. This allow the underlying resources to utilize spinners
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
        """Generate diff view showing changes in the latest deployment.

        Computes differences between source and target service revisions to show
        what resources are being updated or disassociated in the current deployment.

        Args:
            describe_gateway_service_response (dict): Service description from API

        Returns:
            tuple: (resources, info_output) where:
                - resources (ManagedResourceGroup): Diff view of resources
                - info_output (str): Informational messages
        """
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
                return (None, "Trying to describe service revisions)")
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
        """Generate combined view of all active service resources.

        Extracts and combines resources from all active service configurations,
        resolving conflicts by taking the version with the latest timestamp.

        Args:
            describe_gateway_service_response (dict): Service description from API

        Returns:
            tuple: (resources, info_output) where:
                - resources (ManagedResourceGroup): Combined view of all resources
                - info_output (str): Informational messages
        """
        service_revision_arns = [
            config.get("serviceRevisionArn")
            for config in describe_gateway_service_response.get(
                "activeConfigurations"
            )
        ]
        service_revision_resources, _ = (
            self._describe_and_parse_service_revisions(service_revision_arns)
        )

        if len(service_revision_resources) != len(service_revision_arns):
            return (None, "Trying to describe service revisions")

        service_resource = reduce(
            lambda x, y: x.combine(y), service_revision_resources
        )

        return service_resource, None

    def _update_cached_monitor_results(self, resource, info):
        """Update cached monitoring results with new data.

        Args:
            resource: New resource data (replaces existing if provided)
            info: New info message (always replaces existing)
        """
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
        """Validate API response and extract expected field.

        Args:
            response: API response to validate
            operation_name: Name of the operation for error messages
            expected_field: Field to extract from response (optional)
            eventually_consistent: Whether to filter out MISSING failures

        Returns:
            Extracted field value or None if no expected_field specified

        Raises:
            MonitoringError: If response is invalid or missing required fields
        """
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
        """Parse and raise errors for API response failures.

        Args:
            response: API response to check for failures
            operation_name: Name of the operation for error messages
            eventually_consistent: Whether to filter out MISSING failures for eventually consistent operations

        Raises:
            MonitoringError: If failures are found in the response
        """
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
        """Describe and parse service revisions into managed resources.

        Args:
            arns (list): List of service revision ARNs to describe

        Returns:
            tuple: (parsed_resources, described_revisions) where:
                - parsed_resources (list): List of ManagedResourceGroup objects
                - described_revisions (list): Raw API response data
        """
        # API supports up to 20 arns, DescribeExpressGatewayService should never return more than 5
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
