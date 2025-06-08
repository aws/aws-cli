#!/usr/bin/env python3
"""
Unit tests for the YAML comparison utility.
"""

import unittest
from tests.unit.customizations.cloudformation.yaml_compare import (
    compare_yaml_strings,
)


class TestYamlCompare(unittest.TestCase):
    """Test cases for YAML comparison functionality."""

    def test_identical_yaml_strings(self):
        """Test that identical YAML strings are considered equivalent."""
        yaml1 = """
        key1: value1
        key2: value2
        """
        self.assertTrue(compare_yaml_strings(yaml1, yaml1))

    def test_different_key_order(self):
        """
        Test that YAML strings with different key order are
        considered equivalent.
        """
        yaml1 = """
        key1: value1
        key2: value2
        """
        yaml2 = """
        key2: value2
        key1: value1
        """
        self.assertTrue(compare_yaml_strings(yaml1, yaml2))

    def test_nested_dictionaries_different_order(self):
        """
        Test that nested dictionaries with different
        key order are considered equivalent.
        """
        yaml1 = """
        outer:
          inner1: value1
          inner2: value2
        another: value
        """
        yaml2 = """
        another: value
        outer:
          inner2: value2
          inner1: value1
        """
        self.assertTrue(compare_yaml_strings(yaml1, yaml2))

    def test_lists_same_order(self):
        """Test that lists with the same order are considered equivalent."""
        yaml1 = """
        list:
          - item1
          - item2
          - item3
        """
        yaml2 = """
        list:
          - item1
          - item2
          - item3
        """
        self.assertTrue(compare_yaml_strings(yaml1, yaml2))

    def test_lists_different_order(self):
        """Test that lists with different order are considered equivalent."""
        yaml1 = """
        list:
          - item1
          - item2
          - item3
        """
        yaml2 = """
        list:
          - item3
          - item1
          - item2
        """
        self.assertTrue(compare_yaml_strings(yaml1, yaml2))

    def test_nested_lists_different_order(self):
        """
        Test that nested lists with different order are considered equivalent.
        """
        yaml1 = """
        outer:
          list:
            - item1
            - item2
        """
        yaml2 = """
        outer:
          list:
            - item2
            - item1
        """
        self.assertTrue(compare_yaml_strings(yaml1, yaml2))

    def test_complex_nested_structure(self):
        """
        Test complex nested structures with different order
        are considered equivalent.
        """
        yaml1 = """
        Resources:
          MyInstance:
            Type: AWS::EC2::Instance
            Properties:
              ImageId: ami-12345
              Tags:
                - Key: Name
                  Value: TestInstance
                - Key: Environment
                  Value: Dev
        Parameters:
          InstanceType:
            Type: String
            Default: t2.micro
        """
        yaml2 = """
        Parameters:
          InstanceType:
            Default: t2.micro
            Type: String
        Resources:
          MyInstance:
            Properties:
              Tags:
                - Value: Dev
                  Key: Environment
                - Value: TestInstance
                  Key: Name
              ImageId: ami-12345
            Type: AWS::EC2::Instance
        """
        self.assertTrue(compare_yaml_strings(yaml1, yaml2))

    def test_different_values(self):
        """
        Test that YAML strings with different values are not considered
        equivalent.
        """
        yaml1 = """
        key1: value1
        key2: value2
        """
        yaml2 = """
        key1: value1
        key2: different_value
        """
        self.assertFalse(compare_yaml_strings(yaml1, yaml2))

    def test_different_keys(self):
        """
        Test that YAML strings with different keys are not
        considered equivalent.
        """
        yaml1 = """
        key1: value1
        key2: value2
        """
        yaml2 = """
        key1: value1
        different_key: value2
        """
        self.assertFalse(compare_yaml_strings(yaml1, yaml2))

    def test_different_structure(self):
        """
        Test that YAML strings with different structure are
        not considered equivalent.
        """
        yaml1 = """
        key1: value1
        key2:
          nested: value
        """
        yaml2 = """
        key1: value1
        key2: value
        """
        self.assertFalse(compare_yaml_strings(yaml1, yaml2))

    def test_list_vs_dict(self):
        """Test that a list and a dictionary are not considered equivalent."""
        yaml1 = """
        key:
          - item1
          - item2
        """
        yaml2 = """
        key:
          item1: value1
          item2: value2
        """
        self.assertFalse(compare_yaml_strings(yaml1, yaml2))

    def test_lists_with_dicts_different_order(self):
        """Test lists containing dictionaries with different order."""
        yaml1 = """
        list:
          - name: item1
            value: value1
          - name: item2
            value: value2
        """
        yaml2 = """
        list:
          - value: value1
            name: item1
          - value: value2
            name: item2
        """
        self.assertTrue(compare_yaml_strings(yaml1, yaml2))

    def test_lists_with_dicts_different_item_order(self):
        """Test lists containing dictionaries with different item order."""
        yaml1 = """
        list:
          - name: item1
            value: value1
          - name: item2
            value: value2
        """
        yaml2 = """
        list:
          - name: item2
            value: value2
          - name: item1
            value: value1
        """
        self.assertTrue(compare_yaml_strings(yaml1, yaml2))

    def test_cloudformation_intrinsics(self):
        """Test CloudFormation intrinsic functions are properly handled."""
        yaml1 = """
        Resources:
          MyFunction:
            Type: AWS::Lambda::Function
            Properties:
              FunctionName: !Sub "${AWS::StackName}-function"
              Role: !GetAtt MyRole.Arn
              Environment:
                Variables:
                  BUCKET_NAME: !Ref MyBucket
        """
        yaml2 = """
        Resources:
          MyFunction:
            Properties:
              Role: !GetAtt MyRole.Arn
              Environment:
                Variables:
                  BUCKET_NAME: !Ref MyBucket
              FunctionName: !Sub "${AWS::StackName}-function"
            Type: AWS::Lambda::Function
        """
        self.assertTrue(compare_yaml_strings(yaml1, yaml2))

    def test_cloudformation_shorthand_vs_full(self):
        """
        Test that shorthand and full notation for intrinsics
        are equivalent.
        """
        yaml1 = """
        Resources:
          MyFunction:
            Properties:
              Role: !GetAtt MyRole.Arn
        """
        yaml2 = """
        Resources:
          MyFunction:
            Properties:
              Role:
                Fn::GetAtt:
                  - MyRole
                  - Arn
        """
        self.assertTrue(compare_yaml_strings(yaml1, yaml2))


if __name__ == "__main__":
    unittest.main()
