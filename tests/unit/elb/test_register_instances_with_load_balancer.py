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


class TestRegisterInstancesWithLoadBalancer(unittest.TestCase):

    def setUp(self):
        self.driver = awscli.clidriver.CLIDriver()
        self.prefix = 'aws elb register-instances-with-load-balancer'

    def test_one_instance(self):
        cmdline = self.prefix
        cmdline += ' --load-balancer-name my-lb'
        cmdline += ' --instances {"instance_id":"i-12345678"}'
        result = {'LoadBalancerName': 'my-lb',
                  'Instances.member.1.InstanceId': 'i-12345678'}
        params = self.driver.test(cmdline)
        self.assertEqual(params, result)

    def test_two_instance(self):
        cmdline = self.prefix
        cmdline += ' --load-balancer-name my-lb'
        cmdline += ' --instances {"instance_id":"i-12345678"}'
        cmdline += ' {"instance_id":"i-87654321"}'
        result = {'LoadBalancerName': 'my-lb',
                  'Instances.member.1.InstanceId': 'i-12345678',
                  'Instances.member.2.InstanceId': 'i-87654321'}
        params = self.driver.test(cmdline)
        self.assertEqual(params, result)


if __name__ == "__main__":
    unittest.main()
