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

The data collection logic is handled by ServiceViewCollector, which parses AWS resources and
formats monitoring output. This module focuses on display and user interaction.

The module implements two resource view modes:
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

from botocore.exceptions import ClientError

from awscli.customizations.commands import BasicCommand
from awscli.customizations.ecs.exceptions import MonitoringError
from awscli.customizations.ecs.prompt_toolkit_display import Display
from awscli.customizations.ecs.serviceviewcollector import ServiceViewCollector
from awscli.customizations.utils import uni_print


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
    """

    def __init__(
        self,
        client,
        service_arn,
        mode,
        timeout_minutes=30,
        display=None,
        use_color=True,
        collector=None,
    ):
        self._client = client
        self.service_arn = service_arn
        self.mode = mode
        self.timeout_minutes = timeout_minutes
        self.start_time = time.time()
        self.use_color = use_color
        self.display = display or Display()
        self.collector = collector or ServiceViewCollector(
            client, service_arn, mode, use_color
        )

    @staticmethod
    def is_monitoring_available():
        """Check if monitoring is available (requires TTY)."""
        return sys.stdout.isatty()

    def exec(self):
        """Start monitoring the express gateway service with progress display."""

        def monitor_service(spinner_char):
            return self.collector.get_current_view(spinner_char)

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
