# Copyright 2012-2025 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
"""
Test module parameter validation.
"""

import unittest

from awscli.customizations.cloudformation.modules.validation import (
    validate_parameters,
    validate_parameter,
    validate_string,
    validate_number,
    validate_array,
    validate_object,
    apply_defaults,
    ParameterValidationError,
)


class TestParameterValidation(unittest.TestCase):
    """Test parameter schema validation for CloudFormation modules."""

    def test_validate_parameters_no_schema(self):
        """Test that validation is skipped when no schema is present."""
        module_template = {"Parameters": {"Name": {"Type": "String"}}}
        properties = {"Name": "TestValue"}

        # Should not raise any exceptions
        validate_parameters("TestModule", module_template, properties)

    def test_validate_parameters_with_schema(self):
        """Test basic parameter validation with schema."""
        module_template = {
            "Parameters": {"Name": {"Type": "String"}},
            "ParameterSchema": {
                "Name": {"Type": "String", "MinLength": 3, "MaxLength": 10}
            },
        }
        properties = {"Name": "TestValue"}

        # Should not raise any exceptions
        validate_parameters("TestModule", module_template, properties)

    def test_validate_parameters_with_invalid_value(self):
        """Test validation with invalid parameter value."""
        module_template = {
            "Parameters": {"Name": {"Type": "String"}},
            "ParameterSchema": {
                "Name": {"Type": "String", "MinLength": 5, "MaxLength": 10}
            },
        }
        properties = {"Name": "Test"}  # Too short

        with self.assertRaises(ParameterValidationError) as context:
            validate_parameters("TestModule", module_template, properties)

        self.assertIn("minimum length 5", str(context.exception))

    def test_validate_parameters_with_missing_required(self):
        """Test validation with missing required parameter."""
        module_template = {
            "Parameters": {"Config": {"Type": "Object"}},
            "ParameterSchema": {
                "Config": {
                    "Type": "Object",
                    "Required": ["Name"],
                    "Properties": {
                        "Name": {"Type": "String"},
                        "Description": {"Type": "String"},
                    },
                }
            },
        }
        properties = {"Config": {}}  # Missing required Name property

        with self.assertRaises(ParameterValidationError) as context:
            validate_parameters("TestModule", module_template, properties)

        self.assertIn("required property 'Name'", str(context.exception))

    def test_validate_string(self):
        """Test string validation."""
        # Valid string
        validate_string(
            "TestModule",
            "TestParam",
            {"MinLength": 3, "MaxLength": 10, "Pattern": "^Test"},
            "TestValue",
        )

        # Invalid length
        with self.assertRaises(ParameterValidationError):
            validate_string(
                "TestModule", "TestParam", {"MinLength": 10}, "Test"
            )

        # Invalid pattern
        with self.assertRaises(ParameterValidationError):
            validate_string(
                "TestModule", "TestParam", {"Pattern": "^foo"}, "TestValue"
            )

    def test_validate_number(self):
        """Test number validation."""
        # Valid number
        validate_number(
            "TestModule", "TestParam", {"Minimum": 5, "Maximum": 10}, 7
        )

        # Invalid minimum
        with self.assertRaises(ParameterValidationError):
            validate_number("TestModule", "TestParam", {"Minimum": 10}, 5)

        # Invalid exclusive maximum
        with self.assertRaises(ParameterValidationError):
            validate_number(
                "TestModule", "TestParam", {"ExclusiveMaximum": 10}, 10
            )

    def test_validate_array(self):
        """Test array validation."""
        # Valid array
        validate_array(
            "TestModule",
            "TestParam",
            {"MinItems": 2, "MaxItems": 5},
            [1, 2, 3],
        )

        # Invalid min items
        with self.assertRaises(ParameterValidationError):
            validate_array("TestModule", "TestParam", {"MinItems": 5}, [1, 2])

        # Invalid item type
        with self.assertRaises(ParameterValidationError):
            validate_array(
                "TestModule",
                "TestParam",
                {"Items": {"Type": "String"}},
                [1, 2, "test"],
            )

    def test_validate_object(self):
        """Test object validation."""
        # Valid object
        validate_object(
            "TestModule",
            "TestParam",
            {
                "Required": ["name"],
                "Properties": {
                    "name": {"Type": "String"},
                    "age": {"Type": "Number"},
                },
            },
            {"name": "Test", "age": 30},
        )

        # Missing required property
        with self.assertRaises(ParameterValidationError):
            validate_object(
                "TestModule",
                "TestParam",
                {"Required": ["name", "age"]},
                {"name": "Test"},
            )

        # Invalid property type
        with self.assertRaises(ParameterValidationError):
            validate_object(
                "TestModule",
                "TestParam",
                {"Properties": {"age": {"Type": "Number"}}},
                {"age": "thirty"},
            )

    def test_validate_enum(self):
        """Test enum validation."""
        # Valid enum value
        validate_parameter(
            "TestModule",
            "TestParam",
            {"Type": "String", "Enum": ["A", "B", "C"]},
            "B",
        )

        # Invalid enum value
        with self.assertRaises(ParameterValidationError):
            validate_parameter(
                "TestModule",
                "TestParam",
                {"Type": "String", "Enum": ["A", "B", "C"]},
                "D",
            )

    def test_apply_defaults(self):
        """Test applying default values."""
        schema = {
            "Name": {"Type": "String", "Default": "DefaultName"},
            "Config": {
                "Type": "Object",
                "Properties": {
                    "Enabled": {"Type": "Boolean", "Default": True},
                    "Count": {"Type": "Number", "Default": 5},
                },
            },
        }

        # Empty properties
        result = apply_defaults(schema, {})
        self.assertEqual(result["Name"], "DefaultName")

        # Partial properties
        result = apply_defaults(schema, {"Config": {}})
        self.assertEqual(result["Name"], "DefaultName")
        self.assertEqual(result["Config"]["Enabled"], True)
        self.assertEqual(result["Config"]["Count"], 5)

        # Override defaults
        result = apply_defaults(
            schema, {"Name": "CustomName", "Config": {"Count": 10}}
        )
        self.assertEqual(result["Name"], "CustomName")
        self.assertEqual(result["Config"]["Enabled"], True)
        self.assertEqual(result["Config"]["Count"], 10)

    def test_nested_validation(self):
        """Test validation of nested objects and arrays."""
        schema = {
            "Type": "Object",
            "Properties": {
                "Name": {"Type": "String", "MinLength": 3},
                "Tags": {
                    "Type": "Array",
                    "Items": {
                        "Type": "Object",
                        "Required": ["Key", "Value"],
                        "Properties": {
                            "Key": {"Type": "String"},
                            "Value": {"Type": "String"},
                        },
                    },
                },
            },
        }

        # Valid nested structure
        validate_parameter(
            "TestModule",
            "Config",
            schema,
            {
                "Name": "TestResource",
                "Tags": [
                    {"Key": "Environment", "Value": "Dev"},
                    {"Key": "Owner", "Value": "Team"},
                ],
            },
        )

        # Invalid nested structure (missing required property)
        with self.assertRaises(ParameterValidationError):
            validate_parameter(
                "TestModule",
                "Config",
                schema,
                {
                    "Name": "TestResource",
                    "Tags": [
                        {"Key": "Environment", "Value": "Dev"},
                        {"Key": "Owner"},  # Missing Value
                    ],
                },
            )


if __name__ == "__main__":
    unittest.main()
