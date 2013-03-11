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
import base64
import six
import botocore.session


class TestEC2Operations(unittest.TestCase):

    def setUp(self):
        self.session = botocore.session.get_session()
        self.ec2 = self.session.get_service('ec2')

    def test_describe_instances_no_params(self):
        op = self.ec2.get_operation('DescribeInstances')
        params = op.build_parameters()
        result = {}
        self.assertEqual(params, result)

    def test_describe_instances_instance_id(self):
        op = self.ec2.get_operation('DescribeInstances')
        params = op.build_parameters(instance_ids=['i-12345678'])
        result = {'InstanceId.1': 'i-12345678'}
        self.assertEqual(params, result)

    def test_describe_instances_instance_ids(self):
        op = self.ec2.get_operation('DescribeInstances')
        params = op.build_parameters(instance_ids=['i-12345678',
                                                  'i-87654321'])
        result = {'InstanceId.1': 'i-12345678', 'InstanceId.2': 'i-87654321'}
        self.assertEqual(params, result)

    def test_describe_instances_filter(self):
        op = self.ec2.get_operation('DescribeInstances')
        params = op.build_parameters(filters={'name': 'group-name',
                                              'values': ['foobar']})
        result = {'Filter.1.Value.1': 'foobar', 'Filter.1.Name': 'group-name'}
        self.assertEqual(params, result)

    def test_describe_instances_filter_values(self):
        op = self.ec2.get_operation('DescribeInstances')
        params = op.build_parameters(filters={'name': 'group-name',
                                              'values': ['foobar', 'fiebaz']})
        result = {'Filter.1.Value.2': 'fiebaz',
                  'Filter.1.Value.1': 'foobar',
                  'Filter.1.Name': 'group-name'}
        self.assertEqual(params, result)

    def test_create_tags(self):
        op = self.ec2.get_operation('CreateTags')
        params = op.build_parameters(resources=['i-12345678', 'i-87654321'],
                                     tags=[{'key': 'key1', 'value': 'value1'},
                                           {'key': 'key2', 'value': 'value2'}])
        result = {'ResourceId.1': 'i-12345678',
                  'ResourceId.2': 'i-87654321',
                  'Tag.1.Key': 'key1', 'Tag.1.Value': 'value1',
                  'Tag.2.Key': 'key2', 'Tag.2.Value': 'value2'}
        self.assertEqual(params, result)

    def test_request_spot_instances(self):
        op = self.ec2.get_operation('RequestSpotInstances')
        params = op.build_parameters(spot_price='1.00',
                                     instance_count=1,
                                     launch_specification={
                                         'image_id': 'ami-33ec795a',
                                         'instance_type': 'cc2.8xlarge',
                                         'block_device_mappings': [
                                             {"device_name": "/dev/sdb", "virtual_name": "ephemeral0"},
                                             {"device_name": "/dev/sdc", "virtual_name": "ephemeral1"},
                                             {"device_name": "/dev/sdd", "virtual_name": "ephemeral2"},
                                             {"device_name": "/dev/sde", "virtual_name": "ephemeral3"}]})
        result = {'SpotPrice': '1.00',
                  'InstanceCount': '1',
                  'LaunchSpecification.ImageId': 'ami-33ec795a',
                  'LaunchSpecification.InstanceType': 'cc2.8xlarge',
                  'LaunchSpecification.BlockDeviceMapping.1.DeviceName': '/dev/sdb',
                  'LaunchSpecification.BlockDeviceMapping.2.DeviceName': '/dev/sdc',
                  'LaunchSpecification.BlockDeviceMapping.3.DeviceName': '/dev/sdd',
                  'LaunchSpecification.BlockDeviceMapping.4.DeviceName': '/dev/sde',
                  'LaunchSpecification.BlockDeviceMapping.1.VirtualName': 'ephemeral0',
                  'LaunchSpecification.BlockDeviceMapping.2.VirtualName': 'ephemeral1',
                  'LaunchSpecification.BlockDeviceMapping.3.VirtualName': 'ephemeral2',
                  'LaunchSpecification.BlockDeviceMapping.4.VirtualName': 'ephemeral3'}
        self.maxDiff = None
        self.assertEqual(params, result)

    def test_run_instances_userdata(self):
        user_data = 'This is a test'
        b64_user_data = base64.b64encode(six.b(user_data)).decode('utf-8')
        op = self.ec2.get_operation('RunInstances')
        params = op.build_parameters(image_id='img-12345678',
                                     min_count=1, max_count=5,
                                     user_data=user_data)
        result = {'ImageId': 'img-12345678',
                  'MinCount': '1',
                  'MaxCount': '5',
                  'UserData': b64_user_data}
        self.assertEqual(params, result)


if __name__ == "__main__":
    unittest.main()
