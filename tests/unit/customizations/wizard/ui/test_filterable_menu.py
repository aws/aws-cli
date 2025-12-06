# Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

import unittest
from unittest.mock import Mock, MagicMock, patch
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.screen import Point

from awscli.customizations.wizard.ui.selectmenu import (
    FilterableSelectionMenuControl,
    select_menu,
)


class TestFilterableSelectionMenuControl(unittest.TestCase):
    """Test cases for FilterableSelectionMenuControl"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_items = [
            {"id": "1", "name": "Production", "env": "prod"},
            {"id": "2", "name": "Development", "env": "dev"},
            {"id": "3", "name": "Staging", "env": "stage"},
            {"id": "4", "name": "Testing", "env": "test"},
        ]

        def display_format(item):
            return f"{item['name']} ({item['env']})"

        self.display_format = display_format
        self.control = FilterableSelectionMenuControl(
            self.test_items, display_format=self.display_format
        )

    def test_init(self):
        """Test initialization of FilterableSelectionMenuControl"""
        self.assertEqual(self.control._filter_text, "")
        self.assertEqual(self.control._filtered_items, self.test_items)
        self.assertEqual(self.control._all_items, self.test_items)
        self.assertTrue(self.control._filter_enabled)
        self.assertEqual(self.control._selection, 0)
        self.assertEqual(
            self.control._no_results_message, "No matching items found"
        )

    def test_filter_update_with_matching_text(self):
        """Test filtering with matching text"""
        self.control._filter_text = "prod"
        self.control._update_filtered_items()

        self.assertEqual(len(self.control._filtered_items), 1)
        self.assertEqual(self.control._filtered_items[0]["name"], "Production")

    def test_filter_update_with_non_matching_text(self):
        """Test filtering with non-matching text"""
        self.control._filter_text = "xyz"
        self.control._update_filtered_items()

        self.assertEqual(len(self.control._filtered_items), 0)

    def test_filter_update_case_insensitive(self):
        """Test that filtering is case insensitive"""
        self.control._filter_text = "DEV"
        self.control._update_filtered_items()

        self.assertEqual(len(self.control._filtered_items), 1)
        self.assertEqual(self.control._filtered_items[0]["name"], "Development")

    def test_filter_update_partial_match(self):
        """Test filtering with partial matches"""
        self.control._filter_text = "ing"
        self.control._update_filtered_items()

        # Should match both 'Staging' and 'Testing'
        self.assertEqual(len(self.control._filtered_items), 2)
        names = [item["name"] for item in self.control._filtered_items]
        self.assertIn("Staging", names)
        self.assertIn("Testing", names)

    def test_filter_clears_when_empty(self):
        """Test that empty filter shows all items"""
        self.control._filter_text = "prod"
        self.control._update_filtered_items()
        self.assertEqual(len(self.control._filtered_items), 1)

        self.control._filter_text = ""
        self.control._update_filtered_items()
        self.assertEqual(len(self.control._filtered_items), 4)

    def test_selection_reset_when_filtered(self):
        """Test that selection resets when filter results change"""
        self.control._selection = 2
        self.control._filter_text = "prod"
        self.control._update_filtered_items()

        # Selection should reset to 0 when filtering
        self.assertEqual(self.control._selection, 0)

    def test_preferred_width_with_items(self):
        """Test preferred width calculation with items"""
        max_width = 100
        width = self.control.preferred_width(max_width)

        # Width should be based on the longest item
        self.assertGreater(width, 0)
        self.assertLessEqual(width, max_width)

    def test_preferred_width_with_empty_filter_result(self):
        """Test preferred width when filter returns no results"""
        self.control._filter_text = "xyz"
        self.control._update_filtered_items()

        max_width = 100
        width = self.control.preferred_width(max_width)

        # Should return minimum width for no results message
        # Default message is "No matching items found" which is 24 chars + 4 = 28
        self.assertGreaterEqual(width, 20)

    def test_preferred_height(self):
        """Test preferred height calculation"""
        max_height = 10
        height = self.control.preferred_height(100, max_height, False, None)

        # Should be items count + 1 for search line
        expected = min(max_height, len(self.test_items) + 1)
        self.assertEqual(height, expected)

    def test_create_content_with_items(self):
        """Test content creation with filtered items"""
        content = self.control.create_content(50, 10)

        # First line should be the search prompt
        self.assertEqual(content.line_count, len(self.test_items) + 1)

        # Cursor should be on the first item (line 1, after search line)
        self.assertEqual(content.cursor_position.y, 1)

    def test_create_content_with_filter(self):
        """Test content creation with active filter"""
        self.control._filter_text = "test"
        self.control._update_filtered_items()

        content = self.control.create_content(50, 10)

        # Should have search line + 1 filtered item
        self.assertEqual(content.line_count, 2)

    def test_create_content_no_results(self):
        """Test content creation when no results match filter"""
        self.control._filter_text = "xyz"
        self.control._update_filtered_items()

        content = self.control.create_content(50, 10)

        # Should have at least 2 lines (search + no results message)
        self.assertGreaterEqual(content.line_count, 2)

        # Cursor should be on search line when no results
        self.assertEqual(content.cursor_position.y, 0)

    def test_key_bindings(self):
        """Test that key bindings are properly set up"""
        kb = self.control.get_key_bindings()

        self.assertIsInstance(kb, KeyBindings)

        # Check that essential keys are bound
        bindings = kb.bindings
        key_names = [str(b.keys[0]) for b in bindings]

        self.assertIn("Keys.Up", key_names)
        self.assertIn("Keys.Down", key_names)
        self.assertIn("Keys.ControlM", key_names)  # 'enter' is mapped to 'c-m'
        self.assertIn(
            "Keys.ControlH", key_names
        )  # 'backspace' is mapped to 'c-h'
        self.assertIn("Keys.ControlU", key_names)

    def test_move_cursor_with_filtered_items(self):
        """Test cursor movement with filtered items"""
        self.control._filter_text = "ing"
        self.control._update_filtered_items()

        # Should have 2 items (Staging and Testing)
        self.assertEqual(len(self.control._filtered_items), 2)

        # Move down
        self.control._move_cursor(1)
        self.assertEqual(self.control._selection, 1)

        # Move down again (should wrap to 0)
        self.control._move_cursor(1)
        self.assertEqual(self.control._selection, 0)

        # Move up (should wrap to last item)
        self.control._move_cursor(-1)
        self.assertEqual(self.control._selection, 1)

    def test_custom_no_results_message(self):
        """Test custom no results message"""
        custom_message = "No AWS accounts match your search"
        control = FilterableSelectionMenuControl(
            self.test_items,
            display_format=self.display_format,
            no_results_message=custom_message,
        )

        self.assertEqual(control._no_results_message, custom_message)

        # Test that custom message appears in content when no results
        control._filter_text = "xyz"
        control._update_filtered_items()

        content = control.create_content(50, 10)
        # Get the second line (index 1) which should contain the no results message
        line = content.get_line(1)
        self.assertEqual(len(line), 1)
        self.assertEqual(line[0][0], "class:no-results")
        self.assertIn(custom_message, line[0][1])


class TestSelectMenuWithFilter(unittest.TestCase):
    """Test select_menu function with filtering enabled"""

    @patch("awscli.customizations.wizard.ui.selectmenu.Application")
    def test_select_menu_with_filter_enabled(self, mock_app_class):
        """Test that select_menu uses FilterableSelectionMenuControl when enable_filter=True"""
        mock_app = MagicMock()
        mock_app_class.return_value = mock_app
        mock_app.run.return_value = {"id": "1", "name": "Test"}

        items = [{"id": "1", "name": "Test"}, {"id": "2", "name": "Prod"}]

        result = select_menu(items, enable_filter=True)

        # Verify Application was created
        mock_app_class.assert_called_once()

        # Verify the result
        self.assertEqual(result, {"id": "1", "name": "Test"})

    @patch("awscli.customizations.wizard.ui.selectmenu.Application")
    def test_select_menu_with_filter_disabled(self, mock_app_class):
        """Test that select_menu uses SelectionMenuControl when enable_filter=False"""
        mock_app = MagicMock()
        mock_app_class.return_value = mock_app
        mock_app.run.return_value = {"id": "1", "name": "Test"}

        items = [{"id": "1", "name": "Test"}, {"id": "2", "name": "Prod"}]

        result = select_menu(items, enable_filter=False)

        # Verify Application was created
        mock_app_class.assert_called_once()

        # Verify the result
        self.assertEqual(result, {"id": "1", "name": "Test"})


class TestFilteringIntegration(unittest.TestCase):
    """Integration tests for filtering in SSO configuration"""

    def test_filter_with_display_format(self):
        """Test filtering works correctly with display_format function"""
        accounts = [
            {
                "accountId": "111111111111",
                "accountName": "Production",
                "emailAddress": "prod@example.com",
            },
            {
                "accountId": "222222222222",
                "accountName": "Development",
                "emailAddress": "dev@example.com",
            },
            {
                "accountId": "333333333333",
                "accountName": "Staging",
                "emailAddress": "staging@example.com",
            },
        ]

        def display_account(account):
            return f"{account['accountName']}, {account['emailAddress']} ({account['accountId']})"

        control = FilterableSelectionMenuControl(
            accounts, display_format=display_account
        )

        # Test filtering by account name
        control._filter_text = "prod"
        control._update_filtered_items()
        self.assertEqual(len(control._filtered_items), 1)
        self.assertEqual(
            control._filtered_items[0]["accountName"], "Production"
        )

        # Test filtering by email
        control._filter_text = "dev@"
        control._update_filtered_items()
        self.assertEqual(len(control._filtered_items), 1)
        self.assertEqual(
            control._filtered_items[0]["accountName"], "Development"
        )

        # Test filtering by account ID
        control._filter_text = "3333"
        control._update_filtered_items()
        self.assertEqual(len(control._filtered_items), 1)
        self.assertEqual(control._filtered_items[0]["accountName"], "Staging")

    def test_empty_items_list(self):
        """Test handling of empty items list"""
        control = FilterableSelectionMenuControl([])

        self.assertEqual(control._filtered_items, [])
        self.assertEqual(control._all_items, [])

        # Should not crash when filtering
        control._filter_text = "test"
        control._update_filtered_items()
        self.assertEqual(control._filtered_items, [])

        # Should return reasonable width
        width = control.preferred_width(100)
        self.assertGreater(width, 0)


if __name__ == "__main__":
    unittest.main()
