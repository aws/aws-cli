# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import mock

from awscli.testutils import unittest
from awscli.autoprompt.filters import (
    search_input_has_focus, help_section_visible, doc_window_has_focus,
    doc_section_visible, is_history_mode, is_multi_column, is_one_column,
    input_buffer_has_focus
)


class TestFilters(unittest.TestCase):

    @mock.patch('awscli.autoprompt.filters.get_app')
    def test_search_input_has_focus(self, get_app):
        app = mock.Mock()
        app.layout.current_window.style = 'class:search-toolbar'
        get_app.return_value = app
        self.assertTrue(search_input_has_focus())

    @mock.patch('awscli.autoprompt.filters.get_app')
    def test_help_section_visible(self, get_app):
        app = mock.Mock()
        app.show_help = True
        get_app.return_value = app
        self.assertTrue(help_section_visible())

    @mock.patch('awscli.autoprompt.filters.get_app')
    def test_doc_window_has_focus(self, get_app):
        app = mock.Mock()
        app.current_buffer.name = 'doc_buffer'
        get_app.return_value = app
        self.assertTrue(doc_window_has_focus())

    @mock.patch('awscli.autoprompt.filters.get_app')
    def test_doc_section_visible(self, get_app):
        app = mock.Mock()
        app.show_doc = True
        get_app.return_value = app
        self.assertTrue(doc_section_visible())

    @mock.patch('awscli.autoprompt.filters.get_app')
    def test_is_history_mode(self, get_app):
        buffer = mock.Mock()
        buffer.history_mode = True
        app = mock.Mock()
        app.current_buffer = buffer
        app.current_buffer.name = 'input_buffer'
        get_app.return_value = app
        self.assertTrue(is_history_mode())

    @mock.patch('awscli.autoprompt.filters.get_app')
    def test_is_multi_column(self, get_app):
        app = mock.Mock()
        app.multi_column = True
        get_app.return_value = app
        self.assertTrue(is_multi_column())

    @mock.patch('awscli.autoprompt.filters.get_app')
    def test_is_one_column(self, get_app):
        app = mock.Mock()
        app.multi_column = False
        get_app.return_value = app
        self.assertTrue(is_one_column())

    @mock.patch('awscli.autoprompt.filters.get_app')
    def test_input_buffer_has_focus(self, get_app):
        app = mock.Mock()
        app.current_buffer.name = 'input_buffer'
        get_app.return_value = app
        self.assertTrue(input_buffer_has_focus())
