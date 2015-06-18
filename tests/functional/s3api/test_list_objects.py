#!/usr/bin/env python
# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.testutils import BaseAWSCommandParamsTest


class TestListObjects(BaseAWSCommandParamsTest):

    prefix = 's3api list-objects'

    def setUp(self):
        super(TestListObjects, self).setUp()
        self.parsed_response = {'Contents': []}

    def test_simple(self):
        cmdline = self.prefix
        cmdline += ' --bucket mybucket'
        self.assert_params_for_cmd(cmdline, {'Bucket': 'mybucket'})

    def test_max_items(self):
        cmdline = self.prefix
        cmdline += ' --bucket mybucket'
        # The max-items is a customization and therefore won't
        # show up in the result params.
        cmdline += ' --max-items 100'
        self.assert_params_for_cmd(cmdline, {'Bucket': 'mybucket'})

    def test_page_size(self):
        cmdline = self.prefix
        cmdline += ' --bucket mybucket'
        # The max-items is a customization and therefore won't
        # show up in the result params.
        cmdline += ' --page-size 100'
        self.assert_params_for_cmd(cmdline, {'Bucket': 'mybucket',
                                              'MaxKeys': 100})

    def test_starting_token(self):
        # We don't need to test this in depth because botocore
        # tests this.  We just want to make sure this is hooked up
        # properly.
        cmdline = self.prefix
        cmdline += ' --bucket mybucket'
        cmdline += ' --starting-token foo___2'
        self.assert_params_for_cmd(cmdline, {'Bucket': 'mybucket',
                                              'Marker': 'foo'})

    def test_no_paginate(self):
        cmdline = self.prefix
        cmdline += ' --bucket mybucket --no-paginate'
        self.assert_params_for_cmd(cmdline, {'Bucket': 'mybucket'})

    def test_max_keys_can_be_specified(self):
        cmdline = self.prefix
        # --max-keys is a hidden argument and not documented,
        # but for back-compat reasons if a user specifies this,
        # we will automatically see this and turn auto-pagination off.
        cmdline += ' --bucket mybucket --max-keys 1'
        self.assert_params_for_cmd(cmdline, {'Bucket': 'mybucket',
                                              'MaxKeys': 1})
        self.assertEqual(len(self.operations_called), 1)
        self.assertEqual(len(self.operations_called), 1)
        self.assertEqual(self.operations_called[0][0].name, 'ListObjects')
