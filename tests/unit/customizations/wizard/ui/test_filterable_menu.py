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

import pytest
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.layout.containers import Window, to_container
from prompt_toolkit.layout.controls import BufferControl

from awscli.customizations.wizard.ui.selectmenu import (
    FilterableSelectionMenuControl,
    SelectionMenuControl,
    select_menu,
)

UP = '\x1b[A'
DOWN = '\x1b[B'
ENTER = '\r'
BACKSPACE = '\x7f'
CTRL_U = '\x15'


def _walk_windows(container):
    container = to_container(container)
    yield container
    for child in container.get_children():
        yield from _walk_windows(child)


def _find_controls(container, control_type):
    return [
        window.content
        for window in _walk_windows(container)
        if isinstance(window, Window)
        and isinstance(window.content, control_type)
    ]


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

    def _filter(self, text):
        self.control.filter_buffer.text = text

    def _names(self):
        return [item['name'] for item in self.control._get_items()]

    def test_no_filter_shows_all_items(self):
        self.assertEqual(self.control.filter_text, '')
        self.assertEqual(self.control._get_items(), self.items)
        self.assertEqual(self.control._selection, 0)

    def test_default_no_results_message(self):
        self.assertEqual(
            self.control._no_results_message,
            FilterableSelectionMenuControl.DEFAULT_NO_RESULTS_MESSAGE,
        )

    def test_filter_matching(self):
        self._filter('prod')
        self.assertEqual(self._names(), ['Production'])

    def test_filter_no_match(self):
        self._filter('xyz')
        self.assertEqual(self.control._get_items(), [])
        self.assertIsNone(self.control.selected_item())

    def test_filter_is_case_insensitive(self):
        self._filter('DEV')
        self.assertEqual(self._names(), ['Development'])

    def test_filter_partial_match(self):
        self._filter('ing')
        self.assertEqual(self._names(), ['Staging', 'Testing'])

    def test_filter_uses_display_format(self):
        # 'stage' only appears in the formatted text, not in the name.
        self._filter('stage')
        self.assertEqual(self._names(), ['Staging'])

    def test_clearing_filter_restores_all_items(self):
        self._filter('prod')
        self._filter('')
        self.assertEqual(self.control._get_items(), self.items)

    def test_surrounding_whitespace_is_ignored(self):
        self._filter('  prod  ')
        self.assertEqual(self._names(), ['Production'])

    def test_filter_supports_non_ascii_text(self):
        items = ['東京アカウント', 'osaka-account', 'café-account']
        control = FilterableSelectionMenuControl(items)
        control.filter_buffer.text = '東京'
        self.assertEqual(control._get_items(), ['東京アカウント'])
        control.filter_buffer.text = 'café'
        self.assertEqual(control._get_items(), ['café-account'])

    def test_filter_supports_pasted_text(self):
        # A bracketed paste arrives as a single insert_text call.
        self.control.filter_buffer.insert_text('Development')
        self.assertEqual(self._names(), ['Development'])

    def test_selection_is_preserved_when_item_still_matches(self):
        self.control._selection = 2  # Staging
        self._filter('ing')
        self.assertEqual(
            self.control.selected_item()['name'],
            'Staging',
        )

    def test_selection_resets_when_item_filtered_out(self):
        self.control._selection = 3  # Testing
        self._filter('prod')
        self.assertEqual(self.control._selection, 0)
        self.assertEqual(self.control.selected_item()['name'], 'Production')

    def test_move_selection_wraps_within_filtered_items(self):
        self._filter('ing')
        self.control.move_selection(1)
        self.assertEqual(self.control.selected_item()['name'], 'Testing')
        self.control.move_selection(1)
        self.assertEqual(self.control.selected_item()['name'], 'Staging')
        self.control.move_selection(-1)
        self.assertEqual(self.control.selected_item()['name'], 'Testing')

    def test_move_selection_is_a_noop_without_matches(self):
        self._filter('xyz')
        self.control.move_selection(1)
        self.assertIsNone(self.control.selected_item())

    def test_accepts_callable_items(self):
        control = FilterableSelectionMenuControl(lambda: ['alpha', 'beta'])
        self.assertEqual(control._get_items(), ['alpha', 'beta'])
        control.filter_buffer.text = 'al'
        self.assertEqual(control._get_items(), ['alpha'])
        self.assertGreater(control.preferred_width(80), 0)

    def test_accepts_external_filter_buffer(self):
        buffer = Buffer(multiline=False)
        control = FilterableSelectionMenuControl(
            self.items,
            display_format=self.display_format,
            filter_buffer=buffer,
        )
        buffer.text = 'dev'
        self.assertEqual(
            [item['name'] for item in control._get_items()], ['Development']
        )

    def test_content_renders_items_without_a_search_line(self):
        content = self.control.create_content(50, 10)
        self.assertEqual(content.line_count, len(self.items))
        self.assertIn('Production', content.get_line(0)[0][1])

    def test_content_renders_no_results_message(self):
        self._filter('xyz')
        content = self.control.create_content(50, 10)
        self.assertEqual(content.line_count, 1)
        style, text = content.get_line(0)[0]
        self.assertEqual(style, 'class:no-results')
        self.assertIn(
            FilterableSelectionMenuControl.DEFAULT_NO_RESULTS_MESSAGE, text
        )

    def test_custom_no_results_message(self):
        message = 'No AWS accounts match your search'
        control = FilterableSelectionMenuControl(
            self.items, no_results_message=message
        )
        control.filter_buffer.text = 'xyz'
        content = control.create_content(50, 10)
        self.assertIn(message, content.get_line(0)[0][1])

    def test_preferred_height_reserves_a_line_for_no_results(self):
        self._filter('xyz')
        self.assertEqual(self.control.preferred_height(50, 10, False, None), 1)

    def test_preferred_height_tracks_filtered_items(self):
        self._filter('ing')
        self.assertEqual(self.control.preferred_height(50, 10, False, None), 2)

    def test_preferred_width_fits_no_results_message(self):
        message = 'a much longer no results message than any item'
        control = FilterableSelectionMenuControl(
            ['a', 'b'], no_results_message=message
        )
        control.filter_buffer.text = 'xyz'
        self.assertGreaterEqual(control.preferred_width(200), len(message))

    def test_empty_items(self):
        control = FilterableSelectionMenuControl([])
        self.assertEqual(control._get_items(), [])
        self.assertIsNone(control.selected_item())
        self.assertGreater(control.preferred_width(100), 0)

    def test_key_bindings_only_handle_navigation(self):
        kb = self.control.get_key_bindings()
        bound = {str(key) for binding in kb.bindings for key in binding.keys}
        self.assertEqual(bound, {'Keys.Up', 'Keys.Down', 'Keys.ControlM'})

    def test_enter_exits_with_selected_item(self):
        kb = self.control.get_key_bindings()
        enter = next(
            b for b in kb.bindings if str(b.keys[0]) == 'Keys.ControlM'
        )
        self._filter('dev')
        event = MagicMock()
        enter.handler(event)
        event.app.exit.assert_called_once_with(
            result=self.items[1],
        )

    def test_enter_does_nothing_without_matches(self):
        kb = self.control.get_key_bindings()
        enter = next(
            b for b in kb.bindings if str(b.keys[0]) == 'Keys.ControlM'
        )
        self._filter('xyz')
        event = MagicMock()
        enter.handler(event)
        event.app.exit.assert_not_called()


class TestBaseSelectionMenuControlUnchanged(unittest.TestCase):
    def test_no_filter_buffer_on_base_control(self):
        control = SelectionMenuControl(['a', 'b'])
        self.assertFalse(hasattr(control, 'filter_buffer'))

    def test_preferred_width_handles_empty_items(self):
        control = SelectionMenuControl([])
        self.assertEqual(control.preferred_width(100), control.MIN_WIDTH)


class TestSelectMenuLayout(unittest.TestCase):
    def _run_select_menu(self, **kwargs):
        with patch(
            'awscli.customizations.wizard.ui.selectmenu.Application'
        ) as mock_app_class:
            mock_app_class.return_value.run.return_value = 'result'
            result = select_menu(['item1', 'item2'], **kwargs)
        _, app_kwargs = mock_app_class.call_args
        return result, app_kwargs['layout']

    def test_filter_enabled_adds_search_buffer_bound_to_the_menu(self):
        result, layout = self._run_select_menu(enable_filter=True)
        self.assertEqual(result, 'result')
        buffer_controls = _find_controls(layout.container, BufferControl)
        menu_controls = _find_controls(
            layout.container, FilterableSelectionMenuControl
        )
        self.assertEqual(len(buffer_controls), 1)
        self.assertEqual(len(menu_controls), 1)
        self.assertIs(
            buffer_controls[0].buffer, menu_controls[0].filter_buffer
        )

    def test_filter_enabled_focuses_the_search_buffer(self):
        _, layout = self._run_select_menu(enable_filter=True)
        self.assertIsInstance(layout.current_control, BufferControl)

    def test_filter_disabled_has_no_search_buffer(self):
        result, layout = self._run_select_menu(enable_filter=False)
        self.assertEqual(result, 'result')
        self.assertEqual(_find_controls(layout.container, BufferControl), [])
        self.assertEqual(
            len(_find_controls(layout.container, SelectionMenuControl)), 1
        )

    def test_filter_enabled_reserves_an_extra_line(self):
        _, filtered_layout = self._run_select_menu(enable_filter=True)
        _, plain_layout = self._run_select_menu(enable_filter=False)
        filtered_height = to_container(
            filtered_layout.container
        ).content.height
        plain_height = to_container(plain_layout.container).content.height
        self.assertEqual(filtered_height.max, plain_height.max + 1)

    def test_callable_items_are_resolved(self):
        with patch(
            'awscli.customizations.wizard.ui.selectmenu.Application'
        ) as mock_app_class:
            mock_app_class.return_value.run.return_value = 'result'
            select_menu(lambda: ['item1', 'item2'], enable_filter=True)
        _, app_kwargs = mock_app_class.call_args
        menu_control = _find_controls(
            app_kwargs['layout'].container, FilterableSelectionMenuControl
        )[0]
        self.assertEqual(menu_control._get_items(), ['item1', 'item2'])


class TestSelectMenuFilteringEndToEnd:
    """Drive the real application with key presses from a pipe input."""

    ACCOUNTS = [
        {'accountId': '111111111111', 'accountName': 'Production'},
        {'accountId': '222222222222', 'accountName': 'Development'},
        {'accountId': '333333333333', 'accountName': '東京アカウント'},
        {'accountId': '444444444444', 'accountName': 'Staging'},
    ]

    @staticmethod
    def _display(account):
        return f"{account['accountName']} ({account['accountId']})"

    def _select_account(self, app_session, keys, **kwargs):
        app_session.input.send_text(keys)
        return select_menu(
            self.ACCOUNTS,
            display_format=self._display,
            enable_filter=True,
            **kwargs,
        )

    @pytest.mark.parametrize(
        'keys,expected_name',
        [
            # Enter with no filter selects the first item.
            (ENTER, 'Production'),
            # Typing narrows the list down to a single match.
            ('Devel' + ENTER, 'Development'),
            # Filtering is case insensitive.
            ('devel' + ENTER, 'Development'),
            # The account id is searchable through the display format.
            ('4444' + ENTER, 'Staging'),
            # Non-ascii filter text is supported.
            ('東京' + ENTER, '東京アカウント'),
            # Backspace widens the filter again.
            ('Devxx' + BACKSPACE + BACKSPACE + ENTER, 'Development'),
            # Ctrl-U discards the filter text.
            ('Devel' + CTRL_U + '東京' + ENTER, '東京アカウント'),
            # A space is filter text rather than a selection key.
            ('Production (1111' + ENTER, 'Production'),
            # Arrow keys move within the filtered list.
            ('ing' + DOWN + ENTER, 'Staging'),
            # Arrow keys wrap around the unfiltered list.
            (UP + ENTER, 'Staging'),
        ],
    )
    def test_filtering_selects_expected_account(
        self, ptk_app_session, keys, expected_name
    ):
        selected = self._select_account(ptk_app_session, keys)
        assert selected['accountName'] == expected_name

    def test_pasted_text_filters_the_list(self, ptk_app_session):
        # A bracketed paste is delivered as a single key press.
        paste = '\x1b[200~Development\x1b[201~'
        selected = self._select_account(ptk_app_session, paste + ENTER)
        assert selected['accountName'] == 'Development'

    def test_enter_is_ignored_while_nothing_matches(self, ptk_app_session):
        keys = 'zzzz' + ENTER + BACKSPACE * 4 + 'Staging' + ENTER
        selected = self._select_account(
            ptk_app_session,
            keys,
            no_results_message='No matching accounts found',
        )
        assert selected['accountName'] == 'Staging'

    def test_selection_is_kept_when_filter_is_cleared(self, ptk_app_session):
        selected = self._select_account(
            ptk_app_session, 'Devel' + CTRL_U + ENTER
        )
        assert selected['accountName'] == 'Development'

    def test_menu_without_filter_ignores_typed_characters(
        self, ptk_app_session
    ):
        ptk_app_session.input.send_text('Staging' + DOWN + ENTER)
        selected = select_menu(self.ACCOUNTS, display_format=self._display)
        assert selected['accountName'] == 'Development'

    def test_callable_items_are_filterable(self, ptk_app_session):
        ptk_app_session.input.send_text('beta' + ENTER)
        assert (
            select_menu(lambda: ['alpha', 'beta'], enable_filter=True)
            == 'beta'
        )
