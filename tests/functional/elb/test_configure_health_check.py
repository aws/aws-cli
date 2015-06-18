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


class TestConfigureHealthCheck(BaseAWSCommandParamsTest):

    prefix = 'elb configure-health-check'

    def test_shorthand_basic(self):
        cmdline = self.prefix
        cmdline += ' --load-balancer-name my-lb'
        cmdline += (' --health-check Target=HTTP:80/weather/us/wa/seattle,'
                    'Interval=300,Timeout=60,UnhealthyThreshold=5,'
                    'HealthyThreshold=9')
        result = {
            'HealthCheck': {
                'HealthyThreshold': 9,
                'Interval': 300,
                'Target': 'HTTP:80/weather/us/wa/seattle',
                'Timeout': 60,
                'UnhealthyThreshold': 5},
            'LoadBalancerName': 'my-lb'}
        self.assert_params_for_cmd(cmdline, result)

    def test_json(self):
        cmdline = self.prefix
        cmdline += ' --load-balancer-name my-lb '
        cmdline += ('--health-check {"Target":"HTTP:80/weather/us/wa/seattle'
                    '?a=b","Interval":300,"Timeout":60,'
                    '"UnhealthyThreshold":5,"HealthyThreshold":9}')
        result = {
            'HealthCheck': {
                'HealthyThreshold': 9,
                'Interval': 300,
                'Target': 'HTTP:80/weather/us/wa/seattle?a=b',
                'Timeout': 60,
                'UnhealthyThreshold': 5},
            'LoadBalancerName': 'my-lb'}
        self.assert_params_for_cmd(cmdline, result)

    def test_shorthand_with_multiple_equals_for_value(self):
        cmdline = self.prefix
        cmdline += ' --load-balancer-name my-lb'
        cmdline += (
            ' --health-check Target="HTTP:80/weather/us/wa/seattle?a=b"'
            ',Interval=300,Timeout=60,UnhealthyThreshold=5,'
            'HealthyThreshold=9'
        )
        result = {
            'HealthCheck': {
                'HealthyThreshold': 9,
                'Interval': 300,
                'Target': 'HTTP:80/weather/us/wa/seattle?a=b',
                'Timeout': 60,
                'UnhealthyThreshold': 5},
            'LoadBalancerName': 'my-lb'}
        self.assert_params_for_cmd(cmdline, result)
