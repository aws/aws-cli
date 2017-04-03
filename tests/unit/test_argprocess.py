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
import json

import mock
from botocore import xform_name
from botocore import model
from botocore.compat import OrderedDict

from awscli.testutils import unittest
from awscli.testutils import BaseCLIDriverTest
from awscli.testutils import temporary_file
from awscli.help import OperationHelpCommand
from awscli.argprocess import detect_shape_structure
from awscli.argprocess import unpack_cli_arg
from awscli.argprocess import ParamShorthandParser
from awscli.argprocess import ParamShorthandDocGen
from awscli.argprocess import ParamError
from awscli.argprocess import ParamUnknownKeyError
from awscli.argprocess import uri_param
from awscli.arguments import CustomArgument, CLIArgument
from awscli.arguments import ListArgument, BooleanArgument
from awscli.arguments import create_argument_model_from_schema


# These tests use real service types so that we can
# verify the real shapes of services.
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

    def create_argument(self, argument_model, argument_name=None):
        if argument_name is None:
            argument_name = 'foo'
        argument = mock.Mock()
        m = model.DenormalizedStructureBuilder().with_members(
            argument_model)
        argument.argument_model = m.build_model()
        argument.name = argument_name
        argument.cli_name = "--" + argument_name
        return argument


class TestURIParams(BaseArgProcessTest):
    def test_uri_param(self):
        p = self.get_param_model('ec2.DescribeInstances.Filters')
        with temporary_file('r+') as f:
            json_argument = json.dumps([{"Name": "instance-id", "Values": ["i-1234"]}])
            f.write(json_argument)
            f.flush()
            result = uri_param('event-name', p, 'file://%s' % f.name)
        self.assertEqual(result, json_argument)

    def test_uri_param_no_paramfile_false(self):
        p = self.get_param_model('ec2.DescribeInstances.Filters')
        p.no_paramfile = False
        with temporary_file('r+') as f:
            json_argument = json.dumps([{"Name": "instance-id", "Values": ["i-1234"]}])
            f.write(json_argument)
            f.flush()
            result = uri_param('event-name', p, 'file://%s' % f.name)
        self.assertEqual(result, json_argument)

    def test_uri_param_no_paramfile_true(self):
        p = self.get_param_model('ec2.DescribeInstances.Filters')
        p.no_paramfile = True
        with temporary_file('r+') as f:
            json_argument = json.dumps([{"Name": "instance-id", "Values": ["i-1234"]}])
            f.write(json_argument)
            f.flush()
            result = uri_param('event-name', p, 'file://%s' % f.name)
        self.assertEqual(result, None)


class TestArgShapeDetection(BaseArgProcessTest):

    def assert_shape_type(self, spec, expected_type):
        p = self.get_param_model(spec)
        actual_structure = detect_shape_structure(p.argument_model)
        self.assertEqual(actual_structure, expected_type)

    def assert_custom_shape_type(self, schema, expected_type):
        argument_model = create_argument_model_from_schema(schema)
        argument = CustomArgument('test', argument_model=argument_model)
        actual_structure = detect_shape_structure(argument.argument_model)
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

    def test_struct_list_scalar(self):
        self.assert_custom_shape_type({
            "type": "object",
            "properties": {
                "Consistent": {
                    "type": "boolean",
                },
                "Args": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            }
        }, 'structure(list-scalar, scalar)')

    def test_recursive_shape(self):
        shapes = {
            'InputStructure': {
                'type': 'structure',
                'members': {
                    'A': {'shape': 'RecursiveShape'}
                }
            },
            'RecursiveShape': {
                'type': 'structure',
                'members': {
                    'B': {'shape': 'StringType'},
                    'C': {'shape': 'RecursiveShape'},
                }
            },
            'StringType': {
                'type': 'string'
            }
        }
        shape = model.StructureShape(shape_name='InputStructure',
                                     shape_model=shapes['InputStructure'],
                                     shape_resolver=model.ShapeResolver(
                                         shape_map=shapes))
        self.assertIn('recursive', detect_shape_structure(shape))


class TestParamShorthand(BaseArgProcessTest):
    maxDiff = None

    def setUp(self):
        super(TestParamShorthand, self).setUp()
        self._shorthand = ParamShorthandParser()

    def parse_shorthand(self, cli_argument, value, event_name=None):
        event = event_name
        if event is None:
            event = 'process-cli-arg.foo.bar'
        return self._shorthand(cli_argument, value, event)

    def test_simplify_structure_scalars(self):
        p = self.get_param_model(
            'elasticbeanstalk.CreateConfigurationTemplate.SourceConfiguration')
        value = 'ApplicationName=foo,TemplateName=bar'
        json_value = '{"ApplicationName": "foo", "TemplateName": "bar"}'
        returned = self.parse_shorthand(p, value)
        json_version = unpack_cli_arg(p, json_value)
        self.assertEqual(returned, json_version)

    def test_flattens_marked_single_member_structure_list(self):
        argument = self.create_argument({
            'Arg': {
                'type': 'list',
                'member': {
                    'type': 'structure',
                    'members': {
                        'Bar': {'type': 'string'}
                    }
                }
            }
        }, 'arg')
        argument.argument_model = argument.argument_model.members['Arg']
        value = ['foo', 'baz']
        uses_old_list = 'awscli.argprocess.ParamShorthand._uses_old_list_case'
        with mock.patch(uses_old_list, mock.Mock(return_value=True)):
            returned = self.parse_shorthand(argument, value)
        self.assertEqual(returned, [{"Bar": "foo"}, {"Bar": "baz"}])

    def test_does_not_flatten_unmarked_single_member_structure_list(self):
        argument = self.create_argument({
            'Arg': {
                'type': 'list',
                'member': {
                    'type': 'structure',
                    'members': {
                        'Bar': {'type': 'string'}
                    }
                }
            }
        }, 'arg')
        argument.argument_model = argument.argument_model.members['Arg']
        value = ['Bar=foo', 'Bar=baz']
        uses_old_list = 'awscli.argprocess.ParamShorthand._uses_old_list_case'
        with mock.patch(uses_old_list, mock.Mock(return_value=False)):
            returned = self.parse_shorthand(argument, value)
        self.assertEqual(returned, [{"Bar": "foo"}, {"Bar": "baz"}])

    def test_parse_boolean_shorthand(self):
        bool_param = mock.Mock()
        bool_param.cli_type_name = 'boolean'
        bool_param.argument_model.type_name = 'boolean'
        self.assertTrue(unpack_cli_arg(bool_param, True))
        self.assertTrue(unpack_cli_arg(bool_param, 'True'))
        self.assertTrue(unpack_cli_arg(bool_param, 'true'))

        self.assertFalse(unpack_cli_arg(bool_param, False))
        self.assertFalse(unpack_cli_arg(bool_param, 'False'))
        self.assertFalse(unpack_cli_arg(bool_param, 'false'))

    def test_simplify_map_scalar(self):
        p = self.get_param_model('sqs.SetQueueAttributes.Attributes')
        returned = self.parse_shorthand(p, 'VisibilityTimeout=15')
        json_version = unpack_cli_arg(p, '{"VisibilityTimeout": "15"}')
        self.assertEqual(returned, {'VisibilityTimeout': '15'})
        self.assertEqual(returned, json_version)

    def test_list_structure_scalars(self):
        p = self.get_param_model(
            'elb.RegisterInstancesWithLoadBalancer.Instances')
        event_name = ('process-cli-arg.elb'
                      '.register-instances-with-load-balancer')
        # Because this is a list type param, we'll use nargs
        # with argparse which means the value will be presented
        # to us as a list.
        returned = self.parse_shorthand(
            p, ['instance-1', 'instance-2'], event_name)
        self.assertEqual(returned, [{'InstanceId': 'instance-1'},
                                    {'InstanceId': 'instance-2'}])

    def test_list_structure_list_scalar(self):
        p = self.get_param_model('ec2.DescribeInstances.Filters')
        expected = [{"Name": "instance-id", "Values": ["i-1", "i-2"]},
                    {"Name": "architecture", "Values": ["i386"]}]
        returned = self.parse_shorthand(
            p, ["Name=instance-id,Values=i-1,i-2",
                "Name=architecture,Values=i386"])
        self.assertEqual(returned, expected)

        # With spaces around the comma.
        returned2 = self.parse_shorthand(
            p, ["Name=instance-id, Values=i-1,i-2",
                "Name=architecture, Values=i386"])
        self.assertEqual(returned2, expected)

        # Strip off leading/trailing spaces.
        returned3 = self.parse_shorthand(
            p, ["Name = instance-id, Values = i-1,i-2",
                "Name = architecture, Values = i386"])
        self.assertEqual(returned3, expected)

    def test_parse_empty_values(self):
        # A value can be omitted and will default to an empty string.
        p = self.get_param_model('ec2.DescribeInstances.Filters')
        expected = [{"Name": "", "Values": ["i-1", "i-2"]},
                    {"Name": "architecture", "Values": ['']}]
        returned = self.parse_shorthand(
            p, ["Name=,Values=i-1,i-2",
                "Name=architecture,Values="])
        self.assertEqual(returned, expected)

    def test_list_structure_list_scalar_2(self):
        p = self.get_param_model('emr.ModifyInstanceGroups.InstanceGroups')
        expected = [
            {"InstanceGroupId": "foo",
             "InstanceCount": 4},
            {"InstanceGroupId": "bar",
             "InstanceCount": 1}
        ]

        simplified = self.parse_shorthand(p, [
            "InstanceGroupId=foo,InstanceCount=4",
            "InstanceGroupId=bar,InstanceCount=1"
        ])

        self.assertEqual(simplified, expected)

    def test_empty_value_of_list_structure(self):
        p = self.get_param_model('emr.ModifyInstanceGroups.InstanceGroups')
        expected = []
        simplified = self.parse_shorthand(p, [])
        self.assertEqual(simplified, expected)

    def test_list_structure_list_multiple_scalar(self):
        p = self.get_param_model(
            'emr.ModifyInstanceGroups.InstanceGroups')
        returned = self.parse_shorthand(
            p,
            ['InstanceGroupId=foo,InstanceCount=3,'
             'EC2InstanceIdsToTerminate=i-12345,i-67890'])
        self.assertEqual(returned, [{'EC2InstanceIdsToTerminate': [
                                         'i-12345', 'i-67890'
                                     ],
                                     'InstanceGroupId': 'foo',
                                     'InstanceCount': 3}])

    def test_list_structure_scalars_2(self):
        p = self.get_param_model('elb.CreateLoadBalancer.Listeners')
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
        self.assertEqual(returned, expected)
        simplified = self.parse_shorthand(p, [
            'Protocol=protocol1,LoadBalancerPort=1,'
            'InstanceProtocol=instance_protocol1,'
            'InstancePort=2,SSLCertificateId=ssl_certificate_id1',
            'Protocol=protocol2,LoadBalancerPort=3,'
            'InstanceProtocol=instance_protocol2,'
            'InstancePort=4,SSLCertificateId=ssl_certificate_id2'
        ])
        self.assertEqual(simplified, expected)

    def test_keyval_with_long_values(self):
        p = self.get_param_model(
            'dynamodb.UpdateTable.ProvisionedThroughput')
        value = 'WriteCapacityUnits=10,ReadCapacityUnits=10'
        returned = self.parse_shorthand(p, value)
        self.assertEqual(returned, {'WriteCapacityUnits': 10,
                                    'ReadCapacityUnits': 10})

    def test_error_messages_for_structure_scalar(self):
        p = self.get_param_model(
            'elasticbeanstalk.CreateConfigurationTemplate.SourceConfiguration')
        value = 'ApplicationName:foo,TemplateName=bar'
        error_msg = "Error parsing parameter '--source-configuration'.*Expected"
        with self.assertRaisesRegexp(ParamError, error_msg):
            self.parse_shorthand(p, value)

    def test_improper_separator(self):
        # If the user uses ':' instead of '=', we should give a good
        # error message.
        p = self.get_param_model(
            'elasticbeanstalk.CreateConfigurationTemplate.SourceConfiguration')
        value = 'ApplicationName:foo,TemplateName:bar'
        error_msg = "Error parsing parameter '--source-configuration'.*Expected"
        with self.assertRaisesRegexp(ParamError, error_msg):
            self.parse_shorthand(p, value)

    def test_improper_separator_for_filters_param(self):
        p = self.get_param_model('ec2.DescribeInstances.Filters')
        error_msg = "Error parsing parameter '--filters'.*Expected"
        with self.assertRaisesRegexp(ParamError, error_msg):
            self.parse_shorthand(p, ["Name:tag:Name,Values:foo"])

    def test_csv_syntax_escaped(self):
        p = self.get_param_model('cloudformation.CreateStack.Parameters')
        returned = self.parse_shorthand(
            p, ["ParameterKey=key,ParameterValue=foo\,bar"])
        expected = [{"ParameterKey": "key",
                     "ParameterValue": "foo,bar"}]
        self.assertEqual(returned, expected)

    def test_csv_syntax_double_quoted(self):
        p = self.get_param_model('cloudformation.CreateStack.Parameters')
        returned = self.parse_shorthand(
            p, ['ParameterKey=key,ParameterValue="foo,bar"'])
        expected = [{"ParameterKey": "key",
                     "ParameterValue": "foo,bar"}]
        self.assertEqual(returned, expected)

    def test_csv_syntax_single_quoted(self):
        p = self.get_param_model('cloudformation.CreateStack.Parameters')
        returned = self.parse_shorthand(
            p, ["ParameterKey=key,ParameterValue='foo,bar'"])
        expected = [{"ParameterKey": "key",
                     "ParameterValue": "foo,bar"}]
        self.assertEqual(returned, expected)

    def test_csv_syntax_errors(self):
        p = self.get_param_model('cloudformation.CreateStack.Parameters')
        error_msg = "Error parsing parameter '--parameters'.*Expected"
        with self.assertRaisesRegexp(ParamError, error_msg):
            self.parse_shorthand(p, ['ParameterKey=key,ParameterValue="foo,bar'])
        with self.assertRaisesRegexp(ParamError, error_msg):
            self.parse_shorthand(p, ['ParameterKey=key,ParameterValue=foo,bar"'])
        with self.assertRaisesRegexp(ParamError, error_msg):
            self.parse_shorthand(p, ['ParameterKey=key,ParameterValue=""foo,bar"'])
        with self.assertRaisesRegexp(ParamError, error_msg):
            self.parse_shorthand(p, ['ParameterKey=key,ParameterValue="foo,bar\''])


class TestParamShorthandCustomArguments(BaseArgProcessTest):

    def setUp(self):
        super(TestParamShorthandCustomArguments, self).setUp()
        self.shorthand = ParamShorthandParser()

    def test_list_structure_list_scalar_custom_arg(self):
        schema = {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'Name': {
                        'type': 'string'
                    },
                    'Args': {
                        'type': 'array',
                        'items': {
                            'type': 'string'
                        }
                    }
                }
            }
        }
        argument_model = create_argument_model_from_schema(schema)
        cli_argument = CustomArgument('foo', argument_model=argument_model)

        expected = [
            {"Name": "foo",
             "Args": ["a", "k1=v1", "b"]},
            {"Name": "bar",
             "Args": ["baz"]},
            {"Name": "single_kv",
             "Args": ["key=value"]},
            {"Name": "single_v",
             "Args": ["value"]}
        ]

        simplified = self.shorthand(cli_argument, [
            "Name=foo,Args=[a,k1=v1,b]",
            "Name=bar,Args=baz",
            "Name=single_kv,Args=[key=value]",
            "Name=single_v,Args=[value]"
        ], 'process-cli-arg.foo.bar')

        self.assertEqual(simplified, expected)

    def test_struct_list_scalars(self):
        schema = {
            "type": "object",
            "properties": {
                "Consistent": {
                    "type": "boolean",
                },
                "Args": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            }
        }
        argument_model = create_argument_model_from_schema(schema)
        cli_argument = CustomArgument('test', argument_model=argument_model)

        returned = self.shorthand(
            cli_argument, 'Consistent=true,Args=foo1,foo2',
            'process-cli-arg.foo.bar')
        self.assertEqual(returned, {'Consistent': True,
                                    'Args': ['foo1', 'foo2']})


class TestDocGen(BaseArgProcessTest):
    # These aren't very extensive doc tests, as we want to stay somewhat
    # flexible and allow the docs to slightly change without breaking these
    # tests.
    def setUp(self):
        super(TestDocGen, self).setUp()
        self.shorthand_documenter = ParamShorthandDocGen()
        self.service_name = 'foo'
        self.operation_name = 'bar'

    def get_generated_example_for(self, argument):
        # Returns a string containing the generated documentation.
        return self.shorthand_documenter.generate_shorthand_example(
            argument, self.service_name, self.operation_name)

    def assert_generated_example_is(self, argument, expected_docs):
        generated_docs = self.get_generated_example_for(argument)
        self.assertEqual(generated_docs, expected_docs)

    def assert_generated_example_contains(self, argument, expected_to_contain):
        generated_docs = self.get_generated_example_for(argument)
        self.assertIn(expected_to_contain, generated_docs)

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
            'elb.RegisterInstancesWithLoadBalancer.Instances')
        doc_string = '--instances InstanceId1 InstanceId2 InstanceId3'
        self.assert_generated_example_is(argument, doc_string)

    def test_flattens_marked_single_member_structure_list(self):
        argument = self.create_argument({
            'Arg': {
                'type': 'list',
                'member': {
                    'type': 'structure',
                    'members': {
                        'Bar': {'type': 'string'}
                    }
                }
            }
        }, 'arg')
        argument.argument_model = argument.argument_model.members['Arg']
        uses_old_list = 'awscli.argprocess.ParamShorthand._uses_old_list_case'
        with mock.patch(uses_old_list, mock.Mock(return_value=True)):
            self.assert_generated_example_is(argument, '--arg Bar1 Bar2 Bar3')

    def test_does_not_flatten_unmarked_single_member_structure_list(self):
        argument = self.create_argument({
            'Arg': {
                'type': 'list',
                'member': {
                    'type': 'structure',
                    'members': {
                        'Bar': {'type': 'string'}
                    }
                }
            }
        }, 'arg')
        argument.argument_model = argument.argument_model.members['Arg']
        uses_old_list = 'awscli.argprocess.ParamShorthand._uses_old_list_case'
        with mock.patch(uses_old_list, mock.Mock(return_value=False)):
            self.assert_generated_example_is(argument, 'Bar=string ...')

    def test_gen_list_structure_of_scalars_docs(self):
        argument = self.get_param_model('elb.CreateLoadBalancer.Listeners')
        generated_example = self.get_generated_example_for(argument)
        self.assertIn('Protocol=string', generated_example)
        self.assertIn('LoadBalancerPort=integer', generated_example)
        self.assertIn('InstanceProtocol=string', generated_example)
        self.assertIn('InstancePort=integer', generated_example)
        self.assertIn('SSLCertificateId=string', generated_example)

    def test_gen_list_structure_multiple_scalar_docs(self):
        expected = (
            'Scalar1=string,'
            'Scalar2=string,'
            'List1=string,string ...'
        )
        m = model.DenormalizedStructureBuilder().with_members(OrderedDict([
            ('List', {'type': 'list',
                      'member': {
                          'type': 'structure',
                          'members': OrderedDict([
                              ('Scalar1', {'type': 'string'}),
                              ('Scalar2', {'type': 'string'}),
                              ('List1', {
                                  'type': 'list',
                                  'member': {'type': 'string'},
                              }),
                          ]),
                      }}),
        ])).build_model().members['List']
        argument = mock.Mock()
        argument.argument_model = m
        argument.name = 'foo'
        argument.cli_name = '--foo'
        generated_example = self.get_generated_example_for(argument)
        self.assertIn(expected, generated_example)

    def test_gen_list_structure_list_scalar_scalar_docs(self):
        # Verify that we have *two* top level list items displayed,
        # so we make it clear that multiple values are separated by spaces.
        argument = self.get_param_model('ec2.DescribeInstances.Filters')
        generated_example = self.get_generated_example_for(argument)
        self.assertIn('Name=string,Values=string,string',
                      generated_example)

    def test_gen_structure_list_scalar_docs(self):
        argument = self.create_argument(OrderedDict([
            ('Consistent', {'type': 'boolean'}),
            ('Args', {'type': 'list', 'member': {'type': 'string'}}),
        ]), 'foo')
        generated_example = self.get_generated_example_for(argument)
        self.assertIn('Consistent=boolean,Args=string,string',
                      generated_example)

    def test_can_gen_recursive_structure(self):
        argument = self.get_param_model('dynamodb.PutItem.Item')
        generated_example = self.get_generated_example_for(argument)

    def test_can_document_nested_structs(self):
        argument = self.get_param_model('ec2.RunInstances.BlockDeviceMappings')
        generated_example = self.get_generated_example_for(argument)
        self.assertIn('Ebs={SnapshotId=string', generated_example)

    def test_can_document_nested_lists(self):
        argument = self.create_argument({
            'A': {
                'type': 'list',
                'member': {
                    'type': 'list',
                    'member': {'type': 'string'},
                },
            },
        })
        generated_example = self.get_generated_example_for(argument)
        self.assertIn('A=[[string,string],[string,string]]', generated_example)

    def test_can_generated_nested_maps(self):
        argument = self.create_argument({
            'A': {
                'type': 'map',
                'key': {'type': 'string'},
                'value': {'type': 'string'}
            },
        })
        generated_example = self.get_generated_example_for(argument)
        self.assertIn('A={KeyName1=string,KeyName2=string}', generated_example)

    def test_list_of_structures_with_triple_dots(self):
        list_shape = {
            'type': 'list',
            'member': {'shape': 'StructShape'},
        }
        shapes = {
            'Top': list_shape,
            'String': {'type': 'string'},
            'StructShape': {
                'type': 'structure',
                'members': OrderedDict([
                    ('A', {'shape': 'String'}),
                    ('B', {'shape': 'String'}),
                ])
            }
        }
        m = model.ListShape(
            shape_name='Top',
            shape_model=list_shape,
            shape_resolver=model.ShapeResolver(shapes))
        argument = mock.Mock()
        argument.argument_model = m
        argument.name = 'foo'
        argument.cli_name = '--foo'
        generated_example = self.get_generated_example_for(argument)
        self.assertIn('A=string,B=string ...', generated_example)

    def test_handle_special_case_value_struct_not_documented(self):
        argument = self.create_argument({
            'Value': {'type': 'string'}
        })
        generated_example = self.get_generated_example_for(argument)
        # This is one of the special cases, we shouldn't generate any
        # shorthand example for this shape.
        self.assertIsNone(generated_example)

    def test_can_document_recursive_struct(self):
        # It's a little more work to set up a recursive
        # shape because DenormalizedStructureBuilder cannot handle
        # recursion.
        struct_shape = {
            'type': 'structure',
            'members': OrderedDict([
                ('Recurse', {'shape': 'SubShape'}),
                ('Scalar', {'shape': 'String'}),
            ]),
        }
        shapes = {
            'Top': struct_shape,
            'String': {'type': 'string'},
            'SubShape': {
                'type': 'structure',
                'members': OrderedDict([
                    ('SubRecurse', {'shape': 'Top'}),
                    ('Scalar', {'shape': 'String'}),
                ]),
            }
        }
        m = model.StructureShape(
            shape_name='Top',
            shape_model=struct_shape,
            shape_resolver=model.ShapeResolver(shapes))
        argument = mock.Mock()
        argument.argument_model = m
        argument.name = 'foo'
        argument.cli_name = '--foo'
        generated_example = self.get_generated_example_for(argument)
        self.assertIn(
            'Recurse={SubRecurse={( ... recursive ... ),Scalar=string},'
            'Scalar=string},Scalar=string',
            generated_example)

    def test_skip_deeply_nested_shorthand(self):
        # The eventual goal is to have a better way to document
        # deeply nested shorthand params, but for now, we'll
        # only document shorthand params up to a certain stack level.
        argument = self.create_argument({
            'A': {
                'type': 'structure',
                'members': {
                    'B': {
                        'type': 'structure',
                        'members': {
                            'C': {
                                'type': 'structure',
                                'members': {
                                    'D': {'type': 'string'},
                                }
                            }
                        }
                    }
                }
            },
        })
        generated_example = self.get_generated_example_for(argument)
        self.assertEqual(generated_example, '')


class TestUnpackJSONParams(BaseArgProcessTest):
    def setUp(self):
        super(TestUnpackJSONParams, self).setUp()
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


class TestJSONValueHeaderParams(BaseArgProcessTest):
    def setUp(self):
        super(TestJSONValueHeaderParams, self).setUp()
        self.p = self.get_param_model(
            'lex-runtime.PostContent.sessionAttributes')

    def test_json_value_dict(self):
        value = '{"foo": "bar"}'
        self.assertEqual(unpack_cli_arg(self.p, value),
                         OrderedDict([('foo', 'bar')]))

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
