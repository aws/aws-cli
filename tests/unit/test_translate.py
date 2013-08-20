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
from tests import unittest
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
  "operations": {
    "AssumeRole": {
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
          "TokenToken": {
              "shape_name": "String",
              "type": "string",
              "documentation": None,
              "xmlname": "tokenToken"
          },
          "MaxResults": {
              "shape_name": "Integer",
              "type": "int",
              "documentation": None,
              "xmlname": "maxResults"
          }
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
          },
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
    "RealOperation2013_02_04": {
      "name": "RealOperation2013_02_04",
      "input": {},
      "output": {},
      "errors": [],
      "documentation": "docs"
    },
    "DeprecatedOperation": {
      "input": {
        "shape_name": "DeprecatedOperationRequest",
        "type": "structure",
        "members": {
          "FooBar": {
            "shape_name": "foobarType",
            "type": "string",
            "documentation": "blah blah <![CDATA[\n\nfoobar ]]>blah blah",
          },
          "FieBaz": {
            "shape_name": "fiebazType",
            "type": "string",
            "documentation": "Don't use this, it's deprecated"
          }
        }
      },
      "documentation": "This is my <![CDATA[none of \nthis stuff should be here]]> stuff"
    },
    "DeprecatedOperation2": {
      "input": {
        "shape_name": "DeprecatedOperation2Request",
        "type": "structure",
        "members": {
          "FooBar": {
            "shape_name": "foobarType",
            "type": "string",
            "documentation": "blah blah blah blah",
          },
          "FieBaz": {
            "shape_name": "fiebazType",
            "type": "string",
            "documentation": ""
          }
        }
      },
      "documentation": "This operation has been deprecated."
    }
  }
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
        extra = {
            "extra": {
                "metadata": {
                    "regions": {
                        "us-east-1": "https://sts.amazonaws.com/",
                        "us-gov-west-1": None,
                        },
                    "protocols": [
                        "https"
                        ]
                    }
                }
            }
        self.model.enhancements = extra
        self.model.name = 'sts'
        new_model = translate(self.model)
        self.maxDiff = None
        self.assertDictEqual(new_model['metadata'], extra['extra']['metadata'])

    def test_iterators_are_merged_into_operations(self):
        # This may or may not pan out, but if a pagination config is
        # specified, that info is merged into the specific operations.
        extra = {
            'pagination': {
                'AssumeRole': {
                    'input_token': 'NextToken',
                    'output_token': 'NextToken',
                    'limit_key': 'MaxResults',
                    'result_key': 'Credentials',
                }
            }
        }
        self.model.enhancements = extra
        new_model = translate(self.model)
        op = new_model['operations']['AssumeRole']
        self.assertDictEqual(
            op['pagination'], {
                'input_token': 'NextToken',
                'py_input_token': 'next_token',
                'output_token': 'NextToken',
                'limit_key': 'MaxResults',
                'result_key': 'Credentials',
            })

    def test_py_input_name_is_not_added_if_it_exists(self):
        # This may or may not pan out, but if a pagination config is
        # specified, that info is merged into the specific operations.
        extra = {
            'pagination': {
                'AssumeRole': {
                    'input_token': 'NextToken',
                    'output_token': 'NextToken',
                    'py_input_token': 'other_value',
                    'limit_key': 'MaxResults',
                    'result_key': 'Credentials',
                }
            }
        }
        self.model.enhancements = extra
        new_model = translate(self.model)
        op = new_model['operations']['AssumeRole']
        # Note how 'py_input_token' is left untouched.  This allows us
        # to override this naming if we need to.
        self.assertDictEqual(
            op['pagination'], {
                'input_token': 'NextToken',
                'py_input_token': 'other_value',
                'output_token': 'NextToken',
                'limit_key': 'MaxResults',
                'result_key': 'Credentials',
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
                    'result_key': 'Credentials',
                }
            }
        }
        self.model.enhancements = extra
        new_model = translate(self.model)
        self.assertEqual(new_model['pagination'], extra['pagination'])

    def test_extra_key(self):
        # Anything in "extra" is merged as a top level key.
        extra = {
            "extra": {
                "signature_version": "v2",
            }
        }
        self.model.enhancements = extra
        new_model = translate(self.model)
        self.assertEqual(new_model['signature_version'], 'v2')
        self.assertEqual(new_model['documentation'], 'docs')

    def test_paginator_with_multiple_input_outputs(self):
        extra = {
            'pagination': {
                'AssumeRole': {
                    'input_token': ['NextToken', 'TokenToken'],
                    'output_token': ['NextToken', 'NextTokenToken'],
                    'result_key': 'Credentials'
                }
            }
        }
        self.model.enhancements = extra
        new_model = translate(self.model)
        op = new_model['operations']['AssumeRole']
        self.assertDictEqual(
            op['pagination'], {
                'input_token': ['NextToken', 'TokenToken'],
                'py_input_token': ['next_token', 'token_token'],
                'output_token': ['NextToken', 'NextTokenToken'],
                'result_key': 'Credentials',
            })

    def test_result_key_validation(self):
        # result_key must exist.
        extra = {
            'pagination': {
                'AssumeRole': {
                    'input_token': ['Token', 'TokenToken'],
                    'output_token': ['NextToken', 'NextTokenToken']
                }
            }
        }
        self.model.enhancements = extra
        with self.assertRaises(ValueError):
            translate(self.model)

    def test_result_key_exists_in_output(self):
        extra = {
            'pagination': {
                'AssumeRole': {
                    'input_token': ['Token', 'TokenToken'],
                    'output_token': ['NextToken', 'NextTokenToken'],
                    'result_key': 'DoesNotExist',
                }
            }
        }
        self.model.enhancements = extra
        with self.assertRaises(ValueError):
            translate(self.model)

    def test_result_key_can_be_a_list(self):
        extra = {
            'pagination': {
                'AssumeRole': {
                    'input_token': ['NextToken'],
                    'output_token': ['NextToken', 'NextTokenToken'],
                    'result_key': ['Credentials', 'AssumedRoleUser'],
                }
            }
        }
        self.model.enhancements = extra
        new_model = translate(self.model)
        self.assertEqual(new_model['pagination'], extra['pagination'])

    def test_expected_schema_exists(self):
        # In this case, the key 'output_tokens' is suppose to be 'output_token'
        # so we should get an error when this happens.
        extra = {
            'pagination': {
                'AssumeRole': {
                    'input_token': ['Token', 'TokenToken'],
                    'output_tokens': ['NextToken', 'NextTokenToken'],
                    'result_key': ['Credentials', 'AssumedRoleUser'],
                }
            }
        }
        self.model.enhancements = extra
        with self.assertRaises(ValueError):
            translate(self.model)

    def test_input_tokens_exist_in_model(self):
        extra = {
            'pagination': {
                'AssumeRole': {
                    # In this case, "DoesNotExist" token is not in the input
                    # model, so we get an exception complaining about this.
                    'input_token': ['NextToken', 'DoesNotExist'],
                    'output_token': ['NextToken', 'NextTokenToken'],
                    'result_key': ['Credentials', 'AssumedRoleUser'],
                }
            }
        }
        self.model.enhancements = extra
        with self.assertRaises(ValueError):
            translate(self.model)

    def test_validate_limit_key_is_in_input(self):
        extra = {
            'pagination': {
                'AssumeRole': {
                    'input_token': 'NextToken',
                    'output_token': ['NextToken', 'NextTokenToken'],
                    'result_key': ['Credentials', 'AssumedRoleUser'],
                    # In this case, "DoesNotExist" token is not in the input
                    # model, so we get an exception complaining about this.
                    'limit_key': 'DoesNotExist',
                }
            }
        }
        self.model.enhancements = extra
        with self.assertRaises(ValueError):
            translate(self.model)


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


class TestBuildRetryConfig(unittest.TestCase):
    def setUp(self):
        self.retry = {
            "definitions": {
                "def_name": {
                    "from": {"definition": "file"}
                }
            },
            "retry": {
                "__default__": {
                    "max_attempts": 5,
                    "delay": "global_delay",
                    "policies": {
                        "global_one": "global",
                        "override_me": "global",
                    }
                },
                "sts": {
                    "__default__": {
                        "delay": "service_specific_delay",
                        "policies": {
                            "service_one": "service",
                            "override_me": "service",
                        }
                    },
                    "AssumeRole": {
                        "policies": {
                            "name": "policy",
                            "other": {"$ref": "def_name"}
                        }
                    }
                }
            }
        }

    def test_inject_retry_config(self):
        model = ModelFiles(SERVICES, {}, self.retry, {})
        new_model = translate(model)
        self.assertIn('retry', new_model)
        retry = new_model['retry']
        self.assertIn('__default__', retry)
        self.assertEqual(
            retry['__default__'], {
                "max_attempts": 5,
                "delay": "service_specific_delay",
                "policies": {
                    "global_one": "global",
                    "override_me": "service",
                    "service_one": "service",
                }
            }
        )
        # Policies should be merged.
        operation_config = retry['AssumeRole']
        self.assertEqual(operation_config['policies']['name'], 'policy')

    def test_resolve_reference(self):
        model = ModelFiles(SERVICES, {}, self.retry, {})
        new_model = translate(model)
        operation_config = new_model['retry']['AssumeRole']
        # And we should resolve references.
        self.assertEqual(operation_config['policies']['other'],
                         {"from": {"definition": "file"}})


class TestReplacePartOfOperation(unittest.TestCase):
    def test_replace_operation_key_name(self):
        enhancements = {
            'transformations': {
                'operation-name': {'remove': r'\d{4}_\d{2}_\d{2}'}
            }
        }
        model = ModelFiles(SERVICES, regions={}, retry={},
                           enhancements=enhancements)
        new_model = translate(model)
        # But the key into the operation dict is stripped of the
        # matched regex.
        self.assertEqual(list(sorted(new_model['operations'].keys())),
                         ['AssumeRole', 'DeprecatedOperation',
                          'DeprecatedOperation2', 'RealOperation'])
        # But the name key attribute is left unchanged.
        self.assertEqual(new_model['operations']['RealOperation']['name'],
                         'RealOperation2013_02_04')


class TestRemovalOfDeprecatedParams(unittest.TestCase):
    
    def test_remove_deprecated_params(self):
        enhancements = {
            'transformations': {
                'remove-deprecated-params': {'deprecated_keyword': 'deprecated'}
                }
            }
        model = ModelFiles(SERVICES, regions={}, retry={},
                           enhancements=enhancements)
        new_model = translate(model)
        operation = new_model['operations']['DeprecatedOperation']
        # The deprecated param should be gone, the other should remain
        self.assertIn('FooBar', operation['input']['members'])
        self.assertNotIn('FieBaz', operation['input']['members'])

class TestRemovalOfDeprecatedOps(unittest.TestCase):
    
    def test_remove_deprecated_ops(self):
        enhancements = {
            'transformations': {
                'remove-deprecated-operations':
                    {'deprecated_keyword': 'deprecated'}
                }
            }
        model = ModelFiles(SERVICES, regions={}, retry={},
                           enhancements=enhancements)
        new_model = translate(model)
        # The deprecated operation should be gone
        self.assertNotIn('DeprecatedOperation2', new_model['operations'])

        
class TestFilteringOfDocumentation(unittest.TestCase):
    
    def test_remove_deprecated_params(self):
        enhancements = {
            "transformations": {
                "filter-documentation": {
                    "filter": {
                        "regex": "<!\\[CDATA\\[.*\\]\\]>",
                        "replacement": ""
                        }
                    }
                }
            }
        model = ModelFiles(SERVICES, regions={}, retry={},
                           enhancements=enhancements)
        new_model = translate(model)
        operation = new_model['operations']['DeprecatedOperation']
        # The deprecated param should be gone, the other should remain
        self.assertEqual(operation['documentation'], 'This is my  stuff')
        param = operation['input']['members']['FooBar']
        self.assertEqual(param['documentation'], 'blah blah blah blah')


if __name__ == '__main__':
    unittest.main()
