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
from collections import defaultdict


class ParameterRequiredError(ValueError):
    pass


class SchemaTransformer(object):
    """
    Transforms a custom argument parameter schema into an internal
    model representation so that it can be treated like a normal
    service model. This includes shorthand JSON parsing and
    automatic documentation generation. The format of the schema
    follows JSON Schema, which can be found here:

    http://json-schema.org/

    Only a relevant subset of features is supported here:

    * Types: `object`, `array`, `string`, `integer`, `boolean`
    * Properties: `type`, `description`, `required`, `enum`

    For example::

    {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "arg1": {
                    "type": "string",
                    "required": True,
                    "enum": [
                        "Value1",
                        "Value2",
                        "Value3"
                    ]
                },
                "arg2": {
                    "type": "integer",
                    "description": "The number of calls"
                }
            }
        }
    }

    Assuming the schema is applied to a service named `foo`, with an
    operation named `bar` and that the parameter is called `baz`, you
    could call it with the shorthand JSON like so::

        $ aws foo bar --baz arg1=Value1,arg2=5 arg1=Value2

    """
    JSON_SCHEMA_TO_AWS_TYPES = {
        'object': 'structure',
        'array': 'list',
    }

    def __init__(self):
        self._shape_namer = ShapeNameGenerator()

    def transform(self, schema):
        """Convert JSON schema to the format used internally by the AWS CLI.

        :type schema: dict
        :param schema: The JSON schema describing the argument model.

        :rtype: dict
        :return: The transformed model in a form that can be consumed
            internally by the AWS CLI.  The dictionary returned will
            have a list of shapes, where the shape representing the
            transformed schema is always named ``InputShape`` in the
            returned dictionary.

        """
        shapes = {}
        self._transform(schema, shapes, 'InputShape')
        return shapes

    def _transform(self, schema, shapes, shape_name):
        if 'type' not in schema:
            raise ParameterRequiredError("Missing required key: 'type'")
        if schema['type'] == 'object':
            shapes[shape_name] = self._transform_structure(schema, shapes)
        elif schema['type'] == 'array':
            shapes[shape_name] = self._transform_list(schema, shapes)
        else:
            shapes[shape_name] = self._transform_scalar(schema)
        return shapes

    def _transform_scalar(self, schema):
        return self._populate_initial_shape(schema)

    def _transform_structure(self, schema, shapes):
        # Transforming a structure involves:
        # 1. Generating the shape definition for the structure
        # 2. Generating the shape definitions for its members
        structure_shape = self._populate_initial_shape(schema)
        members = {}
        required_members = []

        for key, value in schema['properties'].items():
            current_type_name = self._json_schema_to_aws_type(value)
            current_shape_name = self._shape_namer.new_shape_name(
                current_type_name)
            members[key] = {'shape': current_shape_name}
            if value.get('required', False):
                required_members.append(key)
            self._transform(value, shapes, current_shape_name)
        structure_shape['members'] = members
        if required_members:
            structure_shape['required'] = required_members
        return structure_shape

    def _transform_list(self, schema, shapes):
        # Transforming a structure involves:
        # 1. Generating the shape definition for the structure
        # 2. Generating the shape definitions for its 'items' member
        list_shape = self._populate_initial_shape(schema)
        member_type = self._json_schema_to_aws_type(schema['items'])
        member_shape_name = self._shape_namer.new_shape_name(member_type)
        list_shape['member'] = {'shape': member_shape_name}
        self._transform(schema['items'], shapes, member_shape_name)
        return list_shape

    def _populate_initial_shape(self, schema):
        shape = {'type': self._json_schema_to_aws_type(schema)}
        if 'description' in schema:
            shape['documentation'] = schema['description']
        if 'enum' in schema:
            shape['enum'] = schema['enum']
        return shape

    def _json_schema_to_aws_type(self, schema):
        if 'type' not in schema:
            raise ParameterRequiredError("Missing required key: 'type'")
        type_name = schema['type']
        return self.JSON_SCHEMA_TO_AWS_TYPES.get(type_name, type_name)


class ShapeNameGenerator(object):
    def __init__(self):
        self._name_cache = defaultdict(int)

    def new_shape_name(self, type_name):
        self._name_cache[type_name] += 1
        current_index = self._name_cache[type_name]
        return '%sType%s' % (type_name.capitalize(), current_index)
