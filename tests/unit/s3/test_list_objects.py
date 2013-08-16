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
from tests.unit import BaseAWSCommandParamsTest
import re
import httpretty


class TestListObjects(BaseAWSCommandParamsTest):

    prefix = 's3api list-objects'

    def register_uri(self):
        body = """<ListBucketResult xmlns="http://s3.amazonaws.com/">
        </ListBucketResult>
        """
        httpretty.register_uri(httpretty.GET, re.compile('.*'), body=body)

    def test_simple(self):
        cmdline = self.prefix
        cmdline += ' --bucket mybucket'
        result = {'uri_params': {'Bucket': 'mybucket'},
                  'headers': {},
                  'payload': None}
        self.assert_params_for_cmd(cmdline, result)

    def test_maxkeys(self):
        cmdline = self.prefix
        cmdline += ' --bucket mybucket'
        # The max-items is a customization and therefore won't
        # show up in the result params.
        cmdline += ' --max-items 100'
        result = {'uri_params': {'Bucket': 'mybucket'},
                  'headers': {},
                  'payload': None}
        self.assert_params_for_cmd(cmdline, result)

    def test_starting_token(self):
        # We don't need to test this in depth because botocore
        # tests this.  We just want to make sure this is hooked up
        # properly.
        cmdline = self.prefix
        cmdline += ' --bucket mybucket'
        # The max-items is a customization and therefore won't
        # show up in the result params.
        cmdline += ' --starting-token foo___2'
        result = {'uri_params': {'Bucket': 'mybucket', 'Marker': 'foo'},
                  'headers': {},
                  'payload': None}
        self.assert_params_for_cmd(cmdline, result)


if __name__ == "__main__":
    unittest.main()
