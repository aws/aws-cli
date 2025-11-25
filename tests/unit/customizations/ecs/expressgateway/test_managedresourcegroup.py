import unittest

from awscli.customizations.ecs.expressgateway.managedresource import (
    ManagedResource,
)
from awscli.customizations.ecs.expressgateway.managedresourcegroup import (
    ManagedResourceGroup,
)


class TestManagedResourceGroup(unittest.TestCase):
    def setUp(self):
        self.resource1 = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", 1761230543.151
        )
        self.resource2 = ManagedResource(
            "Certificate", "cert-456", "PROVISIONING", 1761230543.151
        )

    def test_is_terminal_all_terminal(self):
        terminal_resource = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", 1761230543.151
        )
        group = ManagedResourceGroup(resources=[terminal_resource])
        self.assertTrue(group.is_terminal())

    def test_is_terminal_mixed(self):
        group = ManagedResourceGroup(
            resources=[self.resource1, self.resource2]
        )
        self.assertFalse(group.is_terminal())

    def test_is_terminal_empty(self):
        group = ManagedResourceGroup()
        self.assertTrue(group.is_terminal())

    def test_get_status_string_with_header(self):
        group = ManagedResourceGroup(
            resource_type="IngressPaths",
            identifier="endpoint-1",
            resources=[self.resource1],
        )
        status_string = group.get_status_string("⠋")
        self.assertIn("IngressPaths", status_string)
        self.assertIn("endpoint-1", status_string)

    def test_create_key(self):
        group = ManagedResourceGroup()
        key = group._create_key(self.resource1)
        self.assertEqual(key, "LoadBalancer/lb-123")

    def test_get_status_string_empty_group(self):
        group = ManagedResourceGroup(resource_type="EmptyGroup", resources=[])
        status_string = group.get_status_string("⠋")
        self.assertIn("EmptyGroup", status_string)
        self.assertIn("<empty>", status_string)

    def test_combine_resource_groups(self):
        group1 = ManagedResourceGroup(resources=[self.resource1])
        group2 = ManagedResourceGroup(resources=[self.resource2])
        combined = group1.combine(group2)
        self.assertEqual(len(combined.resource_mapping), 2)

    def test_combine_child_resources_both_none(self):
        group = ManagedResourceGroup()
        result = group._combine_child_resources(None, None)
        self.assertIsNone(result)

    def test_combine_child_resources_first_none(self):
        group = ManagedResourceGroup()
        resource = ManagedResource("LoadBalancer", "lb-123", "ACTIVE")
        result = group._combine_child_resources(None, resource)
        self.assertEqual(result, resource)

    def test_combine_overlapping_resources(self):
        older_resource = ManagedResource(
            "LoadBalancer", "lb-123", "PROVISIONING", 1761230543.151
        )
        newer_resource = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", 1761230600.151
        )

        group1 = ManagedResourceGroup(resources=[older_resource])
        group2 = ManagedResourceGroup(resources=[newer_resource])

        combined = group1.combine(group2)

        key = "LoadBalancer/lb-123"
        self.assertIn(key, combined.resource_mapping)
        self.assertEqual(combined.resource_mapping[key].status, "ACTIVE")

    def test_create_key_with_none_values(self):
        group = ManagedResourceGroup()
        resource = ManagedResource(None, None)
        key = group._create_key(resource)
        self.assertEqual(key, "/")

    def test_create_key_partial_none(self):
        group = ManagedResourceGroup()

        resource1 = ManagedResource(None, "identifier")
        key1 = group._create_key(resource1)
        self.assertEqual(key1, "/identifier")

        resource2 = ManagedResource("ResourceType", None)
        key2 = group._create_key(resource2)
        self.assertEqual(key2, "ResourceType/")

    def test_diff_unique_resources(self):
        # Test diff with completely different resources
        group1 = ManagedResourceGroup(
            resources=[self.resource1]
        )  # LoadBalancer
        group2 = ManagedResourceGroup(
            resources=[self.resource2]
        )  # Certificate

        diff1, diff2 = group1.compare_resource_sets(group2)

        # Each group should contain its unique resource
        self.assertEqual(len(diff1.resource_mapping), 1)
        self.assertEqual(len(diff2.resource_mapping), 1)
        self.assertIn("LoadBalancer/lb-123", diff1.resource_mapping)
        self.assertIn("Certificate/cert-456", diff2.resource_mapping)

    def test_diff_overlapping_resources(self):
        # Test diff with same resource type but different identifiers
        resource3 = ManagedResource(
            "LoadBalancer", "lb-456", "FAILED", 1761230600.151
        )
        group1 = ManagedResourceGroup(
            resources=[self.resource1, self.resource2]
        )  # lb-123, cert-456
        group2 = ManagedResourceGroup(
            resources=[self.resource2, resource3]
        )  # cert-456, lb-456

        diff1, diff2 = group1.compare_resource_sets(group2)

        # group1 unique: lb-123, group2 unique: lb-456, common: cert-456 (should not appear in diff)
        self.assertEqual(len(diff1.resource_mapping), 1)
        self.assertEqual(len(diff2.resource_mapping), 1)
        self.assertIn("LoadBalancer/lb-123", diff1.resource_mapping)
        self.assertIn("LoadBalancer/lb-456", diff2.resource_mapping)
        # Common resource should not be in either diff
        self.assertNotIn("Certificate/cert-456", diff1.resource_mapping)
        self.assertNotIn("Certificate/cert-456", diff2.resource_mapping)

    def test_diff_identical_groups(self):
        # Test diff with identical resource groups
        group1 = ManagedResourceGroup(
            resources=[self.resource1, self.resource2]
        )
        group2 = ManagedResourceGroup(
            resources=[self.resource1, self.resource2]
        )

        diff1, diff2 = group1.compare_resource_sets(group2)

        # No differences should be found
        self.assertEqual(len(diff1.resource_mapping), 0)
        self.assertEqual(len(diff2.resource_mapping), 0)

    def test_diff_empty_groups(self):
        # Test diff with empty groups
        group1 = ManagedResourceGroup(resources=[self.resource1])
        group2 = ManagedResourceGroup(resources=[])

        diff1, diff2 = group1.compare_resource_sets(group2)

        # group1 should contain its resource, group2 should be empty
        self.assertEqual(len(diff1.resource_mapping), 1)
        self.assertEqual(len(diff2.resource_mapping), 0)
        self.assertIn("LoadBalancer/lb-123", diff1.resource_mapping)

    def test_diff_excludes_matching_types_without_identifier(self):
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
        self.assertEqual(len(diff1.resource_mapping), 1)
        self.assertIn("LoadBalancer/", diff1.resource_mapping)

        # group2 should be empty because LoadBalancer/lb-456 is excluded by LoadBalancer/
        self.assertEqual(len(diff2.resource_mapping), 0)

    def test_get_status_string_with_status(self):
        group = ManagedResourceGroup(
            resource_type="IngressPaths", identifier="test-id", status="ACTIVE"
        )
        result = group.get_status_string("⠋")
        self.assertIn("IngressPaths", result)
        self.assertIn("test-id", result)
        self.assertIn("✓", result)  # Green checkmark for ACTIVE
        self.assertIn("ACTIVE", result)

    def test_get_status_string_without_status(self):
        group = ManagedResourceGroup(
            resource_type="IngressPaths", identifier="test-id"
        )
        result = group.get_status_string("⠋")
        self.assertIn("IngressPaths", result)
        self.assertIn("test-id", result)
        self.assertNotIn("✓", result)  # No symbol when no status
        self.assertNotIn("ACTIVE", result)

    def test_get_status_string_status_without_identifier(self):
        group = ManagedResourceGroup(
            resource_type="IngressPaths", status="FAILED"
        )
        result = group.get_status_string("⠋")
        self.assertIn("IngressPaths", result)
        self.assertIn("X", result)  # Red X for FAILED
        self.assertIn("FAILED", result)

    def test_get_status_string_no_color(self):
        group = ManagedResourceGroup(
            resource_type="IngressPaths",
            identifier="test-id",
            status="ACTIVE",
            resources=[self.resource1],
        )
        result = group.get_status_string("⠋", use_color=False)
        self.assertIn("IngressPaths", result)
        self.assertIn("test-id", result)
        self.assertIn("✓", result)  # Checkmark should still be there
        self.assertIn("ACTIVE", result)
        # Should not contain ANSI color codes
        self.assertNotIn("\x1b[", result)

    def test_get_status_string_with_color(self):
        group = ManagedResourceGroup(
            resource_type="IngressPaths",
            identifier="test-id",
            status="ACTIVE",
            resources=[self.resource1],
        )
        result = group.get_status_string("⠋", use_color=True)
        self.assertIn("IngressPaths", result)
        self.assertIn("test-id", result)
        self.assertIn("✓", result)  # Checkmark should be there
        self.assertIn("ACTIVE", result)
        # Should contain ANSI color codes
        self.assertIn("\x1b[", result)

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
        self.assertEqual(len(result.resource_mapping), 1)
        combined_resource = list(result.resource_mapping.values())[0]
        self.assertEqual(combined_resource.identifier, "lb-123")


if __name__ == '__main__':
    unittest.main()
