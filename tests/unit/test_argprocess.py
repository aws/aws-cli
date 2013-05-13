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


# These tests use real service types so that we can
# verify the real shapes of services.
class TestArgShapeDetection(unittest.TestCase):

    def setUp(self):
        self.session = botocore.session.get_session()

    def tearDown(self):
        pass

    def assert_shape_type(self, spec, expected_type):
        service_name, operation_name, param_name = spec.split('.')
        service = self.session.get_service(service_name)
        operation = service.get_operation(operation_name)
        for p in operation.params:
            if p.name == param_name:
                param = p
                break
        else:
            raise ValueError("Unknown param: %s" % param_name)
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


if __name__ == '__main__':
    unittest.main()
