# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import pprint

from botocore.compat import OrderedDict

from awscli.testutils import unittest
from awscli.schema import ParameterRequiredError, SchemaTransformer
from awscli.schema import ShapeNameGenerator


MISSING_TYPE = {
    "type": "object",
    "properties": {
        "Foo": {
            "description": "I am a foo"
        }
    }
}


class TestSchemaTransformer(unittest.TestCase):

    maxDiff = None

    def test_missing_top_level_type_raises_exception(self):
        transformer = SchemaTransformer()
        with self.assertRaises(ParameterRequiredError):
            transformer.transform({})

    def test_missing_type_raises_exception(self):
        transformer = SchemaTransformer()

        with self.assertRaises(ParameterRequiredError):
            transformer.transform({
                'type': 'object',
                'properties': {
                    'Foo': {
                        'description': 'foo',
                    }
                }
            })

    def assert_schema_transforms_to(self, schema, transforms_to):
        transformer = SchemaTransformer()
        actual = transformer.transform(schema)
        if actual != transforms_to:
            self.fail("Transform failed.\n\nExpected:\n%s\n\nActual:\n%s\n" % (
                pprint.pformat(transforms_to), pprint.pformat(actual)))

    def test_transforms_list_of_single_string(self):
        schema = {
            'type': 'array',
            'items': {
                'type': 'string'
            }
        }
        transforms_to = {
            'InputShape': {
                'type': 'list',
                'member': {'shape': 'StringType1'}
            },
            'StringType1': {'type': 'string'}
        }
        self.assert_schema_transforms_to(schema, transforms_to)

    def test_transform_list_of_structures(self):
        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "arg1": {
                        "type": "string",
                    },
                    "arg2": {
                        "type": "integer",
                    }
                }
            }
        }
        transforms_to = {
            'InputShape': {
                'type': 'list',
                'member': {
                    'shape': 'StructureType1'
                }
            },
            'StructureType1': {
                'type': 'structure',
                'members': {
                    'arg1': {
                        'shape': 'StringType1',
                    },
                    'arg2': {
                        'shape': 'IntegerType1',
                    },
                }
            },
            'StringType1': {'type': 'string'},
            'IntegerType1': {'type': 'integer'},
        }
        self.assert_schema_transforms_to(schema, transforms_to)

    def test_transform_required_members_on_structure(self):
        pass

    def test_transforms_string(self):
        self.assert_schema_transforms_to(
            schema={
                'type': 'string'
            },
            transforms_to={
                'InputShape': {'type': 'string'}
            }
        )

    def test_transforms_boolean(self):
        self.assert_schema_transforms_to(
            schema={
                'type': 'boolean'
            },
            transforms_to={
                'InputShape': {'type': 'boolean'}
            }
        )

    def test_transforms_integer(self):
        self.assert_schema_transforms_to(
            schema={
                'type': 'integer'
            },
            transforms_to={
                'InputShape': {'type': 'integer'}
            }
        )

    def test_transforms_structure(self):
        self.assert_schema_transforms_to(
            schema={
                "type": "object",
                "properties": OrderedDict([
                    ("A", {"type": "string"}),
                    ("B", {"type": "string"}),
                ]),
            },
            transforms_to={
                'InputShape': {
                    'type': 'structure',
                    'members': {
                        'A': {'shape': 'StringType1'},
                        'B': {'shape': 'StringType2'},
                    }
                },
                'StringType1': {'type': 'string'},
                'StringType2': {'type': 'string'},
            }
        )

    def test_transforms_map(self):
        self.assert_schema_transforms_to(
            schema={
                "type": "map",
                "key": {"type": "string"},
                "value": {"type": "string"}
            },
            transforms_to={
                'InputShape': {
                    "type": "map",
                    "key": {"shape": "StringType1"},
                    "value": {"shape": "StringType2"}
                },
                'StringType1': {'type': 'string'},
                'StringType2': {'type': 'string'},
            }
        )

    def test_description_on_shape_type(self):
        self.assert_schema_transforms_to(
            schema={
                'type': 'string',
                'description': 'a description'
            },
            transforms_to={
                'InputShape': {
                    'type': 'string',
                    'documentation': 'a description'
                }
            }
        )

    def test_enum_on_shape_type(self):
        self.assert_schema_transforms_to(
            schema={
                'type': 'string',
                'enum': ['a', 'b'],
            },
            transforms_to={
                'InputShape': {
                    'type': 'string',
                    'enum': ['a', 'b']
                }
            }
        )

    def test_description_on_shape_ref(self):
        self.assert_schema_transforms_to(
            schema={
                'type': 'object',
                'description': 'object description',
                'properties': {
                    'A': {
                        'type': 'string',
                        'description': 'string description',
                    },
                }
            },
            transforms_to={
                'InputShape': {
                    'type': 'structure',
                    'documentation': 'object description',
                    'members': {
                        'A': {'shape': 'StringType1'},
                    }
                },
                'StringType1': {
                    'documentation': 'string description',
                    'type': 'string'
                }
            }
        )

    def test_required_members_on_structure(self):
        # This case is interesting because we actually
        # don't support a 'required' key on a member shape ref.
        # Now, all the required members are added as a key on the
        # parent structure shape.
        self.assert_schema_transforms_to(
            schema={
                'type': 'object',
                'properties': {
                    'A': {'type': 'string', 'required': True},
                }
            },
            transforms_to={
                'InputShape': {
                    'type': 'structure',
                    # This 'required' key is the change here.
                    'required': ['A'],
                    'members': {
                        'A': {'shape': 'StringType1'},
                    }
                },
                'StringType1': {'type': 'string'},
            }
        )

    def test_nested_structure(self):
        self.assert_schema_transforms_to(
            schema={
                'type': 'object',
                'properties': {
                    'A': {
                        'type': 'object',
                        'properties': {
                            'B': {
                                'type': 'object',
                                'properties': {
                                    'C': {'type': 'string'}
                                }
                            }
                        }
                    },
                }
            },
            transforms_to={
                'InputShape': {
                    'type': 'structure',
                    'members': {
                        'A': {'shape': 'StructureType1'},
                    }
                },
                'StructureType1': {
                    'type': 'structure',
                    'members': {
                        'B': {'shape': 'StructureType2'}
                    }
                },
                'StructureType2': {
                    'type': 'structure',
                    'members': {
                        'C': {'shape': 'StringType1'}
                    }
                },
                'StringType1': {
                    'type': 'string',
                }
            }
        )


class TestShapeNameGenerator(unittest.TestCase):
    def test_generate_name_types(self):
        namer = ShapeNameGenerator()
        self.assertEqual(namer.new_shape_name('string'), 'StringType1')
        self.assertEqual(namer.new_shape_name('list'), 'ListType1')
        self.assertEqual(namer.new_shape_name('structure'), 'StructureType1')

    def test_generate_type_multiple_times(self):
        namer = ShapeNameGenerator()
        self.assertEqual(namer.new_shape_name('string'), 'StringType1')
        self.assertEqual(namer.new_shape_name('string'), 'StringType2')
