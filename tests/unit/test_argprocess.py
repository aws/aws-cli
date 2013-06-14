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
import six

from awscli.clidriver import CLIArgument
from awscli.help import OperationHelpCommand
from awscli.argprocess import detect_shape_structure
from awscli.argprocess import unpack_cli_arg
from awscli.argprocess import ParamShorthand
from awscli.argprocess import ParamError
from awscli.argprocess import ParamUnknownKeyError


MAPHELP = """--attributes key_name=string,key_name2=string
Where valid key names are:
  Policy
  VisibilityTimeout
  MaximumMessageSize
  MessageRetentionPeriod
  ApproximateNumberOfMessages
  ApproximateNumberOfMessagesNotVisible
  CreatedTimestamp
  LastModifiedTimestamp
  QueueArn
  ApproximateNumberOfMessagesDelayed
  DelaySeconds
  ReceiveMessageWaitTimeSeconds\n"""

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

    def test_list_structure_list_multiple_scalar(self):
        p = self.get_param_object('elastictranscoder.CreateJob.Playlists')
        returned = self.simplify(
            p, ['name=foo,format=hslv3,output_keys=iphone1,iphone2'])
        self.assertEqual(returned, [{'output_keys': ['iphone1', 'iphone2'],
                                     'name': 'foo', 'format': 'hslv3'}])

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

    def test_keyval_with_long_values(self):
        p = self.get_param_object(
            'dynamodb.UpdateTable.ProvisionedThroughput')
        value = 'write_capacity_units=10,read_capacity_units=10'
        returned = self.simplify(p, value)
        self.assertEqual(returned, {'write_capacity_units': 10,
                                    'read_capacity_units': 10})

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

    def test_csv_syntax(self):
        p = self.get_param_object('cloudformation.CreateStack.Parameters')
        returned = self.simplify(
            p, ["parameter_key=key,parameter_value=foo\,bar"])
        expected = [{"parameter_key": "key",
                     "parameter_value": "foo,bar"}]

        returned2e = self.simplify(
            p, ['parameter_key=key,parameter_value="foo,bar"'])
        self.assertEqual(returned, expected)

    def test_csv_syntax_errors(self):
        p = self.get_param_object('cloudformation.CreateStack.Parameters')
        error_msg = "Error parsing parameter --parameters.*should be"
        with self.assertRaisesRegexp(ParamError, error_msg):
            returned = self.simplify(
                p, ['parameter_key=key,parameter_value="foo,bar'])
        with self.assertRaisesRegexp(ParamError, error_msg):
            returned = self.simplify(
                p, ['parameter_key=key,parameter_value=foo,bar"'])
        with self.assertRaisesRegexp(ParamError, error_msg):
            returned = self.simplify(
                p, ['parameter_key=key,parameter_value=""foo,bar"'])


class TestDocGen(BaseArgProcessTest):
    # These aren't very extensive doc tests, as we want to stay somewhat
    # flexible and allow the docs to slightly change without breaking these
    # tests.
    def setUp(self):
        super(TestDocGen, self).setUp()
        self.simplify = ParamShorthand()

    def test_gen_map_type_docs(self):
        p = self.get_param_object('sqs.SetQueueAttributes.Attributes')
        argument = CLIArgument(p.cli_name, p, p.operation)
        help_command = OperationHelpCommand(self.session,
                                            p.operation, None,
                                            {p.cli_name: argument})
        help_command.param_shorthand.add_example_fn(p.cli_name, help_command)
        self.assertTrue(p.example_fn)
        doc_string = p.example_fn(p)
        self.assertEqual(doc_string, MAPHELP)

    def test_gen_list_scalar_docs(self):
        p = self.get_param_object(
            'elb.RegisterInstancesWithLoadBalancer.Instances')
        argument = CLIArgument(p.cli_name, p, p.operation)
        help_command = OperationHelpCommand(self.session,
                                            p.operation, None,
                                            {p.cli_name: argument})
        help_command.param_shorthand.add_example_fn(p.cli_name, help_command)
        self.assertTrue(p.example_fn)
        doc_string = p.example_fn(p)
        self.assertEqual(doc_string,
                         '--instances instance_id1 instance_id2 instance_id3')

    def test_gen_list_structure_of_scalars_docs(self):
        p = self.get_param_object('elb.CreateLoadBalancer.Listeners')
        argument = CLIArgument(p.cli_name, p, p.operation)
        help_command = OperationHelpCommand(self.session,
                                            p.operation, None,
                                            {p.cli_name: argument})
        help_command.param_shorthand.add_example_fn(p.cli_name, help_command)
        self.assertTrue(p.example_fn)
        doc_string = p.example_fn(p)
        self.assertIn('Key value pairs, with multiple values separated by a space.', doc_string)
        self.assertIn('protocol=string', doc_string)
        self.assertIn('load_balancer_port=integer', doc_string)
        self.assertIn('instance_protocol=string', doc_string)
        self.assertIn('instance_port=integer', doc_string)
        self.assertIn('ssl_certificate_id=string', doc_string)

    def test_gen_list_structure_multiple_scalar_docs(self):
        p = self.get_param_object('elastictranscoder.CreateJob.Playlists')
        argument = CLIArgument(p.cli_name, p, p.operation)
        help_command = OperationHelpCommand(self.session,
                                            p.operation, None,
                                            {p.cli_name: argument})
        help_command.param_shorthand.add_example_fn(p.cli_name, help_command)
        self.assertTrue(p.example_fn)
        doc_string = p.example_fn(p)
        s = 'Key value pairs, where values are separated by commas.\n--playlists name=string1,format=string1,output_keys=string1,string2'
        self.assertEqual(doc_string, s)


if __name__ == '__main__':
    unittest.main()
