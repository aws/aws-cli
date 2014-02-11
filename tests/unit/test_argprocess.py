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

import botocore.session
import mock

from awscli.clidriver import CLIArgument
from awscli.help import OperationHelpCommand
from awscli.argprocess import detect_shape_structure
from awscli.argprocess import unpack_cli_arg
from awscli.argprocess import ParamShorthand
from awscli.argprocess import ParamError
from awscli.argprocess import ParamUnknownKeyError


MAPHELP = """--attributes key_name=string,key_name2=string
Where valid key names are:
  Policy"""

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

    def test_list_structure_scalars_2(self):
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
        value = 'ApplicationName=foo,TemplateName=bar'
        json_value = '{"ApplicationName": "foo", "TemplateName": "bar"}'
        returned = self.simplify(p, value)
        json_version = unpack_cli_arg(p, json_value)
        self.assertEqual(returned, json_version)

    def test_parse_boolean_shorthand(self):
        bool_param = mock.Mock()
        bool_param.type = 'boolean'
        self.assertTrue(unpack_cli_arg(bool_param, True))
        self.assertTrue(unpack_cli_arg(bool_param, 'True'))
        self.assertTrue(unpack_cli_arg(bool_param, 'true'))

        self.assertFalse(unpack_cli_arg(bool_param, False))
        self.assertFalse(unpack_cli_arg(bool_param, 'False'))
        self.assertFalse(unpack_cli_arg(bool_param, 'false'))

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
        self.assertEqual(returned, [{'InstanceId': 'instance-1'},
                                    {'InstanceId': 'instance-2'}])

    def test_list_structure_list_scalar(self):
        p = self.get_param_object('ec2.DescribeInstances.Filters')
        expected = [{"Name": "instance-id", "Values": ["i-1", "i-2"]},
                    {"Name": "architecture", "Values": ["i386"]}]
        returned = self.simplify(
            p, ["Name=instance-id,Values=i-1,i-2",
                "Name=architecture,Values=i386"])
        self.assertEqual(returned, expected)

        # With spaces around the comma.
        returned2 = self.simplify(
            p, ["Name=instance-id, Values=i-1,i-2",
                "Name=architecture, Values=i386"])
        self.assertEqual(returned2, expected)

        # Strip off leading/trailing spaces.
        returned3 = self.simplify(
            p, ["Name = instance-id, Values = i-1,i-2",
                "Name = architecture, Values = i386"])
        self.assertEqual(returned3, expected)

    def test_list_structure_list_multiple_scalar(self):
        p = self.get_param_object('elastictranscoder.CreateJob.Playlists')
        returned = self.simplify(
            p, ['Name=foo,Format=hslv3,OutputKeys=iphone1,iphone2'])
        self.assertEqual(returned, [{'OutputKeys': ['iphone1', 'iphone2'],
                                     'Name': 'foo', 'Format': 'hslv3'}])

    def test_list_structure_scalars_2(self):
        p = self.get_param_object('elb.CreateLoadBalancer.Listeners')
        expected = [
            {"Protocol": "protocol1",
             "LoadBalancerPort": 1,
             "InstanceProtocol": "instance_protocol1",
             "InstancePort": 2,
             "SSLCertificateId": "ssl_certificate_id1"},
            {"Protocol": "protocol2",
             "LoadBalancerPort": 3,
             "InstanceProtocol": "instance_protocol2",
             "InstancePort": 4,
             "SSLCertificateId": "ssl_certificate_id2"},
        ]
        returned = unpack_cli_arg(
            p, ['{"Protocol": "protocol1", "LoadBalancerPort": 1, '
                '"InstanceProtocol": "instance_protocol1", '
                '"InstancePort": 2, "SSLCertificateId": '
                '"ssl_certificate_id1"}',
                '{"Protocol": "protocol2", "LoadBalancerPort": 3, '
                '"InstanceProtocol": "instance_protocol2", '
                '"InstancePort": 4, "SSLCertificateId": '
                '"ssl_certificate_id2"}',
            ])
        self.maxDiff = None
        self.assertEqual(returned, expected)
        simplified = self.simplify(p, [
            'Protocol=protocol1,LoadBalancerPort=1,'
            'InstanceProtocol=instance_protocol1,'
            'InstancePort=2,SSLCertificateId=ssl_certificate_id1',
            'Protocol=protocol2,LoadBalancerPort=3,'
            'InstanceProtocol=instance_protocol2,'
            'InstancePort=4,SSLCertificateId=ssl_certificate_id2'
        ])
        self.assertEqual(simplified, expected)

    def test_keyval_with_long_values(self):
        p = self.get_param_object(
            'dynamodb.UpdateTable.ProvisionedThroughput')
        value = 'WriteCapacityUnits=10,ReadCapacityUnits=10'
        returned = self.simplify(p, value)
        self.assertEqual(returned, {'WriteCapacityUnits': 10,
                                    'ReadCapacityUnits': 10})

    def test_error_messages_for_structure_scalar(self):
        p = self.get_param_object(
            'elasticbeanstalk.CreateConfigurationTemplate.SourceConfiguration')
        value = 'ApplicationName:foo,TemplateName=bar'
        error_msg = "Error parsing parameter --source-configuration.*should be"
        with self.assertRaisesRegexp(ParamError, error_msg):
            self.simplify(p, value)

    def test_mispelled_param_name(self):
        p = self.get_param_object(
            'elasticbeanstalk.CreateConfigurationTemplate.SourceConfiguration')
        error_msg = 'valid choices.*ApplicationName'
        with self.assertRaisesRegexp(ParamUnknownKeyError, error_msg):
            # Typo in 'ApplicationName'
            self.simplify(p, 'ApplicationNames=foo, TemplateName=bar')

    def test_improper_separator(self):
        # If the user uses ':' instead of '=', we should give a good
        # error message.
        p = self.get_param_object(
            'elasticbeanstalk.CreateConfigurationTemplate.SourceConfiguration')
        value = 'ApplicationName:foo,TemplateName:bar'
        error_msg = "Error parsing parameter --source-configuration.*should be"
        with self.assertRaisesRegexp(ParamError, error_msg):
            self.simplify(p, value)

    def test_improper_separator_for_filters_param(self):
        p = self.get_param_object('ec2.DescribeInstances.Filters')
        error_msg = "Error parsing parameter --filters.*should be"
        with self.assertRaisesRegexp(ParamError, error_msg):
            self.simplify(p, ["Name:tag:Name,Values:foo"])

    def test_unknown_key_for_filters_param(self):
        p = self.get_param_object('ec2.DescribeInstances.Filters')
        with self.assertRaisesRegexp(ParamUnknownKeyError,
                                     'valid choices.*Name'):
            self.simplify(p, ["Names=instance-id,Values=foo,bar"])

    def test_csv_syntax_escaped(self):
        p = self.get_param_object('cloudformation.CreateStack.Parameters')
        returned = self.simplify(
            p, ["ParameterKey=key,ParameterValue=foo\,bar"])
        expected = [{"ParameterKey": "key",
                     "ParameterValue": "foo,bar"}]
        self.assertEqual(returned, expected)

    def test_csv_syntax_double_quoted(self):
        p = self.get_param_object('cloudformation.CreateStack.Parameters')
        returned = self.simplify(
            p, ['ParameterKey=key,ParameterValue="foo,bar"'])
        expected = [{"ParameterKey": "key",
                     "ParameterValue": "foo,bar"}]
        self.assertEqual(returned, expected)

    def test_csv_syntax_single_quoted(self):
        p = self.get_param_object('cloudformation.CreateStack.Parameters')
        returned = self.simplify(
            p, ["ParameterKey=key,ParameterValue='foo,bar'"])
        expected = [{"ParameterKey": "key",
                     "ParameterValue": "foo,bar"}]
        self.assertEqual(returned, expected)

    def test_csv_syntax_errors(self):
        p = self.get_param_object('cloudformation.CreateStack.Parameters')
        error_msg = "Error parsing parameter --parameters.*should be"
        with self.assertRaisesRegexp(ParamError, error_msg):
            self.simplify(p, ['ParameterKey=key,ParameterValue="foo,bar'])
        with self.assertRaisesRegexp(ParamError, error_msg):
            self.simplify(p, ['ParameterKey=key,ParameterValue=foo,bar"'])
        with self.assertRaisesRegexp(ParamError, error_msg):
            self.simplify(p, ['ParameterKey=key,ParameterValue=""foo,bar"'])
        with self.assertRaisesRegexp(ParamError, error_msg):
            self.simplify(p, ['ParameterKey=key,ParameterValue="foo,bar\''])


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
        help_command = OperationHelpCommand(
            self.session, p.operation, None, {p.cli_name: argument},
            name='set-queue-attributes', event_class='sqs')
        help_command.param_shorthand.add_example_fn(p.cli_name, help_command)
        self.assertTrue(p.example_fn)
        doc_string = p.example_fn(p)
        self.assertIn(MAPHELP, doc_string)

    def test_gen_list_scalar_docs(self):
        p = self.get_param_object(
            'elb.RegisterInstancesWithLoadBalancer.Instances')
        argument = CLIArgument(p.cli_name, p, p.operation)
        help_command = OperationHelpCommand(
            self.session, p.operation, None,
            {p.cli_name: argument},
            name='register-instances-with-load-balancer',
            event_class='elb')
        help_command.param_shorthand.add_example_fn(p.cli_name, help_command)
        self.assertTrue(p.example_fn)
        doc_string = p.example_fn(p)
        self.assertEqual(doc_string,
                         '--instances InstanceId1 InstanceId2 InstanceId3')

    def test_gen_list_structure_of_scalars_docs(self):
        p = self.get_param_object('elb.CreateLoadBalancer.Listeners')
        argument = CLIArgument(p.cli_name, p, p.operation)
        help_command = OperationHelpCommand(
            self.session, p.operation, None, {p.cli_name: argument},
            name='create-load-balancer', event_class='elb')
        help_command.param_shorthand.add_example_fn(p.cli_name, help_command)
        self.assertTrue(p.example_fn)
        doc_string = p.example_fn(p)
        self.assertIn('Key value pairs, with multiple values separated by a space.', doc_string)
        self.assertIn('Protocol=string', doc_string)
        self.assertIn('LoadBalancerPort=integer', doc_string)
        self.assertIn('InstanceProtocol=string', doc_string)
        self.assertIn('InstancePort=integer', doc_string)
        self.assertIn('SSLCertificateId=string', doc_string)

    def test_gen_list_structure_multiple_scalar_docs(self):
        p = self.get_param_object('elastictranscoder.CreateJob.Playlists')
        argument = CLIArgument(p.cli_name, p, p.operation)
        help_command = OperationHelpCommand(
            self.session, p.operation, None, {p.cli_name: argument},
            name='create-job', event_class='elastictranscoder')
        help_command.param_shorthand.add_example_fn(p.cli_name, help_command)
        self.assertTrue(p.example_fn)
        doc_string = p.example_fn(p)
        s = 'Key value pairs, where values are separated by commas.\n--playlists Name=string1,Format=string1,OutputKeys=string1,string2'
        self.assertEqual(doc_string, s)


class TestUnpackJSONParams(BaseArgProcessTest):
    def setUp(self):
        super(TestUnpackJSONParams, self).setUp()
        self.simplify = ParamShorthand()

    def test_json_with_spaces(self):
        p = self.get_param_object('ec2.RunInstances.BlockDeviceMappings')
        # If a user specifies the json with spaces, it will show up as
        # a multi element list.  For example:
        # --block-device-mappings [{ "DeviceName":"/dev/sdf",
        # "VirtualName":"ephemeral0"}, {"DeviceName":"/dev/sdg",
        # "VirtualName":"ephemeral1" }]
        #
        # Will show up as:
        block_device_mapping = [
            '[{', 'DeviceName:/dev/sdf,', 'VirtualName:ephemeral0},',
            '{DeviceName:/dev/sdg,', 'VirtualName:ephemeral1', '}]']
        # The shell has removed the double quotes so this is invalid
        # JSON, but we should still raise a better exception.
        with self.assertRaises(ParamError) as e:
            unpack_cli_arg(p, block_device_mapping)
        # Parameter name should be in error message.
        self.assertIn('--block-device-mappings', str(e.exception))
        # The actual JSON itself should be in the error message.
        # Becaues this is a list, only the first element in the JSON
        # will show.  This will at least let customers know what
        # we tried to parse.
        self.assertIn('[{', str(e.exception))


if __name__ == '__main__':
    unittest.main()
