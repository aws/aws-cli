#!/usr/bin/env python
# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


class TestPutMetricData(BaseAWSCommandParamsTest):
    maxDiff = None

    prefix = 'cloudwatch put-metric-data '

    expected_output = {
        'MetricData.member.1.MetricName': 'FreeMemoryBytes',
        'MetricData.member.1.Timestamp': '2013-08-22T10:58:12.283000+00:00',
        'MetricData.member.1.Unit': 'Bytes',
        'MetricData.member.1.Value': '9130160128',
        'Namespace': '"Foo/Bar"'
    }

    def test_using_json(self):
        args = ('--namespace "Foo/Bar" '
                '--metric-data [{"MetricName":"FreeMemoryBytes",'
                '"Unit":"Bytes",'
                '"Timestamp":"2013-08-22T10:58:12.283Z",'
                '"Value":9130160128}]')
        cmdline = self.prefix + args
        self.assert_params_for_cmd(cmdline, self.expected_output)

    def test_using_promoted_params(self):
        # This is equivalent to the json version in test_using_json
        # above.
        args = ('--namespace "Foo/Bar" '
                '--metric-name FreeMemoryBytes '
                '--unit Bytes '
                '--timestamp 2013-08-22T10:58:12.283Z '
                '--value 9130160128')
        cmdline = self.prefix + args
        self.assert_params_for_cmd(cmdline, self.expected_output)
