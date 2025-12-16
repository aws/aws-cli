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

import sys
import time

from botocore.exceptions import ClientError

from awscli.customizations.commands import BasicCommand
from awscli.customizations.ecs.exceptions import MonitoringError
from awscli.customizations.ecs.expressgateway.display_strategy import (
    InteractiveDisplayStrategy,
)
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
        display_strategy=None,
        use_color=True,
        collector=None,
    ):
        self._client = client
        self.service_arn = service_arn
        self.mode = mode
        self.timeout_minutes = timeout_minutes
        self.start_time = time.time()
        self.use_color = use_color
        self.display_strategy = display_strategy or InteractiveDisplayStrategy(
            display=Display(), use_color=use_color
        )
        self.collector = collector or ServiceViewCollector(
            client, service_arn, mode, use_color
        )

    @staticmethod
    def is_monitoring_available():
        """Check if monitoring is available (requires TTY)."""
        return sys.stdout.isatty()

    def exec(self):
        """Start monitoring the express gateway service with progress display."""
        self.display_strategy.execute_monitoring(
            self.collector, self.timeout_minutes, self.start_time
        )
