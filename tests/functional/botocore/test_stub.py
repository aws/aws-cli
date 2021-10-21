# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import botocore.config
from tests import unittest

import botocore
import botocore.session
import botocore.stub as stub
from botocore.stub import Stubber
from botocore.exceptions import StubResponseError, ClientError, \
    StubAssertionError, UnStubbedResponseError
from botocore.exceptions import ParamValidationError
import botocore.client


class TestStubber(unittest.TestCase):
    def setUp(self):
        session = botocore.session.get_session()
        config = botocore.config.Config(
            signature_version=botocore.UNSIGNED,
            s3={'addressing_style': 'path'}
        )
        self.client = session.create_client(
            's3', region_name='us-east-1', config=config)
        self.stubber = Stubber(self.client)

    def test_stubber_returns_response(self):
        service_response = {'ResponseMetadata': {'foo': 'bar'}}
        self.stubber.add_response('list_objects', service_response)
        self.stubber.activate()
        response = self.client.list_objects(Bucket='foo')
        self.assertEqual(response, service_response)

    def test_context_manager_returns_response(self):
        service_response = {'ResponseMetadata': {'foo': 'bar'}}
        self.stubber.add_response('list_objects', service_response)

        with self.stubber:
            response = self.client.list_objects(Bucket='foo')
        self.assertEqual(response, service_response)

    def test_activated_stubber_errors_with_no_registered_stubs(self):
        self.stubber.activate()
        # Params one per line for readability.
        with self.assertRaisesRegex(UnStubbedResponseError,
                                    "Unexpected API Call"):
            self.client.list_objects(
                Bucket='asdfasdfasdfasdf',
                Delimiter='asdfasdfasdfasdf',
                Prefix='asdfasdfasdfasdf',
                EncodingType='url')

    def test_stubber_errors_when_stubs_are_used_up(self):
        self.stubber.add_response('list_objects', {})
        self.stubber.activate()
        self.client.list_objects(Bucket='foo')

        with self.assertRaises(UnStubbedResponseError):
            self.client.list_objects(Bucket='foo')

    def test_client_error_response(self):
        error_code = "AccessDenied"
        error_message = "Access Denied"
        self.stubber.add_client_error(
            'list_objects', error_code, error_message)
        self.stubber.activate()

        with self.assertRaises(ClientError):
            self.client.list_objects(Bucket='foo')

    def test_can_add_expected_params_to_client_error(self):
        self.stubber.add_client_error(
            'list_objects', 'Error', 'error',
            expected_params={'Bucket': 'foo'}
        )
        self.stubber.activate()
        with self.assertRaises(ClientError):
            self.client.list_objects(Bucket='foo')

    def test_can_expected_param_fails_in_client_error(self):
        self.stubber.add_client_error(
            'list_objects', 'Error', 'error',
            expected_params={'Bucket': 'foo'}
        )
        self.stubber.activate()
        # We expect an AssertionError instead of a ClientError
        # because we're calling the operation with the wrong
        # param value.
        with self.assertRaises(AssertionError):
            self.client.list_objects(Bucket='wrong-argument-value')

    def test_expected_params_success(self):
        service_response = {}
        expected_params = {'Bucket': 'foo'}
        self.stubber.add_response(
            'list_objects', service_response, expected_params)
        self.stubber.activate()
        # This should be called successfully with no errors being thrown
        # for mismatching expected params.
        response = self.client.list_objects(Bucket='foo')
        self.assertEqual(response, service_response)

    def test_expected_params_fail(self):
        service_response = {}
        expected_params = {'Bucket': 'bar'}
        self.stubber.add_response(
            'list_objects', service_response, expected_params)
        self.stubber.activate()
        # This should call should raise an for mismatching expected params.
        with self.assertRaisesRegex(StubResponseError,
                                    "{'Bucket': 'bar'},\n"):
            self.client.list_objects(Bucket='foo')

    def test_expected_params_mixed_with_errors_responses(self):
        # Add an error response
        error_code = "AccessDenied"
        error_message = "Access Denied"
        self.stubber.add_client_error(
            'list_objects', error_code, error_message)

        # Add a response with incorrect expected params
        service_response = {}
        expected_params = {'Bucket': 'bar'}
        self.stubber.add_response(
            'list_objects', service_response, expected_params)

        self.stubber.activate()

        # The first call should throw and error as expected.
        with self.assertRaises(ClientError):
            self.client.list_objects(Bucket='foo')

        # The second call should throw an error for unexpected parameters
        with self.assertRaisesRegex(StubResponseError, 'Expected parameters'):
            self.client.list_objects(Bucket='foo')

    def test_can_continue_to_call_after_expected_params_fail(self):
        service_response = {}
        expected_params = {'Bucket': 'bar'}

        self.stubber.add_response(
            'list_objects', service_response, expected_params)

        self.stubber.activate()
        # Throw an error for unexpected parameters
        with self.assertRaises(StubResponseError):
            self.client.list_objects(Bucket='foo')

        # The stubber should still have the responses queued up
        # even though the original parameters did not match the expected ones.
        self.client.list_objects(Bucket='bar')
        self.stubber.assert_no_pending_responses()

    def test_still_relies_on_param_validation_with_expected_params(self):
        service_response = {}
        expected_params = {'Buck': 'bar'}

        self.stubber.add_response(
            'list_objects', service_response, expected_params)

        self.stubber.activate()
        # Throw an error for invalid parameters
        with self.assertRaises(ParamValidationError):
            self.client.list_objects(Buck='bar')

    def test_any_ignores_param_for_validation(self):
        service_response = {}
        expected_params = {'Bucket': stub.ANY}

        self.stubber.add_response(
            'list_objects', service_response, expected_params)
        self.stubber.add_response(
            'list_objects', service_response, expected_params)

        try:
            with self.stubber:
                self.client.list_objects(Bucket='foo')
                self.client.list_objects(Bucket='bar')
        except StubAssertionError:
            self.fail("stub.ANY failed to ignore parameter for validation.")

    def test_mixed_any_and_concrete_params(self):
        service_response = {}
        expected_params = {'Bucket': stub.ANY, 'Key': 'foo.txt'}

        self.stubber.add_response(
            'head_object', service_response, expected_params)
        self.stubber.add_response(
            'head_object', service_response, expected_params)

        try:
            with self.stubber:
                self.client.head_object(Bucket='foo', Key='foo.txt')
                self.client.head_object(Bucket='bar', Key='foo.txt')
        except StubAssertionError:
            self.fail("stub.ANY failed to ignore parameter for validation.")

    def test_nested_any_param(self):
        service_response = {}
        expected_params = {
            'Bucket': 'foo',
            'Key': 'bar.txt',
            'Metadata': {
                'MyMeta': stub.ANY,
            }
        }

        self.stubber.add_response(
            'put_object', service_response, expected_params)
        self.stubber.add_response(
            'put_object', service_response, expected_params)

        try:
            with self.stubber:
                self.client.put_object(
                    Bucket='foo',
                    Key='bar.txt',
                    Metadata={
                        'MyMeta': 'Foo',
                    }
                )
                self.client.put_object(
                    Bucket='foo',
                    Key='bar.txt',
                    Metadata={
                        'MyMeta': 'Bar',
                    }
                )
        except StubAssertionError:
            self.fail(
                "stub.ANY failed to ignore nested parameter for validation.")

    def test_ANY_repr(self):
        self.assertEqual(repr(stub.ANY), '<ANY>')

    def test_none_param(self):
        service_response = {}
        expected_params = {'Buck': None}

        self.stubber.add_response(
            'list_objects', service_response, expected_params)

        self.stubber.activate()
        # Throw an error for invalid parameters
        with self.assertRaises(StubAssertionError):
            self.client.list_objects(Buck='bar')

    def test_many_expected_params(self):
        service_response = {}
        expected_params = {
            'Bucket': 'mybucket',
            'Prefix': 'myprefix',
            'Delimiter': '/',
            'EncodingType': 'url'
        }
        self.stubber.add_response(
            'list_objects', service_response, expected_params)
        try:
            with self.stubber:
                self.client.list_objects(**expected_params)
        except StubAssertionError:
            self.fail(
                "Stubber inappropriately raised error for same parameters.")

    def test_no_stub_for_presign_url(self):
        try:
            with self.stubber:
                url = self.client.generate_presigned_url(
                    ClientMethod='get_object',
                    Params={
                        'Bucket': 'mybucket',
                        'Key': 'mykey'
                    }
                )
                self.assertEqual(
                    url, 'https://s3.us-east-1.amazonaws.com/mybucket/mykey')
        except StubResponseError:
            self.fail(
                'Stubbed responses should not be required for generating '
                'presigned requests'
            )

    def test_can_stub_with_presign_url_mixed_in(self):
        desired_response = {}
        expected_params = {
            'Bucket': 'mybucket',
            'Prefix': 'myprefix',
        }
        self.stubber.add_response(
            'list_objects', desired_response, expected_params)
        with self.stubber:
            url = self.client.generate_presigned_url(
                ClientMethod='get_object',
                Params={
                    'Bucket': 'myotherbucket',
                    'Key': 'myotherkey'
                }
            )
            expected_url = (
                'https://s3.us-east-1.amazonaws.com/myotherbucket/myotherkey'
            )
            self.assertEqual(url, expected_url)
            actual_response = self.client.list_objects(**expected_params)
            self.assertEqual(desired_response, actual_response)
        self.stubber.assert_no_pending_responses()

    def test_parse_get_bucket_location(self):
        error_code = "NoSuchBucket"
        error_message = "The specified bucket does not exist"
        self.stubber.add_client_error(
            'get_bucket_location', error_code, error_message)
        self.stubber.activate()

        with self.assertRaises(ClientError):
            self.client.get_bucket_location(Bucket='foo')

    def test_parse_get_bucket_location_returns_response(self):
        service_response = {"LocationConstraint": "us-west-2"}
        self.stubber.add_response('get_bucket_location',service_response)
        self.stubber.activate()
        response = self.client.get_bucket_location(Bucket='foo')
        self.assertEqual(response, service_response)

