# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.testutils import unittest, mock

from awscli.autocomplete.completer import CompletionResult

from awscli.autocomplete import filters


class TestFilters(unittest.TestCase):
    def setUp(self):
        self.completions = [
            CompletionResult('version'),
            CompletionResult('foo', display_text='Help text'),
            CompletionResult('various text')
        ]

    def _assert_filter_response_as_expected(
            self, response_filter, user_input, expected_output):
        output = response_filter(user_input, self.completions)
        self.assertEqual(output, expected_output)

    def test_fuzzy_filter(self):
        self._assert_filter_response_as_expected(
            filters.fuzzy_filter, 'ro',
            [
                CompletionResult('various text'),
                CompletionResult('version')
            ]
        )
        self._assert_filter_response_as_expected(
            filters.fuzzy_filter, 'et',
            [
                CompletionResult('various text'),
                CompletionResult('foo', display_text='Help text'),
            ]
        )
        self._assert_filter_response_as_expected(
            filters.fuzzy_filter, 'vs',
            [
                CompletionResult('version'),
                CompletionResult('various text'),
            ]
        )

    def test_startswith_filter(self):
        self._assert_filter_response_as_expected(
            filters.startswith_filter, 'He',
            [
                CompletionResult('foo', display_text='Help text'),
            ]
        )
        self._assert_filter_response_as_expected(
            filters.startswith_filter, 'v',
            [
                CompletionResult('version'),
                CompletionResult('various text'),
            ]
        )
