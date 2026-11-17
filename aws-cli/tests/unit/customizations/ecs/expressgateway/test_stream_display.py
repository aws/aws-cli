# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/

import time

import pytest

from awscli.customizations.ecs.expressgateway.managedresource import (
    ManagedResource,
)
from awscli.customizations.ecs.expressgateway.managedresourcegroup import (
    ManagedResourceGroup,
)
from awscli.customizations.ecs.expressgateway.stream_display import (
    StreamDisplay,
)


@pytest.fixture
def display():
    """Fixture that returns a StreamDisplay with color enabled."""
    return StreamDisplay(use_color=True)


class TestStreamDisplay:
    """Test StreamDisplay for text-based monitoring output."""

    def test_show_startup_message(self, display, capsys):
        """Test startup message includes timestamp"""
        display.show_startup_message()

        output = capsys.readouterr().out
        assert "Starting monitoring..." in output
        assert "[" in output

    def test_show_polling_message(self, display, capsys):
        """Test polling message includes timestamp"""
        display.show_polling_message()

        output = capsys.readouterr().out
        assert "Polling for updates..." in output

    def test_show_monitoring_data_with_info(self, display, capsys):
        """Test showing info message"""
        display.show_monitoring_data(None, "Info message")

        output = capsys.readouterr().out
        assert "Info message" in output and output.endswith("\n")

    def test_show_monitoring_data_first_poll_shows_all(self, display, capsys):
        """Test first poll shows all resources"""
        resource = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", None, None
        )
        resource_group = ManagedResourceGroup(resources=[resource])

        display.show_monitoring_data(resource_group, None)

        output = capsys.readouterr().out
        assert "LoadBalancer" in output
        assert "lb-123" in output

    def test_show_monitoring_data_no_changes(self, display, capsys):
        """Test no output when resources haven't changed"""
        resource = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", None, None
        )
        resource_group = ManagedResourceGroup(resources=[resource])

        # First poll - show all
        display.show_monitoring_data(resource_group, None)
        capsys.readouterr()  # Clear output to test second call

        # Second poll - same resources, no changes
        display.show_monitoring_data(resource_group, None)

        output = capsys.readouterr().out
        assert output == ""

    def test_show_monitoring_data_with_new_resource(self, display, capsys):
        """Test output when new resources are added"""
        resource1 = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", None, None
        )
        resource_group1 = ManagedResourceGroup(resources=[resource1])

        display.show_monitoring_data(resource_group1, None)
        capsys.readouterr()  # Clear initial output to verify new resource shows

        # Second resource group with additional resource
        resource2 = ManagedResource(
            "TargetGroup", "tg-456", "ACTIVE", None, None
        )
        resource_group2 = ManagedResourceGroup(
            resources=[resource1, resource2]
        )

        display.show_monitoring_data(resource_group2, None)

        output = capsys.readouterr().out
        assert "TargetGroup" in output

    def test_show_timeout_message(self, display, capsys):
        """Test timeout message"""
        display.show_timeout_message()

        output = capsys.readouterr().out
        assert "timeout reached" in output.lower()

    def test_show_service_inactive_message(self, display, capsys):
        """Test service inactive message"""
        display.show_service_inactive_message()

        output = capsys.readouterr().out
        assert "inactive" in output.lower()

    def test_show_completion_message(self, display, capsys):
        """Test completion message"""
        display.show_completion_message()

        output = capsys.readouterr().out
        assert "complete" in output.lower()

    def test_show_user_stop_message(self, display, capsys):
        """Test user stop message"""
        display.show_user_stop_message()

        output = capsys.readouterr().out
        assert "stopped by user" in output.lower()

    def test_show_error_message(self, display, capsys):
        """Test error message"""
        display.show_error_message("Test error")

        output = capsys.readouterr().out
        assert "Error" in output
        assert "Test error" in output

    def test_use_color_parameter(self):
        """Test use_color parameter is stored"""
        display_with_color = StreamDisplay(use_color=True)
        assert display_with_color.use_color is True

        display_no_color = StreamDisplay(use_color=False)
        assert display_no_color.use_color is False

    def test_print_flattened_resources_with_reason(self, display, capsys):
        """Test resource with reason prints on separate line"""
        resource = ManagedResource(
            "LoadBalancer",
            "lb-123",
            "CREATING",
            None,
            "Waiting for DNS propagation",
        )
        resource_group = ManagedResourceGroup(resources=[resource])

        display.show_monitoring_data(resource_group, None)

        output = capsys.readouterr().out
        lines = output.splitlines()

        # Find the line with LoadBalancer
        lb_line_idx = next(
            i for i, line in enumerate(lines) if "LoadBalancer" in line
        )
        reason_line_idx = next(
            i
            for i, line in enumerate(lines)
            if "Reason: Waiting for DNS propagation" in line
        )

        # Reason should be on a different line than LoadBalancer
        assert lb_line_idx != reason_line_idx
        # Reason should come after the LoadBalancer line
        assert reason_line_idx > lb_line_idx

    def test_print_flattened_resources_with_updated_at(self, display, capsys):
        """Test resource with updated_at timestamp prints on separate line"""
        current_time = time.time()
        resource = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", current_time, None
        )
        resource_group = ManagedResourceGroup(resources=[resource])

        display.show_monitoring_data(resource_group, None)

        output = capsys.readouterr().out
        lines = output.splitlines()

        # Find the line with LoadBalancer
        lb_line_idx = next(
            i for i, line in enumerate(lines) if "LoadBalancer" in line
        )
        updated_line_idx = next(
            i for i, line in enumerate(lines) if "Last Updated At:" in line
        )

        # Updated timestamp should be on a different line than LoadBalancer
        assert lb_line_idx != updated_line_idx
        # Updated timestamp should come after the LoadBalancer line
        assert updated_line_idx > lb_line_idx

    def test_print_flattened_resources_with_additional_info(
        self, display, capsys
    ):
        """Test resource with additional_info prints on separate line"""
        resource = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", None, None
        )
        resource.additional_info = "DNS: example.elb.amazonaws.com"
        resource_group = ManagedResourceGroup(resources=[resource])

        display.show_monitoring_data(resource_group, None)

        output = capsys.readouterr().out
        lines = output.splitlines()

        # Find the line with LoadBalancer
        lb_line_idx = next(
            i for i, line in enumerate(lines) if "LoadBalancer" in line
        )
        info_line_idx = next(
            i
            for i, line in enumerate(lines)
            if "Info: DNS: example.elb.amazonaws.com" in line
        )

        # Info should be on a different line than LoadBalancer
        assert lb_line_idx != info_line_idx
        # Info should come after the LoadBalancer line
        assert info_line_idx > lb_line_idx

    def test_print_flattened_resources_complete_multi_line(
        self, display, capsys
    ):
        """Test resource with all fields prints on multiple lines"""
        resource = ManagedResource(
            "LoadBalancer",
            "lb-123",
            "CREATING",
            time.time(),
            "Provisioning load balancer",
        )
        resource.additional_info = "Type: application"
        resource_group = ManagedResourceGroup(resources=[resource])

        display.show_monitoring_data(resource_group, None)

        output = capsys.readouterr().out
        lines = output.splitlines()

        # Find all the relevant lines
        lb_line_idx = next(
            i
            for i, line in enumerate(lines)
            if "LoadBalancer" in line and "lb-123" in line
        )
        reason_line_idx = next(
            i
            for i, line in enumerate(lines)
            if "Reason: Provisioning load balancer" in line
        )
        updated_line_idx = next(
            i for i, line in enumerate(lines) if "Last Updated At:" in line
        )
        info_line_idx = next(
            i
            for i, line in enumerate(lines)
            if "Info: Type: application" in line
        )

        # All detail lines should be different from the main line
        assert reason_line_idx != lb_line_idx
        assert updated_line_idx != lb_line_idx
        assert info_line_idx != lb_line_idx

        # All detail lines should come after the main line
        assert reason_line_idx > lb_line_idx
        assert updated_line_idx > lb_line_idx
        assert info_line_idx > lb_line_idx

    def test_diff_detects_status_change(self, display, capsys):
        """Test diff detects when status changes"""
        resource1 = ManagedResource(
            "LoadBalancer", "lb-123", "CREATING", None, None
        )
        resource_group1 = ManagedResourceGroup(resources=[resource1])

        # First poll
        display.show_monitoring_data(resource_group1, None)
        capsys.readouterr()  # Clear initial output to test status change detection

        # Second poll - same resource but status changed
        resource2 = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", None, None
        )
        resource_group2 = ManagedResourceGroup(resources=[resource2])

        display.show_monitoring_data(resource_group2, None)

        output = capsys.readouterr().out
        assert "LoadBalancer" in output
        assert "ACTIVE" in output

    def test_diff_detects_reason_change(self, display, capsys):
        """Test diff detects when reason changes"""
        resource1 = ManagedResource(
            "LoadBalancer", "lb-123", "CREATING", None, "Creating resources"
        )
        resource_group1 = ManagedResourceGroup(resources=[resource1])

        # First poll
        display.show_monitoring_data(resource_group1, None)
        capsys.readouterr()  # Clear initial output to test reason change detection

        # Second poll - same resource but reason changed
        resource2 = ManagedResource(
            "LoadBalancer", "lb-123", "CREATING", None, "Waiting for DNS"
        )
        resource_group2 = ManagedResourceGroup(resources=[resource2])

        display.show_monitoring_data(resource_group2, None)

        output = capsys.readouterr().out
        assert "Waiting for DNS" in output

    def test_diff_detects_additional_info_change(self, display, capsys):
        """Test diff detects when additional_info changes"""
        resource1 = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", None, None
        )
        resource1.additional_info = "DNS: old.example.com"
        resource_group1 = ManagedResourceGroup(resources=[resource1])

        # First poll
        display.show_monitoring_data(resource_group1, None)
        capsys.readouterr()  # Clear initial output to test additional_info change detection

        # Second poll - same resource but additional_info changed
        resource2 = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", None, None
        )
        resource2.additional_info = "DNS: new.example.com"
        resource_group2 = ManagedResourceGroup(resources=[resource2])

        display.show_monitoring_data(resource_group2, None)

        output = capsys.readouterr().out
        assert "new.example.com" in output

    def test_resource_with_none_type_shows_identifier(self, display, capsys):
        """Test resources with resource_type=None show identifier without type"""
        resource = ManagedResource(
            None,
            "mystery-resource-123",
            "FAILED",
            reason="Something went wrong",
        )
        resource_group = ManagedResourceGroup(
            resource_type="TestGroup", resources=[resource]
        )

        display.show_monitoring_data(resource_group, None)

        output = capsys.readouterr().out
        assert "mystery-resource-123" in output
        assert "FAILED" in output

    def test_resource_with_none_type_and_none_identifier(
        self, display, capsys
    ):
        """Test resources with both resource_type=None and identifier=None show 'Unknown Resource' placeholder"""
        resource = ManagedResource(None, None, "ACTIVE")
        resource_group = ManagedResourceGroup(
            resource_type="TestGroup", resources=[resource]
        )

        display.show_monitoring_data(resource_group, None)

        output = capsys.readouterr().out
        assert "Unknown Resource" in output
        assert "ACTIVE" in output
