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
import os

attributes = {
    "MysqlRootPasswordUbiquitous": None,
    "RubygemsVersion": "1.8.24",
    "RailsStack": "apache_passenger",
    "HaproxyHealthCheckMethod": None,
    "RubyVersion": "1.9.3",
    "BundlerVersion": "1.2.3",
    "HaproxyStatsPassword": None,
    "PassengerVersion": "3.0.17",
    "MemcachedMemory": None,
    "EnableHaproxyStats": None,
    "ManageBundler": "true",
    "NodejsVersion": None,
    "HaproxyHealthCheckUrl": None,
    "MysqlRootPassword": None,
    "GangliaPassword": None,
    "GangliaUser": None,
    "HaproxyStatsUrl": None,
    "GangliaUrl": None,
    "HaproxyStatsUser": None
}

class TestOpsworksOperations(unittest.TestCase):

    def setUp(self):
        os.environ['BOTO_DATA_PATH'] = '~/.aws_data'
        self.session = botocore.session.get_session()
        self.opsworks = self.session.get_service('opsworks')
        self.stack_id = '35959772-cd1e-4082-8346-79096d4179f2'

    def test_describe_layers(self):
        op = self.opsworks.get_operation('DescribeLayers')
        params = op.build_parameters(stack_id=self.stack_id,
                                     layer_ids=['3e9a9949-a85e-4687-bf95-25c5dab11205'])
        result = {'StackId': self.stack_id,
                  'LayerIds': ['3e9a9949-a85e-4687-bf95-25c5dab11205']}
        self.assertEqual(params, result)

    def test_create_layers(self):
        op = self.opsworks.get_operation('CreateLayer')
        params = op.build_parameters(name='Test CLI',
                                     stack_id=self.stack_id,
                                     auto_assign_elastic_ips=True,
                                     attributes=attributes,
                                     type='rails-app',
                                     shortname='a')
        result = {'StackId': self.stack_id,
                  'Name': 'Test CLI',
                  'AutoAssignElasticIps': True,
                  'Attributes': attributes,
                  'Type': 'rails-app',
                  'Shortname': 'a'}
        self.maxDiff = None
        self.assertEqual(params, result)


if __name__ == "__main__":
    unittest.main()
