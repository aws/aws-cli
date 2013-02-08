# Copyright (c) 2013 Amazon.com, Inc. or its affiliates.  All Rights Reserved
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
from botocore.compat import unittest
from botocore.translate import ModelFiles, translate, merge_dicts


SERVICES = {
  "service_full_name": "AWS Security Token Service",
  "service_abbreviation": "AWS STS",
  "type": "query",
  "signature_version": "v4",
  "result_wrapped": True,
  "global_endpoint": "sts.amazonaws.com",
  "api_version": "2011-06-15",
  "endpoint_prefix": "sts",
  "xmlnamespace": "https://sts.amazonaws.com/doc/2011-06-15/",
  "documentation": "docs",
  "operations": [
    {
      "name": "AssumeRole",
      "input": {
        "shape_name": "AssumeRoleRequest",
        "type": "structure",
        "members": {
          "RoleArn": {
            "shape_name": "arnType",
            "type": "string",
            "min_length": 20,
            "max_length": 2048,
            "documentation": "docs",
            "required": True
          },
          "RoleSessionName": {
            "shape_name": "userNameType",
            "type": "string",
            "min_length": 2,
            "max_length": 32,
            "pattern": "[\\w+=,.@-]*",
            "documentation": "docs",
            "required": True
          },
          "Policy": {
            "shape_name": "sessionPolicyDocumentType",
            "type": "string",
            "pattern": "[\\u0009\\u000A\\u000D\\u0020-\\u00FF]+",
            "min_length": 1,
            "max_length": 2048,
            "documentation": "docs"
          },
          "DurationSeconds": {
            "shape_name": "roleDurationSecondsType",
            "type": "integer",
            "min_length": 900,
            "max_length": 3600,
            "documentation": "docs"
          },
          "ExternalId": {
            "shape_name": "externalIdType",
            "type": "string",
            "min_length": 2,
            "max_length": 96,
            "pattern": "[\\w+=,.@:-]*",
            "documentation": "docs"
          },
          # Not in the actual description, but this is to test iterators.
          "NextToken": {
              "shape_name": "String",
              "type": "string",
              "documentation": None
          },
        },
        "documentation": "docs"
      },
      "output": {
        "shape_name": "AssumeRoleResponse",
        "type": "structure",
        "members": {
          "Credentials": {
            "shape_name": "Credentials",
            "type": "structure",
            "members": {
              "AccessKeyId": {
                "shape_name": "accessKeyIdType",
                "type": "string",
                "min_length": 16,
                "max_length": 32,
                "pattern": "[\\w]*",
                "documentation": "docs",
                "required": True
              },
              "SecretAccessKey": {
                "shape_name": "accessKeySecretType",
                "type": "string",
                "documentation": "docs",
                "required": True
              },
              "SessionToken": {
                "shape_name": "tokenType",
                "type": "string",
                "documentation": "docs",
                "required": True
              },
              "Expiration": {
                "shape_name": "dateType",
                "type": "timestamp",
                "documentation": "docs",
                "required": True
              }
            },
            "documentation": "docs"
          },
          "AssumedRoleUser": {
            "shape_name": "AssumedRoleUser",
            "type": "structure",
            "members": {
              "AssumedRoleId": {
                "shape_name": "assumedRoleIdType",
                "type": "string",
                "min_length": 2,
                "max_length": 96,
                "pattern": "[\\w+=,.@:-]*",
                "documentation": "docs",
                "required": True
              },
              "Arn": {
                "shape_name": "arnType",
                "type": "string",
                "min_length": 20,
                "max_length": 2048,
                "documentation": "docs",
                "required": True
              }
            },
            "documentation": "docs"
          },
          "PackedPolicySize": {
            "shape_name": "nonNegativeIntegerType",
            "type": "integer",
            "min_length": 0,
            "documentation": "docs"
          },
          "NextToken": {
              "shape_name": "String",
              "type": "string",
              "documentation": None,
              "xmlname": "nextToken"
          }
        },
        "documentation": "docs"
      },
      "errors": [
        {
          "shape_name": "MalformedPolicyDocumentException",
          "type": "structure",
          "members": {
            "message": {
              "shape_name": "malformedPolicyDocumentMessage",
              "type": "string",
              "documentation": "docs"
            }
          },
          "documentation": "docs"
        },
        {
          "shape_name": "PackedPolicyTooLargeException",
          "type": "structure",
          "members": {
            "message": {
              "shape_name": "packedPolicyTooLargeMessage",
              "type": "string",
              "documentation": "docs"
            }
          },
          "documentation": "docs"
        }
      ],
      "documentation": "docs"
    },
  ]
}


class TestTranslateExtensions(unittest.TestCase):
    def setUp(self):
        self.model = ModelFiles(SERVICES, {}, {}, {})

    def test_can_add_extras_top_level_keys(self):
        # A use case here would be adding the iterator/waiter configs.
        new_keys = {'extra': {'paginators': 'paginator_config'}}
        self.model.enhancements = new_keys
        new_model = translate(self.model)
        # There should be a new top level key 'iterators' that was merged in.
        self.assertEqual(new_model['paginators'], 'paginator_config')
        self.assertIn('operations', new_model)

    def test_can_add_fields_to_operation(self):
        # A use case would be to add checksum info for a param.

        # We could go for a more streamlined syntax, but this way, it's
        # clear how this maps onto the existing json model.
        new_keys = {
            'operations': {
                'AssumeRole': {
                    'input': {
                        'checksum': 'md5',
                    }
                },
            }
        }
        self.model.enhancements = new_keys
        new_model = translate(self.model)
        self.assertEqual(
            new_model['operations']['AssumeRole']['input']['checksum'],
            'md5')

    def test_can_add_fields_to_op_params(self):
        # A use case would be if we want to annotate that a
        # string type might also come from a file (keypairs, s3 uploads, etc).
        new_keys = {
            'operations': {
                'AssumeRole': {
                    'input': {
                        'members': {
                            'Policy': {
                                'alsofrom': 'filename',
                            },
                        }
                    }
                },
            }
        }
        self.model.enhancements = new_keys
        new_model = translate(self.model)
        self.assertEqual(
            new_model['operations']['AssumeRole']['input']['members']\
                    ['Policy']['alsofrom'],
            'filename')
        self.assertEqual(
            new_model['operations']['AssumeRole']['input']['members']\
                    ['Policy']['type'],
            'string')
        self.assertEqual(
            new_model['operations']['AssumeRole']['input']['members']\
                    ['RoleArn']['shape_name'],
            'arnType')


class TestTranslateModel(unittest.TestCase):
    def setUp(self):
        self.model = ModelFiles(SERVICES, {}, {}, {})

    def test_operations_is_a_dict_not_list(self):
        # In order to make overriding easier, we want the list of
        # operations to be a dict, not a list.  The way we don't have
        # to search through the list to find the operation we want to
        # change.  It also makes it easier to annontate operations.
        new_model = translate(self.model)
        self.assertIn('AssumeRole', new_model['operations'])

    def test_supported_regions_are_merged_into_service(self):
        services = {
            "sts": {
                "regions": {
                    "us-east-1": "https://sts.amazonaws.com/",
		            "us-gov-west-1": None,
                },
                "protocols": [
                    "https"
                ]
            }
        }
        self.model.services = services
        self.model.name = 'sts'
        new_model = translate(self.model)
        self.assertDictEqual(new_model['metadata'], services['sts'])

    def test_iterators_are_merged_into_operations(self):
        # This may or may not pan out, but if a pagination config is
        # specified, that info is merged into the specific operations.
        extra = {
            'pagination': {
                'AssumeRole': {
                    'input_token': 'NextToken',
                    'output_token': 'NextToken',
                    'max_results': 'MaxResults',
                    'merge_key': 'reservedInstancesListingsSet',
                }
            }
        }
        self.model.enhancements = extra
        new_model = translate(self.model)
        op = new_model['operations']['AssumeRole']
        self.assertDictEqual(
            op['pagination'], {
                'input_token': 'NextToken',
                'output_token': 'NextToken',
                'max_results': 'MaxResults',
                'merge_key': 'reservedInstancesListingsSet',
            })

    def test_paginators_are_validated(self):
        # Can't create a paginator config that refers to a non existent
        # operation.
        extra = {
            'pagination': {
                'UnknownOperation': {
                    'input_token': 'NextToken',
                    'output_token': 'NextToken',
                    'max_results': 'MaxResults',
                    'merge_key': 'reservedInstancesListingsSet',
                }
            }
        }
        self.model.enhancements = extra
        with self.assertRaises(ValueError):
            new_model = translate(self.model)

    def test_paginators_are_placed_into_top_level_key(self):
        extra = {
            'pagination': {
                'AssumeRole': {
                    'input_token': 'NextToken',
                    'output_token': 'NextToken',
                }
            }
        }
        self.model.enhancements = extra
        new_model = translate(self.model)
        self.assertEqual(new_model['pagination'], extra['pagination'])

    def test_translate_operation_casing(self):
        pass

    def test_translate_param_casing(self):
        pass

    def test_map_types_to_python_types(self):
        pass


class TestDictMerg(unittest.TestCase):
    def test_merge_dicts_overrides(self):
        first = {'foo': {'bar': {'baz': {'one': 'ORIGINAL', 'two': 'ORIGINAL'}}}}
        second = {'foo': {'bar': {'baz': {'one': 'UPDATE'}}}}

        merge_dicts(first, second)
        # The value from the second dict wins.
        self.assertEqual(first['foo']['bar']['baz']['one'], 'UPDATE')
        # And we still preserve the other attributes.
        self.assertEqual(first['foo']['bar']['baz']['two'], 'ORIGINAL')

    def test_merge_dicts_new_keys(self):
        first = {'foo': {'bar': {'baz': {'one': 'ORIGINAL', 'two': 'ORIGINAL'}}}}
        second = {'foo': {'bar': {'baz': {'three': 'UPDATE'}}}}

        merge_dicts(first, second)
        self.assertEqual(first['foo']['bar']['baz']['one'], 'ORIGINAL')
        self.assertEqual(first['foo']['bar']['baz']['two'], 'ORIGINAL')
        self.assertEqual(first['foo']['bar']['baz']['three'], 'UPDATE')

    def test_merge_empty_dict_does_nothing(self):
        first = {'foo': {'bar': 'baz'}}
        merge_dicts(first, {})
        self.assertEqual(first, {'foo': {'bar': 'baz'}})

    def test_more_than_one_sub_dict(self):
        first = {'one': {'inner': 'ORIGINAL', 'inner2': 'ORIGINAL'},
                 'two': {'inner': 'ORIGINAL', 'inner2': 'ORIGINAL'}}
        second = {'one': {'inner': 'UPDATE'}, 'two': {'inner': 'UPDATE'}}

        merge_dicts(first, second)
        self.assertEqual(first['one']['inner'], 'UPDATE')
        self.assertEqual(first['one']['inner2'], 'ORIGINAL')

        self.assertEqual(first['two']['inner'], 'UPDATE')
        self.assertEqual(first['two']['inner2'], 'ORIGINAL')

    def test_new_keys(self):
        first = {'one': {'inner': 'ORIGINAL'}, 'two': {'inner': 'ORIGINAL'}}
        second = {'three': {'foo': {'bar': 'baz'}}}
        # In this case, second has no keys in common, but we'd still expect
        # this to get merged.
        merge_dicts(first, second)
        self.assertEqual(first['three']['foo']['bar'], 'baz')


if __name__ == '__main__':
    unittest.main()
