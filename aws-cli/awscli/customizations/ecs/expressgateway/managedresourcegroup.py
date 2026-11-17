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

from awscli.customizations.ecs.expressgateway.color_utils import ColorUtils
from awscli.customizations.ecs.expressgateway.managedresource import (
    ManagedResource,
)

MANAGED_RESOURCE_EMPTY = "{indent}<empty>"


class ManagedResourceGroup:
    """
    Represents a logical grouping of ManagedResources.
    """

    RESOURCE_GROUP_HEADER = "{resource_type} - {identifier}"
    RESOURCE_LIST_HEADER = "{resource_type}"

    def __init__(
        self,
        resource_type=None,
        identifier=None,
        resources=[],
        status=None,
        reason=None,
    ):
        self.resource_type = resource_type
        self.identifier = identifier
        # Maintain input ordering
        self.sorted_resource_keys = [
            self._create_key(resource) for resource in resources
        ]
        self.resource_mapping = {
            self._create_key(resource): resource for resource in resources
        }
        self.status = status
        self.reason = reason
        self.color_utils = ColorUtils()

    def _create_key(self, resource):
        resource_type = (
            resource.resource_type if resource.resource_type else ""
        )
        identifier = resource.identifier if resource.identifier else ""
        return resource_type + "/" + identifier

    def get_stream_string(self, timestamp, use_color=True):
        """Returns flattened stream strings for all resources in the group.

        Args:
            timestamp (str): Timestamp string to prefix each resource
            use_color (bool): Whether to use ANSI color codes (default: True)

        Returns:
            str: All flattened resources formatted for stream display, separated by newlines
        """
        flat_resources = []

        for resource in self.resource_mapping.values():
            if isinstance(resource, ManagedResourceGroup):
                # Recursively flatten nested groups
                nested = resource.get_stream_string(timestamp, use_color)
                if nested:
                    flat_resources.append(nested)
            elif isinstance(resource, ManagedResource):
                # Get stream string for individual resource
                flat_resources.append(
                    resource.get_stream_string(timestamp, use_color)
                )

        return "\n".join(flat_resources)

    def get_changed_resources(self, previous_resources_dict):
        """Get flattened list of resources that have changed properties.

        Compares individual resource properties (status, reason, updated_at, etc.)
        against previous state to detect changes. This is used for change detection
        in TEXT-ONLY mode, NOT for DEPLOYMENT diff (use compare_resource_sets for that).

        Args:
            previous_resources_dict: Dict of {(resource_type, identifier): ManagedResource}
                from previous poll. Can be empty dict for first poll.

        Returns:
            tuple: (changed_resources, updated_dict, removed_keys)
                - changed_resources: List of ManagedResource that changed or None if no changes
                - updated_dict: Updated dict with current resources for next comparison
                - removed_keys: Set of keys that were removed since last poll
        """
        current_resources = self._flatten_to_list()
        changed_resources = []
        updated_dict = {}

        for resource in current_resources:
            resource_key = (resource.resource_type, resource.identifier)
            previous_resource = previous_resources_dict.get(resource_key)

            if not previous_resource:
                changed_resources.append(resource)
            else:
                if resource.compare_properties(previous_resource):
                    changed_resources.append(resource)

            updated_dict[resource_key] = resource

        current_keys = {
            (r.resource_type, r.identifier) for r in current_resources
        }
        removed_keys = set(previous_resources_dict.keys()) - current_keys

        return (
            changed_resources if changed_resources else None,
            updated_dict,
            removed_keys,
        )

    def _flatten_to_list(self):
        """Flatten this resource group into a list of individual resources."""
        flat_list = []
        for resource in self.resource_mapping.values():
            if isinstance(resource, ManagedResourceGroup):
                flat_list.extend(resource._flatten_to_list())
            elif isinstance(resource, ManagedResource):
                flat_list.append(resource)
        return flat_list

    def is_terminal(self):
        return not self.resource_mapping or all(
            [
                resource.is_terminal()
                for resource in self.resource_mapping.values()
            ]
        )

    def get_status_string(self, spinner_char, depth=0, use_color=True):
        """Returns the resource information as a string.

        Args:
            spinner_char (str): Character to display for in-progress resources
            depth (int): Indentation depth for nested display (default: 0)
            use_color (bool): Whether to use ANSI color codes (default: True)

        Returns:
            str: Formatted status string with resource information
        """
        lines = []

        if self.resource_type:
            header = " " * depth + self.color_utils.make_cyan(
                str(self.resource_type), use_color
            )

            if self.identifier:
                header += ": "
                if self.status:
                    header += self.color_utils.make_status_symbol(
                        self.status, spinner_char, use_color
                    )
                    header += self.color_utils.color_by_status(
                        self.identifier, self.status, use_color
                    )
                    header += " - " + self.color_utils.color_by_status(
                        self.status, self.status, use_color
                    )
                else:
                    header += self.identifier
            elif self.status:
                header += " " + self.color_utils.make_status_symbol(
                    self.status, spinner_char, use_color
                )
                header += "- " + self.color_utils.color_by_status(
                    self.status, self.status, use_color
                )

            lines.append(header)

            if self.status and self.reason:
                lines.append(" " * (depth + 1) + "Reason: " + self.reason)

            if self.sorted_resource_keys:
                # Add a new line to help with spacing
                lines.append("")

        depth_offset = 1 if self.resource_type else 0
        for key in self.sorted_resource_keys:
            resource_string = self.resource_mapping.get(key).get_status_string(
                spinner_char, depth=depth + depth_offset, use_color=use_color
            )
            lines.append(resource_string)

        if not self.sorted_resource_keys and self.resource_type:
            empty_line = MANAGED_RESOURCE_EMPTY.format(
                indent=" " * (depth + depth_offset)
            )
            lines.append(empty_line)

        return '\n'.join(lines)

    def combine(self, other_resource_group):
        """Returns a ManagedResourceGroup containing the combined responses of each resource.

        Args:
            other_resource_group (ManagedResourceGroup): Resource group to combine with this one

        Returns:
            ManagedResourceGroup: Combined resource group with merged resources
        """
        if not other_resource_group:
            return self

        # Collect all resources from both groups
        all_resources = list(self.resource_mapping.values()) + list(
            other_resource_group.resource_mapping.values()
        )

        # Group by resource type, prioritizing resources with identifiers
        type_groups = {}
        for resource in all_resources:
            resource_type = resource.resource_type
            if resource_type not in type_groups:
                type_groups[resource_type] = []
            type_groups[resource_type].append(resource)

        # For each type, if we have both resources with and without identifiers, keep only those with identifiers
        filtered_resources = []
        for resource_type, resources in type_groups.items():
            resources_with_id = [r for r in resources if r.identifier]
            resources_without_id = [r for r in resources if not r.identifier]

            if resources_with_id and resources_without_id:
                # Only keep resources with identifiers
                filtered_resources.extend(resources_with_id)
            else:
                # Keep all resources (either all have identifiers or all don't)
                filtered_resources.extend(resources)

        # Now create keys and combine as before
        resource_mapping = {}
        for resource in filtered_resources:
            key = self._create_key(resource)
            if key in resource_mapping:
                resource_mapping[key] = resource_mapping[key].combine(resource)
            else:
                resource_mapping[key] = resource

        return ManagedResourceGroup(
            resource_type=self.resource_type,
            identifier=self.identifier,
            resources=resource_mapping.values(),
        )

    def _combine_child_resources(self, resource_a, resource_b):
        if resource_a:
            return resource_a.combine(resource_b)
        else:
            return resource_b

    def compare_resource_sets(self, other_resource_group):
        """Compares resource SETS between two groups to find additions/removals.

        This is used for DEPLOYMENT view to show which resources were added or removed
        between service configurations, NOT for detecting property changes within
        individual resources (that's compare_properties() in ManagedResource).

        Args:
            other_resource_group (ManagedResourceGroup): Resource group to compare against

        Returns:
            tuple: (self_unique, other_unique) where:
                - self_unique (ManagedResourceGroup): Resources unique to this group
                - other_unique (ManagedResourceGroup): Resources unique to the other group
        """
        other_keys = set(other_resource_group.resource_mapping.keys())
        self_keys = set(self.resource_mapping.keys())

        unique_to_self = self_keys - other_keys

        # Get resource types from self that have no identifier (end with '/')
        self_types_without_id = {
            key.rstrip('/') for key in self_keys if key.endswith('/')
        }

        # Exclude keys from other if their type matches a type in self without identifier
        unique_to_other = {
            key
            for key in (other_keys - self_keys)
            if not any(key.startswith(t + '/') for t in self_types_without_id)
        }
        common_keys = self_keys & other_keys

        common_diff = {
            key: self.resource_mapping[key].compare_resource_sets(
                other_resource_group.resource_mapping.get(key)
            )
            for key in common_keys
            if not isinstance(self.resource_mapping[key], ManagedResource)
        }
        common_self = {
            key: val[0]
            for key, val in common_diff.items()
            if val[0] is not None
        }
        common_other = {
            key: val[1]
            for key, val in common_diff.items()
            if val[1] is not None
        }

        self_resources = [
            self.resource_mapping[key]
            if key in unique_to_self
            else common_self[key]
            for key in self.sorted_resource_keys
            if key in unique_to_self or key in common_self
        ]

        other_resources = [
            other_resource_group.resource_mapping[key]
            if key in unique_to_other
            else common_other[key]
            for key in other_resource_group.sorted_resource_keys
            if key in unique_to_other or key in common_other
        ]

        return (
            ManagedResourceGroup(
                resource_type=self.resource_type,
                identifier=self.identifier,
                resources=self_resources,
            ),
            ManagedResourceGroup(
                resource_type=self.resource_type,
                identifier=self.identifier,
                resources=other_resources,
            ),
        )
