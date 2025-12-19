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

import sys
from datetime import datetime, timezone

import dateutil.parser

from awscli.customizations.ecs.expressgateway.color_utils import ColorUtils

MANAGED_RESOURCE_REASON_MESSAGE = "{indent}Reason: {reason}"
MANAGED_RESOURCE_LAST_UPDATED_MESSAGE = (
    "{indent}Last updated at: {last_updated_at}"
)

TERMINAL_RESOURCE_STATUSES = ["ACTIVE", "DELETED", "FAILED"]
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class ManagedResource:
    """
    Represents a managed ECS resource.
    """

    def __init__(
        self,
        resource_type,
        identifier,
        status=None,
        updated_at=None,
        reason=None,
        additional_info=None,
    ):
        self.resource_type = resource_type
        self.identifier = identifier
        self.status = status
        if isinstance(updated_at, str):
            dt = dateutil.parser.parse(updated_at)
            self.updated_at = dt.timestamp()
        else:
            self.updated_at = updated_at
        self.reason = reason
        self.additional_info = additional_info
        self.color_utils = ColorUtils()

    def is_terminal(self):
        return self.status in TERMINAL_RESOURCE_STATUSES

    def get_status_string(self, spinner_char, depth=0, use_color=True):
        """Returns the resource information as a formatted string.

        Args:
            spinner_char (str): Character to display for in-progress resources
            depth (int): Indentation depth for nested display (default: 0)
            use_color (bool): Whether to use ANSI color codes (default: True)

        Returns:
            str: Formatted status string with resource information
        """
        lines = []
        resource_header = " " * depth + self.color_utils.make_cyan(
            self.resource_type, use_color
        )

        resource_header += ": " if self.identifier else " "
        resource_header += self.color_utils.make_status_symbol(
            self.status, spinner_char, use_color
        )
        if self.identifier:
            resource_header += (
                self.color_utils.color_by_status(
                    self.identifier, self.status, use_color
                )
                + " "
            )
        if self.status:
            resource_header += "- " + self.color_utils.color_by_status(
                self.status, self.status, use_color
            )
        lines.append(resource_header)

        if self.reason:
            lines.append(
                MANAGED_RESOURCE_REASON_MESSAGE.format(
                    indent=" " * (depth + 1), reason=self.reason
                )
            )

        if self.updated_at:
            lines.append(
                MANAGED_RESOURCE_LAST_UPDATED_MESSAGE.format(
                    indent=" " * (depth + 1),
                    last_updated_at=datetime.fromtimestamp(
                        self.updated_at
                    ).strftime(TIMESTAMP_FORMAT),
                )
            )

        if self.additional_info:
            lines.append(" " * (depth + 1) + self.additional_info)

        # Spacing between resources
        lines.append("")
        return '\n'.join(lines)

    def get_stream_string(self, timestamp, use_color=True):
        """Returns the resource information formatted for stream/text-only display.

        Args:
            timestamp (str): Timestamp string to prefix the output
            use_color (bool): Whether to use ANSI color codes (default: True)

        Returns:
            str: Formatted string with timestamp prefix and bracket-enclosed status
        """
        lines = []
        parts = [f"[{timestamp}]"]

        # If both resource_type and identifier are None, show a placeholder
        if not self.resource_type and not self.identifier:
            parts.append(
                self.color_utils.make_cyan("Unknown Resource", use_color)
            )
        else:
            if self.resource_type:
                parts.append(
                    self.color_utils.make_cyan(self.resource_type, use_color)
                )

            if self.identifier:
                colored_id = self.color_utils.color_by_status(
                    self.identifier, self.status, use_color
                )
                parts.append(colored_id)

        if self.status:
            status_text = self.color_utils.color_by_status(
                self.status, self.status, use_color
            )
            parts.append(f"[{status_text}]")

        lines.append(" ".join(parts))

        if self.reason:
            lines.append(f"  Reason: {self.reason}")

        if self.updated_at:
            updated_time = datetime.fromtimestamp(
                self.updated_at, tz=timezone.utc
            ).strftime("%Y-%m-%d %H:%M:%SZ")
            lines.append(f"  Last Updated At: {updated_time}")

        if self.additional_info:
            lines.append(f"  Info: {self.additional_info}")

        return "\n".join(lines)

    def combine(self, other_resource):
        """Returns the version of the resource which has the most up to date timestamp.

        Args:
            other_resource (ManagedResource): Resource to compare timestamps with

        Returns:
            ManagedResource: The resource with the latest timestamp
        """
        return (
            self
            if not other_resource
            or not other_resource.updated_at
            or self.updated_at >= other_resource.updated_at
            else other_resource
        )

    def compare_properties(self, other_resource):
        """Compares individual resource properties to detect changes.

        This compares properties like status, reason, updated_at, additional_info
        to detect if a resource has changed between polls.

        Args:
            other_resource (ManagedResource): Resource to compare against

        Returns:
            bool: True if properties differ, False if same
        """
        if not other_resource:
            # No previous resource means it's new/different
            return True

        # Resources are different if any field differs
        return (
            self.resource_type != other_resource.resource_type
            or self.identifier != other_resource.identifier
            or self.status != other_resource.status
            or self.reason != other_resource.reason
            or self.updated_at != other_resource.updated_at
            or self.additional_info != other_resource.additional_info
        )
