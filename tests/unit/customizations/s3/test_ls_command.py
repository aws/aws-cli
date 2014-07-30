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
from awscli.testutils import BaseAWSCommandParamsTest
from dateutil import parser, tz

class TestLSCommand(BaseAWSCommandParamsTest):

    def test_operations_used_in_recursive_list(self):
        time_utc = "2014-01-09T20:45:49.000Z"
        self.parsed_responses = [{"CommonPrefixes": [], "Contents": [
            {"Key": "foo/bar.txt", "Size": 100,
             "LastModified": time_utc}]}]
        stdout, _, _ = self.run_cmd('s3 ls s3://bucket/ --recursive', expected_rc=0)
        call_args = self.operations_called[0][1]
        # We should not be calling the args with any delimiter because we
        # want a recursive listing.
        self.assertEqual(call_args['prefix'], '')
        self.assertEqual(call_args['bucket'], 'bucket')
        self.assertNotIn('delimiter', call_args)
        # Time is stored in UTC timezone, but the actual time displayed
        # is specific to your tzinfo, so shift the timezone to your local's.
        time_local = parser.parse(time_utc).astimezone(tz.tzlocal())
        self.assertEqual(
            stdout, '%s        100 foo/bar.txt\n'%time_local.strftime('%Y-%m-%d %H:%M:%S'))


if __name__ == "__main__":
    unittest.main()
