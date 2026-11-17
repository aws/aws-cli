import re

import pytest

from awscli.customizations.ecs.expressgateway.managedresource import (
    TERMINAL_RESOURCE_STATUSES,
    ManagedResource,
)


class TestManagedResource:
    def test_is_terminal_active(self):
        resource = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", 1761230543.151
        )
        assert resource.is_terminal()

    def test_is_terminal_failed(self):
        resource = ManagedResource(
            "LoadBalancer", "lb-123", "FAILED", 1761230543.151
        )
        assert resource.is_terminal()

    def test_is_terminal_provisioning(self):
        resource = ManagedResource(
            "LoadBalancer", "lb-123", "PROVISIONING", 1761230543.151
        )
        assert not resource.is_terminal()

    def test_get_status_string_active(self):
        resource = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", 1761230543.151
        )
        status_string = resource.get_status_string("⠋")
        assert "LoadBalancer" in status_string
        assert "lb-123" in status_string
        assert "ACTIVE" in status_string

    def test_get_status_string_failed_with_reason(self):
        resource = ManagedResource(
            "LoadBalancer",
            "lb-123",
            "FAILED",
            1761230543.151,
            "Connection timeout",
        )
        status_string = resource.get_status_string("⠋")
        assert "FAILED" in status_string
        assert "Connection timeout" in status_string

    def test_get_status_string_active_with_reason(self):
        resource = ManagedResource(
            "LoadBalancer",
            "lb-123",
            "ACTIVE",
            1761230543.151,
            "Load balancer ready",
        )
        status_string = resource.get_status_string("⠋")
        assert "ACTIVE" in status_string
        assert "Load balancer ready" in status_string

    def test_combine_newer_resource(self):
        older = ManagedResource(
            "LoadBalancer", "lb-123", "PROVISIONING", 1761230543.151
        )
        newer = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", 1761230600.151
        )
        result = older.combine(newer)
        assert result == newer

    def test_combine_older_resource(self):
        older = ManagedResource(
            "LoadBalancer", "lb-123", "PROVISIONING", 1761230543.151
        )
        newer = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", 1761230600.151
        )
        result = newer.combine(older)
        assert result == newer

    def test_combine_with_none(self):
        resource = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", 1761230543.151
        )
        result = resource.combine(None)
        assert result == resource

    def test_is_terminal_deleted_status(self):
        resource = ManagedResource("LoadBalancer", "lb-123", "DELETED")
        assert resource.is_terminal()

    def test_is_terminal_no_status(self):
        resource = ManagedResource("LoadBalancer", "lb-123", None)
        assert not resource.is_terminal()

    def test_init_with_string_timestamp(self):
        resource = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", "2025-11-05T18:00:00Z"
        )
        assert isinstance(resource.updated_at, float)
        assert resource.updated_at > 0

    def test_init_with_none_timestamp(self):
        resource = ManagedResource("LoadBalancer", "lb-123", "ACTIVE", None)
        assert resource.updated_at is None

    def test_combine_with_no_timestamp(self):
        resource1 = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", 1761230543.151
        )
        resource2 = ManagedResource(
            "LoadBalancer", "lb-123", "PROVISIONING", None
        )
        result = resource1.combine(resource2)
        assert result == resource1

    def test_combine_equal_timestamps(self):
        timestamp = 1761230543.151
        resource1 = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", timestamp
        )
        resource2 = ManagedResource(
            "LoadBalancer", "lb-123", "PROVISIONING", timestamp
        )
        result = resource1.combine(resource2)
        assert result == resource1

    def test_get_status_string_with_depth(self):
        resource = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", 1761230543.151
        )
        status_string = resource.get_status_string("⠋", depth=2)
        # Should have proper indentation
        lines = status_string.split('\n')
        assert lines[0].startswith("  ")  # 2 spaces for depth=2

    def test_get_status_string_with_additional_info(self):
        resource = ManagedResource(
            "LoadBalancer",
            "lb-123",
            "ACTIVE",
            1761230543.151,
            additional_info="Load balancer is healthy",
        )
        status_string = resource.get_status_string("⠋")
        assert "Load balancer is healthy" in status_string

    def test_get_status_string_no_identifier(self):
        resource = ManagedResource(
            "LoadBalancer", None, "ACTIVE", 1761230543.151
        )
        status_string = resource.get_status_string("⠋")
        assert "LoadBalancer" in status_string
        assert "ACTIVE" in status_string

    def test_get_status_string_no_color(self):
        resource = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", 1761230543.151
        )
        status_string = resource.get_status_string("⠋", use_color=False)
        assert "LoadBalancer" in status_string
        assert "lb-123" in status_string
        assert "ACTIVE" in status_string
        # Should not contain ANSI color codes
        assert "\x1b[" not in status_string

    def test_get_status_string_with_color(self):
        resource = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", 1761230543.151
        )
        status_string = resource.get_status_string("⠋", use_color=True)
        assert "LoadBalancer" in status_string
        assert "lb-123" in status_string
        assert "ACTIVE" in status_string
        # Should contain ANSI color codes
        assert "\x1b[" in status_string

    def test_get_stream_string_basic(self):
        resource = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", 1761230543.151
        )
        stream_string = resource.get_stream_string("2025-12-15 10:00:00")
        assert "[2025-12-15 10:00:00]" in stream_string
        assert "LoadBalancer" in stream_string
        assert "lb-123" in stream_string
        assert "ACTIVE" in stream_string

    def test_get_stream_string_with_reason(self):
        resource = ManagedResource(
            "LoadBalancer",
            "lb-123",
            "PROVISIONING",
            1761230543.151,
            "Waiting for DNS propagation",
        )
        stream_string = resource.get_stream_string("2025-12-15 10:00:00")
        assert "Reason: Waiting for DNS propagation" in stream_string

    def test_get_stream_string_with_additional_info(self):
        resource = ManagedResource(
            "LoadBalancer",
            "lb-123",
            "ACTIVE",
            1761230543.151,
            additional_info="DNS: example.elb.amazonaws.com",
        )
        stream_string = resource.get_stream_string("2025-12-15 10:00:00")
        assert "Info: DNS: example.elb.amazonaws.com" in stream_string

    def test_get_stream_string_with_updated_at(self):
        resource = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", 1761230543.151
        )
        stream_string = resource.get_stream_string("2025-12-15 10:00:00")
        assert "Last Updated At:" in stream_string
        # Check timestamp format YYYY-MM-DD HH:MM:SS
        assert re.search(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", stream_string)

    def test_get_stream_string_all_fields(self):
        resource = ManagedResource(
            "TargetGroup",
            "tg-456",
            "PROVISIONING",
            1761230543.151,
            "Registering targets",
            "Health check interval: 30s",
        )
        stream_string = resource.get_stream_string("2025-12-15 10:00:00")
        assert "[2025-12-15 10:00:00]" in stream_string
        assert "TargetGroup" in stream_string
        assert "tg-456" in stream_string
        assert "PROVISIONING" in stream_string
        assert "Reason: Registering targets" in stream_string
        assert "Last Updated At:" in stream_string
        assert "Info: Health check interval: 30s" in stream_string

    def test_get_stream_string_no_identifier(self):
        resource = ManagedResource(
            "LoadBalancer", None, "ACTIVE", 1761230543.151
        )
        stream_string = resource.get_stream_string("2025-12-15 10:00:00")
        assert "[2025-12-15 10:00:00]" in stream_string
        assert "LoadBalancer" in stream_string
        assert "ACTIVE" in stream_string
        assert "None" not in stream_string

    def test_get_stream_string_no_status(self):
        resource = ManagedResource(
            "LoadBalancer", "lb-123", None, 1761230543.151
        )
        stream_string = resource.get_stream_string("2025-12-15 10:00:00")
        assert "LoadBalancer" in stream_string
        assert "lb-123" in stream_string
        # Should not have status brackets when status is None
        assert "[None]" not in stream_string

    def test_get_stream_string_no_color(self):
        resource = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", 1761230543.151
        )
        stream_string = resource.get_stream_string(
            "2025-12-15 10:00:00", use_color=False
        )
        assert "LoadBalancer" in stream_string
        assert "lb-123" in stream_string
        assert "ACTIVE" in stream_string
        # Should not contain ANSI color codes
        assert "\x1b[" not in stream_string

    def test_get_stream_string_with_color(self):
        resource = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", 1761230543.151
        )
        stream_string = resource.get_stream_string(
            "2025-12-15 10:00:00", use_color=True
        )
        assert "LoadBalancer" in stream_string
        assert "lb-123" in stream_string
        assert "ACTIVE" in stream_string
        # Should contain ANSI color codes
        assert "\x1b[" in stream_string

    def test_get_stream_string_failed_status(self):
        resource = ManagedResource(
            "LoadBalancer",
            "lb-123",
            "FAILED",
            1761230543.151,
            "Connection timeout",
        )
        stream_string = resource.get_stream_string("2025-12-15 10:00:00")
        assert "FAILED" in stream_string
        assert "Reason: Connection timeout" in stream_string
        # Failed status should use color coding
        assert "\x1b[" in stream_string


class TestConstants:
    def test_terminal_resource_statuses(self):
        expected_statuses = ["ACTIVE", "DELETED", "FAILED"]
        assert TERMINAL_RESOURCE_STATUSES == expected_statuses
