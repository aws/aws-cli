# Copyright 2012-2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from tests import unittest, BaseSessionTest

import base64
import mock
import copy
import os
import json

import pytest

import botocore
import botocore.session
from botocore.compat import OrderedDict
from botocore.exceptions import ParamValidationError, MD5UnavailableError
from botocore.exceptions import AliasConflictParameterError
from botocore.exceptions import MissingServiceIdError
from botocore.awsrequest import AWSRequest
from botocore.compat import quote, six
from botocore.config import Config
from botocore.docs.bcdoc.restdoc import DocumentStructure
from botocore.docs.params import RequestParamsDocumenter
from botocore.docs.example import RequestExampleDocumenter
from botocore.hooks import HierarchicalEmitter
from botocore.loaders import Loader
from botocore.model import OperationModel, ServiceModel, ServiceId
from botocore.model import DenormalizedStructureBuilder
from botocore.session import Session
from botocore.signers import RequestSigner
from botocore.credentials import Credentials
from botocore.utils import conditionally_calculate_md5
from botocore import handlers


class TestHandlers(BaseSessionTest):

    def test_get_console_output(self):
        parsed = {'Output': base64.b64encode(b'foobar').decode('utf-8')}
        handlers.decode_console_output(parsed)
        self.assertEqual(parsed['Output'], 'foobar')

    def test_get_console_output_cant_be_decoded(self):
        parsed = {'Output': 1}
        handlers.decode_console_output(parsed)
        self.assertEqual(parsed['Output'], 1)

    def test_get_console_output_bad_unicode_errors(self):
        original = base64.b64encode(b'before\xffafter').decode('utf-8')
        parsed = {'Output': original}
        handlers.decode_console_output(parsed)
        self.assertEqual(parsed['Output'], u'before\ufffdafter')

    def test_noop_if_output_key_does_not_exist(self):
        original = {'foo': 'bar'}
        parsed = original.copy()

        handlers.decode_console_output(parsed)
        # Should be unchanged because the 'Output'
        # key is not in the output.
        self.assertEqual(parsed, original)

    def test_decode_quoted_jsondoc(self):
        value = quote('{"foo":"bar"}')
        converted_value = handlers.decode_quoted_jsondoc(value)
        self.assertEqual(converted_value, {'foo': 'bar'})

    def test_cant_decode_quoted_jsondoc(self):
        value = quote('{"foo": "missing end quote}')
        converted_value = handlers.decode_quoted_jsondoc(value)
        self.assertEqual(converted_value, value)

    def test_disable_signing(self):
        self.assertEqual(handlers.disable_signing(), botocore.UNSIGNED)

    def test_only_quote_url_path_not_version_id(self):
        params = {'CopySource': '/foo/bar++baz?versionId=123'}
        handlers.handle_copy_source_param(params)
        self.assertEqual(params['CopySource'],
                         '/foo/bar%2B%2Bbaz?versionId=123')

    def test_only_version_id_is_special_cased(self):
        params = {'CopySource': '/foo/bar++baz?notVersion=foo+'}
        handlers.handle_copy_source_param(params)
        self.assertEqual(params['CopySource'],
                         '/foo/bar%2B%2Bbaz%3FnotVersion%3Dfoo%2B')

    def test_copy_source_with_multiple_questions(self):
        params = {'CopySource': '/foo/bar+baz?a=baz+?versionId=a+'}
        handlers.handle_copy_source_param(params)
        self.assertEqual(params['CopySource'],
                         '/foo/bar%2Bbaz%3Fa%3Dbaz%2B?versionId=a+')

    def test_copy_source_supports_dict(self):
        params = {
            'CopySource': {'Bucket': 'foo', 'Key': 'keyname+'}
        }
        handlers.handle_copy_source_param(params)
        self.assertEqual(params['CopySource'], 'foo/keyname%2B')

    def test_copy_source_ignored_if_not_dict(self):
        params = {
            'CopySource': 'stringvalue'
        }
        handlers.handle_copy_source_param(params)
        self.assertEqual(params['CopySource'], 'stringvalue')

    def test_copy_source_supports_optional_version_id(self):
        params = {
            'CopySource': {'Bucket': 'foo',
                           'Key': 'keyname+',
                           'VersionId': 'asdf+'}
        }
        handlers.handle_copy_source_param(params)
        self.assertEqual(params['CopySource'],
                         # Note, versionId is not url encoded.
                         'foo/keyname%2B?versionId=asdf+')

    def test_copy_source_has_validation_failure(self):
        with self.assertRaisesRegex(ParamValidationError, 'Key'):
            handlers.handle_copy_source_param(
                {'CopySource': {'Bucket': 'foo'}})

    def test_quote_source_header_needs_no_changes(self):
        params = {'CopySource': '/foo/bar?versionId=123'}
        handlers.handle_copy_source_param(params)
        self.assertEqual(params['CopySource'],
                         '/foo/bar?versionId=123')

    def test_presigned_url_already_present_ec2(self):
        operation_model = mock.Mock()
        operation_model.name = 'CopySnapshot'
        params = {'body': {'PresignedUrl': 'https://foo'}}
        credentials = Credentials('key', 'secret')
        event_emitter = HierarchicalEmitter()
        request_signer = RequestSigner(
            ServiceId('ec2'), 'us-east-1', 'ec2', 'v4',
            credentials, event_emitter)
        handlers.inject_presigned_url_ec2(
            params, request_signer, operation_model)
        self.assertEqual(params['body']['PresignedUrl'], 'https://foo')

    def test_presigned_url_with_source_region_ec2(self):
        operation_model = mock.Mock()
        operation_model.name = 'CopySnapshot'
        params = {
            'body': {
                'PresignedUrl': 'https://foo',
                'SourceRegion': 'us-east-1'
            }
        }
        credentials = Credentials('key', 'secret')
        event_emitter = HierarchicalEmitter()
        request_signer = RequestSigner(
            ServiceId('ec2'), 'us-east-1', 'ec2', 'v4', credentials,
            event_emitter)
        handlers.inject_presigned_url_ec2(
            params, request_signer, operation_model)
        self.assertEqual(params['body']['PresignedUrl'], 'https://foo')
        self.assertEqual(params['body']['SourceRegion'], 'us-east-1')

    def test_presigned_url_already_present_rds(self):
        operation_model = mock.Mock()
        operation_model.name = 'CopyDBSnapshot'
        params = {'body': {'PreSignedUrl': 'https://foo'}}
        credentials = Credentials('key', 'secret')
        event_emitter = HierarchicalEmitter()
        request_signer = RequestSigner(
            ServiceId('rds'), 'us-east-1', 'rds', 'v4', credentials,
            event_emitter)
        handlers.inject_presigned_url_rds(
            params, request_signer, operation_model)
        self.assertEqual(params['body']['PreSignedUrl'], 'https://foo')

    def test_presigned_url_with_source_region_rds(self):
        operation_model = mock.Mock()
        operation_model.name = 'CopyDBSnapshot'
        params = {
            'body': {
                'PreSignedUrl': 'https://foo',
                'SourceRegion': 'us-east-1'
            }
        }
        credentials = Credentials('key', 'secret')
        event_emitter = HierarchicalEmitter()
        request_signer = RequestSigner(
            ServiceId('rds'), 'us-east-1', 'rds', 'v4', credentials,
            event_emitter)
        handlers.inject_presigned_url_rds(
            params, request_signer, operation_model)
        self.assertEqual(params['body']['PreSignedUrl'], 'https://foo')
        self.assertNotIn('SourceRegion', params['body'])

    def test_inject_presigned_url_ec2(self):
        operation_model = mock.Mock()
        operation_model.name = 'CopySnapshot'
        credentials = Credentials('key', 'secret')
        event_emitter = HierarchicalEmitter()
        request_signer = RequestSigner(
            ServiceId('ec2'), 'us-east-1', 'ec2', 'v4', credentials,
            event_emitter)
        request_dict = {}
        params = {'SourceRegion': 'us-west-2'}
        request_dict['body'] = params
        request_dict['url'] = 'https://ec2.us-east-1.amazonaws.com'
        request_dict['method'] = 'POST'
        request_dict['headers'] = {}
        request_dict['context'] = {}

        handlers.inject_presigned_url_ec2(
            request_dict, request_signer, operation_model)

        self.assertIn('https://ec2.us-west-2.amazonaws.com?',
                      params['PresignedUrl'])
        self.assertIn('X-Amz-Signature',
                      params['PresignedUrl'])
        self.assertIn('DestinationRegion', params['PresignedUrl'])
        # We should also populate the DestinationRegion with the
        # region_name of the endpoint object.
        self.assertEqual(params['DestinationRegion'], 'us-east-1')

    def test_use_event_operation_name(self):
        operation_model = mock.Mock()
        operation_model.name = 'FakeOperation'
        request_signer = mock.Mock()
        request_signer._region_name = 'us-east-1'
        request_dict = {}
        params = {'SourceRegion': 'us-west-2'}
        request_dict['body'] = params
        request_dict['url'] = 'https://myservice.us-east-1.amazonaws.com'
        request_dict['method'] = 'POST'
        request_dict['headers'] = {}
        request_dict['context'] = {}

        handlers.inject_presigned_url_ec2(
            request_dict, request_signer, operation_model)

        call_args = request_signer.generate_presigned_url.call_args
        operation_name = call_args[1].get('operation_name')
        self.assertEqual(operation_name, 'FakeOperation')

    def test_destination_region_always_changed(self):
        # If the user provides a destination region, we will still
        # override the DesinationRegion with the region_name from
        # the endpoint object.
        actual_region = 'us-west-1'
        operation_model = mock.Mock()
        operation_model.name = 'CopySnapshot'

        credentials = Credentials('key', 'secret')
        event_emitter = HierarchicalEmitter()
        request_signer = RequestSigner(
            ServiceId('ec2'), actual_region, 'ec2', 'v4', credentials,
            event_emitter)
        request_dict = {}
        params = {
            'SourceRegion': 'us-west-2',
            'DestinationRegion': 'us-east-1'}
        request_dict['body'] = params
        request_dict['url'] = 'https://ec2.us-west-1.amazonaws.com'
        request_dict['method'] = 'POST'
        request_dict['headers'] = {}
        request_dict['context'] = {}

        # The user provides us-east-1, but we will override this to
        # endpoint.region_name, of 'us-west-1' in this case.
        handlers.inject_presigned_url_ec2(
            request_dict, request_signer, operation_model)

        self.assertIn('https://ec2.us-west-2.amazonaws.com?',
                      params['PresignedUrl'])

        # Always use the DestinationRegion from the endpoint, regardless of
        # whatever value the user provides.
        self.assertEqual(params['DestinationRegion'], actual_region)

    def test_inject_presigned_url_rds(self):
        operation_model = mock.Mock()
        operation_model.name = 'CopyDBSnapshot'
        credentials = Credentials('key', 'secret')
        event_emitter = HierarchicalEmitter()
        request_signer = RequestSigner(
            ServiceId('rds'), 'us-east-1', 'rds', 'v4', credentials,
            event_emitter)
        request_dict = {}
        params = {'SourceRegion': 'us-west-2'}
        request_dict['body'] = params
        request_dict['url'] = 'https://rds.us-east-1.amazonaws.com'
        request_dict['method'] = 'POST'
        request_dict['headers'] = {}
        request_dict['context'] = {}

        handlers.inject_presigned_url_rds(
            request_dict, request_signer, operation_model)

        self.assertIn('https://rds.us-west-2.amazonaws.com?',
                      params['PreSignedUrl'])
        self.assertIn('X-Amz-Signature',
                      params['PreSignedUrl'])
        self.assertIn('DestinationRegion', params['PreSignedUrl'])
        # We should not populate the destination region for rds
        self.assertNotIn('DestinationRegion', params)

    def test_source_region_removed(self):
        operation_model = mock.Mock()
        operation_model.name = 'CopyDBSnapshot'
        credentials = Credentials('key', 'secret')
        event_emitter = HierarchicalEmitter()
        request_signer = RequestSigner(
            ServiceId('rds'), 'us-east-1', 'rds', 'v4', credentials,
            event_emitter
        )
        request_dict = {}
        params = {'SourceRegion': 'us-west-2'}
        request_dict['body'] = params
        request_dict['url'] = 'https://rds.us-east-1.amazonaws.com'
        request_dict['method'] = 'POST'
        request_dict['headers'] = {}
        request_dict['context'] = {}

        handlers.inject_presigned_url_rds(
            params=request_dict,
            request_signer=request_signer,
            model=operation_model
        )

        self.assertNotIn('SourceRegion', params)

    def test_source_region_removed_when_presigned_url_provided_for_rds(self):
        operation_model = mock.Mock()
        operation_model.name = 'CopyDBSnapshot'
        credentials = Credentials('key', 'secret')
        event_emitter = HierarchicalEmitter()
        request_signer = RequestSigner(
            ServiceId('rds'), 'us-east-1', 'rds', 'v4', credentials,
            event_emitter)
        request_dict = {}
        params = {'SourceRegion': 'us-west-2', 'PreSignedUrl': 'https://foo'}
        request_dict['body'] = params
        request_dict['url'] = 'https://rds.us-east-1.amazonaws.com'
        request_dict['method'] = 'POST'
        request_dict['headers'] = {}
        request_dict['context'] = {}

        handlers.inject_presigned_url_rds(
            params=request_dict,
            request_signer=request_signer,
            model=operation_model
        )

        self.assertNotIn('SourceRegion', params)

    def test_dest_region_removed(self):
        operation_model = mock.Mock()
        operation_model.name = 'CopyDBSnapshot'
        credentials = Credentials('key', 'secret')
        event_emitter = HierarchicalEmitter()
        request_signer = RequestSigner(
            ServiceId('rds'), 'us-east-1', 'rds', 'v4', credentials,
            event_emitter)
        request_dict = {}
        params = {'SourceRegion': 'us-west-2'}
        request_dict['body'] = params
        request_dict['url'] = 'https://rds.us-east-1.amazonaws.com'
        request_dict['method'] = 'POST'
        request_dict['headers'] = {}
        request_dict['context'] = {}

        handlers.inject_presigned_url_rds(
            params=request_dict,
            request_signer=request_signer,
            model=operation_model
        )

        self.assertNotIn('DestinationRegion', params)

    def test_presigned_url_already_present_for_rds(self):
        operation_model = mock.Mock()
        operation_model.name = 'CopyDBSnapshot'
        params = {'body': {'PresignedUrl': 'https://foo'}}
        credentials = Credentials('key', 'secret')
        event_emitter = HierarchicalEmitter()
        request_signer = RequestSigner(
            ServiceId('rds'), 'us-east-1', 'rds', 'v4', credentials,
            event_emitter)
        handlers.inject_presigned_url_rds(
            params=params,
            request_signer=request_signer,
            model=operation_model
        )
        self.assertEqual(params['body']['PresignedUrl'], 'https://foo')

    def test_presigned_url_casing_changed_for_rds(self):
        operation_model = mock.Mock()
        operation_model.name = 'CopyDBSnapshot'
        credentials = Credentials('key', 'secret')
        event_emitter = HierarchicalEmitter()
        request_signer = RequestSigner(
            ServiceId('rds'), 'us-east-1', 'rds', 'v4', credentials,
            event_emitter)
        request_dict = {}
        params = {'SourceRegion': 'us-west-2'}
        request_dict['body'] = params
        request_dict['url'] = 'https://rds.us-east-1.amazonaws.com'
        request_dict['method'] = 'POST'
        request_dict['headers'] = {}
        request_dict['context'] = {}

        handlers.inject_presigned_url_rds(
            params=request_dict,
            request_signer=request_signer,
            model=operation_model
        )

        self.assertNotIn('PresignedUrl', params)
        self.assertIn('https://rds.us-west-2.amazonaws.com?',
                      params['PreSignedUrl'])
        self.assertIn('X-Amz-Signature', params['PreSignedUrl'])

    def test_500_status_code_set_for_200_response(self):
        http_response = mock.Mock()
        http_response.status_code = 200
        http_response.content = """
            <Error>
              <Code>AccessDenied</Code>
              <Message>Access Denied</Message>
              <RequestId>id</RequestId>
              <HostId>hostid</HostId>
            </Error>
        """
        handlers.check_for_200_error((http_response, {}))
        self.assertEqual(http_response.status_code, 500)

    def test_200_response_with_no_error_left_untouched(self):
        http_response = mock.Mock()
        http_response.status_code = 200
        http_response.content = "<NotAnError></NotAnError>"
        handlers.check_for_200_error((http_response, {}))
        # We don't touch the status code since there are no errors present.
        self.assertEqual(http_response.status_code, 200)

    def test_500_response_can_be_none(self):
        # A 500 response can raise an exception, which means the response
        # object is None.  We need to handle this case.
        handlers.check_for_200_error(None)

    def test_route53_resource_id(self):
        event = 'before-parameter-build.route-53.GetHostedZone'
        params = {'Id': '/hostedzone/ABC123',
                  'HostedZoneId': '/hostedzone/ABC123',
                  'ResourceId': '/hostedzone/DEF456',
                  'DelegationSetId': '/hostedzone/GHI789',
                  'ChangeId': '/hostedzone/JKL012',
                  'Other': '/hostedzone/foo'}
        operation_def = {
            'name': 'GetHostedZone',
            'input': {
                'shape': 'GetHostedZoneInput'
            }
        }
        service_def = {
            'metadata': {},
            'shapes': {
                'GetHostedZoneInput': {
                    'type': 'structure',
                    'members': {
                        'Id': {
                            'shape': 'ResourceId'
                        },
                        'HostedZoneId': {
                            'shape': 'ResourceId'
                        },
                        'ResourceId': {
                            'shape': 'ResourceId'
                        },
                        'DelegationSetId': {
                            'shape': 'DelegationSetId'
                        },
                        'ChangeId': {
                            'shape': 'ChangeId'
                        },
                        'Other': {
                            'shape': 'String'
                        }
                    }
                },
                'ResourceId': {
                    'type': 'string'
                },
                'DelegationSetId': {
                    'type': 'string'
                },
                'ChangeId': {
                    'type': 'string'
                },
                'String': {
                    'type': 'string'
                }
            }
        }
        model = OperationModel(operation_def, ServiceModel(service_def))
        self.session.emit(event, params=params, model=model)

        self.assertEqual(params['Id'], 'ABC123')
        self.assertEqual(params['HostedZoneId'], 'ABC123')
        self.assertEqual(params['ResourceId'], 'DEF456')
        self.assertEqual(params['DelegationSetId'], 'GHI789')
        self.assertEqual(params['ChangeId'], 'JKL012')

        # This one should have been left alone
        self.assertEqual(params['Other'], '/hostedzone/foo')

    def test_route53_resource_id_missing_input_shape(self):
        event = 'before-parameter-build.route-53.GetHostedZone'
        params = {'HostedZoneId': '/hostedzone/ABC123'}
        operation_def = {
            'name': 'GetHostedZone'
        }
        service_def = {
            'metadata': {},
            'shapes': {}
        }
        model = OperationModel(operation_def, ServiceModel(service_def))
        self.session.emit(event, params=params, model=model)

        self.assertEqual(params['HostedZoneId'], '/hostedzone/ABC123')

    def test_run_instances_userdata(self):
        user_data = 'This is a test'
        b64_user_data = base64.b64encode(six.b(user_data)).decode('utf-8')
        params = dict(ImageId='img-12345678',
                      MinCount=1, MaxCount=5, UserData=user_data)
        handlers.base64_encode_user_data(params=params)
        result = {'ImageId': 'img-12345678',
                  'MinCount': 1,
                  'MaxCount': 5,
                  'UserData': b64_user_data}
        self.assertEqual(params, result)

    def test_run_instances_userdata_blob(self):
        # Ensure that binary can be passed in as user data.
        # This is valid because you can send gzip compressed files as
        # user data.
        user_data = b'\xc7\xa9This is a test'
        b64_user_data = base64.b64encode(user_data).decode('utf-8')
        params = dict(ImageId='img-12345678',
                      MinCount=1, MaxCount=5, UserData=user_data)
        handlers.base64_encode_user_data(params=params)
        result = {'ImageId': 'img-12345678',
                  'MinCount': 1,
                  'MaxCount': 5,
                  'UserData': b64_user_data}
        self.assertEqual(params, result)

    def test_get_template_has_error_response(self):
        original = {'Error': {'Code': 'Message'}}
        handler_input = copy.deepcopy(original)
        handlers.json_decode_template_body(parsed=handler_input)
        # The handler should not have changed the response because it's
        # an error response.
        self.assertEqual(original, handler_input)

    def test_does_decode_template_body_in_order(self):
        expected_ordering = OrderedDict([
            ('TemplateVersion', 1.0),
            ('APropertyOfSomeKind', 'a value'),
            ('list', [1, 2, 3]),
            ('nested', OrderedDict([('key', 'value'),
                                    ('foo', 'bar')]))
        ])
        template_string = json.dumps(expected_ordering)
        parsed_response = {'TemplateBody': template_string}

        handlers.json_decode_template_body(parsed=parsed_response)
        result = parsed_response['TemplateBody']

        self.assertTrue(isinstance(result, OrderedDict))
        for element, expected_element in zip(result, expected_ordering):
            self.assertEqual(element, expected_element)

    def test_decode_json_policy(self):
        parsed = {
            'Document': '{"foo": "foobarbaz"}',
            'Other': 'bar',
        }
        service_def = {
            'operations': {
                'Foo': {
                    'output': {'shape': 'PolicyOutput'},
                }
            },
            'shapes': {
                'PolicyOutput': {
                    'type': 'structure',
                    'members': {
                        'Document': {
                            'shape': 'policyDocumentType'
                        },
                        'Other': {
                            'shape': 'stringType'
                        }
                    }
                },
                'policyDocumentType': {
                    'type': 'string'
                },
                'stringType': {
                    'type': 'string'
                },
            }
        }
        model = ServiceModel(service_def)
        op_model = model.operation_model('Foo')
        handlers.json_decode_policies(parsed, op_model)
        self.assertEqual(parsed['Document'], {'foo': 'foobarbaz'})

        no_document = {'Other': 'bar'}
        handlers.json_decode_policies(no_document, op_model)
        self.assertEqual(no_document, {'Other': 'bar'})

    def test_inject_account_id(self):
        params = {}
        handlers.inject_account_id(params)
        self.assertEqual(params['accountId'], '-')

    def test_account_id_not_added_if_present(self):
        params = {'accountId': 'foo'}
        handlers.inject_account_id(params)
        self.assertEqual(params['accountId'], 'foo')

    def test_glacier_version_header_added(self):
        request_dict = {
            'headers': {}
        }
        model = ServiceModel({'metadata': {'apiVersion': '2012-01-01'}})
        handlers.add_glacier_version(model, request_dict)
        self.assertEqual(request_dict['headers']['x-amz-glacier-version'],
                         '2012-01-01')

    def test_application_json_header_added(self):
        request_dict = {
            'headers': {}
        }
        handlers.add_accept_header(None, request_dict)
        self.assertEqual(request_dict['headers']['Accept'], 'application/json')

    def test_accept_header_not_added_if_present(self):
        request_dict = {
            'headers': {'Accept': 'application/yaml'}
        }
        handlers.add_accept_header(None, request_dict)
        self.assertEqual(request_dict['headers']['Accept'], 'application/yaml')

    def test_glacier_checksums_added(self):
        request_dict = {
            'headers': {},
            'body': six.BytesIO(b'hello world'),
        }
        handlers.add_glacier_checksums(request_dict)
        self.assertIn('x-amz-content-sha256', request_dict['headers'])
        self.assertIn('x-amz-sha256-tree-hash', request_dict['headers'])
        self.assertEqual(
            request_dict['headers']['x-amz-content-sha256'],
            'b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9')
        self.assertEqual(
            request_dict['headers']['x-amz-sha256-tree-hash'],
            'b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9')
        # And verify that the body can still be read.
        self.assertEqual(request_dict['body'].read(), b'hello world')

    def test_tree_hash_added_only_if_not_exists(self):
        request_dict = {
            'headers': {
                'x-amz-sha256-tree-hash': 'pre-exists',
            },
            'body': six.BytesIO(b'hello world'),
        }
        handlers.add_glacier_checksums(request_dict)
        self.assertEqual(request_dict['headers']['x-amz-sha256-tree-hash'],
                         'pre-exists')

    def test_checksum_added_only_if_not_exists(self):
        request_dict = {
            'headers': {
                'x-amz-content-sha256': 'pre-exists',
            },
            'body': six.BytesIO(b'hello world'),
        }
        handlers.add_glacier_checksums(request_dict)
        self.assertEqual(request_dict['headers']['x-amz-content-sha256'],
                         'pre-exists')

    def test_glacier_checksums_support_raw_bytes(self):
        request_dict = {
            'headers': {},
            'body': b'hello world',
        }
        handlers.add_glacier_checksums(request_dict)
        self.assertEqual(
            request_dict['headers']['x-amz-content-sha256'],
            'b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9')
        self.assertEqual(
            request_dict['headers']['x-amz-sha256-tree-hash'],
            'b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9')

    def test_switch_host_with_param(self):
        request = AWSRequest()
        url = 'https://machinelearning.us-east-1.amazonaws.com'
        new_endpoint = 'https://my-custom-endpoint.amazonaws.com'
        data = '{"PredictEndpoint":"%s"}' % new_endpoint
        request.data = data.encode('utf-8')
        request.url = url
        handlers.switch_host_with_param(request, 'PredictEndpoint')
        self.assertEqual(request.url, new_endpoint)

    def test_invalid_char_in_bucket_raises_exception(self):
        params = {
            'Bucket': 'bad/bucket/name',
            'Key': 'foo',
            'Body': b'asdf',
        }
        with self.assertRaises(ParamValidationError):
            handlers.validate_bucket_name(params)

    def test_bucket_too_long_raises_exception(self):
        params = {
            'Bucket': 'a' * 300,
            'Key': 'foo',
            'Body': b'asdf',
        }
        with self.assertRaises(ParamValidationError):
            handlers.validate_bucket_name(params)

    def test_not_dns_compat_but_still_valid_bucket_name(self):
        params = {
            'Bucket': 'foasdf......bar--baz-a_b_CD10',
            'Key': 'foo',
            'Body': b'asdf',
        }
        self.assertIsNone(handlers.validate_bucket_name(params))

    def test_valid_bucket_name_hyphen(self):
        self.assertIsNone(
            handlers.validate_bucket_name({'Bucket': 'my-bucket-name'}))

    def test_valid_bucket_name_underscore(self):
        self.assertIsNone(
            handlers.validate_bucket_name({'Bucket': 'my_bucket_name'}))

    def test_valid_bucket_name_period(self):
        self.assertIsNone(
            handlers.validate_bucket_name({'Bucket': 'my.bucket.name'}))

    def test_validation_is_noop_if_no_bucket_param_exists(self):
        self.assertIsNone(handlers.validate_bucket_name(params={}))

    def test_validation_is_s3_accesspoint_arn(self):
        try:
            arn = 'arn:aws:s3:us-west-2:123456789012:accesspoint:endpoint'
            handlers.validate_bucket_name({'Bucket': arn})
        except ParamValidationError:
            self.fail('The s3 arn: %s should pass validation' % arn)

    def test_validation_is_s3_outpost_arn(self):
        try:
            arn = (
                'arn:aws:s3-outposts:us-west-2:123456789012:outpost:'
                'op-01234567890123456:accesspoint:myaccesspoint'
            )
            handlers.validate_bucket_name({'Bucket': arn})
        except ParamValidationError:
            self.fail('The s3 arn: %s should pass validation' % arn)

    def test_validation_is_global_s3_bucket_arn(self):
        with self.assertRaises(ParamValidationError):
            arn = 'arn:aws:s3:::mybucket'
            handlers.validate_bucket_name({'Bucket': arn})

    def test_validation_is_other_service_arn(self):
        with self.assertRaises(ParamValidationError):
            arn = 'arn:aws:ec2:us-west-2:123456789012:instance:myinstance'
            handlers.validate_bucket_name({'Bucket': arn})

    def test_validate_non_ascii_metadata_values(self):
        with self.assertRaises(ParamValidationError):
            handlers.validate_ascii_metadata({'Metadata': {'foo': u'\u2713'}})

    def test_validate_non_ascii_metadata_keys(self):
        with self.assertRaises(ParamValidationError):
            handlers.validate_ascii_metadata(
                {'Metadata': {u'\u2713': 'bar'}})

    def test_validate_non_triggered_when_no_md_specified(self):
        original = {'NotMetadata': ''}
        copied = original.copy()
        handlers.validate_ascii_metadata(copied)
        self.assertEqual(original, copied)

    def test_validation_passes_when_all_ascii_chars(self):
        original = {'Metadata': {'foo': 'bar'}}
        copied = original.copy()
        handlers.validate_ascii_metadata(original)
        self.assertEqual(original, copied)

    def test_set_encoding_type(self):
        params = {}
        context = {}
        handlers.set_list_objects_encoding_type_url(params, context=context)
        self.assertEqual(params['EncodingType'], 'url')
        self.assertTrue(context['encoding_type_auto_set'])

        params['EncodingType'] = 'new_value'
        handlers.set_list_objects_encoding_type_url(params, context={})
        self.assertEqual(params['EncodingType'], 'new_value')

    def test_decode_list_objects(self):
        parsed = {
            'Contents': [{'Key': "%C3%A7%C3%B6s%25asd%08"}],
            'EncodingType': 'url',
        }
        context = {'encoding_type_auto_set': True}
        handlers.decode_list_object(parsed, context=context)
        self.assertEqual(parsed['Contents'][0]['Key'], u'\xe7\xf6s%asd\x08')

    def test_decode_list_objects_does_not_decode_without_context(self):
        parsed = {
            'Contents': [{'Key': "%C3%A7%C3%B6s%25asd"}],
            'EncodingType': 'url',
        }
        handlers.decode_list_object(parsed, context={})
        self.assertEqual(parsed['Contents'][0]['Key'], u'%C3%A7%C3%B6s%25asd')

    def test_decode_list_objects_with_marker(self):
        parsed = {
            'Marker': "%C3%A7%C3%B6s%25%20asd%08+c",
            'EncodingType': 'url',
        }
        context = {'encoding_type_auto_set': True}
        handlers.decode_list_object(parsed, context=context)
        self.assertEqual(parsed['Marker'], u'\xe7\xf6s% asd\x08 c')

    def test_decode_list_objects_with_nextmarker(self):
        parsed = {
            'NextMarker': "%C3%A7%C3%B6s%25%20asd%08+c",
            'EncodingType': 'url',
        }
        context = {'encoding_type_auto_set': True}
        handlers.decode_list_object(parsed, context=context)
        self.assertEqual(parsed['NextMarker'], u'\xe7\xf6s% asd\x08 c')

    def test_decode_list_objects_with_common_prefixes(self):
        parsed = {
            'CommonPrefixes': [{'Prefix': "%C3%A7%C3%B6s%25%20asd%08+c"}],
            'EncodingType': 'url',
        }
        context = {'encoding_type_auto_set': True}
        handlers.decode_list_object(parsed, context=context)
        self.assertEqual(parsed['CommonPrefixes'][0]['Prefix'],
                         u'\xe7\xf6s% asd\x08 c')

    def test_decode_list_objects_with_delimiter(self):
        parsed = {
            'Delimiter': "%C3%A7%C3%B6s%25%20asd%08+c",
            'EncodingType': 'url',
        }
        context = {'encoding_type_auto_set': True}
        handlers.decode_list_object(parsed, context=context)
        self.assertEqual(parsed['Delimiter'], u'\xe7\xf6s% asd\x08 c')

    def test_decode_list_objects_v2(self):
        parsed = {
            'Contents': [{'Key': "%C3%A7%C3%B6s%25asd%08"}],
            'EncodingType': 'url',
        }
        context = {'encoding_type_auto_set': True}
        handlers.decode_list_object_v2(parsed, context=context)
        self.assertEqual(parsed['Contents'][0]['Key'], u'\xe7\xf6s%asd\x08')

    def test_decode_list_objects_v2_does_not_decode_without_context(self):
        parsed = {
            'Contents': [{'Key': "%C3%A7%C3%B6s%25asd"}],
            'EncodingType': 'url',
        }
        handlers.decode_list_object_v2(parsed, context={})
        self.assertEqual(parsed['Contents'][0]['Key'], u'%C3%A7%C3%B6s%25asd')

    def test_decode_list_objects_v2_with_delimiter(self):
        parsed = {
            'Delimiter': "%C3%A7%C3%B6s%25%20asd%08+c",
            'EncodingType': 'url',
        }
        context = {'encoding_type_auto_set': True}
        handlers.decode_list_object_v2(parsed, context=context)
        self.assertEqual(parsed['Delimiter'], u'\xe7\xf6s% asd\x08 c')

    def test_decode_list_objects_v2_with_prefix(self):
        parsed = {
            'Prefix': "%C3%A7%C3%B6s%25%20asd%08+c",
            'EncodingType': 'url',
        }
        context = {'encoding_type_auto_set': True}
        handlers.decode_list_object_v2(parsed, context=context)
        self.assertEqual(parsed['Prefix'], u'\xe7\xf6s% asd\x08 c')

    def test_decode_list_objects_v2_does_not_decode_continuationtoken(self):
        parsed = {
            'ContinuationToken': "%C3%A7%C3%B6s%25%20asd%08+c",
            'EncodingType': 'url',
        }
        context = {'encoding_type_auto_set': True}
        handlers.decode_list_object_v2(parsed, context=context)
        self.assertEqual(
            parsed['ContinuationToken'], u"%C3%A7%C3%B6s%25%20asd%08+c")

    def test_decode_list_objects_v2_with_startafter(self):
        parsed = {
            'StartAfter': "%C3%A7%C3%B6s%25%20asd%08+c",
            'EncodingType': 'url',
        }
        context = {'encoding_type_auto_set': True}
        handlers.decode_list_object_v2(parsed, context=context)
        self.assertEqual(parsed['StartAfter'], u'\xe7\xf6s% asd\x08 c')

    def test_decode_list_objects_v2_with_common_prefixes(self):
        parsed = {
            'CommonPrefixes': [{'Prefix': "%C3%A7%C3%B6s%25%20asd%08+c"}],
            'EncodingType': 'url',
        }
        context = {'encoding_type_auto_set': True}
        handlers.decode_list_object_v2(parsed, context=context)
        self.assertEqual(parsed['CommonPrefixes'][0]['Prefix'],
                         u'\xe7\xf6s% asd\x08 c')

    def test_set_operation_specific_signer_no_auth_type(self):
        signing_name = 'myservice'
        context = {'auth_type': None}
        response = handlers.set_operation_specific_signer(
            context=context, signing_name=signing_name)
        self.assertIsNone(response)

    def test_set_operation_specific_signer_unsigned(self):
        signing_name = 'myservice'
        context = {'auth_type': 'none'}
        response = handlers.set_operation_specific_signer(
            context=context, signing_name=signing_name)
        self.assertEqual(response, botocore.UNSIGNED)

    def test_set_operation_specific_signer_v4(self):
        signing_name = 'myservice'
        context = {'auth_type': 'v4'}
        response = handlers.set_operation_specific_signer(
            context=context, signing_name=signing_name)
        self.assertEqual(response, 'v4')

    def test_set_operation_specific_signer_v4a(self):
        signing_name = 'myservice'
        context = {'auth_type': 'v4a'}
        response = handlers.set_operation_specific_signer(
            context=context, signing_name=signing_name
        )
        self.assertEqual(response, 'v4a')
        # for v4a, context gets updated in place
        self.assertIsNotNone(context.get('signing'))
        self.assertEqual(context['signing']['region'], '*')
        self.assertEqual(context['signing']['signing_name'], signing_name)

    def test_set_operation_specific_signer_v4a_existing_signing_context(self):
        signing_name = 'myservice'
        context = {
            'auth_type': 'v4a',
            'signing': {'foo': 'bar', 'region': 'abc'},
        }
        handlers.set_operation_specific_signer(
            context=context, signing_name=signing_name
        )
        # region has been updated
        self.assertEqual(context['signing']['region'], '*')
        # signing_name has been added
        self.assertEqual(context['signing']['signing_name'], signing_name)
        # foo remained untouched
        self.assertEqual(context['signing']['foo'], 'bar')

    def test_set_operation_specific_signer_v4_unsinged_payload(self):
        signing_name = 'myservice'
        context = {'auth_type': 'v4-unsigned-body'}
        response = handlers.set_operation_specific_signer(
            context=context, signing_name=signing_name)
        self.assertEqual(response, 'v4')
        self.assertEqual(context.get('payload_signing_enabled'), False)

    def test_set_operation_specific_signer_s3v4_unsigned_payload(self):
        signing_name = 's3'
        context = {'auth_type': 'v4-unsigned-body'}
        response = handlers.set_operation_specific_signer(
            context=context, signing_name=signing_name)
        self.assertEqual(response, 's3v4')
        self.assertEqual(context.get('payload_signing_enabled'), False)


@pytest.mark.parametrize(
    'auth_type, expected_response', [('v4', 's3v4'), ('v4a', 's3v4a')]
)
def test_set_operation_specific_signer_s3v4(auth_type, expected_response):
    signing_name = 's3'
    context = {'auth_type': auth_type}
    response = handlers.set_operation_specific_signer(
        context=context, signing_name=signing_name
    )
    assert response == expected_response


class TestConvertStringBodyToFileLikeObject(BaseSessionTest):
    def assert_converts_to_file_like_object_with_bytes(self, body, body_bytes):
        params = {'Body': body}
        handlers.convert_body_to_file_like_object(params)
        self.assertTrue(hasattr(params['Body'], 'read'))
        contents = params['Body'].read()
        self.assertIsInstance(contents, six.binary_type)
        self.assertEqual(contents, body_bytes)

    def test_string(self):
        self.assert_converts_to_file_like_object_with_bytes('foo', b'foo')

    def test_binary(self):
        body = os.urandom(500)
        body_bytes = body
        self.assert_converts_to_file_like_object_with_bytes(body, body_bytes)

    def test_file(self):
        body = six.StringIO()
        params = {'Body': body}
        handlers.convert_body_to_file_like_object(params)
        self.assertEqual(params['Body'], body)

    def test_unicode(self):
        self.assert_converts_to_file_like_object_with_bytes(u'bar', b'bar')

    def test_non_ascii_characters(self):
        self.assert_converts_to_file_like_object_with_bytes(
            u'\u2713', b'\xe2\x9c\x93')


class TestRetryHandlerOrder(BaseSessionTest):
    def get_handler_names(self, responses):
        names = []
        for response in responses:
            handler = response[0]
            if hasattr(handler, '__name__'):
                names.append(handler.__name__)
            elif hasattr(handler, '__class__'):
                names.append(handler.__class__.__name__)
            else:
                names.append(str(handler))
        return names

    def test_s3_special_case_is_before_other_retry(self):
        client = self.session.create_client('s3')
        service_model = self.session.get_service_model('s3')
        operation = service_model.operation_model('CopyObject')
        responses = client.meta.events.emit(
            'needs-retry.s3.CopyObject',
            request_dict={'context': {}},
            response=(mock.Mock(), mock.Mock()), endpoint=mock.Mock(),
            operation=operation, attempts=1, caught_exception=None)
        # This is implementation specific, but we're trying to verify that
        # the check_for_200_error is before any of the retry logic in
        # botocore.retries.*.
        # Technically, as long as the relative order is preserved, we don't
        # care about the absolute order.
        names = self.get_handler_names(responses)
        self.assertIn('check_for_200_error', names)
        self.assertIn('needs_retry', names)
        s3_200_handler = names.index('check_for_200_error')
        general_retry_handler = names.index('needs_retry')
        self.assertTrue(s3_200_handler < general_retry_handler,
                        "S3 200 error handler was supposed to be before "
                        "the general retry handler, but it was not.")


class BaseMD5Test(BaseSessionTest):
    def setUp(self, **environ):
        super(BaseMD5Test, self).setUp(**environ)
        self.md5_object = mock.Mock()
        self.md5_digest = mock.Mock(return_value=b'foo')
        self.md5_object.digest = self.md5_digest
        md5_builder = mock.Mock(return_value=self.md5_object)
        self.md5_patch = mock.patch('hashlib.md5', md5_builder)
        self.md5_patch.start()
        self._md5_available_patch = None
        self.set_md5_available()

    def tearDown(self):
        super(BaseMD5Test, self).tearDown()
        self.md5_patch.stop()
        if self._md5_available_patch:
            self._md5_available_patch.stop()

    def set_md5_available(self, is_available=True):
        if self._md5_available_patch:
            self._md5_available_patch.stop()

        self._md5_available_patch = \
            mock.patch('botocore.compat.MD5_AVAILABLE', is_available)
        self._md5_available_patch.start()


class TestSSEMD5(BaseMD5Test):
    def test_raises_error_when_md5_unavailable(self):
        self.set_md5_available(False)

        with self.assertRaises(MD5UnavailableError):
            handlers.sse_md5({'SSECustomerKey': b'foo'})

        with self.assertRaises(MD5UnavailableError):
            handlers.copy_source_sse_md5({'CopySourceSSECustomerKey': b'foo'})

    def test_sse_params(self):
        for op in ('HeadObject', 'GetObject', 'PutObject', 'CopyObject',
                   'CreateMultipartUpload', 'UploadPart', 'UploadPartCopy'):
            event = 'before-parameter-build.s3.%s' % op
            params = {'SSECustomerKey': b'bar',
                      'SSECustomerAlgorithm': 'AES256'}
            self.session.emit(event, params=params, model=mock.MagicMock())
            self.assertEqual(params['SSECustomerKey'], 'YmFy')
            self.assertEqual(params['SSECustomerKeyMD5'], 'Zm9v')

    def test_sse_params_as_str(self):
        event = 'before-parameter-build.s3.PutObject'
        params = {'SSECustomerKey': 'bar',
                  'SSECustomerAlgorithm': 'AES256'}
        self.session.emit(event, params=params, model=mock.MagicMock())
        self.assertEqual(params['SSECustomerKey'], 'YmFy')
        self.assertEqual(params['SSECustomerKeyMD5'], 'Zm9v')

    def test_copy_source_sse_params(self):
        for op in ['CopyObject', 'UploadPartCopy']:
            event = 'before-parameter-build.s3.%s' % op
            params = {'CopySourceSSECustomerKey': b'bar',
                      'CopySourceSSECustomerAlgorithm': 'AES256'}
            self.session.emit(event, params=params, model=mock.MagicMock())
            self.assertEqual(params['CopySourceSSECustomerKey'], 'YmFy')
            self.assertEqual(params['CopySourceSSECustomerKeyMD5'], 'Zm9v')

    def test_copy_source_sse_params_as_str(self):
        event = 'before-parameter-build.s3.CopyObject'
        params = {'CopySourceSSECustomerKey': 'bar',
                  'CopySourceSSECustomerAlgorithm': 'AES256'}
        self.session.emit(event, params=params, model=mock.MagicMock())
        self.assertEqual(params['CopySourceSSECustomerKey'], 'YmFy')
        self.assertEqual(params['CopySourceSSECustomerKeyMD5'], 'Zm9v')


class TestAddMD5(BaseMD5Test):
    def get_context(self, s3_config=None):
        if s3_config is None:
            s3_config = {}
        return {
            'client_config': Config(s3=s3_config)
        }

    def test_adds_md5_when_v4(self):
        credentials = Credentials('key', 'secret')
        request_signer = RequestSigner(
            ServiceId('s3'), 'us-east-1', 's3', 'v4', credentials, mock.Mock())
        request_dict = {'body': b'bar',
                        'url': 'https://s3.us-east-1.amazonaws.com',
                        'method': 'PUT',
                        'headers': {}}
        context = self.get_context()
        conditionally_calculate_md5(
            request_dict, request_signer=request_signer, context=context)
        self.assertTrue('Content-MD5' in request_dict['headers'])

    def test_adds_md5_when_s3v4(self):
        credentials = Credentials('key', 'secret')
        request_signer = RequestSigner(
            ServiceId('s3'), 'us-east-1', 's3', 's3v4', credentials,
            mock.Mock())
        request_dict = {'body': b'bar',
                        'url': 'https://s3.us-east-1.amazonaws.com',
                        'method': 'PUT',
                        'headers': {}}
        context = self.get_context({'payload_signing_enabled': False})
        conditionally_calculate_md5(
            request_dict, request_signer=request_signer, context=context)
        self.assertTrue('Content-MD5' in request_dict['headers'])

    def test_conditional_does_not_add_when_md5_unavailable(self):
        credentials = Credentials('key', 'secret')
        request_signer = RequestSigner(
            's3', 'us-east-1', 's3', 's3', credentials, mock.Mock())
        request_dict = {'body': b'bar',
                        'url': 'https://s3.us-east-1.amazonaws.com',
                        'method': 'PUT',
                        'headers': {}}

        context = self.get_context()
        self.set_md5_available(False)
        with mock.patch('botocore.utils.MD5_AVAILABLE', False):
            conditionally_calculate_md5(
                request_dict, request_signer=request_signer, context=context)
            self.assertFalse('Content-MD5' in request_dict['headers'])

    def test_add_md5_raises_error_when_md5_unavailable(self):
        credentials = Credentials('key', 'secret')
        request_signer = RequestSigner(
            ServiceId('s3'), 'us-east-1', 's3', 's3', credentials, mock.Mock())
        request_dict = {'body': b'bar',
                        'url': 'https://s3.us-east-1.amazonaws.com',
                        'method': 'PUT',
                        'headers': {}}

        self.set_md5_available(False)
        with self.assertRaises(MD5UnavailableError):
            conditionally_calculate_md5(
                request_dict, request_signer=request_signer)

    def test_adds_md5_when_s3v2(self):
        credentials = Credentials('key', 'secret')
        request_signer = RequestSigner(
            ServiceId('s3'), 'us-east-1', 's3', 's3', credentials, mock.Mock())
        request_dict = {'body': b'bar',
                        'url': 'https://s3.us-east-1.amazonaws.com',
                        'method': 'PUT',
                        'headers': {}}
        context = self.get_context()
        conditionally_calculate_md5(
            request_dict, request_signer=request_signer, context=context)
        self.assertTrue('Content-MD5' in request_dict['headers'])

    def test_add_md5_with_file_like_body(self):
        request_dict = {
            'body': six.BytesIO(b'foobar'),
            'headers': {}
        }
        self.md5_digest.return_value = b'8X\xf6"0\xac<\x91_0\x0cfC\x12\xc6?'
        conditionally_calculate_md5(request_dict)
        self.assertEqual(request_dict['headers']['Content-MD5'],
                         'OFj2IjCsPJFfMAxmQxLGPw==')

    def test_add_md5_with_bytes_object(self):
        request_dict = {
            'body': b'foobar',
            'headers': {}
        }
        self.md5_digest.return_value = b'8X\xf6"0\xac<\x91_0\x0cfC\x12\xc6?'
        conditionally_calculate_md5(request_dict)
        self.assertEqual(
            request_dict['headers']['Content-MD5'],
            'OFj2IjCsPJFfMAxmQxLGPw==')

    def test_add_md5_with_empty_body(self):
        request_dict = {
            'body': b'',
            'headers': {}
        }
        self.md5_digest.return_value = b'8X\xf6"0\xac<\x91_0\x0cfC\x12\xc6?'
        conditionally_calculate_md5(request_dict)
        self.assertEqual(
            request_dict['headers']['Content-MD5'],
            'OFj2IjCsPJFfMAxmQxLGPw==')

    def test_add_md5_with_bytearray_object(self):
        request_dict = {
            'body': bytearray(b'foobar'),
            'headers': {}
        }
        self.md5_digest.return_value = b'8X\xf6"0\xac<\x91_0\x0cfC\x12\xc6?'
        conditionally_calculate_md5(request_dict)
        self.assertEqual(
            request_dict['headers']['Content-MD5'],
            'OFj2IjCsPJFfMAxmQxLGPw==')

    def test_skip_md5_when_flexible_checksum_context(self):
        request_dict = {
            'body': six.BytesIO(b'foobar'),
            'headers': {},
            'context': {
                'checksum': {
                    'request_algorithm': {
                        'in': 'header',
                        'algorithm': 'crc32',
                        'name': 'x-amz-checksum-crc32',
                    }
                }
            }
        }
        conditionally_calculate_md5(request_dict)
        self.assertNotIn('Content-MD5', request_dict['headers'])

    def test_skip_md5_when_flexible_checksum_explicit_header(self):
        request_dict = {
            'body': six.BytesIO(b'foobar'),
            'headers': {'x-amz-checksum-crc32': 'foo'},
        }
        conditionally_calculate_md5(request_dict)
        self.assertNotIn('Content-MD5', request_dict['headers'])


class TestParameterAlias(unittest.TestCase):
    def setUp(self):
        self.original_name = 'original'
        self.alias_name = 'alias'
        self.parameter_alias = handlers.ParameterAlias(
            self.original_name, self.alias_name)

        self.operation_model = mock.Mock()
        request_shape = DenormalizedStructureBuilder().with_members(
            {self.original_name: {'type': 'string'}}).build_model()
        self.operation_model.input_shape = request_shape
        self.sample_section = DocumentStructure('')
        self.event_emitter = HierarchicalEmitter()

    def test_alias_parameter_in_call(self):
        value = 'value'
        params = {self.alias_name: value}
        self.parameter_alias.alias_parameter_in_call(
            params, self.operation_model)
        self.assertEqual(params, {self.original_name: value})

    def test_alias_parameter_and_original_in_call(self):
        params = {
            self.original_name: 'orginal_value',
            self.alias_name: 'alias_value'
        }
        with self.assertRaises(AliasConflictParameterError):
            self.parameter_alias.alias_parameter_in_call(
                params, self.operation_model)

    def test_alias_parameter_in_call_does_not_touch_original(self):
        value = 'value'
        params = {self.original_name: value}
        self.parameter_alias.alias_parameter_in_call(
            params, self.operation_model)
        self.assertEqual(params, {self.original_name: value})

    def test_does_not_alias_parameter_for_no_input_shape(self):
        value = 'value'
        params = {self.alias_name: value}
        self.operation_model.input_shape = None
        self.parameter_alias.alias_parameter_in_call(
            params, self.operation_model)
        self.assertEqual(params, {self.alias_name: value})

    def test_does_not_alias_parameter_for_not_modeled_member(self):
        value = 'value'
        params = {self.alias_name: value}

        request_shape = DenormalizedStructureBuilder().with_members(
            {'foo': {'type': 'string'}}).build_model()
        self.operation_model.input_shape = request_shape
        self.parameter_alias.alias_parameter_in_call(
            params, self.operation_model)
        self.assertEqual(params, {self.alias_name: value})

    def test_alias_parameter_in_documentation_request_params(self):
        RequestParamsDocumenter(
            'myservice', 'myoperation', self.event_emitter).document_params(
                self.sample_section, self.operation_model.input_shape)
        self.parameter_alias.alias_parameter_in_documentation(
            'docs.request-params.myservice.myoperation.complete-section',
            self.sample_section
        )
        contents = self.sample_section.flush_structure().decode('utf-8')
        self.assertIn(':type ' + self.alias_name + ':',  contents)
        self.assertIn(':param ' + self.alias_name + ':',  contents)
        self.assertNotIn(':type ' + self.original_name + ':',  contents)
        self.assertNotIn(':param ' + self.original_name + ':',  contents)

    def test_alias_parameter_in_documentation_request_example(self):
        RequestExampleDocumenter(
            'myservice', 'myoperation', self.event_emitter).document_example(
                self.sample_section, self.operation_model.input_shape)
        self.parameter_alias.alias_parameter_in_documentation(
            'docs.request-example.myservice.myoperation.complete-section',
            self.sample_section
        )
        contents = self.sample_section.flush_structure().decode('utf-8')
        self.assertIn(self.alias_name + '=',  contents)
        self.assertNotIn(self.original_name + '=', contents)


class TestCommandAlias(unittest.TestCase):
    def test_command_alias(self):
        alias = handlers.ClientMethodAlias('foo')
        client = mock.Mock()
        client.foo.return_value = 'bar'

        response = alias(client=client)()
        self.assertEqual(response, 'bar')


class TestPrependToHost(unittest.TestCase):
    def setUp(self):
        self.hoister = handlers.HeaderToHostHoister('test-header')

    def _prepend_to_host(self, url, prepend_string):
        params = {
            'headers': {
                'test-header': prepend_string,
            },
            'url': url,
        }
        self.hoister.hoist(params=params)
        return params['url']

    def test_does_prepend_to_host(self):
        prepended = self._prepend_to_host('https://bar.example.com/', 'foo')
        self.assertEqual(prepended, 'https://foo.bar.example.com/')

    def test_does_prepend_to_host_with_http(self):
        prepended = self._prepend_to_host('http://bar.example.com/', 'foo')
        self.assertEqual(prepended, 'http://foo.bar.example.com/')

    def test_does_prepend_to_host_with_path(self):
        prepended = self._prepend_to_host(
            'https://bar.example.com/path', 'foo')
        self.assertEqual(prepended, 'https://foo.bar.example.com/path')

    def test_does_prepend_to_host_with_more_components(self):
        prepended = self._prepend_to_host(
            'https://bar.baz.example.com/path', 'foo')
        self.assertEqual(prepended, 'https://foo.bar.baz.example.com/path')

    def test_does_validate_long_host(self):
        with self.assertRaises(ParamValidationError):
           self._prepend_to_host(
               'https://example.com/path', 'toolong'*100)

    def test_does_validate_host_with_illegal_char(self):
        with self.assertRaises(ParamValidationError):
           self._prepend_to_host(
               'https://example.com/path', 'host#name')
