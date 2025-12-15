import pytest

from awscli.customizations.ecs.expressgateway.managedresource import (
    ManagedResource,
)
from awscli.customizations.ecs.expressgateway.managedresourcegroup import (
    ManagedResourceGroup,
)


@pytest.fixture
def resource1():
    return ManagedResource("LoadBalancer", "lb-123", "ACTIVE", 1761230543.151)


@pytest.fixture
def resource2():
    return ManagedResource(
        "Certificate", "cert-456", "PROVISIONING", 1761230543.151
    )


class TestManagedResourceGroup:
    def test_is_terminal_all_terminal(self):
        terminal_resource = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", 1761230543.151
        )
        group = ManagedResourceGroup(resources=[terminal_resource])
        assert group.is_terminal()

    def test_is_terminal_mixed(self, resource1, resource2):
        group = ManagedResourceGroup(resources=[resource1, resource2])
        assert not group.is_terminal()

    def test_is_terminal_empty(self):
        group = ManagedResourceGroup()
        assert group.is_terminal()

    def test_get_status_string_with_header(self, resource1):
        group = ManagedResourceGroup(
            resource_type="IngressPaths",
            identifier="endpoint-1",
            resources=[resource1],
        )
        status_string = group.get_status_string("⠋")
        assert "IngressPaths" in status_string
        assert "endpoint-1" in status_string

    def test_compare_resource_sets_unique_resources(
        self, resource1, resource2
    ):
        # Test compare_resource_sets with completely different resources
        group1 = ManagedResourceGroup(resources=[resource1])  # LoadBalancer
        group2 = ManagedResourceGroup(resources=[resource2])  # Certificate

        diff1, diff2 = group1.compare_resource_sets(group2)

        # Each group should contain its unique resource
        assert len(diff1.resource_mapping) == 1
        assert len(diff2.resource_mapping) == 1
        assert "LoadBalancer/lb-123" in diff1.resource_mapping
        assert "Certificate/cert-456" in diff2.resource_mapping

    def test_compare_resource_sets_overlapping_resources(
        self, resource1, resource2
    ):
        # Test compare_resource_sets with same resource type but different identifiers
        resource3 = ManagedResource(
            "LoadBalancer", "lb-456", "FAILED", 1761230600.151
        )
        group1 = ManagedResourceGroup(
            resources=[resource1, resource2]
        )  # lb-123, cert-456
        group2 = ManagedResourceGroup(
            resources=[resource2, resource3]
        )  # cert-456, lb-456

        diff1, diff2 = group1.compare_resource_sets(group2)

        # group1 unique: lb-123, group2 unique: lb-456, common: cert-456 (should not appear in diff)
        assert len(diff1.resource_mapping) == 1
        assert len(diff2.resource_mapping) == 1
        assert "LoadBalancer/lb-123" in diff1.resource_mapping
        assert "LoadBalancer/lb-456" in diff2.resource_mapping
        # Common resource should not be in either diff
        assert "Certificate/cert-456" not in diff1.resource_mapping
        assert "Certificate/cert-456" not in diff2.resource_mapping

    def test_compare_resource_sets_identical_groups(
        self, resource1, resource2
    ):
        # Test compare_resource_sets with identical resource groups
        group1 = ManagedResourceGroup(resources=[resource1, resource2])
        group2 = ManagedResourceGroup(resources=[resource1, resource2])

        diff1, diff2 = group1.compare_resource_sets(group2)

        # No differences should be found
        assert len(diff1.resource_mapping) == 0
        assert len(diff2.resource_mapping) == 0

    def test_compare_resource_sets_empty_groups(self, resource1):
        # Test compare_resource_sets with empty groups
        group1 = ManagedResourceGroup(resources=[resource1])
        group2 = ManagedResourceGroup(resources=[])

        diff1, diff2 = group1.compare_resource_sets(group2)

        # group1 should contain its resource, group2 should be empty
        assert len(diff1.resource_mapping) == 1
        assert len(diff2.resource_mapping) == 0
        assert "LoadBalancer/lb-123" in diff1.resource_mapping

    def test_compare_resource_sets_excludes_matching_types_without_identifier(
        self,
    ):
        # Test that resources in other are excluded if self has same type without identifier
        resource_without_id = ManagedResource("LoadBalancer", None)
        resource_with_id = ManagedResource("LoadBalancer", "lb-456")

        group1 = ManagedResourceGroup(
            resources=[resource_without_id]
        )  # LoadBalancer/
        group2 = ManagedResourceGroup(
            resources=[resource_with_id]
        )  # LoadBalancer/lb-456

        diff1, diff2 = group1.compare_resource_sets(group2)

        # group1 should contain its resource without identifier
        assert len(diff1.resource_mapping) == 1
        assert "LoadBalancer/" in diff1.resource_mapping

        # group2 should be empty because LoadBalancer/lb-456 is excluded by LoadBalancer/
        assert len(diff2.resource_mapping) == 0

    def test_get_status_string_with_status(self):
        group = ManagedResourceGroup(
            resource_type="IngressPaths", identifier="test-id", status="ACTIVE"
        )
        result = group.get_status_string("⠋")
        assert "IngressPaths" in result
        assert "test-id" in result
        assert "✓" in result  # Green checkmark for ACTIVE
        assert "ACTIVE" in result

    def test_get_status_string_without_status(self):
        group = ManagedResourceGroup(
            resource_type="IngressPaths", identifier="test-id"
        )
        result = group.get_status_string("⠋")
        assert "IngressPaths" in result
        assert "test-id" in result
        assert "✓" not in result  # No symbol when no status
        assert "ACTIVE" not in result

    def test_get_status_string_status_without_identifier(self):
        group = ManagedResourceGroup(
            resource_type="IngressPaths", status="FAILED"
        )
        result = group.get_status_string("⠋")
        assert "IngressPaths" in result
        assert "X" in result  # Red X for FAILED
        assert "FAILED" in result

    def test_get_status_string_no_color(self, resource1):
        group = ManagedResourceGroup(
            resource_type="IngressPaths",
            identifier="test-id",
            status="ACTIVE",
            resources=[resource1],
        )
        result = group.get_status_string("⠋", use_color=False)
        assert "IngressPaths" in result
        assert "test-id" in result
        assert "✓" in result  # Checkmark should still be there
        assert "ACTIVE" in result
        # Should not contain ANSI color codes
        assert "\x1b[" not in result

    def test_get_status_string_with_color(self, resource1):
        group = ManagedResourceGroup(
            resource_type="IngressPaths",
            identifier="test-id",
            status="ACTIVE",
            resources=[resource1],
        )
        result = group.get_status_string("⠋", use_color=True)
        assert "IngressPaths" in result
        assert "test-id" in result
        assert "✓" in result  # Checkmark should be there
        assert "ACTIVE" in result
        # Should contain ANSI color codes
        assert "\x1b[" in result

    def test_combine_prioritizes_resources_with_identifier(self):
        resource_with_id = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", 1761230543.151
        )
        resource_without_id = ManagedResource(
            "LoadBalancer",
            None,
            "PROVISIONING",
            1761230600.151,  # newer timestamp
        )

        group1 = ManagedResourceGroup(
            resource_type="Service", resources=[resource_with_id]
        )
        group2 = ManagedResourceGroup(
            resource_type="Service", resources=[resource_without_id]
        )

        # Should prefer the one with identifier despite older timestamp
        result = group1.combine(group2)

        # Should only have the resource with identifier
        assert len(result.resource_mapping) == 1
        combined_resource = list(result.resource_mapping.values())[0]
        assert combined_resource.identifier == "lb-123"

    def test_get_stream_string_empty_group(self):
        """Test empty resource group returns empty string"""
        group = ManagedResourceGroup()
        result = group.get_stream_string("2025-12-15 10:00:00")
        assert result == ""

    def test_get_stream_string_single_resource(self):
        """Test resource group with single resource"""
        resource = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", 1761230543.151
        )
        group = ManagedResourceGroup(resources=[resource])
        result = group.get_stream_string("2025-12-15 10:00:00")
        assert "[2025-12-15 10:00:00]" in result
        assert "LoadBalancer" in result
        assert "lb-123" in result
        assert "ACTIVE" in result

    def test_get_stream_string_multiple_resources(self):
        """Test resource group with multiple resources"""
        resource1 = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", 1761230543.151
        )
        resource2 = ManagedResource(
            "TargetGroup", "tg-456", "PROVISIONING", 1761230543.151
        )
        group = ManagedResourceGroup(resources=[resource1, resource2])
        result = group.get_stream_string("2025-12-15 10:00:00")

        # Should have both resources
        assert "LoadBalancer" in result
        assert "lb-123" in result
        assert "TargetGroup" in result
        assert "tg-456" in result

        # Should have newline between resources
        lines = result.split("\n")
        assert len(lines) > 1

    def test_get_stream_string_nested_groups(self):
        """Test resource group with nested groups"""
        resource1 = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", 1761230543.151
        )
        resource2 = ManagedResource(
            "TargetGroup", "tg-456", "ACTIVE", 1761230543.151
        )
        nested_group = ManagedResourceGroup(resources=[resource2])

        group = ManagedResourceGroup(resources=[resource1, nested_group])
        result = group.get_stream_string("2025-12-15 10:00:00")

        # Should have flattened both resources
        assert "LoadBalancer" in result
        assert "lb-123" in result
        assert "TargetGroup" in result
        assert "tg-456" in result

    def test_get_stream_string_deeply_nested_groups(self):
        """Test resource group with multiple levels of nesting"""
        resource1 = ManagedResource(
            "Cluster", "cluster-1", "ACTIVE", 1761230543.151
        )
        resource2 = ManagedResource(
            "Service", "service-1", "ACTIVE", 1761230543.151
        )
        resource3 = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", 1761230543.151
        )

        nested_level2 = ManagedResourceGroup(resources=[resource3])
        nested_level1 = ManagedResourceGroup(
            resources=[resource2, nested_level2]
        )
        group = ManagedResourceGroup(resources=[resource1, nested_level1])

        result = group.get_stream_string("2025-12-15 10:00:00")

        # Should have all resources flattened
        assert "Cluster" in result
        assert "Service" in result
        assert "LoadBalancer" in result

    def test_get_stream_string_with_resource_details(self):
        """Test that resource details are preserved in stream output"""
        resource = ManagedResource(
            "LoadBalancer",
            "lb-123",
            "PROVISIONING",
            1761230543.151,
            "Waiting for DNS propagation",
            "DNS: example.elb.amazonaws.com",
        )
        group = ManagedResourceGroup(resources=[resource])
        result = group.get_stream_string("2025-12-15 10:00:00")

        assert "Reason: Waiting for DNS propagation" in result
        assert "Info: DNS: example.elb.amazonaws.com" in result
        assert "Last Updated At:" in result

    def test_get_stream_string_preserves_order(self):
        """Test that resource order is preserved in output"""
        resource1 = ManagedResource(
            "Cluster", "cluster-1", "ACTIVE", 1761230543.151
        )
        resource2 = ManagedResource(
            "Service", "service-1", "ACTIVE", 1761230543.151
        )
        resource3 = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", 1761230543.151
        )

        group = ManagedResourceGroup(
            resources=[resource1, resource2, resource3]
        )
        result = group.get_stream_string("2025-12-15 10:00:00")

        # Find positions of each resource type in output
        cluster_pos = result.find("Cluster")
        service_pos = result.find("Service")
        lb_pos = result.find("LoadBalancer")

        # Order should be preserved
        assert cluster_pos < service_pos
        assert service_pos < lb_pos

    def test_get_stream_string_no_color(self):
        """Test stream string without color codes"""
        resource = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", 1761230543.151
        )
        group = ManagedResourceGroup(resources=[resource])
        result = group.get_stream_string(
            "2025-12-15 10:00:00", use_color=False
        )

        assert "LoadBalancer" in result
        assert "lb-123" in result
        # Should not contain ANSI color codes
        assert "\x1b[" not in result

    def test_get_stream_string_with_color(self):
        """Test stream string with color codes"""
        resource = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", 1761230543.151
        )
        group = ManagedResourceGroup(resources=[resource])
        result = group.get_stream_string("2025-12-15 10:00:00", use_color=True)

        assert "LoadBalancer" in result
        assert "lb-123" in result
        # Should contain ANSI color codes
        assert "\x1b[" in result

    def test_get_stream_string_mixed_resource_types(self):
        """Test group with various resource types and statuses"""
        resources = [
            ManagedResource("Cluster", "cluster-1", "ACTIVE", 1761230543.151),
            ManagedResource(
                "Service", "service-1", "UPDATING", 1761230543.151
            ),
            ManagedResource(
                "LoadBalancer",
                "lb-123",
                "PROVISIONING",
                1761230543.151,
                "Creating",
            ),
            ManagedResource(
                "TargetGroup", "tg-456", "FAILED", 1761230543.151, "Error"
            ),
        ]
        group = ManagedResourceGroup(resources=resources)
        result = group.get_stream_string("2025-12-15 10:00:00")

        # All resources should be present
        assert "Cluster" in result
        assert "Service" in result
        assert "LoadBalancer" in result
        assert "TargetGroup" in result

        # All statuses should be present
        assert "ACTIVE" in result
        assert "UPDATING" in result
        assert "PROVISIONING" in result
        assert "FAILED" in result

    def test_get_stream_string_with_group_metadata(self):
        """Test that group-level metadata doesn't affect stream output"""
        resource = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", 1761230543.151
        )
        group = ManagedResourceGroup(
            resource_type="ManagedResources",
            identifier="group-1",
            resources=[resource],
            status="ACTIVE",
            reason="All resources healthy",
        )
        result = group.get_stream_string("2025-12-15 10:00:00")

        # Should still show the actual resource, not group metadata
        assert "LoadBalancer" in result
        assert "lb-123" in result

        # Group metadata should not appear in stream output
        # (stream output is for individual resources only)
        assert "group-1" not in result

    def test_get_stream_string_empty_nested_group(self):
        """Test nested group that is empty is handled correctly"""
        resource = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", 1761230543.151
        )
        empty_nested = ManagedResourceGroup()

        group = ManagedResourceGroup(resources=[resource, empty_nested])
        result = group.get_stream_string("2025-12-15 10:00:00")

        # Should show the resource from non-empty group
        assert "LoadBalancer" in result
        # Empty nested group shouldn't add extra content
        lines = [line for line in result.split("\n") if line.strip()]
        # LoadBalancer resource produces multiple lines (timestamp line + optional detail lines)
        assert len(lines) > 0
