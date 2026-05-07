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
"""Functional tests for the 'aws schema' command."""
import json

from awscli.testutils import BaseAWSCommandParamsTest


class TestSchemaOperation(BaseAWSCommandParamsTest):
    """Test 'aws schema <service> <operation>' outputs JSON schema."""

    def test_put_object_output_structure(self):
        stdout, _, _ = self.run_cmd(
            'schema s3 put-object', expected_rc=0
        )
        parsed = json.loads(stdout)
        self.assertEqual(parsed['name'], 'PutObject')
        self.assertEqual(parsed['operation']['http']['method'], 'PUT')
        self.assertIn('shape', parsed['operation']['input'])
        input_shape = parsed['shapes'][parsed['operation']['input']['shape']]
        self.assertEqual(input_shape['type'], 'structure')
        self.assertIn('Bucket', input_shape['required'])
        self.assertIsInstance(parsed['operation']['errors'], list)

    def test_dynamodb_recursive_shapes(self):
        stdout, _, _ = self.run_cmd(
            'schema dynamodb put-item', expected_rc=0
        )
        parsed = json.loads(stdout)
        self.assertIn('AttributeValue', parsed['shapes'])
        self.assertIn('ListAttributeValue', parsed['shapes'])


class TestSchemaTopLevel(BaseAWSCommandParamsTest):
    """Test 'aws schema' (no args) lists all services."""

    def test_lists_services(self):
        stdout, _, _ = self.run_cmd('schema', expected_rc=0)
        parsed = json.loads(stdout)
        self.assertIn('services', parsed)
        names = [s['name'] for s in parsed['services']]
        self.assertIn('s3', names)
        self.assertIn('ec2', names)
        s3_entry = next(s for s in parsed['services'] if s['name'] == 's3')
        self.assertNotIn('documentation', s3_entry)

    def test_includes_documentation_with_docs_flag(self):
        stdout, _, _ = self.run_cmd('schema --docs', expected_rc=0)
        parsed = json.loads(stdout)
        self.assertIn('services', parsed)
        ddb_entry = next(
            (s for s in parsed['services'] if s['name'] == 'dynamodb'), None
        )
        self.assertIsNotNone(ddb_entry)
        self.assertIn('documentation', ddb_entry)


class TestSchemaErrors(BaseAWSCommandParamsTest):
    """Test error handling for 'aws schema'."""

    def test_invalid_operation_returns_json_error(self):
        stdout, stderr, _ = self.run_cmd(
            'schema s3 nonexistent-op', expected_rc=1
        )
        self.assertEqual(stdout, '')
        parsed = json.loads(stderr)
        self.assertIn('not found', parsed['error']['message'])

    def test_typo_suggests_correction(self):
        stdout, stderr, _ = self.run_cmd(
            'schema s3 put-objekt', expected_rc=1
        )
        self.assertEqual(stdout, '')
        parsed = json.loads(stderr)
        self.assertIn('put-object', parsed['error']['message'])

    def test_invalid_service_returns_json_error(self):
        stdout, stderr, _ = self.run_cmd(
            'schema nonexistent-service list-things', expected_rc=1
        )
        self.assertEqual(stdout, '')
        parsed = json.loads(stderr)
        self.assertIn('error', parsed)
        self.assertEqual(parsed['error']['reason'], 'serviceNotFound')

    def test_invalid_service_suggests_close_match(self):
        stdout, stderr, _ = self.run_cmd(
            'schema dynamdb list-things', expected_rc=1
        )
        self.assertEqual(stdout, '')
        parsed = json.loads(stderr)
        self.assertIn('dynamodb', parsed['error']['message'])

    def test_cli_command_name_suggests_service(self):
        stdout, stderr, _ = self.run_cmd(
            'schema s3api put-object', expected_rc=1
        )
        self.assertEqual(stdout, '')
        parsed = json.loads(stderr)
        self.assertIn("'s3api' is the CLI command name", parsed['error']['message'])


class TestSchemaSemanticFields(BaseAWSCommandParamsTest):
    """Test that semantic fields are correctly preserved."""

    def test_streaming_member_preserved(self):
        stdout, _, _ = self.run_cmd(
            'schema s3 get-object', expected_rc=0
        )
        parsed = json.loads(stdout)
        output_shape = parsed['shapes']['GetObjectOutput']
        body_member = output_shape['members']['Body']
        self.assertTrue(body_member.get('streaming'))

    def test_idempotency_token_preserved(self):
        stdout, _, _ = self.run_cmd(
            'schema ec2 run-instances', expected_rc=0
        )
        parsed = json.loads(stdout)
        input_shape_name = parsed['operation']['input']['shape']
        input_shape = parsed['shapes'][input_shape_name]
        client_token = input_shape['members']['ClientToken']
        self.assertTrue(client_token.get('idempotencyToken'))

    def test_sensitive_flag_preserved(self):
        stdout, _, _ = self.run_cmd(
            'schema s3 put-object', expected_rc=0
        )
        parsed = json.loads(stdout)
        sse_shape = parsed['shapes'].get('SSEKMSKeyId', {})
        self.assertTrue(sse_shape.get('sensitive'))

    def test_constraints_preserved(self):
        stdout, _, _ = self.run_cmd(
            'schema dynamodb put-item', expected_rc=0
        )
        parsed = json.loads(stdout)
        table_shape = parsed['shapes'].get('TableArn', {})
        self.assertEqual(table_shape.get('min'), 1)
        self.assertEqual(table_shape.get('max'), 1024)

    def test_enum_preserved(self):
        stdout, _, _ = self.run_cmd(
            'schema s3 put-object', expected_rc=0
        )
        parsed = json.loads(stdout)
        acl_shape = parsed['shapes'].get('ObjectCannedACL', {})
        self.assertIn('enum', acl_shape)
        self.assertIn('private', acl_shape['enum'])


class TestSchemaPagination(BaseAWSCommandParamsTest):
    """Test pagination info is included for paginated operations."""

    def test_paginated_operation_has_pagination(self):
        stdout, _, _ = self.run_cmd(
            'schema s3 list-objects-v2', expected_rc=0
        )
        parsed = json.loads(stdout)
        self.assertIn('pagination', parsed['operation'])
        self.assertEqual(
            parsed['operation']['pagination']['inputToken'],
            'ContinuationToken'
        )
        self.assertEqual(
            parsed['operation']['pagination']['outputToken'],
            'NextContinuationToken'
        )

    def test_non_paginated_operation_no_pagination(self):
        stdout, _, _ = self.run_cmd(
            'schema s3 put-object', expected_rc=0
        )
        parsed = json.loads(stdout)
        self.assertNotIn('pagination', parsed['operation'])


class TestSchemaServiceLevel(BaseAWSCommandParamsTest):
    """Test service-level schema output."""

    def test_service_schema_structure(self):
        stdout, _, _ = self.run_cmd('schema s3', expected_rc=0)
        parsed = json.loads(stdout)
        self.assertIsInstance(parsed['operations'], list)
        op_names = [op['name'] for op in parsed['operations']]
        self.assertIn('PutObject', op_names)

    def test_service_schema_lists_paginated_operations(self):
        stdout, _, _ = self.run_cmd('schema s3', expected_rc=0)
        parsed = json.loads(stdout)
        for op in parsed['operations']:
            if op['name'] == 'ListObjectsV2':
                self.assertTrue(op.get('paginated'))
                return
        self.fail('ListObjectsV2 not found')

    def test_service_schema_lists_waiters(self):
        stdout, _, _ = self.run_cmd('schema s3', expected_rc=0)
        parsed = json.loads(stdout)
        self.assertIn('waiters', parsed)
        names = [w['name'] for w in parsed['waiters']]
        self.assertIn('BucketExists', names)

    def test_service_schema_marks_deprecated_operations(self):
        stdout, _, _ = self.run_cmd('schema s3', expected_rc=0)
        parsed = json.loads(stdout)
        for op in parsed['operations']:
            if op['name'] == 'GetBucketLifecycle':
                self.assertTrue(op.get('deprecated'))
                return
        self.fail('GetBucketLifecycle not found')

    def test_service_without_waiters_omits_field(self):
        stdout, _, _ = self.run_cmd('schema sts', expected_rc=0)
        parsed = json.loads(stdout)
        self.assertNotIn('waiters', parsed)

    def test_service_schema_with_docs_flag(self):
        stdout, _, _ = self.run_cmd('schema dynamodb --docs', expected_rc=0)
        parsed = json.loads(stdout)
        self.assertIn('documentation', parsed)
        for op in parsed['operations']:
            if op['name'] == 'PutItem':
                self.assertIn('documentation', op)
                return
        self.fail('PutItem not found')

    def test_waiters_always_include_description(self):
        """Waiter description is always included, independent of --docs."""
        stdout, _, _ = self.run_cmd('schema mediaconnect', expected_rc=0)
        parsed = json.loads(stdout)
        self.assertIn('waiters', parsed)
        first = parsed['waiters'][0]
        self.assertIsInstance(first, dict)
        self.assertIn('name', first)
        self.assertIn('description', first)


class TestDocStripping(BaseAWSCommandParamsTest):
    """Global scan: default output has no 'documentation', --docs does."""

    @staticmethod
    def _find_doc_keys(obj, path=''):
        """Paths of every 'documentation' dict key (case-sensitive)."""
        violations = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == 'documentation':
                    violations.append(f"{path}.{k}")
                violations.extend(
                    TestDocStripping._find_doc_keys(v, f"{path}.{k}")
                )
        elif isinstance(obj, list):
            for i, x in enumerate(obj):
                violations.extend(
                    TestDocStripping._find_doc_keys(x, f"{path}[{i}]")
                )
        return violations

    def _assert_no_doc_leaks(self, cmd):
        stdout, _, _ = self.run_cmd(cmd, expected_rc=0)
        parsed = json.loads(stdout)
        violations = self._find_doc_keys(parsed)
        self.assertEqual(
            violations, [], f"{cmd}: leaked doc keys at {violations}"
        )

    def _assert_docs_present(self, cmd):
        stdout, _, _ = self.run_cmd(cmd, expected_rc=0)
        parsed = json.loads(stdout)
        violations = self._find_doc_keys(parsed)
        self.assertTrue(
            len(violations) > 0,
            f"{cmd}: no documentation found"
        )

    def test_s3_put_object_no_leak(self):
        self._assert_no_doc_leaks('schema s3 put-object')

    def test_pinpoint_create_app_no_leak(self):
        # pinpoint CreateApp has docs on op.output and op.errors[].
        self._assert_no_doc_leaks('schema pinpoint create-app')

    def test_s3_put_object_docs_present(self):
        self._assert_docs_present('schema s3 put-object --docs')

    def test_pinpoint_create_app_docs_present(self):
        self._assert_docs_present('schema pinpoint create-app --docs')

    def test_service_level_s3_no_leak(self):
        self._assert_no_doc_leaks('schema s3')

    def test_service_level_mediaconnect_no_leak(self):
        # Waiter 'description' is preserved.
        self._assert_no_doc_leaks('schema mediaconnect')
