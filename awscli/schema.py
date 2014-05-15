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

class ParameterRequiredError(ValueError): pass


class SchemaTransformer(object):
    """
    Transforms a custom argument parameter schema into an internal
    model representation so that it can be treated like a normal
    service model. This includes shorthand JSON parsing and
    automatic documentation generation. The format of the schema
    follows JSON Schema, which can be found here:

    http://json-schema.org/

    Only a relevant subset of features is supported here:

    * Types: `object`, `array`, `string`, `number`, `integer`,
             `boolean`
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
    # Map schema types to internal representation types
    TYPE_MAP = {
        'array': 'list',
        'object': 'structure',
    }

    # Map schema properties to internal representation properties
    PROPERTY_MAP = {
        # List item description
        'items': 'members',
        # Object properties description
        'properties': 'members',
    }

    # List of known properties to copy or transform without any
    # other special processing.
    SUPPORTED_BASIC_PROPERTIES = [
        'type', 'description', 'required', 'enum'
    ]

    def __init__(self, schema):
        self.schema = schema

    def transform(self):
        """Convert to an internal representation of parameters"""
        return self._process_param(self.schema)

    def _process_param(self, param):
        transformed = {}

        if 'type' not in param:
            raise ParameterRequiredError(
                'The type property is required: {0}'.format(param))

        # Handle basic properties which are just copied and optionally
        # mapped to new values.
        for basic_property in self.SUPPORTED_BASIC_PROPERTIES:
            if basic_property in param:
                value = param[basic_property]

                if basic_property == 'type':
                    value = self.TYPE_MAP.get(value, value)

                mapped = self.PROPERTY_MAP.get(basic_property, basic_property)
                transformed[mapped] = value

        # Handle complex properties
        if 'items' in param:
            mapped = self.PROPERTY_MAP.get('items', 'items')
            transformed[mapped] = self._process_param(param['items'])

        if 'properties' in param:
            mapped = self.PROPERTY_MAP.get('properties', 'properties')
            transformed[mapped] = {}

            for key, value in param['properties'].items():
                transformed[mapped][key] = self._process_param(value)

        return transformed
