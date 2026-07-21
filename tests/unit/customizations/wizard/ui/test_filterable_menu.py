# Copyright 2026 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from unittest.mock import MagicMock, patch

from prompt_toolkit.key_binding import KeyBindings

from awscli.customizations.wizard.ui.selectmenu import (
    FilterableSelectionMenuControl,
    select_menu,
)


class TestFilterableSelectionMenuControl(unittest.TestCase):
    def setUp(self):
        self.items = [
            {'id': '1', 'name': 'Production', 'env': 'prod'},
            {'id': '2', 'name': 'Development', 'env': 'dev'},
            {'id': '3', 'name': 'Staging', 'env': 'stage'},
            {'id': '4', 'name': 'Testing', 'env': 'test'},
        ]
        self.display_format = lambda item: f"{item['name']} ({item['env']})"
        self.control = FilterableSelectionMenuControl(
            self.items, display_format=self.display_format
        )

    def test_init(self):
        self.assertEqual(self.control._filter_text, '')
        self.assertEqual(self.control._filtered_items, self.items)
        self.assertEqual(self.control._all_items, self.items)
        self.assertEqual(self.control._selection, 0)
        self.assertEqual(
            self.control._no_results_message, 'No matching items found'
        )

    def test_filter_matching(self):
        self.control._filter_text = 'prod'
        self.control._update_filtered_items()
        self.assertEqual(len(self.control._filtered_items), 1)
        self.assertEqual(self.control._filtered_items[0]['name'], 'Production')

    def test_filter_no_match(self):
        self.control._filter_text = 'xyz'
        self.control._update_filtered_items()
        self.assertEqual(self.control._filtered_items, [])

    def test_filter_case_insensitive(self):
        self.control._filter_text = 'DEV'
        self.control._update_filtered_items()
        self.assertEqual(len(self.control._filtered_items), 1)
        self.assertEqual(
            self.control._filtered_items[0]['name'], 'Development'
        )

    def test_filter_partial_match(self):
        self.control._filter_text = 'ing'
        self.control._update_filtered_items()
        names = [i['name'] for i in self.control._filtered_items]
        self.assertIn('Staging', names)
        self.assertIn('Testing', names)

    def test_filter_empty_resets_to_all(self):
        self.control._filter_text = 'prod'
        self.control._update_filtered_items()
        self.control._filter_text = ''
        self.control._update_filtered_items()
        self.assertEqual(len(self.control._filtered_items), 4)

    def test_selection_resets_when_out_of_bounds(self):
        self.control._selection = 3
        self.control._filter_text = 'prod'
        self.control._update_filtered_items()
        self.assertEqual(self.control._selection, 0)

    def test_preferred_height(self):
        height = self.control.preferred_height(100, 10, False, None)
        self.assertEqual(height, min(10, len(self.items) + 1))

    def test_create_content_first_line_is_search(self):
        content = self.control.create_content(50, 10)
        line = content.get_line(0)
        self.assertEqual(line[0][0], 'class:filter')
        self.assertIn('Search:', line[0][1])

    def test_create_content_no_results_message(self):
        self.control._filter_text = 'xyz'
        self.control._update_filtered_items()
        content = self.control.create_content(50, 10)
        line = content.get_line(1)
        self.assertEqual(line[0][0], 'class:no-results')

    def test_custom_no_results_message(self):
        msg = 'No AWS accounts match your search'
        control = FilterableSelectionMenuControl(
            self.items, no_results_message=msg
        )
        self.assertEqual(control._no_results_message, msg)
        control._filter_text = 'xyz'
        control._update_filtered_items()
        content = control.create_content(50, 10)
        line = content.get_line(1)
        self.assertIn(msg, line[0][1])

    def test_key_bindings_registered(self):
        kb = self.control.get_key_bindings()
        self.assertIsInstance(kb, KeyBindings)
        key_names = [str(b.keys[0]) for b in kb.bindings]
        self.assertIn('Keys.Up', key_names)
        self.assertIn('Keys.Down', key_names)
        self.assertIn('Keys.ControlH', key_names)  # backspace
        self.assertIn('Keys.ControlU', key_names)

    def test_empty_items(self):
        control = FilterableSelectionMenuControl([])
        self.assertEqual(control._filtered_items, [])
        control._filter_text = 'test'
        control._update_filtered_items()
        self.assertEqual(control._filtered_items, [])
        self.assertGreater(control.preferred_width(100), 0)


class TestSelectMenuFilterArg(unittest.TestCase):
    @patch('awscli.customizations.wizard.ui.selectmenu.Application')
    def test_enable_filter_true(self, mock_app_class):
        mock_app = MagicMock()
        mock_app_class.return_value = mock_app
        mock_app.run.return_value = 'item1'
        result = select_menu(['item1', 'item2'], enable_filter=True)
        mock_app_class.assert_called_once()
        self.assertEqual(result, 'item1')

    @patch('awscli.customizations.wizard.ui.selectmenu.Application')
    def test_enable_filter_false(self, mock_app_class):
        mock_app = MagicMock()
        mock_app_class.return_value = mock_app
        mock_app.run.return_value = 'item1'
        result = select_menu(['item1', 'item2'], enable_filter=False)
        mock_app_class.assert_called_once()
        self.assertEqual(result, 'item1')


class TestFilteringWithDisplayFormat(unittest.TestCase):
    def test_filter_by_display_format_content(self):
        accounts = [
            {'accountId': '111111111111', 'accountName': 'Production'},
            {'accountId': '222222222222', 'accountName': 'Development'},
        ]

        def display(a):
            return f"{a['accountName']} ({a['accountId']})"

        control = FilterableSelectionMenuControl(
            accounts, display_format=display
        )

        control._filter_text = 'prod'
        control._update_filtered_items()
        self.assertEqual(len(control._filtered_items), 1)
        self.assertEqual(
            control._filtered_items[0]['accountName'], 'Production'
        )

        control._filter_text = '2222'
        control._update_filtered_items()
        self.assertEqual(len(control._filtered_items), 1)
        self.assertEqual(
            control._filtered_items[0]['accountName'], 'Development'
        )
