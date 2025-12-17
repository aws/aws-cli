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

And two display modes:
- INTERACTIVE: Real-time display with spinner and keyboard navigation (requires TTY)
- TEXT-ONLY: Text output with timestamps and change detection (works without TTY)

Key Features:
- Real-time progress monitoring with spinner animations
- Diff-based resource tracking for deployment changes
- Comprehensive resource parsing (load balancers, security groups, auto-scaling, etc.)
- Graceful keyboard interrupt handling

Classes:
    ECSMonitorExpressGatewayService: Main CLI command class for service monitoring
    ECSExpressGatewayServiceWatcher: Core monitoring logic and resource tracking

Usage:
    aws ecs monitor-express-gateway-service --service-arn <arn> [--resource-view RESOURCE|DEPLOYMENT] [--mode INTERACTIVE|TEXT-ONLY]
"""

import sys
import time

from botocore.exceptions import ClientError

from awscli.customizations.commands import BasicCommand
from awscli.customizations.ecs.exceptions import MonitoringError
from awscli.customizations.ecs.expressgateway.display_strategy import (
    InteractiveDisplayStrategy,
    TextOnlyDisplayStrategy,
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
        "This command provides real-time monitoring of service deployments showing the status "
        "of load balancers, security groups, auto-scaling "
        "configurations, and other AWS resources as they are created or updated. "
        "Use ``--resource-view RESOURCE`` to view all service resources, or ``--resource-view DEPLOYMENT`` to track only "
        "resources that have changed in the most recent deployment. "
        "Choose ``--mode INTERACTIVE`` for real-time display with keyboard navigation (requires TTY), "
        "or ``--mode TEXT-ONLY`` for text output with timestamps (works without TTY). "
        "The monitoring session continues until manually stopped by the user or the specified timeout is reached. "
        "In INTERACTIVE mode, use keyboard shortcuts: up/down to scroll through resources, 'q' to quit. "
        "In TEXT-ONLY mode, press Ctrl+C to stop monitoring."
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
            'name': 'mode',
            'help_text': (
                "Display mode for monitoring output. "
                "INTERACTIVE (default if TTY available) - Real-time display with spinner and keyboard navigation. "
                "TEXT-ONLY - Text output with timestamps and change detection (works without TTY)."
            ),
            'required': False,
            'choices': ['INTERACTIVE', 'TEXT-ONLY'],
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
            display_mode = self._determine_display_mode(parsed_args.mode)
        except ValueError as e:
            uni_print(f"aws: [ERROR]: {str(e)}", sys.stderr)
            return 1

        try:
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
                display_mode,
                timeout_minutes=parsed_args.timeout,
                use_color=use_color,
            ).exec()
        except MonitoringError as e:
            uni_print(f"Error monitoring service: {e}", sys.stderr)
            return 1

    def _determine_display_mode(self, requested_mode):
        """Determine and validate the display mode.

        Args:
            requested_mode: User-requested mode ('interactive', 'text-only', or None)

        Returns:
            str: Validated display mode ('interactive' or 'text-only')

        Raises:
            ValueError: If interactive mode is requested without TTY
        """
        # Determine display mode with auto-detection
        if requested_mode is None:
            # Auto-detect: interactive if TTY available, else text-only
            return 'INTERACTIVE' if sys.stdout.isatty() else 'TEXT-ONLY'

        # Validate requested mode
        if requested_mode == 'INTERACTIVE':
            if not sys.stdout.isatty():
                raise ValueError(
                    "Interactive mode requires a TTY (terminal). "
                    "Use --mode TEXT-ONLY for non-interactive environments."
                )
            return 'INTERACTIVE'

        # text-only mode doesn't require TTY
        return requested_mode

    def _should_use_color(self, parsed_globals):
        """Determine if color output should be used based on global settings.

        Args:
            parsed_globals: Global CLI configuration

        Returns:
            bool: True if color should be used
        """
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
        resource_view (str): Resource view mode - 'RESOURCE' or 'DEPLOYMENT'
        display_mode (str): Display mode - 'INTERACTIVE' or 'TEXT-ONLY'
        timeout_minutes (int): Maximum monitoring time in minutes (default: 30)
    """

    def __init__(
        self,
        client,
        service_arn,
        resource_view,
        display_mode,
        timeout_minutes=30,
        display_strategy=None,
        use_color=True,
        collector=None,
    ):
        self.service_arn = service_arn
        self.display_mode = display_mode
        self.timeout_minutes = timeout_minutes
        self.start_time = time.time()
        self.use_color = use_color
        self.display_strategy = (
            display_strategy or self._create_display_strategy()
        )
        self.collector = collector or ServiceViewCollector(
            client, service_arn, resource_view, use_color
        )

    @staticmethod
    def is_monitoring_available():
        """Check if monitoring is available (requires TTY)."""
        return sys.stdout.isatty()

    def exec(self):
        """Execute monitoring using the appropriate display strategy."""
        self.display_strategy.execute_monitoring(
            collector=self.collector,
            start_time=self.start_time,
            timeout_minutes=self.timeout_minutes,
        )

    def _create_display_strategy(self):
        """Create display strategy based on display mode.

        Returns:
            DisplayStrategy: Appropriate strategy for the selected mode

        Raises:
            ValueError: If display mode is not 'INTERACTIVE' or 'TEXT-ONLY'
        """
        if self.display_mode == 'TEXT-ONLY':
            return TextOnlyDisplayStrategy(use_color=self.use_color)
        elif self.display_mode == 'INTERACTIVE':
            return InteractiveDisplayStrategy(
                display=Display(), use_color=self.use_color
            )
        else:
            raise ValueError(f"Invalid display mode: {self.display_mode}")
