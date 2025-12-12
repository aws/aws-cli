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

"""Stream display implementation for ECS Express Gateway Service monitoring."""

import time

from awscli.customizations.ecs.expressgateway.managedresourcegroup import (
    ManagedResourceGroup,
)
from awscli.customizations.utils import uni_print


class StreamDisplay:
    """Stream display for monitoring that outputs changes to stdout.

    Provides text-based monitoring output suitable for non-interactive
    environments, logging, or piping to other commands.
    """

    def __init__(self, use_color=True):
        self.previous_resources_by_key = {}
        self.use_color = use_color

    def show_startup_message(self):
        """Show startup message."""
        timestamp = self._get_timestamp()
        uni_print(f"[{timestamp}] Starting monitoring...\n")

    def show_polling_message(self):
        """Show polling message."""
        timestamp = self._get_timestamp()
        uni_print(f"[{timestamp}] Polling for updates...\n")

    def show_monitoring_data(self, resource_group, info):
        """Show monitoring data for resources with diff detection.

        Args:
            resource_group: ManagedResourceGroup or None
            info: Additional info text to display
        """
        timestamp = self._get_timestamp()

        if resource_group:
            (
                changed_resources,
                updated_dict,
                removed_keys,
            ) = resource_group.get_changed_resources(
                self.previous_resources_by_key
            )
            self.previous_resources_by_key = updated_dict

            if changed_resources:
                self._print_flattened_resources_list(
                    changed_resources, timestamp
                )

        if info:
            uni_print(f"[{timestamp}] {info}\n")

    def _print_flattened_resources_list(self, resources_list, timestamp):
        """Print individual resources from a flat list as timestamped lines.

        Args:
            resources_list: List of ManagedResource objects to print
            timestamp: Timestamp string to prefix each line
        """
        for resource in resources_list:
            output = resource.get_stream_string(timestamp, self.use_color)
            uni_print(output + "\n")

    def show_timeout_message(self):
        """Show timeout message."""
        timestamp = self._get_timestamp()
        uni_print(f"[{timestamp}] Monitoring timeout reached!\n")

    def show_service_inactive_message(self):
        """Show service inactive message."""
        timestamp = self._get_timestamp()
        uni_print(f"[{timestamp}] Service is inactive\n")

    def show_completion_message(self):
        """Show completion message."""
        timestamp = self._get_timestamp()
        uni_print(f"[{timestamp}] Monitoring complete!\n")

    def show_user_stop_message(self):
        """Show user stop message."""
        timestamp = self._get_timestamp()
        uni_print(f"[{timestamp}] Monitoring stopped by user\n")

    def show_error_message(self, error):
        """Show error message."""
        timestamp = self._get_timestamp()
        uni_print(f"[{timestamp}] Error: {error}\n")

    def _get_timestamp(self):
        """Get formatted timestamp."""
        return time.strftime("%Y-%m-%d %H:%M:%S")
