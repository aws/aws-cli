# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0e
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import tempfile

from botocore.compat import json
from botocore.compat import OrderedDict

from awscli.testutils import mock, unittest
from awscli.customizations.cloudformation.deployer import Deployer
from awscli.customizations.cloudformation.yamlhelper import yaml_parse, yaml_dump


class TestYaml(unittest.TestCase):

    yaml_with_tags = """
    Resource:
        Key1: !Ref Something
        Key2: !GetAtt Another.Arn
        Key3: !FooBar [!Baz YetAnother, "hello"]
        Key4: !SomeTag {"a": "1"}
        Key5: !GetAtt OneMore.Outputs.Arn
        Key6: !Condition OtherCondition
    """

    parsed_yaml_dict = {
        "Resource": {
            "Key1": {
                "Ref": "Something"
            },
            "Key2": {
                "Fn::GetAtt": ["Another", "Arn"]
            },
            "Key3": {
                "Fn::FooBar": [
                    {"Fn::Baz": "YetAnother"},
                    "hello"
                ]
            },
            "Key4": {
                "Fn::SomeTag": {
                    "a": "1"
                }
            },
            "Key5": {
                "Fn::GetAtt": ["OneMore", "Outputs.Arn"]
            },
            "Key6": {
                "Condition": "OtherCondition"
            }
        }
    }

    def test_yaml_with_tags(self):
        output = yaml_parse(self.yaml_with_tags)
        self.assertEqual(self.parsed_yaml_dict, output)

        # Make sure formatter and parser work well with each other
        formatted_str = yaml_dump(output)
        output_again = yaml_parse(formatted_str)
        self.assertEqual(output, output_again)

    def test_yaml_getatt(self):
        # This is an invalid syntax for !GetAtt. But make sure the code does
        # not crash when we encounter this syntax. Let CloudFormation
        # interpret this value at runtime
        yaml_input = """
        Resource:
            Key: !GetAtt ["a", "b"]
        """

        output = {
            "Resource": {
               "Key": {
                "Fn::GetAtt": ["a", "b"]
               }

            }
        }

        actual_output = yaml_parse(yaml_input)
        self.assertEqual(actual_output, output)

    def test_parse_json_with_tabs(self):
        template = '{\n\t"foo": "bar"\n}'
        output = yaml_parse(template)
        self.assertEqual(output, {'foo': 'bar'})

    def test_parse_json_preserve_elements_order(self):
        input_template = """
        {
            "B_Resource": {
                "Key2": {
                    "Name": "name2"
                },
                "Key1": {
                    "Name": "name1"
                }
            },
            "A_Resource": {
                "Key2": {
                    "Name": "name2"
                },
                "Key1": {
                    "Name": "name1"
                }
            }
        }
        """
        expected_dict = OrderedDict([
            ('B_Resource', OrderedDict([('Key2', {'Name': 'name2'}), ('Key1', {'Name': 'name1'})])),
            ('A_Resource', OrderedDict([('Key2', {'Name': 'name2'}), ('Key1', {'Name': 'name1'})]))
        ])
        output_dict = yaml_parse(input_template)
        self.assertEqual(expected_dict, output_dict)

    def test_parse_yaml_preserve_elements_order(self):
        input_template = (
        'B_Resource:\n'
        '  Key2:\n'
        '    Name: name2\n'
        '  Key1:\n'
        '    Name: name1\n'
        'A_Resource:\n'
        '  Key2:\n'
        '    Name: name2\n'
        '  Key1:\n'
        '    Name: name1\n'
        )
        output_dict = yaml_parse(input_template)
        expected_dict = OrderedDict([
            ('B_Resource', OrderedDict([('Key2', {'Name': 'name2'}), ('Key1', {'Name': 'name1'})])),
            ('A_Resource', OrderedDict([('Key2', {'Name': 'name2'}), ('Key1', {'Name': 'name1'})]))
        ])
        self.assertEqual(expected_dict, output_dict)

        output_template = yaml_dump(output_dict)
        self.assertEqual(input_template, output_template)

    def test_yaml_merge_tag(self):
        test_yaml = """
        base: &base
            property: value
        test:
            <<: *base
        """
        output = yaml_parse(test_yaml)
        self.assertTrue(isinstance(output, OrderedDict))
        self.assertEqual(output.get('test').get('property'), 'value')

    def test_unroll_yaml_anchors(self):
        properties = {
            "Foo": "bar",
            "Spam": "eggs",
        }
        template = {
            "Resources": {
                "Resource1": {"Properties": properties},
                "Resource2": {"Properties": properties}
            }
        }

        expected = (
            'Resources:\n'
            '  Resource1:\n'
            '    Properties:\n'
            '      Foo: bar\n'
            '      Spam: eggs\n'
            '  Resource2:\n'
            '    Properties:\n'
            '      Foo: bar\n'
            '      Spam: eggs\n'
        )
        actual = yaml_dump(template)
        self.assertEqual(actual, expected)

    def test_scientific_notation_strings_are_quoted(self):
        """
        Test fix for issue #3991: strings that look like scientific notation
        should be quoted to prevent them from being interpreted as numbers.
        """
        template = {
            "Parameters": {
                "Value1": {"Default": "1e10"},
                "Value2": {"Default": "1E-5"},
                "Value3": {"Default": "2.5e+3"},
            }
        }
        dumped = yaml_dump(template)
        
        # Scientific notation strings should be quoted
        self.assertIn("'1e10'", dumped)
        self.assertIn("'1E-5'", dumped)
        self.assertIn("'2.5e+3'", dumped)
        
        # Verify round-trip preserves string type
        reparsed = yaml_parse(dumped)
        self.assertEqual(reparsed["Parameters"]["Value1"]["Default"], "1e10")
        self.assertEqual(reparsed["Parameters"]["Value2"]["Default"], "1E-5")
        self.assertEqual(reparsed["Parameters"]["Value3"]["Default"], "2.5e+3")

    def test_octal_hex_binary_strings_are_quoted(self):
        """
        Test that octal, hex, and binary notation strings are quoted.
        """
        template = {
            "Values": {
                "Octal": "0755",
                "OctalNew": "0o755",
                "Hex": "0x1A2B",
                "Binary": "0b1010",
            }
        }
        dumped = yaml_dump(template)
        
        # These should be quoted
        self.assertIn("'0755'", dumped)
        self.assertIn("'0o755'", dumped)
        self.assertIn("'0x1A2B'", dumped)
        self.assertIn("'0b1010'", dumped)
        
        # Verify round-trip
        reparsed = yaml_parse(dumped)
        self.assertEqual(reparsed["Values"]["Octal"], "0755")
        self.assertEqual(reparsed["Values"]["Hex"], "0x1A2B")

    def test_sexagesimal_strings_are_quoted(self):
        """
        Test that sexagesimal (base 60) notation strings are quoted.
        """
        template = {
            "Values": {
                "Time1": "1:30:00",
                "Time2": "12:30",
            }
        }
        dumped = yaml_dump(template)
        
        # Should be quoted
        self.assertIn("'1:30:00'", dumped)
        self.assertIn("'12:30'", dumped)
        
        # Verify round-trip
        reparsed = yaml_parse(dumped)
        self.assertEqual(reparsed["Values"]["Time1"], "1:30:00")
        self.assertEqual(reparsed["Values"]["Time2"], "12:30")

    def test_normal_strings_not_excessively_quoted(self):
        """
        Test that normal strings are not unnecessarily quoted.
        """
        template = {
            "Values": {
                "Normal1": "hello",
                "Normal2": "world-123",
                "Arn": "arn:aws:s3:::bucket",
            }
        }
        dumped = yaml_dump(template)
        
        # Normal strings should not be quoted (except ARN which has colons)
        self.assertIn("Normal1: hello", dumped)
        self.assertIn("Normal2: world-123", dumped)

