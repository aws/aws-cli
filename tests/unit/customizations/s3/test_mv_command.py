#!/usr/bin/env python
# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.testutils import BaseAWSCommandParamsTest, FileCreator
import re

import mock
from awscli.compat import six


class TestMvCommand(BaseAWSCommandParamsTest):

    prefix = 's3 mv '

    def setUp(self):
        super(TestMvCommand, self).setUp()
        self.files = FileCreator()

    def tearDown(self):
        super(TestMvCommand, self).tearDown()
        self.files.remove_all()

    def test_cant_mv_object_onto_itself(self):
        cmdline = '%s s3://bucket/key s3://bucket/key' % self.prefix
        stderr = self.run_cmd(cmdline, expected_rc=255)[1]
        self.assertIn('Cannot mv a file onto itself', stderr)

    def test_cant_mv_object_with_implied_name(self):
        # The "key" key name is implied in the dst argument.
        cmdline = '%s s3://bucket/key s3://bucket/' % self.prefix
        stderr = self.run_cmd(cmdline, expected_rc=255)[1]
        self.assertIn('Cannot mv a file onto itself', stderr)

    def test_website_redirect_ignore_paramfile(self):
        full_path = self.files.create_file('foo.txt', 'mycontent')
        cmdline = '%s %s s3://bucket/key.txt --website-redirect %s' % \
            (self.prefix, full_path, 'http://someserver')
        self.parsed_responses = [{'ETag': '"c8afdb36c52cf4727836669019e69222"'}]
        self.run_cmd(cmdline, expected_rc=0)
        self.assertEqual(self.operations_called[0][0].name, 'PutObject')
        # Make sure that the specified web address is used as opposed to the
        # contents of the web address.
        self.assertEqual(
            self.operations_called[0][1]['website_redirect_location'],
            'http://someserver'
        )


if __name__ == "__main__":
    unittest.main()
