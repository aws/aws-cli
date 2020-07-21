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
import decimal

from awscli.testutils import BaseAWSCommandParamsTest


class TestPutMetricData(BaseAWSCommandParamsTest):
    maxDiff = None

    prefix = 'cloudwatch put-metric-data '

    expected_output = {
        'MetricData': [
            {'MetricName': 'FreeMemoryBytes',
             'Unit': 'Bytes',
             'Timestamp': '2013-08-22T10:58:12.283Z',
             'Value': decimal.Decimal("9130160128")}],
        'Namespace': '"Foo/Bar"'}

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

    def test_using_shorthand_syntax(self):
        args = (
            '--metric-name PageViewCount '
            '--namespace MyService '
            '--statistic-value Sum=11,Minimum=2,Maximum=5,SampleCount=3 '
            '--timestamp 2014-02-14T12:00:00.000Z'
        )
        cmdline = self.prefix + args
        expected = {
            'MetricData': [
                {'MetricName': 'PageViewCount',
                 'StatisticValues': {
                     'Maximum': decimal.Decimal('5'),
                     'Minimum': decimal.Decimal('2'),
                     'SampleCount': decimal.Decimal('3'),
                     'Sum': decimal.Decimal('11')},
                 'Timestamp': '2014-02-14T12:00:00.000Z'}
            ],
            'Namespace': 'MyService'
        }
        self.assert_params_for_cmd(cmdline, expected)

    def test_using_storage_resolution(self):
        args = (
            '--metric-name Foo '
            '--namespace Bar '
            '--value 5 '
            '--storage-resolution 1 '
        )
        cmdline = self.prefix + args
        expected = {
            'MetricData': [{
                'MetricName': 'Foo',
                'Value': decimal.Decimal('5'),
                'StorageResolution': 1
            }],
            'Namespace': 'Bar'
        }
        self.assert_params_for_cmd(cmdline, expected)
