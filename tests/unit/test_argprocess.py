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
import unittest

import botocore.session
from awscli.argprocess import detect_shape_structure
from awscli.argprocess import unpack_cli_arg
from awscli.argprocess import ParamShorthand


# These tests use real service types so that we can
# verify the real shapes of services.
class BaseArgProcessTest(unittest.TestCase):
    def setUp(self):
        self.session = botocore.session.get_session()

    def get_param_object(self, dotted_name):
        service_name, operation_name, param_name = dotted_name.split('.')
        service = self.session.get_service(service_name)
        operation = service.get_operation(operation_name)
        for p in operation.params:
            if p.name == param_name:
                return p
        else:
            raise ValueError("Unknown param: %s" % param_name)


class TestArgShapeDetection(BaseArgProcessTest):

    def assert_shape_type(self, spec, expected_type):
        p = self.get_param_object(spec)
        actual_structure = detect_shape_structure(p)
        self.assertEqual(actual_structure, expected_type)

    def test_detect_scalar(self):
        self.assert_shape_type('iam.AddRoleToInstanceProfile.RoleName',
                               'scalar')

    def test_detect_list_of_strings(self):
        self.assert_shape_type('sns.AddPermission.AWSAccountId', 'list-scalar')

    def test_detect_structure_of_scalars(self):
        self.assert_shape_type(
            'elasticbeanstalk.CreateConfigurationTemplate.SourceConfiguration',
            'structure(scalar)')

    def test_list_structure_scalars(self):
        self.assert_shape_type(
            'elb.RegisterInstancesWithLoadBalancer.Instances',
            'list-structure(scalar)')

    def test_list_structure_of_list_and_strings(self):
        self.assert_shape_type(
            'ec2.DescribeInstances.Filters', 'list-structure(list-scalar, scalar)')

    def test_map_scalar(self):
        self.assert_shape_type(
            'sqs.SetQueueAttributes.Attributes', 'map-scalar')


class TestParamShorthand(BaseArgProcessTest):
    def setUp(self):
        super(TestParamShorthand, self).setUp()
        self.simplify = ParamShorthand()

    def test_simplify_structure_scalars(self):
        p = self.get_param_object(
            'elasticbeanstalk.CreateConfigurationTemplate.SourceConfiguration')
        value = 'application_name:foo,template_name:bar'
        json_value = '{"application_name": "foo", "template_name": "bar"}'
        returned = self.simplify(p, value)
        json_version = unpack_cli_arg(p, json_value)
        self.assertEqual(returned, json_version)

    def test_simplify_map_scalar(self):
        p = self.get_param_object('sqs.SetQueueAttributes.Attributes')
        returned = self.simplify(p, 'visibility_timeout:15')
        self.assertEqual(returned, {'visibility_timeout': '15'})

    def test_list_structure_scalars(self):
        p = self.get_param_object(
            'elb.RegisterInstancesWithLoadBalancer.Instances')
        # Because this is a list type param, we'll use nargs
        # with argparse which means the value will be presented
        # to us as a list.
        returned = self.simplify(p, ['instance-1',  'instance-2'])
        self.assertEqual(returned, [{'instance_id': 'instance-1'},
                                    {'instance_id': 'instance-2'}])

    def test_list_structure_list_scalar(self):
        p = self.get_param_object('ec2.DescribeInstances.Filters')
        expected = [{"name": "instance-id", "values": ["i-1", "i-2"]},
                    {"name": "architecture", "values": ["i386"]}]
        returned = self.simplify(
            p, ["name:instance-id,values:i-1,i-2",
                "name:architecture,values:i386"])
        self.assertEqual(returned, expected)

        # With spaces around the comma.
        returned2 = self.simplify(
            p, ["name:instance-id, values:i-1,i-2",
                "name:architecture, values:i386"])
        self.assertEqual(returned2, expected)

        # Strip off leading/trailing spaces.
        returned3 = self.simplify(
            p, ["name: instance-id, values: i-1,i-2",
                "name: architecture, values: i386"])
        self.assertEqual(returned2, expected)


if __name__ == '__main__':
    unittest.main()
