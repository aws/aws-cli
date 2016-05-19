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
import base64
import json


class TestListObjects(BaseAWSCommandParamsTest):

    prefix = 's3api list-objects'

    def setUp(self):
        super(TestListObjects, self).setUp()
        self.parsed_response = {'Contents': []}

    def test_simple(self):
        cmdline = self.prefix
        cmdline += ' --bucket mybucket'
        self.assert_params_for_cmd(cmdline, {'Bucket': 'mybucket',
                                             'EncodingType': 'url'})

    def test_max_items(self):
        cmdline = self.prefix
        cmdline += ' --bucket mybucket'
        # The max-items is a customization and therefore won't
        # show up in the result params.
        cmdline += ' --max-items 100'
        self.assert_params_for_cmd(cmdline, {'Bucket': 'mybucket',
                                             'EncodingType': 'url'})

    def test_page_size(self):
        cmdline = self.prefix
        cmdline += ' --bucket mybucket'
        # The max-items is a customization and therefore won't
        # show up in the result params.
        cmdline += ' --page-size 100'
        self.assert_params_for_cmd(cmdline, {'Bucket': 'mybucket',
                                             'MaxKeys': 100,
                                             'EncodingType': 'url'})

    def test_starting_token(self):
        # We don't need to test this in depth because botocore
        # tests this.  We just want to make sure this is hooked up
        # properly.
        cmdline = self.prefix
        cmdline += ' --bucket mybucket'
        token = {"Marker": "foo"}
        token = base64.b64encode(json.dumps(token).encode('utf-8'))
        token = token.decode('utf-8')
        cmdline += ' --starting-token %s' % token
        self.assert_params_for_cmd(cmdline, {'Bucket': 'mybucket',
                                             'Marker': 'foo',
                                             'EncodingType': 'url'})

    def test_no_paginate(self):
        cmdline = self.prefix
        cmdline += ' --bucket mybucket --no-paginate'
        self.assert_params_for_cmd(cmdline, {'Bucket': 'mybucket',
                                             'EncodingType': 'url'})

    def test_max_keys_can_be_specified(self):
        cmdline = self.prefix
        # --max-keys is a hidden argument and not documented,
        # but for back-compat reasons if a user specifies this,
        # we will automatically see this and turn auto-pagination off.
        cmdline += ' --bucket mybucket --max-keys 1'
        self.assert_params_for_cmd(cmdline, {'Bucket': 'mybucket',
                                             'MaxKeys': 1,
                                             'EncodingType': 'url'})
        self.assertEqual(len(self.operations_called), 1)
        self.assertEqual(len(self.operations_called), 1)
        self.assertEqual(self.operations_called[0][0].name, 'ListObjects')

    def test_pagination_params_cannot_be_supplied_with_no_paginate(self):
        cmdline = self.prefix + ' --bucket mybucket --no-paginate ' \
                                '--max-items 100'
        self.assert_params_for_cmd(
            cmdline, expected_rc=255,
            stderr_contains="Error during pagination: Cannot specify "
                            "--no-paginate along with pagination arguments: "
                            "--max-items")
