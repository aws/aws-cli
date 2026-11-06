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

from botocore import model
from botocore.compat import OrderedDict

from awscli.argparser import ArgTableArgParser
from awscli.argprocess import (
    ParamShorthandDocGen,
    ParamShorthandParser,
    detect_shape_structure,
    unpack_cli_arg,
)
from awscli.arguments import (
    BooleanArgument,
    CLIArgument,
    CustomArgument,
    create_argument_model_from_schema,
)
from awscli.testutils import mock, unittest


class BaseArgProcessTest(unittest.TestCase):
    def create_argument(self, argument_model, argument_name=None):
        if argument_name is None:
            argument_name = 'foo'
        argument = mock.Mock()
        m = model.DenormalizedStructureBuilder().with_members(argument_model)
        argument.argument_model = m.build_model()
        argument.name = argument_name
        argument.cli_name = "--" + argument_name
        return argument


class TestArgShapeDetection(BaseArgProcessTest):
    def test_struct_list_scalar(self):
        schema = {
            "type": "object",
            "properties": {
                "Consistent": {
                    "type": "boolean",
                },
                "Args": {"type": "array", "items": {"type": "string"}},
            },
        }
        argument_model = create_argument_model_from_schema(schema)
        argument = CustomArgument('test', argument_model=argument_model)
        actual_structure = detect_shape_structure(argument.argument_model)
        self.assertEqual(actual_structure, 'structure(list-scalar, scalar)')

    def test_recursive_shape(self):
        shapes = {
            'InputStructure': {
                'type': 'structure',
                'members': {'A': {'shape': 'RecursiveShape'}},
            },
            'RecursiveShape': {
                'type': 'structure',
                'members': {
                    'B': {'shape': 'StringType'},
                    'C': {'shape': 'RecursiveShape'},
                },
            },
            'StringType': {'type': 'string'},
        }
        shape = model.StructureShape(
            shape_name='InputStructure',
            shape_model=shapes['InputStructure'],
            shape_resolver=model.ShapeResolver(shape_map=shapes),
        )
        self.assertIn('recursive', detect_shape_structure(shape))


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

    def test_flattens_marked_single_member_structure_list(self):
        argument = self.create_argument(
            {
                'Arg': {
                    'type': 'list',
                    'member': {
                        'type': 'structure',
                        'members': {'Bar': {'type': 'string'}},
                    },
                }
            },
            'arg',
        )
        argument.argument_model = argument.argument_model.members['Arg']
        value = ['foo', 'baz']
        uses_old_list = 'awscli.argprocess.ParamShorthand._uses_old_list_case'
        with mock.patch(uses_old_list, mock.Mock(return_value=True)):
            returned = self.parse_shorthand(argument, value)
        self.assertEqual(returned, [{"Bar": "foo"}, {"Bar": "baz"}])

    def test_does_not_flatten_unmarked_single_member_structure_list(self):
        argument = self.create_argument(
            {
                'Arg': {
                    'type': 'list',
                    'member': {
                        'type': 'structure',
                        'members': {'Bar': {'type': 'string'}},
                    },
                }
            },
            'arg',
        )
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
        bool_param.argument_model.is_document_type = False
        self.assertTrue(unpack_cli_arg(bool_param, True))
        self.assertTrue(unpack_cli_arg(bool_param, 'True'))
        self.assertTrue(unpack_cli_arg(bool_param, 'true'))

        self.assertFalse(unpack_cli_arg(bool_param, False))
        self.assertFalse(unpack_cli_arg(bool_param, 'False'))
        self.assertFalse(unpack_cli_arg(bool_param, 'false'))


class TestParamShorthandCustomArguments(BaseArgProcessTest):
    def setUp(self):
        super().setUp()
        self.shorthand = ParamShorthandParser()

    def test_list_structure_list_scalar_custom_arg(self):
        schema = {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'Name': {'type': 'string'},
                    'Args': {'type': 'array', 'items': {'type': 'string'}},
                },
            },
        }
        argument_model = create_argument_model_from_schema(schema)
        cli_argument = CustomArgument('foo', argument_model=argument_model)

        expected = [
            {"Name": "foo", "Args": ["a", "k1=v1", "b"]},
            {"Name": "bar", "Args": ["baz"]},
            {"Name": "single_kv", "Args": ["key=value"]},
            {"Name": "single_v", "Args": ["value"]},
        ]

        simplified = self.shorthand(
            cli_argument,
            [
                "Name=foo,Args=[a,k1=v1,b]",
                "Name=bar,Args=baz",
                "Name=single_kv,Args=[key=value]",
                "Name=single_v,Args=[value]",
            ],
            'process-cli-arg.foo.bar',
        )

        self.assertEqual(simplified, expected)

    def test_struct_list_scalars(self):
        schema = {
            "type": "object",
            "properties": {
                "Consistent": {
                    "type": "boolean",
                },
                "Args": {"type": "array", "items": {"type": "string"}},
            },
        }
        argument_model = create_argument_model_from_schema(schema)
        cli_argument = CustomArgument('test', argument_model=argument_model)

        returned = self.shorthand(
            cli_argument,
            'Consistent=true,Args=foo1,foo2',
            'process-cli-arg.foo.bar',
        )
        self.assertEqual(
            returned, {'Consistent': True, 'Args': ['foo1', 'foo2']}
        )


class TestDocGen(BaseArgProcessTest):
    # These aren't very extensive doc tests, as we want to stay somewhat
    # flexible and allow the docs to slightly change without breaking these
    # tests.
    def setUp(self):
        super().setUp()
        self.shorthand_documenter = ParamShorthandDocGen()
        self.service_name = 'foo'
        self.operation_name = 'bar'

    def get_generated_example_for(self, argument):
        # Returns a string containing the generated documentation.
        return self.shorthand_documenter.generate_shorthand_example(
            argument, self.service_name, self.operation_name
        )

    def assert_generated_example_is(self, argument, expected_docs):
        generated_docs = self.get_generated_example_for(argument)
        self.assertEqual(generated_docs, expected_docs)

    def test_flattens_marked_single_member_structure_list(self):
        argument = self.create_argument(
            {
                'Arg': {
                    'type': 'list',
                    'member': {
                        'type': 'structure',
                        'members': {'Bar': {'type': 'string'}},
                    },
                }
            },
            'arg',
        )
        argument.argument_model = argument.argument_model.members['Arg']
        uses_old_list = 'awscli.argprocess.ParamShorthand._uses_old_list_case'
        with mock.patch(uses_old_list, mock.Mock(return_value=True)):
            self.assert_generated_example_is(argument, '--arg Bar1 Bar2 Bar3')

    def test_generates_single_example_with_min_max_1(self):
        # An example of this is
        # 'workspaces rebuild-workspaces --rebuild-workspace-requests'
        argument = self.create_argument(
            {
                'Arg': {
                    'type': 'list',
                    'max': 1,
                    'min': 1,
                    'member': {
                        'type': 'structure',
                        'members': {'Bar': {'type': 'string'}},
                    },
                }
            },
            'arg',
        )
        argument.argument_model = argument.argument_model.members['Arg']
        uses_old_list = 'awscli.argprocess.ParamShorthand._uses_old_list_case'
        with mock.patch(uses_old_list, mock.Mock(return_value=True)):
            self.assert_generated_example_is(argument, '--arg Bar1')

    def test_does_not_flatten_unmarked_single_member_structure_list(self):
        argument = self.create_argument(
            {
                'Arg': {
                    'type': 'list',
                    'member': {
                        'type': 'structure',
                        'members': {'Bar': {'type': 'string'}},
                    },
                }
            },
            'arg',
        )
        argument.argument_model = argument.argument_model.members['Arg']
        uses_old_list = 'awscli.argprocess.ParamShorthand._uses_old_list_case'
        with mock.patch(uses_old_list, mock.Mock(return_value=False)):
            self.assert_generated_example_is(argument, 'Bar=string ...')

    def test_gen_list_structure_multiple_scalar_docs(self):
        expected = (
            'Scalar1=string,' 'Scalar2=string,' 'List1=string,string ...'
        )
        m = (
            model.DenormalizedStructureBuilder()
            .with_members(
                OrderedDict(
                    [
                        (
                            'List',
                            {
                                'type': 'list',
                                'member': {
                                    'type': 'structure',
                                    'members': OrderedDict(
                                        [
                                            ('Scalar1', {'type': 'string'}),
                                            ('Scalar2', {'type': 'string'}),
                                            (
                                                'List1',
                                                {
                                                    'type': 'list',
                                                    'member': {
                                                        'type': 'string'
                                                    },
                                                },
                                            ),
                                        ]
                                    ),
                                },
                            },
                        ),
                    ]
                )
            )
            .build_model()
            .members['List']
        )
        argument = mock.Mock()
        argument.argument_model = m
        argument.name = 'foo'
        argument.cli_name = '--foo'
        generated_example = self.get_generated_example_for(argument)
        self.assertIn(expected, generated_example)

    def test_gen_structure_list_scalar_docs(self):
        argument = self.create_argument(
            OrderedDict(
                [
                    ('Consistent', {'type': 'boolean'}),
                    ('Args', {'type': 'list', 'member': {'type': 'string'}}),
                ]
            ),
            'foo',
        )
        generated_example = self.get_generated_example_for(argument)
        self.assertIn(
            'Consistent=boolean,Args=string,string', generated_example
        )

    def test_can_document_nested_structs(self):
        argument = self.create_argument(
            {
                'A': {
                    'type': 'structure',
                    'members': {
                        'B': {'type': 'string'},
                        'C': {
                            'type': 'structure',
                            'members': {
                                'D': {'type': 'string'},
                                'E': {'type': 'integer'},
                            },
                        },
                    },
                },
            }
        )
        generated_example = self.get_generated_example_for(argument)
        self.assertIn('A={B=string,C={D=string,E=integer}}', generated_example)

    def test_can_document_nested_lists(self):
        argument = self.create_argument(
            {
                'A': {
                    'type': 'list',
                    'member': {
                        'type': 'list',
                        'member': {'type': 'string'},
                    },
                },
            }
        )
        generated_example = self.get_generated_example_for(argument)
        self.assertIn('A=[[string,string],[string,string]]', generated_example)

    def test_can_generated_nested_maps(self):
        argument = self.create_argument(
            {
                'A': {
                    'type': 'map',
                    'key': {'type': 'string'},
                    'value': {'type': 'string'},
                },
            }
        )
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
                'members': OrderedDict(
                    [
                        ('A', {'shape': 'String'}),
                        ('B', {'shape': 'String'}),
                    ]
                ),
            },
        }
        m = model.ListShape(
            shape_name='Top',
            shape_model=list_shape,
            shape_resolver=model.ShapeResolver(shapes),
        )
        argument = mock.Mock()
        argument.argument_model = m
        argument.name = 'foo'
        argument.cli_name = '--foo'
        generated_example = self.get_generated_example_for(argument)
        self.assertIn('A=string,B=string ...', generated_example)

    def test_handle_special_case_value_struct_not_documented(self):
        argument = self.create_argument({'Value': {'type': 'string'}})
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
            'members': OrderedDict(
                [
                    ('Recurse', {'shape': 'SubShape'}),
                    ('Scalar', {'shape': 'String'}),
                ]
            ),
        }
        shapes = {
            'Top': struct_shape,
            'String': {'type': 'string'},
            'SubShape': {
                'type': 'structure',
                'members': OrderedDict(
                    [
                        ('SubRecurse', {'shape': 'Top'}),
                        ('Scalar', {'shape': 'String'}),
                    ]
                ),
            },
        }
        m = model.StructureShape(
            shape_name='Top',
            shape_model=struct_shape,
            shape_resolver=model.ShapeResolver(shapes),
        )
        argument = mock.Mock()
        argument.argument_model = m
        argument.name = 'foo'
        argument.cli_name = '--foo'
        generated_example = self.get_generated_example_for(argument)
        self.assertIn(
            'Recurse={SubRecurse={( ... recursive ... ),Scalar=string},'
            'Scalar=string},Scalar=string',
            generated_example,
        )

    def test_skip_deeply_nested_shorthand(self):
        # The eventual goal is to have a better way to document
        # deeply nested shorthand params, but for now, we'll
        # only document shorthand params up to a certain stack level.
        argument = self.create_argument(
            {
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
                                    },
                                }
                            },
                        }
                    },
                },
            }
        )
        generated_example = self.get_generated_example_for(argument)
        self.assertEqual(generated_example, '')

    def test_structure_within_map(self):
        argument = self.create_argument(
            {
                'A': {
                    'type': 'map',
                    'key': {'type': 'string'},
                    'value': {
                        'type': 'structure',
                        'members': {
                            'B': {'type': 'string'},
                        },
                    },
                },
            }
        )
        generated_example = self.get_generated_example_for(argument)
        self.assertEqual(
            'A={KeyName1={B=string},KeyName2={B=string}}', generated_example
        )


class TestArgumentPercentEscaping(BaseArgProcessTest):
    def _test_percent_escaping(self, arg_type, arg_class, doc_string):
        argument = self.create_argument(
            {
                'Test': {
                    'type': arg_type,
                    'documentation': doc_string,
                }
            }
        )
        arg = arg_class(
            'test-arg',
            argument.argument_model.members['Test'],
            mock.Mock(),
            mock.Mock(),
            is_required=False,
        )
        arg_table = {arg.name: arg}
        parser = ArgTableArgParser(arg_table)
        help_output = parser.format_help()
        self.assertIn(doc_string, help_output)

    def test_cli_argument_escapes_percent(self):
        self._test_percent_escaping('string', CLIArgument, 'Symbols: % ^ & *')

    def test_boolean_argument_escapes_percent(self):
        self._test_percent_escaping(
            'boolean', BooleanArgument, 'Symbols: % ^ & *'
        )

    def test_cli_argument_escapes_url_encoded_percent(self):
        self._test_percent_escaping(
            'string', CLIArgument, 'File: test%28file%29.png'
        )

    def test_boolean_argument_escapes_url_encoded_percent(self):
        self._test_percent_escaping(
            'boolean', BooleanArgument, 'File: test%28file%29.png'
        )


if __name__ == '__main__':
    unittest.main()
