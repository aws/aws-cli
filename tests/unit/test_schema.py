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
import unittest

from awscli.schema import ParameterRequiredError, SchemaTransformer

INPUT_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "Name": {
                "type": "string",
                "description": "Instance group name",
                "required": True
            },
            "Market": {
                "type": "string",
                "description": "On-demand or spot instance market",
                "enum": ["ONDEMAND", "SPOT"],
                "default": "ONDEMAND"
            },
            "InstanceRole": {
                "type": "string",
                "description": "Master, core or task role for instances",
                "enum": ["MASTER", "CORE", "TASK"]
            },
            "BidPrice": {
                "type": "string"
            },
            "InstanceType": {
                "type": "string"
            },
            "InstanceCount": {
                "type": "integer"
            }
        }
    }
}

EXPECTED_OUTPUT = {
    "type": "list",
    "members": {
        "type": "structure",
        "members": {
            "Name": {
                "type": "string",
                "description": "Instance group name",
                "required": True
            },
            "Market": {
                "type": "string",
                "description": "On-demand or spot instance market",
                "enum": ["ONDEMAND", "SPOT"]
            },
            "InstanceRole": {
                "type": "string",
                "description": "Master, core or task role for instances",
                "enum": ["MASTER", "CORE", "TASK"]
            },
            "BidPrice": {
                "type": "string"
            },
            "InstanceType": {
                "type": "string"
            },
            "InstanceCount": {
                "type": "integer"
            }
        }
    }
}

MISSING_TYPE = {
    "type": "object",
    "properties": {
        "Foo": {
            "description": "I am a foo"
        }
    }
}

class TestSchemaTransformer(unittest.TestCase):
    def test_schema(self):
        transformer = SchemaTransformer(INPUT_SCHEMA)
        output = transformer.transform()

        self.assertEqual(output, EXPECTED_OUTPUT)

    def test_missing_type(self):
        transformer = SchemaTransformer(MISSING_TYPE)

        with self.assertRaises(ParameterRequiredError):
            transformer.transform()
