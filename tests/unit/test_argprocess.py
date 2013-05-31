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
from tests import unittest
from argparse import Namespace

import botocore.session
from bcdoc.mangen import OperationDocument
import six

from awscli.clidriver import CLIArgument
from awscli.argprocess import detect_shape_structure
from awscli.argprocess import unpack_cli_arg
from awscli.argprocess import ParamShorthand
from awscli.argprocess import ParamError
from awscli.argprocess import ParamUnknownKeyError


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
            'structure(scalars)')

    def test_list_structure_scalars(self):
        self.assert_shape_type(
            'elb.RegisterInstancesWithLoadBalancer.Instances',
            'list-structure(scalar)')

    def test_list_structure_scalars(self):
        self.assert_shape_type(
            'elb.CreateLoadBalancer.Listeners',
            'list-structure(scalars)')

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
        value = 'application_name=foo,template_name=bar'
        json_value = '{"application_name": "foo", "template_name": "bar"}'
        returned = self.simplify(p, value)
        json_version = unpack_cli_arg(p, json_value)
        self.assertEqual(returned, json_version)

    def test_simplify_map_scalar(self):
        p = self.get_param_object('sqs.SetQueueAttributes.Attributes')
        returned = self.simplify(p, 'VisibilityTimeout=15')
        json_version = unpack_cli_arg(p, '{"VisibilityTimeout": "15"}')
        self.assertEqual(returned, {'VisibilityTimeout': '15'})
        self.assertEqual(returned, json_version)

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
            p, ["name=instance-id,values=i-1,i-2",
                "name=architecture,values=i386"])
        self.assertEqual(returned, expected)

        # With spaces around the comma.
        returned2 = self.simplify(
            p, ["name=instance-id, values=i-1,i-2",
                "name=architecture, values=i386"])
        self.assertEqual(returned2, expected)

        # Strip off leading/trailing spaces.
        returned3 = self.simplify(
            p, ["name = instance-id, values = i-1,i-2",
                "name = architecture, values = i386"])
        self.assertEqual(returned2, expected)

    def test_list_structure_scalars(self):
        p = self.get_param_object('elb.CreateLoadBalancer.Listeners')
        expected = [
            {"protocol": "protocol1",
             "load_balancer_port": 1,
             "instance_protocol": "instance_protocol1",
             "instance_port": 2,
             "ssl_certificate_id": "ssl_certificate_id1"},
            {"protocol": "protocol2",
             "load_balancer_port": 3,
             "instance_protocol": "instance_protocol2",
             "instance_port": 4,
             "ssl_certificate_id": "ssl_certificate_id2"},
        ]
        returned = unpack_cli_arg(
            p, ['{"protocol": "protocol1", "load_balancer_port": 1, '
                '"instance_protocol": "instance_protocol1", '
                '"instance_port": 2, "ssl_certificate_id": '
                '"ssl_certificate_id1"}',
                '{"protocol": "protocol2", "load_balancer_port": 3, '
                '"instance_protocol": "instance_protocol2", '
                '"instance_port": 4, "ssl_certificate_id": '
                '"ssl_certificate_id2"}',
            ])
        self.assertEqual(returned, expected)
        simplified = self.simplify(p, [
            'protocol=protocol1,load_balancer_port=1,'
            'instance_protocol=instance_protocol1,'
            'instance_port=2,ssl_certificate_id=ssl_certificate_id1',
            'protocol=protocol2,load_balancer_port=3,'
            'instance_protocol=instance_protocol2,'
            'instance_port=4,ssl_certificate_id=ssl_certificate_id2'
        ])
        self.assertEqual(simplified, expected)

    def test_error_messages_for_structure_scalar(self):
        p = self.get_param_object(
            'elasticbeanstalk.CreateConfigurationTemplate.SourceConfiguration')
        value = 'application_names==foo,template_name=bar'
        error_msg = "Error parsing parameter --source-configuration.*should be"
        with self.assertRaisesRegexp(ParamError, error_msg):
            self.simplify(p, value)

    def test_mispelled_param_name(self):
        p = self.get_param_object(
            'elasticbeanstalk.CreateConfigurationTemplate.SourceConfiguration')
        error_msg = 'valid choices.*application_name'
        with self.assertRaisesRegexp(ParamUnknownKeyError, error_msg):
            # Typo in 'application_names'
            self.simplify(p, 'application_namess=foo, template_name=bar')

    def test_improper_separator(self):
        # If the user uses ':' instead of '=', we should give a good
        # error message.
        p = self.get_param_object(
            'elasticbeanstalk.CreateConfigurationTemplate.SourceConfiguration')
        value = 'application_names:foo,template_name:bar'
        error_msg = "Error parsing parameter --source-configuration.*should be"
        with self.assertRaisesRegexp(ParamError, error_msg):
            self.simplify(p, value)

    def test_improper_separator_for_filters_param(self):
        p = self.get_param_object('ec2.DescribeInstances.Filters')
        error_msg = "Error parsing parameter --filters.*should be"
        with self.assertRaisesRegexp(ParamError, error_msg):
            returned = self.simplify(
                p, ["name:tag:Name,values:foo"])

    def test_unknown_key_for_filters_param(self):
        p = self.get_param_object('ec2.DescribeInstances.Filters')
        with self.assertRaisesRegexp(ParamUnknownKeyError,
                                     'valid choices.*name'):
            self.simplify(p, ["names=instance-id,values=foo,bar"])


class TestDocGen(BaseArgProcessTest):
    # These aren't very extensive doc tests, as we want to stay somewhat
    # flexible and allow the docs to slightly change without breaking these
    # tests.
    def setUp(self):
        super(TestDocGen, self).setUp()
        self.simplify = ParamShorthand()

    def test_gen_map_type_docs(self):
        p = self.get_param_object('sqs.SetQueueAttributes.Attributes')
        op_doc = OperationDocument(self.session, p.operation)
        self.simplify.add_docs(op_doc, p)
        fp = six.StringIO()
        op_doc.render(fp=fp)
        rendered = fp.getvalue()
        # Key parts include:
        # Title that says it's the shorthand syntax.
        self.assertIn('Shorthand Syntax', rendered)
        # sample syntax
        self.assertIn('key_name=string', rendered)
        # valid key names
        self.assertIn('VisibilityTimeout', rendered)

    def test_gen_list_scalar_docs(self):
        p = self.get_param_object(
            'elb.RegisterInstancesWithLoadBalancer.Instances')
        op_doc = OperationDocument(self.session, p.operation)
        self.simplify.add_docs(op_doc, p)
        fp = six.StringIO()
        op_doc.render(fp=fp)
        rendered = fp.getvalue()
        # Key parts include:
        # Title that says it's the shorthand syntax.
        self.assertIn('Shorthand Syntax', rendered)
        # sample syntax
        self.assertIn('--instances instance_id1', rendered)

    def test_gen_list_structure_of_scalars_docs(self):
        p = self.get_param_object('elb.CreateLoadBalancer.Listeners')
        op_doc = OperationDocument(self.session, p.operation)
        self.simplify.add_docs(op_doc, p)
        fp = six.StringIO()
        op_doc.render(fp=fp)
        rendered = fp.getvalue()
        self.assertIn('Shorthand Syntax', rendered)
        self.assertIn('--listeners', rendered)
        self.assertIn('protocol=string', rendered)


if __name__ == '__main__':
    unittest.main()
