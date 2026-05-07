# Copyright 2025 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
"""Unit tests for the 'aws schema' command."""
import json
from argparse import Namespace
from unittest import mock

from awscli.compat import StringIO
from awscli.customizations.schema.schema import SchemaCommand
from awscli.testutils import unittest

SAMPLE_SERVICE_MODEL = {
    'metadata': {
        'apiVersion': '2006-03-01',
        'endpointPrefix': 's3',
        'protocol': 'rest-xml',
        'serviceId': 'S3',
    },
    'operations': {
        'PutObject': {
            'name': 'PutObject',
            'documentation': '<p>Adds an object.</p>',
            'http': {'method': 'PUT', 'requestUri': '/{Bucket}/{Key+}'},
            'input': {'shape': 'PutObjectRequest'},
            'output': {'shape': 'PutObjectOutput'},
            'errors': [{'shape': 'NoSuchBucket'}],
        },
        'DeprecatedOp': {
            'name': 'DeprecatedOp',
            'documentation': '<p>Old.</p>',
            'deprecated': True,
            'http': {'method': 'GET'},
        },
    },
    'shapes': {
        'PutObjectRequest': {
            'type': 'structure',
            'required': ['Bucket', 'Key'],
            'members': {
                'Bucket': {
                    'shape': 'BucketName',
                    'documentation': '<p>The bucket.</p>',
                },
                'Key': {
                    'shape': 'ObjectKey',
                    'documentation': '<p>The key.</p>',
                },
                'Body': {'shape': 'Body'},
                'ACL': {'shape': 'CannedACL'},
            },
        },
        'PutObjectOutput': {
            'type': 'structure',
            'members': {
                'ETag': {'shape': 'ETag'},
            },
        },
        'BucketName': {'type': 'string', 'min': 3, 'max': 63},
        'ObjectKey': {'type': 'string', 'min': 1},
        'Body': {'type': 'blob'},
        'ETag': {'type': 'string'},
        'CannedACL': {
            'type': 'string',
            'enum': ['private', 'public-read'],
        },
        'NoSuchBucket': {
            'type': 'structure',
            'members': {},
            'error': {'httpStatusCode': 404, 'code': 'NoSuchBucket'},
            'exception': True,
        },
    },
}


class TestSchemaCommand(unittest.TestCase):
    """Test SchemaCommand behavior with mocked service models."""

    def setUp(self):
        self.session = mock.Mock()
        self.stream = StringIO()
        self.error_stream = StringIO()
        self.command = SchemaCommand(
            self.session, stream=self.stream, error_stream=self.error_stream
        )
        self.mock_loader = mock.Mock()
        self.mock_loader.list_available_services.return_value = [
            's3', 'ec2', 'dynamodb', 'lambda',
        ]
        self.mock_loader.load_service_model.return_value = SAMPLE_SERVICE_MODEL
        self.session.get_component.return_value = self.mock_loader

    def _run(self, service, operation=None, docs=False):
        parsed_args = Namespace(
            service=service, operation=operation, docs=docs
        )
        parsed_globals = Namespace()
        return self.command._run_main(parsed_args, parsed_globals)

    def _get_output(self):
        return json.loads(self.stream.getvalue())

    def _get_error(self):
        return json.loads(self.error_stream.getvalue())

    def test_top_level_fields(self):
        rc = self._run('s3', 'put-object')
        self.assertEqual(rc, 0)
        output = self._get_output()
        self.assertEqual(output['name'], 'PutObject')
        self.assertEqual(output['operation']['http']['method'], 'PUT')

    def test_documentation_stripped_by_default(self):
        self._run('s3', 'put-object')
        output = self._get_output()
        self.assertNotIn('documentation', output['operation'])
        bucket_member = output['shapes']['PutObjectRequest']['members']['Bucket']
        self.assertNotIn('documentation', bucket_member)

    def test_input_is_shape_ref(self):
        self._run('s3', 'put-object')
        output = self._get_output()
        self.assertEqual(
            output['operation']['input'], {'shape': 'PutObjectRequest'}
        )

    def test_output_is_shape_ref(self):
        self._run('s3', 'put-object')
        output = self._get_output()
        self.assertEqual(
            output['operation']['output'], {'shape': 'PutObjectOutput'}
        )

    def test_errors_preserved(self):
        self._run('s3', 'put-object')
        output = self._get_output()
        self.assertEqual(
            output['operation']['errors'], [{'shape': 'NoSuchBucket'}]
        )

    def test_shapes_contains_reachable_shapes(self):
        self._run('s3', 'put-object')
        output = self._get_output()
        self.assertIn('PutObjectRequest', output['shapes'])
        self.assertIn('BucketName', output['shapes'])
        self.assertIn('CannedACL', output['shapes'])
        self.assertIn('NoSuchBucket', output['shapes'])

    def test_shape_constraints_preserved(self):
        self._run('s3', 'put-object')
        output = self._get_output()
        bucket_shape = output['shapes']['BucketName']
        self.assertEqual(bucket_shape['min'], 3)
        self.assertEqual(bucket_shape['max'], 63)

    def test_shape_enum_preserved(self):
        self._run('s3', 'put-object')
        output = self._get_output()
        acl_shape = output['shapes']['CannedACL']
        self.assertEqual(acl_shape['enum'], ['private', 'public-read'])

    def test_deprecated_flag(self):
        self._run('s3', 'deprecated-op')
        output = self._get_output()
        self.assertTrue(output['operation']['deprecated'])

    def test_non_deprecated_omits_flag(self):
        self._run('s3', 'put-object')
        output = self._get_output()
        self.assertNotIn('deprecated', output['operation'])

    def test_docs_included_when_flag_set(self):
        parsed_args = Namespace(
            service='s3', operation='put-object', docs=True
        )
        self.command._run_main(parsed_args, Namespace())
        output = self._get_output()
        self.assertIn('documentation', output['operation'])
        bucket = output['shapes']['PutObjectRequest']['members']['Bucket']
        self.assertIn('documentation', bucket)

    def test_service_level_docs_can_be_included(self):
        self.mock_loader.load_service_model.return_value = {
            **SAMPLE_SERVICE_MODEL,
            'documentation': '<p>S3 service docs.</p>',
        }
        parsed_args = Namespace(service='s3', operation=None, docs=True)
        self.command._run_main(parsed_args, Namespace())
        output = self._get_output()
        self.assertEqual(output['documentation'], '<p>S3 service docs.</p>')
        for op in output['operations']:
            self.assertIn('documentation', op)

    def test_missing_service_returns_service_list(self):
        self.mock_loader.list_available_services.return_value = ['s3', 'ec2']
        rc = self._run(None)
        self.assertEqual(rc, 0)
        output = self._get_output()
        self.assertIn('services', output)
        self.assertEqual(
            output['services'], [{"name": "s3"}, {"name": "ec2"}]
        )

    def test_missing_service_with_docs_includes_documentation(self):
        self.mock_loader.list_available_services.return_value = ['s3']
        self.mock_loader.load_service_model.return_value = {
            'documentation': '<p>Amazon S3 docs.</p>'
        }
        parsed_args = Namespace(service=None, operation=None, docs=True)
        rc = self.command._run_main(parsed_args, Namespace())
        self.assertEqual(rc, 0)
        output = self._get_output()
        self.assertEqual(
            output['services'],
            [{"name": "s3", "documentation": "<p>Amazon S3 docs.</p>"}],
        )

    def test_missing_operation_returns_service_overview(self):
        rc = self._run('s3', None)
        self.assertEqual(rc, 0)
        output = self._get_output()
        self.assertIn('operations', output)

    def test_invalid_operation_returns_error_with_suggestion(self):
        rc = self._run('s3', 'put-objec')
        self.assertEqual(rc, 1)
        self.assertEqual(self.stream.getvalue(), '')
        output = self._get_error()
        self.assertIn('put-object', output['error']['message'])

    def test_cli_command_name_suggests_service(self):
        rc = self._run('s3api', 'put-object')
        self.assertEqual(rc, 1)
        output = self._get_error()
        self.assertIn("'s3api' is the CLI command name", output['error']['message'])
        self.assertIn("'s3'", output['error']['message'])

    def test_invalid_service_returns_error_with_suggestion(self):
        rc = self._run('dynamdb', 'list')
        self.assertEqual(rc, 1)
        self.assertEqual(self.stream.getvalue(), '')
        output = self._get_error()
        self.assertEqual(output['error']['reason'], 'serviceNotFound')
        self.assertIn('dynamodb', output['error']['message'])


class TestSchemaRecursiveShapes(unittest.TestCase):
    """Test that recursive shapes are handled without infinite loops."""

    def setUp(self):
        self.service_model = {
            'metadata': {
                'apiVersion': '2012-08-10',
                'endpointPrefix': 'dynamodb',
                'protocol': 'json',
                'serviceId': 'DynamoDB',
            },
            'operations': {
                'PutItem': {
                    'name': 'PutItem',
                    'documentation': '<p>Puts an item.</p>',
                    'http': {'method': 'POST'},
                    'input': {'shape': 'PutItemInput'},
                    'output': {'shape': 'PutItemOutput'},
                },
            },
            'shapes': {
                'PutItemInput': {
                    'type': 'structure',
                    'required': ['TableName', 'Item'],
                    'members': {
                        'TableName': {'shape': 'TableName'},
                        'Item': {'shape': 'AttributeMap'},
                    },
                },
                'PutItemOutput': {
                    'type': 'structure',
                    'members': {},
                },
                'TableName': {'type': 'string'},
                'AttributeMap': {
                    'type': 'map',
                    'key': {'shape': 'AttributeName'},
                    'value': {'shape': 'AttributeValue'},
                },
                'AttributeName': {'type': 'string'},
                'AttributeValue': {
                    'type': 'structure',
                    'members': {
                        'S': {'shape': 'StringValue'},
                        'L': {'shape': 'ListAttributeValue'},
                        'M': {'shape': 'MapAttributeValue'},
                    },
                },
                'StringValue': {'type': 'string'},
                'ListAttributeValue': {
                    'type': 'list',
                    'member': {'shape': 'AttributeValue'},
                },
                'MapAttributeValue': {
                    'type': 'map',
                    'key': {'shape': 'AttributeName'},
                    'value': {'shape': 'AttributeValue'},
                },
            },
        }
        self.session = mock.Mock()
        self.stream = StringIO()
        self.error_stream = StringIO()
        self.command = SchemaCommand(
            self.session, stream=self.stream, error_stream=self.error_stream
        )
        self.mock_loader = mock.Mock()
        self.mock_loader.list_available_services.return_value = ['dynamodb']
        self.session.get_component.return_value = self.mock_loader

    def test_recursive_model_does_not_crash(self):
        self.mock_loader.load_service_model.return_value = self.service_model
        parsed_args = Namespace(
            service='dynamodb', operation='put-item', docs=False
        )
        rc = self.command._run_main(parsed_args, Namespace())
        self.assertEqual(rc, 0)
        output = json.loads(self.stream.getvalue())
        self.assertIn('shapes', output)

    def test_recursive_shapes_collected(self):
        self.mock_loader.load_service_model.return_value = self.service_model
        parsed_args = Namespace(
            service='dynamodb', operation='put-item', docs=False
        )
        self.command._run_main(parsed_args, Namespace())
        output = json.loads(self.stream.getvalue())
        self.assertIn('AttributeValue', output['shapes'])
        self.assertIn('ListAttributeValue', output['shapes'])
        list_shape = output['shapes']['ListAttributeValue']
        self.assertEqual(list_shape['member']['shape'], 'AttributeValue')
