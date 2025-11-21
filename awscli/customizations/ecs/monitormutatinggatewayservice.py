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
AWS CLI ECS Gateway Service Mutation Monitoring Module.

This module provides automatic monitoring capabilities for ECS Gateway Service
mutation operations (create, update, delete). It extends CLI commands with an
optional --monitor-resources flag that enables real-time tracking of resource
changes during service operations.

The module integrates with the AWS CLI event system to:
- Add monitoring arguments to gateway service commands
- Automatically start monitoring after successful API calls
- Display live progress updates during resource provisioning
- Update command output with final service state

Supported Operations:
- create-express-gateway-service: Monitors resource creation with DELTA mode
- update-express-gateway-service: Monitors resource updates with DELTA mode
- delete-express-gateway-service: Monitors resource cleanup with ALL mode

Classes:
    MonitoringResourcesArgument: Custom CLI argument for enabling monitoring
    MonitorMutatingGatewayService: Event handler for mutation monitoring

Usage:
    aws ecs create-express-gateway-service --monitor-resources [other-args...]
"""

import argparse
import sys
from urllib.parse import urlparse

from botocore.session import get_session

from awscli.arguments import CustomArgument
from awscli.customizations.ecs.monitorexpressgatewayservice import (
    ECSExpressGatewayServiceWatcher,
)
from awscli.customizations.utils import uni_print


class MonitorResourcesAction(argparse.Action):
    """Custom action for monitor-resources argument."""

    def __call__(self, parser, namespace, values, option_string=None):
        if values is None:
            # Flag provided without value - use sentinel for default
            setattr(namespace, self.dest, '__DEFAULT__')
        else:
            # Explicit value provided
            setattr(namespace, self.dest, values)


class MonitoringResourcesArgument(CustomArgument):
    """Custom CLI argument for enabling resource monitoring.

    Adds the --monitor-resources flag to gateway service commands,
    allowing users to opt into real-time monitoring of resource changes.
    """

    def __init__(self, name):
        super().__init__(
            name,
            help_text=(
                'Enable live monitoring of service resource status. '
                'Specify ``DEPLOYMENT`` to show only resources that are being added or removed '
                'as part of the latest service deployment, or ``RESOURCE`` to show all resources '
                'from all active configurations of the service. '
                'Defaults based on operation type: create-express-gateway-service and '
                'update-express-gateway-service default to ``DEPLOYMENT`` mode. '
                'delete-express-gateway-service defaults to ``RESOURCE`` mode. '
                'Requires a terminal (TTY) to run.'
            ),
            choices=['DEPLOYMENT', 'RESOURCE'],
            nargs='?',
            action=MonitorResourcesAction,
            dest='monitor_resources',
        )


class MonitorMutatingGatewayService:
    """Event handler for monitoring gateway service mutations.

    Integrates with AWS CLI event system to automatically start monitoring
    when --monitor-resources flag is used with gateway service operations.

    Args:
        api (str): API operation name (e.g., 'create-express-gateway-service')
        default_resource_view (str): Resource view mode, choices=['DEPLOYMENT', 'RESOURCE']
    """

    def __init__(self, api, default_resource_view, watcher_class=None):
        self.api = api
        self.default_resource_view = default_resource_view
        self.api_pascal_case = ''.join(
            word.capitalize() for word in api.split('-')
        )
        self.session = None
        self.parsed_globals = None
        self.effective_resource_view = None
        self._watcher_class = watcher_class or ECSExpressGatewayServiceWatcher

    def before_building_argument_table_parser(self, session, **kwargs):
        """Store session for later use in monitoring.

        Args:
            session: AWS CLI session object
        """
        # Store session for later use
        self.session = session

    def building_argument_table(self, argument_table, session, **kwargs):
        """Add monitoring argument to the command's argument table.

        Args:
            argument_table (dict): CLI argument table to extend
            session: AWS CLI session object
        """
        argument_table['monitor-resources'] = MonitoringResourcesArgument(
            'monitor-resources'
        )

    def operation_args_parsed(self, parsed_args, parsed_globals, **kwargs):
        """Store monitoring flag state and globals after argument parsing.

        Args:
            parsed_args: Parsed command line arguments
            parsed_globals: Global CLI configuration
        """
        # Store parsed_globals for later use
        self.parsed_globals = parsed_globals

        # Get monitor_resources value and determine actual monitoring mode
        monitor_value = getattr(parsed_args, 'monitor_resources', None)

        if monitor_value is None:
            # Not specified, no monitoring
            self.effective_resource_view = None
        elif monitor_value == '__DEFAULT__':
            # Flag specified without value, use default based on operation
            self.effective_resource_view = self.default_resource_view
        else:
            # Explicit choice provided (DEPLOYMENT or RESOURCE)
            self.effective_resource_view = monitor_value

    def after_call(self, parsed, context, http_response, **kwargs):
        """Start monitoring after successful API call if flag is enabled.

        Args:
            parsed (dict): API response data
            context: CLI execution context
            http_response: HTTP response object
        """
        if not self.effective_resource_view:
            return

        if http_response.status_code >= 300 or not parsed.get(
            'service', {}
        ).get('serviceArn'):
            return

        # Check monitoring availability
        if not self._watcher_class.is_monitoring_available():
            uni_print(
                "Monitoring is not available (requires TTY). Skipping monitoring.\n",
                out_file=sys.stderr,
            )
            return

        if not self.session or not self.parsed_globals:
            uni_print(
                "Unable to create ECS client. Skipping monitoring.",
                out_file=sys.stderr,
            )
            return

        ecs_client = self.session.create_client(
            'ecs',
            region_name=self.parsed_globals.region,
            endpoint_url=self.parsed_globals.endpoint_url,
            verify=self.parsed_globals.verify_ssl,
        )

        # Get service ARN from response
        service_arn = parsed.get('service', {}).get('serviceArn')

        # Clear output when monitoring is invoked
        parsed.clear()

        try:
            self._watcher_class(
                ecs_client,
                service_arn,
                self.effective_resource_view,
                use_color=self._should_use_color(self.parsed_globals),
            ).exec()
        except Exception as e:
            uni_print(
                "Encountered an error, terminating monitoring\n"
                + str(e)
                + "\n",
                out_file=sys.stderr,
            )

    def _should_use_color(self, parsed_globals):
        """Determine if color output should be used based on global settings."""
        if parsed_globals.color == 'on':
            return True
        elif parsed_globals.color == 'off':
            return False
        # Default 'auto' behavior - use color if output is a TTY
        return sys.stdout.isatty()

    def events(self):
        """Return list of CLI events and their corresponding handlers.

        Returns:
            list: Tuples of (event_name, handler_method) for CLI integration
        """
        return [
            (
                "before-building-argument-table-parser.ecs." + self.api,
                self.before_building_argument_table_parser,
            ),
            (
                "building-argument-table.ecs." + self.api,
                self.building_argument_table,
            ),
            (
                "operation-args-parsed.ecs." + self.api,
                self.operation_args_parsed,
            ),
            ("after-call.ecs." + self.api_pascal_case, self.after_call),
        ]


MUTATION_HANDLERS = [
    MonitorMutatingGatewayService(
        'create-express-gateway-service', "DEPLOYMENT"
    ),
    MonitorMutatingGatewayService(
        'update-express-gateway-service', "DEPLOYMENT"
    ),
    MonitorMutatingGatewayService(
        'delete-express-gateway-service', "RESOURCE"
    ),
]


def register_monitor_mutating_gateway_service(event_handler):
    """Register monitoring handlers for all gateway service mutation operations.

    Args:
        event_handler: AWS CLI event handler for registering callbacks
    """
    # Register all of the events for customizing
    for handler in MUTATION_HANDLERS:
        for event, handler_method in handler.events():
            event_handler.register(event, handler_method)
