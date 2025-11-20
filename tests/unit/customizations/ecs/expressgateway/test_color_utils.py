import unittest
from unittest.mock import patch

from awscli.customizations.ecs.expressgateway.color_utils import ColorUtils


class TestColorUtils(unittest.TestCase):
    def test_make_cyan(self):
        result = ColorUtils.make_cyan("test text")
        self.assertIn("test text", result)
        # Should contain ANSI color codes for cyan
        self.assertIn("\033[", result)

    def test_make_cyan_no_color(self):
        result = ColorUtils.make_cyan("test text", use_color=False)
        self.assertEqual(result, "test text")
        # Should not contain ANSI color codes
        self.assertNotIn("\033[", result)

    def test_make_status_symbol_active(self):
        result = ColorUtils.make_status_symbol("ACTIVE", "⠋")
        # Should return a checkmark for ACTIVE status
        self.assertIn("✓", result)
        self.assertIn("\033[32m", result)  # Green color

    def test_make_status_symbol_active_no_color(self):
        result = ColorUtils.make_status_symbol("ACTIVE", "⠋", use_color=False)
        # Should return a checkmark for ACTIVE status without color
        self.assertIn("✓", result)
        self.assertNotIn("\033[", result)  # No ANSI codes

    def test_make_status_symbol_failed(self):
        result = ColorUtils.make_status_symbol("FAILED", "⠋")
        # Should return an X for FAILED status
        self.assertIn("X", result)
        self.assertIn("\033[31m", result)  # Red color

    def test_make_status_symbol_failed_no_color(self):
        result = ColorUtils.make_status_symbol("FAILED", "⠋", use_color=False)
        # Should return an X for FAILED status without color
        self.assertIn("X", result)
        self.assertNotIn("\033[", result)  # No ANSI codes

    def test_make_status_symbol_provisioning(self):
        result = ColorUtils.make_status_symbol("PROVISIONING", "⠋")
        # Should return purple spinner for PROVISIONING status
        self.assertIn("⠋", result)
        self.assertIn("\x1b[35m", result)  # Purple color

    def test_make_status_symbol_none_status(self):
        result = ColorUtils.make_status_symbol(None, "⠋")
        # Should return green checkmark for None status (treated as success)
        self.assertIn("✓", result)
        self.assertIn("\033[32m", result)  # Green color

    def test_color_by_status_active(self):
        result = ColorUtils.color_by_status("test text", "ACTIVE")
        self.assertIn("test text", result)
        # Should contain ANSI color codes for green (success)
        self.assertIn("\033[32m", result)

    def test_color_by_status_active_no_color(self):
        result = ColorUtils.color_by_status(
            "test text", "ACTIVE", use_color=False
        )
        self.assertEqual(result, "test text")
        # Should not contain ANSI color codes
        self.assertNotIn("\033[", result)

    def test_color_by_status_failed(self):
        result = ColorUtils.color_by_status("test text", "FAILED")
        self.assertIn("test text", result)
        # Should contain ANSI color codes for red (error)
        self.assertIn("\033[31m", result)

    def test_color_by_status_failed_no_color(self):
        result = ColorUtils.color_by_status(
            "test text", "FAILED", use_color=False
        )
        self.assertEqual(result, "test text")
        # Should not contain ANSI color codes
        self.assertNotIn("\033[", result)

    def test_color_by_status_provisioning(self):
        result = ColorUtils.color_by_status("test text", "PROVISIONING")
        self.assertIn("test text", result)
        # Should contain ANSI color codes for purple (in-progress)
        self.assertIn("\x1b[35m", result)

    def test_color_by_status_none_status(self):
        result = ColorUtils.color_by_status("test text", None)
        # Should return green text for None status (treated as success)
        self.assertIn("test text", result)
        self.assertIn("\033[32m", result)  # Green color code

    def test_color_by_status_unknown_status(self):
        result = ColorUtils.color_by_status("test text", "UNKNOWN_STATUS")
        # Should return purple text for unknown status
        self.assertIn("test text", result)
        self.assertIn("\x1b[35m", result)  # Purple color code

    def test_make_status_symbol_deleted(self):
        result = ColorUtils.make_status_symbol("DELETED", "⠋")
        # Should return appropriate symbol for DELETED status
        self.assertIn("—", result)
        self.assertIn("\033[33m", result)  # Yellow color

    def test_color_by_status_deleted(self):
        result = ColorUtils.color_by_status("test text", "DELETED")
        self.assertIn("test text", result)
        # Should contain ANSI color codes for yellow
        self.assertIn("\033[33m", result)

    def test_make_cyan_empty_string(self):
        result = ColorUtils.make_cyan("")
        self.assertIsInstance(result, str)

    def test_color_by_status_empty_text(self):
        result = ColorUtils.color_by_status("", "ACTIVE")
        self.assertIsInstance(result, str)

    def test_color_by_status_case_sensitive(self):
        # Test that status matching is case sensitive
        result_upper = ColorUtils.color_by_status("test", "ACTIVE")
        result_lower = ColorUtils.color_by_status("test", "active")
        # ACTIVE should be green, active should be purple (case sensitive)
        self.assertIn("\033[32m", result_upper)  # Green for ACTIVE
        self.assertIn("\x1b[35m", result_lower)  # Purple for active

    def test_make_status_symbol_case_sensitive(self):
        # Test that status matching is case sensitive
        result_upper = ColorUtils.make_status_symbol("ACTIVE", "⠋")
        result_lower = ColorUtils.make_status_symbol("active", "⠋")
        # ACTIVE should be checkmark, active should be spinner (case sensitive)
        self.assertIn("✓", result_upper)  # Checkmark for ACTIVE
        self.assertIn("⠋", result_lower)  # Spinner for active


if __name__ == '__main__':
    unittest.main()
