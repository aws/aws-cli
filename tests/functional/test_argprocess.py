# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import json

from botocore import xform_name
from botocore.compat import OrderedDict

from awscli.argprocess import (
    ParamError,
    ParamShorthandDocGen,
    ParamShorthandParser,
    detect_shape_structure,
    unpack_cli_arg,
)
from awscli.arguments import (
    BooleanArgument,
    CLIArgument,
    ListArgument,
)
from awscli.paramfile import LOCAL_PREFIX_MAP, URIArgumentHandler
from awscli.testutils import BaseCLIDriverTest, mock, temporary_file, unittest


class BaseArgProcessTest(BaseCLIDriverTest):
    def get_param_model(self, dotted_name):
        service_name, operation_name, param_name = dotted_name.split('.')
        service_model = self.session.get_service_model(service_name)
        operation = service_model.operation_model(operation_name)
        input_shape = operation.input_shape
        required_arguments = input_shape.required_members
        is_required = param_name in required_arguments
        member_shape = input_shape.members[param_name]
        type_name = member_shape.type_name
        cli_arg_name = xform_name(param_name, '-')
        if type_name == 'boolean':
            cls = BooleanArgument
        elif type_name == 'list':
            cls = ListArgument
        else:
            cls = CLIArgument
        return cls(cli_arg_name, member_shape, mock.Mock(), is_required)


class TestURIParams(BaseArgProcessTest):
    def setUp(self):
        super().setUp()
        self.uri_param = URIArgumentHandler(LOCAL_PREFIX_MAP.copy())

    def test_uri_param(self):
        p = self.get_param_model('ec2.DescribeInstances.Filters')
        with temporary_file('r+') as f:
            json_argument = json.dumps(
                [{"Name": "instance-id", "Values": ["i-1234"]}]
            )
            f.write(json_argument)
            f.flush()
            result = self.uri_param('event-name', p, f'file://{f.name}')
        self.assertEqual(result, json_argument)


class TestArgShapeDetection(BaseArgProcessTest):
    def assert_shape_type(self, spec, expected_type):
        p = self.get_param_model(spec)
        actual_structure = detect_shape_structure(p.argument_model)
        self.assertEqual(actual_structure, expected_type)

    def test_detect_scalar(self):
        self.assert_shape_type(
            'iam.AddRoleToInstanceProfile.RoleName', 'scalar'
        )

    def test_detect_list_of_strings(self):
        self.assert_shape_type('sns.AddPermission.AWSAccountId', 'list-scalar')

    def test_detect_structure_of_scalars(self):
        self.assert_shape_type(
            'elasticbeanstalk.CreateConfigurationTemplate.SourceConfiguration',
            'structure(scalars)',
        )

    def test_list_structure_scalars(self):
        self.assert_shape_type(
            'elb.RegisterInstancesWithLoadBalancer.Instances',
            'list-structure(scalar)',
        )

    def test_list_structure_scalars_2(self):
        self.assert_shape_type(
            'elb.CreateLoadBalancer.Listeners', 'list-structure(scalars)'
        )

    def test_list_structure_of_list_and_strings(self):
        self.assert_shape_type(
            'ec2.DescribeInstances.Filters',
            'list-structure(list-scalar, scalar)',
        )

    def test_map_scalar(self):
        self.assert_shape_type(
            'sqs.SetQueueAttributes.Attributes', 'map-scalar'
        )


class TestParamShorthand(BaseArgProcessTest):
    maxDiff = None

    def setUp(self):
        super().setUp()
        self._shorthand = ParamShorthandParser()

    def parse_shorthand(self, cli_argument, value, event_name=None):
        event = event_name
        if event is None:
            event = 'process-cli-arg.foo.bar'
        return self._shorthand(cli_argument, value, event)

    def test_simplify_structure_scalars(self):
        p = self.get_param_model(
            'elasticbeanstalk.CreateConfigurationTemplate.SourceConfiguration'
        )
        value = 'ApplicationName=foo,TemplateName=bar'
        json_value = '{"ApplicationName": "foo", "TemplateName": "bar"}'
        returned = self.parse_shorthand(p, value)
        json_version = unpack_cli_arg(p, json_value)
        self.assertEqual(returned, json_version)

    def test_simplify_map_scalar(self):
        p = self.get_param_model('sqs.SetQueueAttributes.Attributes')
        returned = self.parse_shorthand(p, 'VisibilityTimeout=15')
        json_version = unpack_cli_arg(p, '{"VisibilityTimeout": "15"}')
        self.assertEqual(returned, {'VisibilityTimeout': '15'})
        self.assertEqual(returned, json_version)

    def test_list_structure_scalars(self):
        p = self.get_param_model(
            'elb.RegisterInstancesWithLoadBalancer.Instances'
        )
        event_name = (
            'process-cli-arg.elb.register-instances-with-load-balancer'
        )
        # Because this is a list type param, we'll use nargs
        # with argparse which means the value will be presented
        # to us as a list.
        returned = self.parse_shorthand(
            p, ['instance-1', 'instance-2'], event_name
        )
        self.assertEqual(
            returned,
            [{'InstanceId': 'instance-1'}, {'InstanceId': 'instance-2'}],
        )

    def test_list_structure_list_scalar(self):
        p = self.get_param_model('ec2.DescribeInstances.Filters')
        expected = [
            {"Name": "instance-id", "Values": ["i-1", "i-2"]},
            {"Name": "architecture", "Values": ["i386"]},
        ]
        returned = self.parse_shorthand(
            p,
            [
                "Name=instance-id,Values=i-1,i-2",
                "Name=architecture,Values=i386",
            ],
        )
        self.assertEqual(returned, expected)

        # With spaces around the comma.
        returned2 = self.parse_shorthand(
            p,
            [
                "Name=instance-id, Values=i-1,i-2",
                "Name=architecture, Values=i386",
            ],
        )
        self.assertEqual(returned2, expected)

        # Strip off leading/trailing spaces.
        returned3 = self.parse_shorthand(
            p,
            [
                "Name = instance-id, Values = i-1,i-2",
                "Name = architecture, Values = i386",
            ],
        )
        self.assertEqual(returned3, expected)

    def test_parse_empty_values(self):
        # A value can be omitted and will default to an empty string.
        p = self.get_param_model('ec2.DescribeInstances.Filters')
        expected = [
            {"Name": "", "Values": ["i-1", "i-2"]},
            {"Name": "architecture", "Values": ['']},
        ]
        returned = self.parse_shorthand(
            p, ["Name=,Values=i-1,i-2", "Name=architecture,Values="]
        )
        self.assertEqual(returned, expected)

    def test_list_structure_list_scalar_2(self):
        p = self.get_param_model('emr.ModifyInstanceGroups.InstanceGroups')
        expected = [
            {"InstanceGroupId": "foo", "InstanceCount": 4},
            {"InstanceGroupId": "bar", "InstanceCount": 1},
        ]

        simplified = self.parse_shorthand(
            p,
            [
                "InstanceGroupId=foo,InstanceCount=4",
                "InstanceGroupId=bar,InstanceCount=1",
            ],
        )

        self.assertEqual(simplified, expected)

    def test_empty_value_of_list_structure(self):
        p = self.get_param_model('emr.ModifyInstanceGroups.InstanceGroups')
        expected = []
        simplified = self.parse_shorthand(p, [])
        self.assertEqual(simplified, expected)

    def test_list_structure_list_multiple_scalar(self):
        p = self.get_param_model('emr.ModifyInstanceGroups.InstanceGroups')
        returned = self.parse_shorthand(
            p,
            [
                'InstanceGroupId=foo,InstanceCount=3,'
                'EC2InstanceIdsToTerminate=i-12345,i-67890'
            ],
        )
        self.assertEqual(
            returned,
            [
                {
                    'EC2InstanceIdsToTerminate': ['i-12345', 'i-67890'],
                    'InstanceGroupId': 'foo',
                    'InstanceCount': 3,
                }
            ],
        )

    def test_list_structure_scalars_2(self):
        p = self.get_param_model('elb.CreateLoadBalancer.Listeners')
        expected = [
            {
                "Protocol": "protocol1",
                "LoadBalancerPort": 1,
                "InstanceProtocol": "instance_protocol1",
                "InstancePort": 2,
                "SSLCertificateId": "ssl_certificate_id1",
            },
            {
                "Protocol": "protocol2",
                "LoadBalancerPort": 3,
                "InstanceProtocol": "instance_protocol2",
                "InstancePort": 4,
                "SSLCertificateId": "ssl_certificate_id2",
            },
        ]
        returned = unpack_cli_arg(
            p,
            [
                '{"Protocol": "protocol1", "LoadBalancerPort": 1, '
                '"InstanceProtocol": "instance_protocol1", '
                '"InstancePort": 2, "SSLCertificateId": '
                '"ssl_certificate_id1"}',
                '{"Protocol": "protocol2", "LoadBalancerPort": 3, '
                '"InstanceProtocol": "instance_protocol2", '
                '"InstancePort": 4, "SSLCertificateId": '
                '"ssl_certificate_id2"}',
            ],
        )
        self.assertEqual(returned, expected)
        simplified = self.parse_shorthand(
            p,
            [
                'Protocol=protocol1,LoadBalancerPort=1,'
                'InstanceProtocol=instance_protocol1,'
                'InstancePort=2,SSLCertificateId=ssl_certificate_id1',
                'Protocol=protocol2,LoadBalancerPort=3,'
                'InstanceProtocol=instance_protocol2,'
                'InstancePort=4,SSLCertificateId=ssl_certificate_id2',
            ],
        )
        self.assertEqual(simplified, expected)

    def test_keyval_with_long_values(self):
        p = self.get_param_model('dynamodb.UpdateTable.ProvisionedThroughput')
        value = 'WriteCapacityUnits=10,ReadCapacityUnits=10'
        returned = self.parse_shorthand(p, value)
        self.assertEqual(
            returned, {'WriteCapacityUnits': 10, 'ReadCapacityUnits': 10}
        )

    def test_error_messages_for_structure_scalar(self):
        p = self.get_param_model(
            'elasticbeanstalk.CreateConfigurationTemplate.SourceConfiguration'
        )
        value = 'ApplicationName:foo,TemplateName=bar'
        error_msg = (
            "Error parsing parameter '--source-configuration'.*Expected"
        )
        with self.assertRaisesRegex(ParamError, error_msg):
            self.parse_shorthand(p, value)

    def test_improper_separator(self):
        # If the user uses ':' instead of '=', we should give a good
        # error message.
        p = self.get_param_model(
            'elasticbeanstalk.CreateConfigurationTemplate.SourceConfiguration'
        )
        value = 'ApplicationName:foo,TemplateName:bar'
        error_msg = (
            "Error parsing parameter '--source-configuration'.*Expected"
        )
        with self.assertRaisesRegex(ParamError, error_msg):
            self.parse_shorthand(p, value)

    def test_improper_separator_for_filters_param(self):
        p = self.get_param_model('ec2.DescribeInstances.Filters')
        error_msg = "Error parsing parameter '--filters'.*Expected"
        with self.assertRaisesRegex(ParamError, error_msg):
            self.parse_shorthand(p, ["Name:tag:Name,Values:foo"])

    def test_csv_syntax_escaped(self):
        p = self.get_param_model('cloudformation.CreateStack.Parameters')
        returned = self.parse_shorthand(
            p, [r"ParameterKey=key,ParameterValue=foo\,bar"]
        )
        expected = [{"ParameterKey": "key", "ParameterValue": "foo,bar"}]
        self.assertEqual(returned, expected)

    def test_csv_syntax_double_quoted(self):
        p = self.get_param_model('cloudformation.CreateStack.Parameters')
        returned = self.parse_shorthand(
            p, ['ParameterKey=key,ParameterValue="foo,bar"']
        )
        expected = [{"ParameterKey": "key", "ParameterValue": "foo,bar"}]
        self.assertEqual(returned, expected)

    def test_csv_syntax_single_quoted(self):
        p = self.get_param_model('cloudformation.CreateStack.Parameters')
        returned = self.parse_shorthand(
            p, ["ParameterKey=key,ParameterValue='foo,bar'"]
        )
        expected = [{"ParameterKey": "key", "ParameterValue": "foo,bar"}]
        self.assertEqual(returned, expected)

    def test_csv_syntax_errors(self):
        p = self.get_param_model('cloudformation.CreateStack.Parameters')
        error_msg = "Error parsing parameter '--parameters'.*Expected"
        with self.assertRaisesRegex(ParamError, error_msg):
            self.parse_shorthand(
                p, ['ParameterKey=key,ParameterValue="foo,bar']
            )
        with self.assertRaisesRegex(ParamError, error_msg):
            self.parse_shorthand(
                p, ['ParameterKey=key,ParameterValue=foo,bar"']
            )
        with self.assertRaisesRegex(ParamError, error_msg):
            self.parse_shorthand(
                p, ['ParameterKey=key,ParameterValue=""foo,bar"']
            )
        with self.assertRaisesRegex(ParamError, error_msg):
            self.parse_shorthand(
                p, ['ParameterKey=key,ParameterValue="foo,bar\'']
            )


class TestDocGen(BaseArgProcessTest):
    def setUp(self):
        super().setUp()
        self.shorthand_documenter = ParamShorthandDocGen()
        self.service_name = 'foo'
        self.operation_name = 'bar'

    def get_generated_example_for(self, argument):
        return self.shorthand_documenter.generate_shorthand_example(
            argument, self.service_name, self.operation_name
        )

    def assert_generated_example_contains(self, argument, expected_to_contain):
        generated_docs = self.get_generated_example_for(argument)
        self.assertIn(expected_to_contain, generated_docs)

    def assert_generated_example_is(self, argument, expected_docs):
        generated_docs = self.get_generated_example_for(argument)
        self.assertEqual(generated_docs, expected_docs)

    def test_gen_map_type_docs(self):
        argument = self.get_param_model('sqs.SetQueueAttributes.Attributes')
        expected_example_str = (
            "KeyName1=string,KeyName2=string\n\n"
            "Where valid key names are:\n"
        )
        self.assert_generated_example_contains(argument, expected_example_str)

    def test_gen_list_scalar_docs(self):
        self.service_name = 'elb'
        self.operation_name = 'register-instances-with-load-balancer'
        argument = self.get_param_model(
            'elb.RegisterInstancesWithLoadBalancer.Instances'
        )
        doc_string = '--instances InstanceId1 InstanceId2 InstanceId3'
        self.assert_generated_example_is(argument, doc_string)

    def test_gen_list_structure_of_scalars_docs(self):
        argument = self.get_param_model('elb.CreateLoadBalancer.Listeners')
        generated_example = self.get_generated_example_for(argument)
        self.assertIn('Protocol=string', generated_example)
        self.assertIn('LoadBalancerPort=integer', generated_example)
        self.assertIn('InstanceProtocol=string', generated_example)
        self.assertIn('InstancePort=integer', generated_example)
        self.assertIn('SSLCertificateId=string', generated_example)

    def test_gen_list_structure_list_scalar_scalar_docs(self):
        # Verify that we have *two* top level list items displayed,
        # so we make it clear that multiple values are separated by spaces.
        argument = self.get_param_model('ec2.DescribeInstances.Filters')
        generated_example = self.get_generated_example_for(argument)
        self.assertIn('Name=string,Values=string,string', generated_example)

    def test_can_gen_recursive_structure(self):
        argument = self.get_param_model('dynamodb.PutItem.Item')
        self.get_generated_example_for(argument)


class TestUnpackJSONParams(BaseArgProcessTest):
    def setUp(self):
        super().setUp()
        self.simplify = ParamShorthandParser()

    def test_json_with_spaces(self):
        p = self.get_param_model('ec2.RunInstances.BlockDeviceMappings')
        # If a user specifies the json with spaces, it will show up as
        # a multi element list.  For example:
        # --block-device-mappings [{ "DeviceName":"/dev/sdf",
        # "VirtualName":"ephemeral0"}, {"DeviceName":"/dev/sdg",
        # "VirtualName":"ephemeral1" }]
        #
        # Will show up as:
        block_device_mapping = [
            '[{',
            'DeviceName:/dev/sdf,',
            'VirtualName:ephemeral0},',
            '{DeviceName:/dev/sdg,',
            'VirtualName:ephemeral1',
            '}]',
        ]
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


class TestJSONValueHeaderParams(BaseArgProcessTest):
    def setUp(self):
        super().setUp()
        self.p = self.get_param_model(
            'lex-runtime.PostContent.sessionAttributes'
        )

    def test_json_value_dict(self):
        value = '{"foo": "bar"}'
        self.assertEqual(
            unpack_cli_arg(self.p, value), OrderedDict([('foo', 'bar')])
        )

    def test_json_value_list(self):
        value = '["foo", "bar"]'
        self.assertEqual(unpack_cli_arg(self.p, value), ['foo', 'bar'])

    def test_json_value_int(self):
        value = "5"
        self.assertEqual(unpack_cli_arg(self.p, value), 5)

    def test_json_value_float(self):
        value = "1.2"
        self.assertEqual(unpack_cli_arg(self.p, value), 1.2)

    def test_json_value_string(self):
        value = '"5"'
        self.assertEqual(unpack_cli_arg(self.p, value), '5')

    def test_json_value_boolean(self):
        value = "true"
        self.assertEqual(unpack_cli_arg(self.p, value), True)
        value = "false"
        self.assertEqual(unpack_cli_arg(self.p, value), False)

    def test_json_value_null(self):
        value = 'null'
        self.assertEqual(unpack_cli_arg(self.p, value), None)

    def test_json_value_decode_error(self):
        value = 'invalid string to be serialized'
        with self.assertRaises(ParamError):
            unpack_cli_arg(self.p, value)


if __name__ == '__main__':
    unittest.main()
