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
import re
import copy

from awscli.testutils import BaseAWSCommandParamsTest


# file is gone in python3, so instead IOBase must be used.
# Given this test module is the only place that cares about
# this type check, we do the check directly in this test module.
try:
    file_type = file
except NameError:
    import io
    file_type = io.IOBase


TAGSET = """{"TagSet":[{"Key":"key1","Value":"value1"},{"Key":"key2","Value":"value2"}]}"""


class TestPutBucketTagging(BaseAWSCommandParamsTest):

    prefix = 's3api put-bucket-tagging'

    def setUp(self):
        super(TestPutBucketTagging, self).setUp()
        self.payload = None

    def test_simple(self):
        cmdline = self.prefix
        cmdline += ' --bucket mybucket'
        cmdline += ' --tagging %s' % TAGSET
        expected = {
            'Bucket': 'mybucket',
            'Tagging': {
                'TagSet': [
                    {'Key': 'key1', 'Value': 'value1'},
                    {'Key': 'key2', 'Value': 'value2'},
                ]
            }
        }
        self.assert_params_for_cmd(cmdline, expected)


if __name__ == "__main__":
    unittest.main()
