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
from tests.unit import BaseAWSCommandParamsTest


class TestLSCommand(BaseAWSCommandParamsTest):

    def test_operations_used_in_recursive_list(self):
        self.parsed_responses = [{"CommonPrefixes": [], "Contents": [
            {"Key": "foo/bar.txt", "Size": 100,
             "LastModified": "2014-01-09T20:45:49.000Z"}]}]
        stdout, _, _ = self.run_cmd('s3 ls s3://bucket/ --recursive', expected_rc=0)
        call_args = self.operations_called[0][1]
        # We should not be calling the args with any delimiter because we
        # want a recursive listing.
        self.assertEqual(call_args['prefix'], '')
        self.assertEqual(call_args['bucket'], 'bucket')
        self.assertNotIn('delimiter', call_args)
        # Using assertRegexpMatches because the actual time displayed
        # is specific to your tzinfo.
        self.assertRegexpMatches(
            stdout, '2014-01-09 \d{2}:\d{2}:\d{2}        100 foo/bar.txt\n')
