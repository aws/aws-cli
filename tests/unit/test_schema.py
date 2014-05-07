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

"""
Note: this schema is currently not supported by the ParamShorthand
parser due to its complexity, but is tested here to ensure the
robustness of the transformer.
"""
INPUT_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "Name": {
                "type": "string",
                "description": "The name of the step. ",
            },
            "Jar": {
                "type": "string",
                "description": "A path to a JAR file run during the step.",
            },
            "Args": {
                "type": "array",
                "description":
                    "A list of command line arguments to pass to the step.",
                "items": {
                        "type": "string"
                    }
            },
            "MainClass": {
                "type": "string",
                "description":
                    "The name of the main class in the specified "
                    "Java file. If not specified, the JAR file should "
                    "specify a Main-Class in its manifest file."
            },
            "Properties": {
                "type": "array",
                "description":
                    "A list of Java properties that are set when the step "
                    "runs. You can use these properties to pass key value "
                    "pairs to your main function.",
                "items": {
                    "type": "object",
                    "properties": {
                        "Key":{
                            "type": "string",
                            "description":
                                "The unique identifier of a key value pair."
                        },
                        "Value": {
                            "type": "string",
                            "description":
                                "The value part of the identified key."
                        }
                    }
                }
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
                "description": "The name of the step. ",
            },
            "Jar": {
                "type": "string",
                "description": "A path to a JAR file run during the step.",
            },
            "Args": {
                "type": "list",
                "description":
                    "A list of command line arguments to pass to the step.",
                "members": {
                    "type": "string"
                }
            },
            "MainClass": {
                "type": "string",
                "description":
                    "The name of the main class in the specified "
                    "Java file. If not specified, the JAR file should "
                    "specify a Main-Class in its manifest file."
            },
            "Properties": {
                "type": "list",
                "description":
                    "A list of Java properties that are set when the step "
                    "runs. You can use these properties to pass key value "
                    "pairs to your main function.",
                "members": {
                    "type": "structure",
                    "members": {
                        "Key":{
                            "type": "string",
                            "description":
                                "The unique identifier of a key value pair."
                        },
                        "Value": {
                            "type": "string",
                            "description":
                                "The value part of the identified key."
                        }
                    }
                }
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
