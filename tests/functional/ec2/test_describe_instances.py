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


class TestDescribeInstances(BaseAWSCommandParamsTest):

    prefix = 'ec2 describe-instances'

    def test_no_params(self):
        cmdline = self.prefix
        result = {}
        self.assert_params_for_cmd(cmdline, result)

    def test_instance_id(self):
        args = ' --instance-ids i-12345678'
        cmdline = self.prefix + args
        result = {'InstanceIds': ['i-12345678']}
        self.assert_params_for_cmd(cmdline, result)

    def test_instance_ids(self):
        args = ' --instance-ids i-12345678 i-87654321'
        cmdline = self.prefix + args
        result = {'InstanceIds': ['i-12345678', 'i-87654321']}
        self.assert_params_for_cmd(cmdline, result)

    def test_instance_ids_alternate(self):
        # Not required, but will still work if you use JSON.
        args = ' --instance-ids ["i-12345678","i-87654321"]'
        cmdline = self.prefix + args
        result = {'InstanceIds': ['i-12345678', 'i-87654321']}
        self.assert_params_for_cmd(cmdline, result)

    def test_filter_json(self):
        args = """ --filters {"Name":"group-name","Values":["foobar"]}"""
        cmdline = self.prefix + args
        result = {
            'Filters': [
                {'Name': 'group-name',
                 'Values': ['foobar']},
            ],
        }
        self.assert_params_for_cmd(cmdline, result)

    def test_filter_simple(self):
        args = """ --filters Name=group-name,Values=foobar"""
        cmdline = self.prefix + args
        result = {
            'Filters': [
                {'Name': 'group-name',
                 'Values': ['foobar']},
            ],
        }
        self.assert_params_for_cmd(cmdline, result)

    def test_filter_values(self):
        args = """ --filters Name=group-name,Values=foobar,fiebaz"""
        cmdline = self.prefix + args
        result = {
            'Filters': [
                {'Name': 'group-name',
                 'Values': ['foobar', 'fiebaz']},
            ],
        }
        self.assert_params_for_cmd(cmdline, result)

    def test_multiple_filters(self):
        args = (' --filters Name=group-name,Values=foobar '
                'Name=instance-id,Values=i-12345')
        cmdline = self.prefix + args
        result = {
            'Filters': [
                {'Name': 'group-name',
                 'Values': ['foobar']},
                {'Name': 'instance-id',
                 'Values': ['i-12345']},
            ],
        }
        self.assert_params_for_cmd(cmdline, result)

    def test_multiple_filters_alternate(self):
        cmdlist = 'ec2 describe-instances'.split()
        cmdlist.extend(['--filters',
                        'Name = group-name, Values= foobar',
                        'Name=instance-id,Values=i-12345'])
        result = {
            'Filters': [
                {'Name': 'group-name',
                 'Values': ['foobar']},
                {'Name': 'instance-id',
                 'Values': ['i-12345']},
            ],
        }
        self.assert_params_for_cmd(cmdlist, result)

    def test_page_size(self):
        args = ' --page-size 10'
        cmdline = self.prefix + args
        result = {'MaxResults': 10}
        self.assert_params_for_cmd(cmdline, result)


if __name__ == "__main__":
    unittest.main()
