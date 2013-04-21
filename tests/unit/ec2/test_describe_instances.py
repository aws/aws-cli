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
import unittest
import awscli.clidriver


class TestDescribeInstances(unittest.TestCase):

    def setUp(self):
        self.driver = awscli.clidriver.CLIDriver()
        self.prefix = 'aws ec2 describe-instances'

    def test_no_params(self):
        cmdline = self.prefix
        result = {}
        params = self.driver.test(cmdline)
        self.assertEqual(params, result)

    def test_instance_id(self):
        args = ' --instance-ids i-12345678'
        cmdline = self.prefix + args
        result = {'InstanceId.1': 'i-12345678'}
        params = self.driver.test(cmdline)
        self.assertEqual(params, result)

    def test_instance_ids(self):
        args = ' --instance-ids i-12345678 i-87654321'
        cmdline = self.prefix + args
        result = {'InstanceId.1': 'i-12345678', 'InstanceId.2': 'i-87654321'}
        params = self.driver.test(cmdline)
        self.assertEqual(params, result)

    def test_filter(self):
        args = """ --filters {"name":"group-name","values":["foobar"]}"""
        cmdline = self.prefix + args
        result = {'Filter.1.Value.1': 'foobar', 'Filter.1.Name': 'group-name'}
        params = self.driver.test(cmdline)
        self.assertEqual(params, result)

    def test_filter_values(self):
        args = """ --filters {"name":"group-name","values":["foobar","fiebaz"]}"""
        cmdline = self.prefix + args
        result = {'Filter.1.Value.2': 'fiebaz',
                  'Filter.1.Value.1': 'foobar',
                  'Filter.1.Name': 'group-name'}
        params = self.driver.test(cmdline)
        self.assertEqual(params, result)

    def test_multiple_filters(self):
        args = (' --filters {"name":"group-name","values":["foobar"]} '
                '{"name":"instance-id","values":["i-12345"]}')
        cmdline = self.prefix + args
        result = {
            'Filter.1.Name': 'group-name',
            'Filter.1.Value.1': 'foobar',
            'Filter.2.Name': 'instance-id',
            'Filter.2.Value.1': 'i-12345',
        }
        params = self.driver.test(cmdline)
        self.assertEqual(params, result)



if __name__ == "__main__":
    unittest.main()
