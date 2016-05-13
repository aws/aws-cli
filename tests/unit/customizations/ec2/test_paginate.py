# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from awscli.customizations.ec2.paginate import set_max_results_default
from awscli.customizations.ec2.paginate import DEFAULT_MAX_RESULTS
from awscli.testutils import unittest


class TestSetMaxResult(unittest.TestCase):
    def setUp(self):
        self.parsed_args = mock.Mock()
        self.parsed_globals = mock.Mock()

        self.parsed_args.max_results = None
        self.parsed_args.page_size = None
        self.parsed_globals.paginate = True

    def test_default_is_set(self):
        set_max_results_default(self.parsed_args, self.parsed_globals)
        self.assertEqual(self.parsed_args.page_size, DEFAULT_MAX_RESULTS)

    def test_page_size_isnt_overwritten(self):
        page_size = DEFAULT_MAX_RESULTS - 10
        self.parsed_args.page_size = page_size
        set_max_results_default(self.parsed_args, self.parsed_globals)
        self.assertEqual(self.parsed_args.page_size, page_size)

    def test_max_results_isnt_overwritten(self):
        max_results = DEFAULT_MAX_RESULTS - 10
        self.parsed_args.max_results = max_results
        set_max_results_default(self.parsed_args, self.parsed_globals)
        self.assertEqual(self.parsed_args.max_results, max_results)
        self.assertEqual(self.parsed_args.page_size, None)

    def test_no_paginate_disables_default(self):
        self.parsed_globals.paginate = False
        set_max_results_default(self.parsed_args, self.parsed_globals)
        self.assertEqual(self.parsed_args.page_size, None)

    def test_only_applies_if_page_size_is_present(self):
        del self.parsed_args.page_size
        set_max_results_default(self.parsed_args, self.parsed_globals)
        self.assertFalse(hasattr(self.parsed_args, 'page_size'))
