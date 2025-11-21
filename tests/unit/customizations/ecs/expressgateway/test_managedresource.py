import unittest

from awscli.customizations.ecs.expressgateway.managedresource import (
    TERMINAL_RESOURCE_STATUSES,
    ManagedResource,
)


class TestManagedResource(unittest.TestCase):
    def test_is_terminal_active(self):
        resource = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", 1761230543.151
        )
        self.assertTrue(resource.is_terminal())

    def test_is_terminal_failed(self):
        resource = ManagedResource(
            "LoadBalancer", "lb-123", "FAILED", 1761230543.151
        )
        self.assertTrue(resource.is_terminal())

    def test_is_terminal_provisioning(self):
        resource = ManagedResource(
            "LoadBalancer", "lb-123", "PROVISIONING", 1761230543.151
        )
        self.assertFalse(resource.is_terminal())

    def test_get_status_string_active(self):
        resource = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", 1761230543.151
        )
        status_string = resource.get_status_string("⠋")
        self.assertIn("LoadBalancer", status_string)
        self.assertIn("lb-123", status_string)
        self.assertIn("ACTIVE", status_string)

    def test_get_status_string_failed_with_reason(self):
        resource = ManagedResource(
            "LoadBalancer",
            "lb-123",
            "FAILED",
            1761230543.151,
            "Connection timeout",
        )
        status_string = resource.get_status_string("⠋")
        self.assertIn("FAILED", status_string)
        self.assertIn("Connection timeout", status_string)

    def test_get_status_string_active_with_reason(self):
        resource = ManagedResource(
            "LoadBalancer",
            "lb-123",
            "ACTIVE",
            1761230543.151,
            "Load balancer ready",
        )
        status_string = resource.get_status_string("⠋")
        self.assertIn("ACTIVE", status_string)
        self.assertIn("Load balancer ready", status_string)

    def test_combine_newer_resource(self):
        older = ManagedResource(
            "LoadBalancer", "lb-123", "PROVISIONING", 1761230543.151
        )
        newer = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", 1761230600.151
        )
        result = older.combine(newer)
        self.assertEqual(result, newer)

    def test_combine_older_resource(self):
        older = ManagedResource(
            "LoadBalancer", "lb-123", "PROVISIONING", 1761230543.151
        )
        newer = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", 1761230600.151
        )
        result = newer.combine(older)
        self.assertEqual(result, newer)

    def test_combine_with_none(self):
        resource = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", 1761230543.151
        )
        result = resource.combine(None)
        self.assertEqual(result, resource)

    def test_is_terminal_deleted_status(self):
        resource = ManagedResource("LoadBalancer", "lb-123", "DELETED")
        self.assertTrue(resource.is_terminal())

    def test_is_terminal_no_status(self):
        resource = ManagedResource("LoadBalancer", "lb-123", None)
        self.assertFalse(resource.is_terminal())

    def test_init_with_string_timestamp(self):
        resource = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", "2025-11-05T18:00:00Z"
        )
        self.assertIsInstance(resource.updated_at, float)
        self.assertGreater(resource.updated_at, 0)

    def test_init_with_none_timestamp(self):
        resource = ManagedResource("LoadBalancer", "lb-123", "ACTIVE", None)
        self.assertIsNone(resource.updated_at)

    def test_combine_with_no_timestamp(self):
        resource1 = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", 1761230543.151
        )
        resource2 = ManagedResource(
            "LoadBalancer", "lb-123", "PROVISIONING", None
        )
        result = resource1.combine(resource2)
        self.assertEqual(result, resource1)

    def test_combine_equal_timestamps(self):
        timestamp = 1761230543.151
        resource1 = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", timestamp
        )
        resource2 = ManagedResource(
            "LoadBalancer", "lb-123", "PROVISIONING", timestamp
        )
        result = resource1.combine(resource2)
        self.assertEqual(result, resource1)

    def test_get_status_string_with_depth(self):
        resource = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", 1761230543.151
        )
        status_string = resource.get_status_string("⠋", depth=2)
        # Should have proper indentation
        lines = status_string.split('\n')
        self.assertTrue(lines[0].startswith("  "))  # 2 spaces for depth=2

    def test_get_status_string_with_additional_info(self):
        resource = ManagedResource(
            "LoadBalancer",
            "lb-123",
            "ACTIVE",
            1761230543.151,
            additional_info="Load balancer is healthy",
        )
        status_string = resource.get_status_string("⠋")
        self.assertIn("Load balancer is healthy", status_string)

    def test_get_status_string_no_identifier(self):
        resource = ManagedResource(
            "LoadBalancer", None, "ACTIVE", 1761230543.151
        )
        status_string = resource.get_status_string("⠋")
        self.assertIn("LoadBalancer", status_string)
        self.assertIn("ACTIVE", status_string)

    def test_get_status_string_no_color(self):
        resource = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", 1761230543.151
        )
        status_string = resource.get_status_string("⠋", use_color=False)
        self.assertIn("LoadBalancer", status_string)
        self.assertIn("lb-123", status_string)
        self.assertIn("ACTIVE", status_string)
        # Should not contain ANSI color codes
        self.assertNotIn("\x1b[", status_string)

    def test_get_status_string_with_color(self):
        resource = ManagedResource(
            "LoadBalancer", "lb-123", "ACTIVE", 1761230543.151
        )
        status_string = resource.get_status_string("⠋", use_color=True)
        self.assertIn("LoadBalancer", status_string)
        self.assertIn("lb-123", status_string)
        self.assertIn("ACTIVE", status_string)
        # Should contain ANSI color codes
        self.assertIn("\x1b[", status_string)


class TestConstants(unittest.TestCase):
    def test_terminal_resource_statuses(self):
        expected_statuses = ["ACTIVE", "DELETED", "FAILED"]
        self.assertEqual(TERMINAL_RESOURCE_STATUSES, expected_statuses)


if __name__ == '__main__':
    unittest.main()
