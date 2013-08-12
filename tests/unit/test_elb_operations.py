#!/usr/bin/env python
# Copyright (c) 2012-2013 Mitch Garnaat http://garnaat.org/
# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
import unittest
import botocore.session


class TestELBOperations(unittest.TestCase):

    def setUp(self):
        self.session = botocore.session.get_session()
        self.elb = self.session.get_service('elb')

    def test_describe_load_balancers_no_params(self):
        op = self.elb.get_operation('DescribeLoadBalancers')
        params = op.build_parameters()
        result = {}
        self.assertEqual(params, result)

    def test_describe_load_balancers_name(self):
        op = self.elb.get_operation('DescribeLoadBalancers')
        params = op.build_parameters(load_balancer_names=['foo'])
        result = {'LoadBalancerNames.member.1': 'foo'}
        self.assertEqual(params, result)

    def test_describe_load_balancers_names(self):
        op = self.elb.get_operation('DescribeLoadBalancers')
        params = op.build_parameters(load_balancer_names=['foo', 'bar'])
        result = {'LoadBalancerNames.member.1': 'foo',
                  'LoadBalancerNames.member.2': 'bar'}
        self.assertEqual(params, result)

    def test_create_load_balancer_listeners(self):
        op = self.elb.get_operation('CreateLoadBalancerListeners')
        params = op.build_parameters(listeners=[{'InstancePort':80,
                                                 'SSLCertificateId': 'foobar',
                                                 'LoadBalancerPort':81,
                                                 'Protocol':'HTTPS',
                                                 'InstanceProtocol':'HTTP'}],
                                     load_balancer_name='foobar')
        result = {'Listeners.member.1.LoadBalancerPort': '81',
                  'Listeners.member.1.InstancePort': '80',
                  'Listeners.member.1.Protocol': 'HTTPS',
                  'Listeners.member.1.InstanceProtocol': 'HTTP',
                  'Listeners.member.1.SSLCertificateId': 'foobar',
                  'LoadBalancerName': 'foobar'}
        self.assertEqual(params, result)

    def test_register_instances_with_load_balancer(self):
        op = self.elb.get_operation('RegisterInstancesWithLoadBalancer')
        params = op.build_parameters(load_balancer_name='foobar',
                                     instances=[{'InstanceId': 'i-12345678'},
                                                {'InstanceId': 'i-87654321'}])
        result = {'LoadBalancerName': 'foobar',
                  'Instances.member.1.InstanceId': 'i-12345678',
                  'Instances.member.2.InstanceId': 'i-87654321'}
        self.assertEqual(params, result)


if __name__ == "__main__":
    unittest.main()
