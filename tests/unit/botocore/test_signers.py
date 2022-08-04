# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import mock
import datetime
import json

from dateutil.tz import tzutc

import botocore
import botocore.session
import botocore.auth
import botocore.awsrequest
from botocore.config import Config
from botocore.credentials import Credentials
from botocore.credentials import ReadOnlyCredentials
from botocore.hooks import HierarchicalEmitter
from botocore.model import ServiceId
from botocore.exceptions import NoRegionError, UnknownSignatureVersionError
from botocore.exceptions import UnknownClientMethodError, ParamValidationError
from botocore.exceptions import UnsupportedSignatureVersionError
from botocore.signers import RequestSigner, S3PostPresigner, CloudFrontSigner
from botocore.signers import generate_db_auth_token

from tests import unittest
from tests import assert_url_equal


class BaseSignerTest(unittest.TestCase):
    def setUp(self):
        self.credentials = Credentials('key', 'secret')
        self.emitter = mock.Mock()
        self.emitter.emit_until_response.return_value = (None, None)
        self.signer = RequestSigner(
            ServiceId('service_name'), 'region_name', 'signing_name',
            'v4', self.credentials, self.emitter)
        self.fixed_credentials = self.credentials.get_frozen_credentials()
        self.request = botocore.awsrequest.AWSRequest()


class TestSigner(BaseSignerTest):

    def test_region_name(self):
        self.assertEqual(self.signer.region_name, 'region_name')

    def test_signature_version(self):
        self.assertEqual(self.signer.signature_version, 'v4')

    def test_signing_name(self):
        self.assertEqual(self.signer.signing_name, 'signing_name')

    def test_region_required_for_sigv4(self):
        self.signer = RequestSigner(
            ServiceId('service_name'), None, 'signing_name', 'v4',
            self.credentials, self.emitter
        )

        with self.assertRaises(NoRegionError):
            self.signer.sign('operation_name', self.request)

    def test_get_auth(self):
        auth_cls = mock.Mock()
        with mock.patch.dict(botocore.auth.AUTH_TYPE_MAPS,
                             {'v4': auth_cls}):
            auth = self.signer.get_auth('service_name', 'region_name')

            self.assertEqual(auth, auth_cls.return_value)
            auth_cls.assert_called_with(
                credentials=self.fixed_credentials,
                service_name='service_name',
                region_name='region_name')

    def test_get_auth_signature_override(self):
        auth_cls = mock.Mock()
        with mock.patch.dict(botocore.auth.AUTH_TYPE_MAPS,
                             {'v4-custom': auth_cls}):
            auth = self.signer.get_auth(
                'service_name', 'region_name', signature_version='v4-custom')

            self.assertEqual(auth, auth_cls.return_value)
            auth_cls.assert_called_with(
                credentials=self.fixed_credentials,
                service_name='service_name',
                region_name='region_name')

    def test_get_auth_bad_override(self):
        with self.assertRaises(UnknownSignatureVersionError):
            self.signer.get_auth('service_name', 'region_name',
                                 signature_version='bad')

    def test_emits_choose_signer(self):
        with mock.patch.dict(botocore.auth.AUTH_TYPE_MAPS,
                             {'v4': mock.Mock()}):
            self.signer.sign('operation_name', self.request)

        self.emitter.emit_until_response.assert_called_with(
            'choose-signer.service_name.operation_name',
            signing_name='signing_name', region_name='region_name',
            signature_version='v4', context=mock.ANY)

    def test_choose_signer_override(self):
        auth = mock.Mock()
        auth.REQUIRES_REGION = False
        self.emitter.emit_until_response.return_value = (None, 'custom')

        with mock.patch.dict(botocore.auth.AUTH_TYPE_MAPS,
                             {'custom': auth}):
            self.signer.sign('operation_name', self.request)

        auth.assert_called_with(credentials=self.fixed_credentials)
        auth.return_value.add_auth.assert_called_with(self.request)

    def test_emits_before_sign(self):
        with mock.patch.dict(botocore.auth.AUTH_TYPE_MAPS,
                             {'v4': mock.Mock()}):
            self.signer.sign('operation_name', self.request)

        self.emitter.emit.assert_called_with(
            'before-sign.service_name.operation_name',
            request=self.request, signing_name='signing_name',
            region_name='region_name', signature_version='v4',
            request_signer=self.signer, operation_name='operation_name')

    def test_disable_signing(self):
        # Returning botocore.UNSIGNED from choose-signer disables signing!
        auth = mock.Mock()
        self.emitter.emit_until_response.return_value = (None,
                                                         botocore.UNSIGNED)

        with mock.patch.dict(botocore.auth.AUTH_TYPE_MAPS,
                             {'v4': auth}):
            self.signer.sign('operation_name', self.request)

        auth.assert_not_called()

    def test_generate_url_emits_choose_signer(self):
        request_dict = {
            'headers': {},
            'url': 'https://foo.com',
            'body': b'',
            'url_path': '/',
            'method': 'GET',
            'context': {}
        }

        with mock.patch.dict(botocore.auth.AUTH_TYPE_MAPS,
                             {'v4': mock.Mock()}):
            self.signer.generate_presigned_url(request_dict, 'operation_name')

        self.emitter.emit_until_response.assert_called_with(
            'choose-signer.service_name.operation_name',
            signing_name='signing_name', region_name='region_name',
            signature_version='v4-query', context=mock.ANY)

    def test_choose_signer_passes_context(self):
        self.request.context = {'foo': 'bar'}

        with mock.patch.dict(botocore.auth.AUTH_TYPE_MAPS,
                             {'v4': mock.Mock()}):
            self.signer.sign('operation_name', self.request)

        self.emitter.emit_until_response.assert_called_with(
            'choose-signer.service_name.operation_name',
            signing_name='signing_name', region_name='region_name',
            signature_version='v4', context={'foo': 'bar'})

    def test_generate_url_choose_signer_override(self):
        request_dict = {
            'headers': {},
            'url': 'https://foo.com',
            'body': b'',
            'url_path': '/',
            'method': 'GET',
            'context': {}
        }
        auth = mock.Mock()
        auth.REQUIRES_REGION = False
        self.emitter.emit_until_response.return_value = (None, 'custom')

        auth_types_map = {'custom': mock.Mock(), 'custom-query': auth}
        with mock.patch.dict(botocore.auth.AUTH_TYPE_MAPS, auth_types_map):
            self.signer.generate_presigned_url(request_dict, 'operation_name')

        auth.assert_called_with(credentials=self.fixed_credentials,
                                expires=3600)

    def test_generate_url_unsigned(self):
        request_dict = {
            'headers': {},
            'url': 'https://foo.com',
            'body': b'',
            'url_path': '/',
            'method': 'GET',
            'context': {}
        }
        self.emitter.emit_until_response.return_value = (
            None, botocore.UNSIGNED)

        url = self.signer.generate_presigned_url(
            request_dict, 'operation_name')

        self.assertEqual(url, 'https://foo.com')

    def test_generate_presigned_url(self):
        auth = mock.Mock()
        auth.REQUIRES_REGION = True

        request_dict = {
            'headers': {},
            'url': 'https://foo.com',
            'body': b'',
            'url_path': '/',
            'method': 'GET',
            'context': {}
        }
        with mock.patch.dict(botocore.auth.AUTH_TYPE_MAPS,
                             {'v4-query': auth}):
            presigned_url = self.signer.generate_presigned_url(
                request_dict, operation_name='operation_name')
        auth.assert_called_with(
            credentials=self.fixed_credentials, region_name='region_name',
            service_name='signing_name', expires=3600)
        self.assertEqual(presigned_url, 'https://foo.com')

    def test_generate_presigned_url_with_region_override(self):
        auth = mock.Mock()
        auth.REQUIRES_REGION = True

        request_dict = {
            'headers': {},
            'url': 'https://foo.com',
            'body': b'',
            'url_path': '/',
            'method': 'GET',
            'context': {}
        }
        with mock.patch.dict(botocore.auth.AUTH_TYPE_MAPS,
                             {'v4-query': auth}):
            presigned_url = self.signer.generate_presigned_url(
                request_dict, operation_name='operation_name',
                region_name='us-west-2')
        auth.assert_called_with(
            credentials=self.fixed_credentials, region_name='us-west-2',
            service_name='signing_name', expires=3600)
        self.assertEqual(presigned_url, 'https://foo.com')

    def test_generate_presigned_url_with_exipres_in(self):
        auth = mock.Mock()
        auth.REQUIRES_REGION = True

        request_dict = {
            'headers': {},
            'url': 'https://foo.com',
            'body': b'',
            'url_path': '/',
            'method': 'GET',
            'context': {}
        }
        with mock.patch.dict(botocore.auth.AUTH_TYPE_MAPS,
                             {'v4-query': auth}):
            presigned_url = self.signer.generate_presigned_url(
                request_dict, operation_name='operation_name', expires_in=900)
        auth.assert_called_with(
            credentials=self.fixed_credentials,
            region_name='region_name',
            expires=900, service_name='signing_name')
        self.assertEqual(presigned_url, 'https://foo.com')

    def test_presigned_url_throws_unsupported_signature_error(self):
        request_dict = {
            'headers': {},
            'url': 'https://s3.amazonaws.com/mybucket/myobject',
            'body': b'',
            'url_path': '/',
            'method': 'GET',
            'context': {}
        }
        self.signer = RequestSigner(
            ServiceId('service_name'), 'region_name', 'signing_name',
            'foo', self.credentials, self.emitter)
        with self.assertRaises(UnsupportedSignatureVersionError):
            self.signer.generate_presigned_url(
                request_dict, operation_name='foo')

    def test_signer_with_refreshable_credentials_gets_credential_set(self):
        class FakeCredentials(Credentials):
            def get_frozen_credentials(self):
                return ReadOnlyCredentials('foo', 'bar', 'baz')
        self.credentials = FakeCredentials('a', 'b', 'c')

        self.signer = RequestSigner(
            ServiceId('service_name'), 'region_name', 'signing_name',
            'v4', self.credentials, self.emitter)

        auth_cls = mock.Mock()
        with mock.patch.dict(botocore.auth.AUTH_TYPE_MAPS,
                             {'v4': auth_cls}):
            auth = self.signer.get_auth('service_name', 'region_name')
            self.assertEqual(auth, auth_cls.return_value)
            # Note we're called with 'foo', 'bar', 'baz', and *not*
            # 'a', 'b', 'c'.
            auth_cls.assert_called_with(
                credentials=ReadOnlyCredentials('foo', 'bar', 'baz'),
                service_name='service_name',
                region_name='region_name')

    def test_no_credentials_case_is_forwarded_to_signer(self):
        # If no credentials are given to the RequestSigner, we should
        # forward that fact on to the Auth class and let them handle
        # the error (which they already do).
        self.credentials = None
        self.signer = RequestSigner(
            ServiceId('service_name'), 'region_name', 'signing_name',
            'v4', self.credentials, self.emitter)
        auth_cls = mock.Mock()
        with mock.patch.dict(botocore.auth.AUTH_TYPE_MAPS,
                             {'v4': auth_cls}):
            auth = self.signer.get_auth_instance(
                'service_name', 'region_name', 'v4')
            auth_cls.assert_called_with(
                service_name='service_name',
                region_name='region_name',
                credentials=None,
            )

    def test_sign_with_signing_type_standard(self):
        auth = mock.Mock()
        post_auth = mock.Mock()
        query_auth = mock.Mock()
        auth_types = {
            'v4-presign-post': post_auth,
            'v4-query': query_auth,
            'v4': auth
        }
        with mock.patch.dict(botocore.auth.AUTH_TYPE_MAPS, auth_types):
            self.signer.sign('operation_name', self.request,
                             signing_type='standard')
        self.assertFalse(post_auth.called)
        self.assertFalse(query_auth.called)
        auth.assert_called_with(
            credentials=ReadOnlyCredentials('key', 'secret', None),
            service_name='signing_name',
            region_name='region_name'
        )

    def test_sign_with_signing_type_presign_url(self):
        auth = mock.Mock()
        post_auth = mock.Mock()
        query_auth = mock.Mock()
        auth_types = {
            'v4-presign-post': post_auth,
            'v4-query': query_auth,
            'v4': auth
        }
        with mock.patch.dict(botocore.auth.AUTH_TYPE_MAPS, auth_types):
            self.signer.sign('operation_name', self.request,
                             signing_type='presign-url')
        self.assertFalse(post_auth.called)
        self.assertFalse(auth.called)
        query_auth.assert_called_with(
            credentials=ReadOnlyCredentials('key', 'secret', None),
            service_name='signing_name',
            region_name='region_name'
        )

    def test_sign_with_signing_type_presign_post(self):
        auth = mock.Mock()
        post_auth = mock.Mock()
        query_auth = mock.Mock()
        auth_types = {
            'v4-presign-post': post_auth,
            'v4-query': query_auth,
            'v4': auth
        }
        with mock.patch.dict(botocore.auth.AUTH_TYPE_MAPS, auth_types):
            self.signer.sign('operation_name', self.request,
                             signing_type='presign-post')
        self.assertFalse(auth.called)
        self.assertFalse(query_auth.called)
        post_auth.assert_called_with(
            credentials=ReadOnlyCredentials('key', 'secret', None),
            service_name='signing_name',
            region_name='region_name'
        )

    def test_sign_with_region_name(self):
        auth = mock.Mock()
        auth_types = {
            'v4': auth
        }
        with mock.patch.dict(botocore.auth.AUTH_TYPE_MAPS, auth_types):
            self.signer.sign('operation_name', self.request, region_name='foo')
        auth.assert_called_with(
            credentials=ReadOnlyCredentials('key', 'secret', None),
            service_name='signing_name',
            region_name='foo'
        )

    def test_sign_override_region_from_context(self):
        auth = mock.Mock()
        auth_types = {
            'v4': auth
        }
        self.request.context = {'signing': {'region': 'my-override-region'}}
        with mock.patch.dict(botocore.auth.AUTH_TYPE_MAPS, auth_types):
            self.signer.sign('operation_name', self.request)
        auth.assert_called_with(
            credentials=ReadOnlyCredentials('key', 'secret', None),
            service_name='signing_name',
            region_name='my-override-region'
        )

    def test_sign_with_region_name_overrides_context(self):
        auth = mock.Mock()
        auth_types = {
            'v4': auth
        }
        self.request.context = {'signing': {'region': 'context-override'}}
        with mock.patch.dict(botocore.auth.AUTH_TYPE_MAPS, auth_types):
            self.signer.sign('operation_name', self.request,
                             region_name='param-override')
        auth.assert_called_with(
            credentials=ReadOnlyCredentials('key', 'secret', None),
            service_name='signing_name',
            region_name='param-override'
        )

    def test_sign_override_signing_name_from_context(self):
        auth = mock.Mock()
        auth_types = {
            'v4': auth
        }
        self.request.context = {'signing': {'signing_name': 'override_name'}}
        with mock.patch.dict(botocore.auth.AUTH_TYPE_MAPS, auth_types):
            self.signer.sign('operation_name', self.request)
        auth.assert_called_with(
            credentials=ReadOnlyCredentials('key', 'secret', None),
            service_name='override_name',
            region_name='region_name'
        )

    def test_sign_with_expires_in(self):
        auth = mock.Mock()
        auth_types = {
            'v4': auth
        }
        with mock.patch.dict(botocore.auth.AUTH_TYPE_MAPS, auth_types):
            self.signer.sign('operation_name', self.request, expires_in=2)
        auth.assert_called_with(
            credentials=ReadOnlyCredentials('key', 'secret', None),
            service_name='signing_name',
            region_name='region_name',
            expires=2
        )

    def test_sign_with_custom_signing_name(self):
        auth = mock.Mock()
        auth_types = {
            'v4': auth
        }
        with mock.patch.dict(botocore.auth.AUTH_TYPE_MAPS, auth_types):
            self.signer.sign('operation_name', self.request,
                             signing_name='foo')
        auth.assert_called_with(
            credentials=ReadOnlyCredentials('key', 'secret', None),
            service_name='foo',
            region_name='region_name'
        )

    def test_presign_with_custom_signing_name(self):
        auth = mock.Mock()
        auth.REQUIRES_REGION = True

        request_dict = {
            'headers': {},
            'url': 'https://foo.com',
            'body': b'',
            'url_path': '/',
            'method': 'GET',
            'context': {}
        }
        with mock.patch.dict(botocore.auth.AUTH_TYPE_MAPS,
                             {'v4-query': auth}):
            presigned_url = self.signer.generate_presigned_url(
                request_dict, operation_name='operation_name',
                signing_name='foo')
        auth.assert_called_with(
            credentials=self.fixed_credentials,
            region_name='region_name',
            expires=3600, service_name='foo')
        self.assertEqual(presigned_url, 'https://foo.com')

    def test_unknown_signer_raises_unknown_on_standard(self):
        auth = mock.Mock()
        auth_types = {
            'v4': auth
        }
        self.emitter.emit_until_response.return_value = (None, 'custom')
        with mock.patch.dict(botocore.auth.AUTH_TYPE_MAPS, auth_types):
            with self.assertRaises(UnknownSignatureVersionError):
                self.signer.sign('operation_name', self.request,
                                 signing_type='standard')

    def test_unknown_signer_raises_unsupported_when_not_standard(self):
        auth = mock.Mock()
        auth_types = {
            'v4': auth
        }
        self.emitter.emit_until_response.return_value = (None, 'custom')
        with mock.patch.dict(botocore.auth.AUTH_TYPE_MAPS, auth_types):
            with self.assertRaises(UnsupportedSignatureVersionError):
                self.signer.sign('operation_name', self.request,
                                 signing_type='presign-url')

            with self.assertRaises(UnsupportedSignatureVersionError):
                self.signer.sign('operation_name', self.request,
                                 signing_type='presign-post')


class TestCloudfrontSigner(BaseSignerTest):
    def setUp(self):
        super(TestCloudfrontSigner, self).setUp()
        self.signer = CloudFrontSigner("MY_KEY_ID", lambda message: b'signed')
        # It helps but the long string diff will still be slightly different on
        # Python 2.6/2.7/3.x. We won't soly rely on that anyway, so it's fine.
        self.maxDiff = None

    def test_build_canned_policy(self):
        policy = self.signer.build_policy('foo', datetime.datetime(2016, 1, 1))
        expected = (
            '{"Statement":[{"Resource":"foo",'
            '"Condition":{"DateLessThan":{"AWS:EpochTime":1451606400}}}]}')
        self.assertEqual(json.loads(policy), json.loads(expected))
        self.assertEqual(policy, expected)  # This is to ensure the right order

    def test_build_custom_policy(self):
        policy = self.signer.build_policy(
            'foo', datetime.datetime(2016, 1, 1),
            date_greater_than=datetime.datetime(2015, 12, 1),
            ip_address='12.34.56.78/9')
        expected = {
            "Statement": [{
                "Resource": "foo",
                "Condition": {
                    "DateGreaterThan": {"AWS:EpochTime": 1448928000},
                    "DateLessThan": {"AWS:EpochTime": 1451606400},
                    "IpAddress": {"AWS:SourceIp": "12.34.56.78/9"}
                },
            }]
        }
        self.assertEqual(json.loads(policy), expected)

    def test_generate_presign_url_with_expire_time(self):
        signed_url = self.signer.generate_presigned_url(
            'http://test.com/foo.txt',
            date_less_than=datetime.datetime(2016, 1, 1))
        expected = (
            'http://test.com/foo.txt?Expires=1451606400&Signature=c2lnbmVk'
            '&Key-Pair-Id=MY_KEY_ID')
        assert_url_equal(signed_url, expected)

    def test_generate_presign_url_with_custom_policy(self):
        policy = self.signer.build_policy(
            'foo', datetime.datetime(2016, 1, 1),
            date_greater_than=datetime.datetime(2015, 12, 1),
            ip_address='12.34.56.78/9')
        signed_url = self.signer.generate_presigned_url(
            'http://test.com/index.html?foo=bar', policy=policy)
        expected = (
            'http://test.com/index.html?foo=bar'
            '&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiZm9vIiwiQ29uZ'
            'Gl0aW9uIjp7IkRhdGVMZXNzVGhhbiI6eyJBV1M6RXBvY2hUaW1lIj'
            'oxNDUxNjA2NDAwfSwiSXBBZGRyZXNzIjp7IkFXUzpTb3VyY2VJcCI'
            '6IjEyLjM0LjU2Ljc4LzkifSwiRGF0ZUdyZWF0ZXJUaGFuIjp7IkFX'
            'UzpFcG9jaFRpbWUiOjE0NDg5MjgwMDB9fX1dfQ__'
            '&Signature=c2lnbmVk&Key-Pair-Id=MY_KEY_ID')
        assert_url_equal(signed_url, expected)


class TestS3PostPresigner(BaseSignerTest):
    def setUp(self):
        super(TestS3PostPresigner, self).setUp()
        self.request_signer = RequestSigner(
            ServiceId('service_name'), 'region_name', 'signing_name',
            's3v4', self.credentials, self.emitter)
        self.signer = S3PostPresigner(self.request_signer)
        self.request_dict = {
            'headers': {},
            'url': 'https://s3.amazonaws.com/mybucket',
            'body': b'',
            'url_path': '/',
            'method': 'POST',
            'context': {}
        }
        self.auth = mock.Mock()
        self.auth.REQUIRES_REGION = True
        self.add_auth = mock.Mock()
        self.auth.return_value.add_auth = self.add_auth
        self.fixed_credentials = self.credentials.get_frozen_credentials()

        self.datetime_patch = mock.patch('botocore.signers.datetime')
        self.datetime_mock = self.datetime_patch.start()
        self.fixed_date = datetime.datetime(2014, 3, 10, 17, 2, 55, 0)
        self.fixed_delta = datetime.timedelta(seconds=3600)
        self.datetime_mock.datetime.utcnow.return_value = self.fixed_date
        self.datetime_mock.timedelta.return_value = self.fixed_delta

    def tearDown(self):
        super(TestS3PostPresigner, self).tearDown()
        self.datetime_patch.stop()

    def test_generate_presigned_post(self):
        with mock.patch.dict(botocore.auth.AUTH_TYPE_MAPS,
                             {'s3v4-presign-post': self.auth}):
            post_form_args = self.signer.generate_presigned_post(
                self.request_dict)
        self.auth.assert_called_with(
            credentials=self.fixed_credentials, region_name='region_name',
            service_name='signing_name')
        self.assertEqual(self.add_auth.call_count, 1)
        ref_request = self.add_auth.call_args[0][0]
        ref_policy = ref_request.context['s3-presign-post-policy']
        self.assertEqual(ref_policy['expiration'], '2014-03-10T18:02:55Z')
        self.assertEqual(ref_policy['conditions'], [])

        self.assertEqual(post_form_args['url'],
                         'https://s3.amazonaws.com/mybucket')
        self.assertEqual(post_form_args['fields'], {})

    def test_generate_presigned_post_emits_choose_signer(self):
        with mock.patch.dict(botocore.auth.AUTH_TYPE_MAPS,
                             {'s3v4-presign-post': self.auth}):
            self.signer.generate_presigned_post(self.request_dict)
        self.emitter.emit_until_response.assert_called_with(
            'choose-signer.service_name.PutObject',
            signing_name='signing_name', region_name='region_name',
            signature_version='s3v4-presign-post', context=mock.ANY)

    def test_generate_presigned_post_choose_signer_override(self):
        auth = mock.Mock()
        self.emitter.emit_until_response.return_value = (None, 'custom')
        auth_types = {
            's3v4-presign-post': self.auth,
            'custom-presign-post': auth
        }
        with mock.patch.dict(botocore.auth.AUTH_TYPE_MAPS, auth_types):
            self.signer.generate_presigned_post(self.request_dict)
        auth.assert_called_with(
            credentials=self.fixed_credentials, region_name='region_name',
            service_name='signing_name')

    def test_generate_presigne_post_choose_signer_override_known(self):
        auth = mock.Mock()
        self.emitter.emit_until_response.return_value = (
            None, 's3v4-presign-post')
        auth_types = {
            's3v4-presign-post': self.auth,
            'custom-presign-post': auth
        }
        with mock.patch.dict(botocore.auth.AUTH_TYPE_MAPS, auth_types):
            self.signer.generate_presigned_post(self.request_dict)
        self.auth.assert_called_with(
            credentials=self.fixed_credentials, region_name='region_name',
            service_name='signing_name')

    def test_generate_presigned_post_bad_signer_raises_error(self):
        auth = mock.Mock()
        self.emitter.emit_until_response.return_value = (None, 's3-query')
        auth_types = {
            's3v4-presign-post': self.auth,
            's3-query': auth
        }
        with mock.patch.dict(botocore.auth.AUTH_TYPE_MAPS, auth_types):
            with self.assertRaises(UnsupportedSignatureVersionError):
                self.signer.generate_presigned_post(self.request_dict)

    def test_generate_unsigned_post(self):
        self.emitter.emit_until_response.return_value = (
            None, botocore.UNSIGNED)
        with mock.patch.dict(botocore.auth.AUTH_TYPE_MAPS,
                             {'s3v4-presign-post': self.auth}):
            post_form_args = self.signer.generate_presigned_post(
                self.request_dict)
        expected = {'fields': {}, 'url': 'https://s3.amazonaws.com/mybucket'}
        self.assertEqual(post_form_args, expected)

    def test_generate_presigned_post_with_conditions(self):
        conditions = [
            {'bucket': 'mybucket'},
            ['starts-with', '$key', 'bar']
        ]
        with mock.patch.dict(botocore.auth.AUTH_TYPE_MAPS,
                             {'s3v4-presign-post': self.auth}):
            self.signer.generate_presigned_post(
                self.request_dict, conditions=conditions)
        self.auth.assert_called_with(
            credentials=self.fixed_credentials, region_name='region_name',
            service_name='signing_name')
        self.assertEqual(self.add_auth.call_count, 1)
        ref_request = self.add_auth.call_args[0][0]
        ref_policy = ref_request.context['s3-presign-post-policy']
        self.assertEqual(ref_policy['conditions'], conditions)

    def test_generate_presigned_post_with_region_override(self):
        with mock.patch.dict(botocore.auth.AUTH_TYPE_MAPS,
                             {'s3v4-presign-post': self.auth}):
            self.signer.generate_presigned_post(
                self.request_dict, region_name='foo')
        self.auth.assert_called_with(
            credentials=self.fixed_credentials, region_name='foo',
            service_name='signing_name')

    def test_presigned_post_throws_unsupported_signature_error(self):
        request_dict = {
            'headers': {},
            'url': 'https://s3.amazonaws.com/mybucket/myobject',
            'body': b'',
            'url_path': '/',
            'method': 'POST',
            'context': {}
        }
        self.request_signer = RequestSigner(
            ServiceId('service_name'), 'region_name', 'signing_name',
            'foo', self.credentials, self.emitter)
        self.signer = S3PostPresigner(self.request_signer)
        with self.assertRaises(UnsupportedSignatureVersionError):
            self.signer.generate_presigned_post(request_dict)


class TestGenerateUrl(unittest.TestCase):
    def setUp(self):
        self.session = botocore.session.get_session()
        self.client = self.session.create_client('s3', region_name='us-east-1')
        self.bucket = 'mybucket'
        self.key = 'mykey'
        self.client_kwargs = {'Bucket': self.bucket, 'Key': self.key}
        self.generate_url_patch = mock.patch(
            'botocore.signers.RequestSigner.generate_presigned_url')
        self.generate_url_mock = self.generate_url_patch.start()

    def tearDown(self):
        self.generate_url_patch.stop()

    def test_generate_presigned_url(self):
        self.client.generate_presigned_url(
            'get_object', Params={'Bucket': self.bucket, 'Key': self.key})

        ref_request_dict = {
            'body': b'',
            'url': 'https://mybucket.s3.amazonaws.com/mykey',
            'headers': {},
            'auth_path': '/mybucket/mykey',
            'query_string': {},
            'url_path': '/mykey',
            'method': u'GET',
            # mock.ANY is used because client parameter related events
            # inject values into the context. So using the context's exact
            # value for these tests will be a maintenance burden if
            # anymore customizations are added that inject into the context.
            'context': mock.ANY}
        self.generate_url_mock.assert_called_with(
            request_dict=ref_request_dict, expires_in=3600,
            operation_name='GetObject')

    def test_generate_presigned_url_with_query_string(self):
        disposition = 'attachment; filename="download.jpg"'
        self.client.generate_presigned_url(
            'get_object', Params={
                'Bucket': self.bucket,
                'Key': self.key,
                'ResponseContentDisposition': disposition})
        ref_request_dict = {
            'body': b'',
            'url': ('https://mybucket.s3.amazonaws.com/mykey'
                    '?response-content-disposition='
                    'attachment%3B%20filename%3D%22download.jpg%22'),
            'auth_path': '/mybucket/mykey',
            'headers': {},
            'query_string': {u'response-content-disposition': disposition},
            'url_path': '/mykey',
            'method': u'GET',
            'context': mock.ANY}
        self.generate_url_mock.assert_called_with(
            request_dict=ref_request_dict, expires_in=3600,
            operation_name='GetObject')

    def test_generate_presigned_url_unknown_method_name(self):
        with self.assertRaises(UnknownClientMethodError):
            self.client.generate_presigned_url('getobject')

    def test_generate_presigned_url_missing_required_params(self):
        with self.assertRaises(ParamValidationError):
            self.client.generate_presigned_url('get_object')

    def test_generate_presigned_url_expires(self):
        self.client.generate_presigned_url(
            'get_object', Params={'Bucket': self.bucket, 'Key': self.key},
            ExpiresIn=20)
        ref_request_dict = {
            'body': b'',
            'url': 'https://mybucket.s3.amazonaws.com/mykey',
            'auth_path': '/mybucket/mykey',
            'headers': {},
            'query_string': {},
            'url_path': '/mykey',
            'method': u'GET',
            'context': mock.ANY}
        self.generate_url_mock.assert_called_with(
            request_dict=ref_request_dict, expires_in=20,
            operation_name='GetObject')

    def test_generate_presigned_url_override_http_method(self):
        self.client.generate_presigned_url(
            'get_object', Params={'Bucket': self.bucket, 'Key': self.key},
            HttpMethod='PUT')
        ref_request_dict = {
            'body': b'',
            'url': 'https://mybucket.s3.amazonaws.com/mykey',
            'auth_path': '/mybucket/mykey',
            'headers': {},
            'query_string': {},
            'url_path': '/mykey',
            'method': u'PUT',
            'context': mock.ANY}
        self.generate_url_mock.assert_called_with(
            request_dict=ref_request_dict, expires_in=3600,
            operation_name='GetObject')

    def test_generate_presigned_url_emits_param_events(self):
        emitter = mock.Mock(HierarchicalEmitter)
        emitter.emit.return_value = []
        self.client.meta.events = emitter
        self.client.generate_presigned_url(
            'get_object', Params={'Bucket': self.bucket, 'Key': self.key})
        events_emitted = [
            emit_call[0][0] for emit_call in emitter.emit.call_args_list
        ]
        self.assertEqual(
            events_emitted,
            [
                'provide-client-params.s3.GetObject',
                'before-parameter-build.s3.GetObject'
            ]
        )

    def test_generate_presign_url_emits_is_presign_in_context(self):
        emitter = mock.Mock(HierarchicalEmitter)
        emitter.emit.return_value = []
        self.client.meta.events = emitter
        self.client.generate_presigned_url(
            'get_object', Params={'Bucket': self.bucket, 'Key': self.key})
        kwargs_emitted = [
            emit_call[1] for emit_call in emitter.emit.call_args_list
        ]
        for kwargs in kwargs_emitted:
            self.assertTrue(
                kwargs.get('context', {}).get('is_presign_request'),
                'The context did not have is_presign_request set to True for '
                'the following kwargs emitted: %s' % kwargs
            )


class TestGeneratePresignedPost(unittest.TestCase):
    def setUp(self):
        self.session = botocore.session.get_session()
        self.client = self.session.create_client('s3', region_name='us-east-1')
        self.bucket = 'mybucket'
        self.key = 'mykey'
        self.presign_post_patch = mock.patch(
            'botocore.signers.S3PostPresigner.generate_presigned_post')
        self.presign_post_mock = self.presign_post_patch.start()

    def tearDown(self):
        self.presign_post_patch.stop()

    def test_generate_presigned_post(self):
        self.client.generate_presigned_post(self.bucket, self.key)

        _, post_kwargs = self.presign_post_mock.call_args
        request_dict = post_kwargs['request_dict']
        fields = post_kwargs['fields']
        conditions = post_kwargs['conditions']
        self.assertEqual(
            request_dict['url'], 'https://mybucket.s3.amazonaws.com/')
        self.assertEqual(post_kwargs['expires_in'], 3600)
        self.assertEqual(
            conditions,
            [{'bucket': 'mybucket'}, {'key': 'mykey'}])
        self.assertEqual(
            fields,
            {'key': 'mykey'})

    def test_generate_presigned_post_with_filename(self):
        self.key = 'myprefix/${filename}'
        self.client.generate_presigned_post(self.bucket, self.key)

        _, post_kwargs = self.presign_post_mock.call_args
        request_dict = post_kwargs['request_dict']
        fields = post_kwargs['fields']
        conditions = post_kwargs['conditions']
        self.assertEqual(
            request_dict['url'], 'https://mybucket.s3.amazonaws.com/')
        self.assertEqual(post_kwargs['expires_in'], 3600)
        self.assertEqual(
            conditions,
            [{'bucket': 'mybucket'}, ['starts-with', '$key', 'myprefix/']])
        self.assertEqual(
            fields,
            {'key': 'myprefix/${filename}'})

    def test_generate_presigned_post_expires(self):
        self.client.generate_presigned_post(
            self.bucket, self.key, ExpiresIn=50)
        _, post_kwargs = self.presign_post_mock.call_args
        request_dict = post_kwargs['request_dict']
        fields = post_kwargs['fields']
        conditions = post_kwargs['conditions']
        self.assertEqual(
            request_dict['url'], 'https://mybucket.s3.amazonaws.com/')
        self.assertEqual(post_kwargs['expires_in'], 50)
        self.assertEqual(
            conditions,
            [{'bucket': 'mybucket'}, {'key': 'mykey'}])
        self.assertEqual(
            fields,
            {'key': 'mykey'})

    def test_generate_presigned_post_with_prefilled(self):
        conditions = [{'acl': 'public-read'}]
        fields = {'acl': 'public-read'}

        self.client.generate_presigned_post(
            self.bucket, self.key, Fields=fields, Conditions=conditions)

        self.assertEqual(fields, {'acl': 'public-read'})

        _, post_kwargs = self.presign_post_mock.call_args
        request_dict = post_kwargs['request_dict']
        fields = post_kwargs['fields']
        conditions = post_kwargs['conditions']
        self.assertEqual(
            request_dict['url'], 'https://mybucket.s3.amazonaws.com/')
        self.assertEqual(
            conditions,
            [{'acl': 'public-read'}, {'bucket': 'mybucket'}, {'key': 'mykey'}])
        self.assertEqual(fields['acl'], 'public-read')
        self.assertEqual(
            fields, {'key': 'mykey', 'acl': 'public-read'})

    def test_generate_presigned_post_non_s3_client(self):
        self.client = self.session.create_client('ec2', 'us-west-2')
        with self.assertRaises(AttributeError):
            self.client.generate_presigned_post()


class TestGenerateDBAuthToken(BaseSignerTest):
    maxDiff = None

    def setUp(self):
        self.session = botocore.session.get_session()
        self.client = self.session.create_client(
            'rds', region_name='us-east-1', aws_access_key_id='akid',
            aws_secret_access_key='skid', config=Config(signature_version='v4')
        )

    def test_generate_db_auth_token(self):
        hostname = 'prod-instance.us-east-1.rds.amazonaws.com'
        port = 3306
        username = 'someusername'
        clock = datetime.datetime(2016, 11, 7, 17, 39, 33, tzinfo=tzutc())

        with mock.patch('datetime.datetime') as dt:
            dt.utcnow.return_value = clock
            result = generate_db_auth_token(
                self.client, hostname, port, username)

        expected_result = (
            'prod-instance.us-east-1.rds.amazonaws.com:3306/?Action=connect'
            '&DBUser=someusername&X-Amz-Algorithm=AWS4-HMAC-SHA256'
            '&X-Amz-Date=20161107T173933Z&X-Amz-SignedHeaders=host'
            '&X-Amz-Expires=900&X-Amz-Credential=akid%2F20161107%2F'
            'us-east-1%2Frds-db%2Faws4_request&X-Amz-Signature'
            '=d1138cdbc0ca63eec012ec0fc6c2267e03642168f5884a7795320d4c18374c61'
        )

        # A scheme needs to be appended to the beginning or urlsplit may fail
        # on certain systems.
        assert_url_equal(
            'https://' + result, 'https://' + expected_result)

    def test_custom_region(self):
        hostname = 'host.us-east-1.rds.amazonaws.com'
        port = 3306
        username = 'mySQLUser'
        region = 'us-west-2'
        result = generate_db_auth_token(
            self.client, hostname, port, username, Region=region)

        self.assertIn(region, result)
        # The hostname won't be changed even if a different region is specified
        self.assertIn(hostname, result)
