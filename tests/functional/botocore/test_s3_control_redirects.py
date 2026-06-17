# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import re
from contextlib import contextmanager

import pytest

from botocore import exceptions
from botocore.compat import urlsplit
from botocore.config import Config
from botocore.exceptions import (
    InvalidHostLabelError,
    ParamValidationError,
    UnsupportedS3ControlArnError,
)
from botocore.session import Session
from tests import ClientHTTPStubber, unittest

ACCESSPOINT_ARN_TEST_CASES = [
    # Outpost accesspoint arn test cases
    {
        'arn': (
            'arn:aws:s3-outposts:us-west-2:123456789012:'
            'outpost:op-01234567890123456:accesspoint:myaccesspoint'
        ),
        'region': 'us-west-2',
        'config': {},
        'assertions': {
            'signing_name': 's3-outposts',
            'netloc': 's3-outposts.us-west-2.amazonaws.com',
            'headers': {
                'x-amz-outpost-id': 'op-01234567890123456',
                'x-amz-account-id': '123456789012',
            },
        },
    },
    {
        'arn': 'arn:aws:s3-outposts:us-east-1:123456789012:outpost:op-01234567890123456:accesspoint:myaccesspoint',
        'region': 'us-west-2',
        'config': {'s3': {'use_arn_region': True}},
        'assertions': {
            'signing_name': 's3-outposts',
            'netloc': 's3-outposts.us-east-1.amazonaws.com',
            'headers': {
                'x-amz-outpost-id': 'op-01234567890123456',
                'x-amz-account-id': '123456789012',
            },
        },
    },
    {
        'arn': 'arn:aws:s3-outposts:us-east-1:123456789012:outpost:op-01234567890123456:accesspoint:myaccesspoint',
        'region': 'us-west-2',
        'config': {'s3': {'use_arn_region': False}},
        'assertions': {
            'exception': 'UnsupportedS3ControlConfigurationError',
        },
    },
    {
        'arn': 'arn:aws-cn:s3-outposts:cn-north-1:123456789012:outpost:op-01234567890123456:accesspoint:myaccesspoint',
        'region': 'us-west-2',
        'config': {'s3': {'use_arn_region': True}},
        'assertions': {
            'exception': 'UnsupportedS3ControlConfigurationError',
        },
    },
    {
        'arn': 'arn:aws-us-gov:s3-outposts:us-gov-east-1:123456789012:outpost:op-01234567890123456:accesspoint:myaccesspoint',
        'region': 'us-gov-east-1',
        'config': {'s3': {'use_arn_region': True}},
        'assertions': {
            'signing_name': 's3-outposts',
            'netloc': 's3-outposts.us-gov-east-1.amazonaws.com',
            'headers': {
                'x-amz-outpost-id': 'op-01234567890123456',
                'x-amz-account-id': '123456789012',
            },
        },
    },
    {
        'arn': 'arn:aws-us-gov:s3-outposts:us-gov-east-1:123456789012:outpost:op-01234567890123456:accesspoint:myaccesspoint',
        'region': 'us-gov-east-1-fips',
        'config': {'s3': {'use_arn_region': False}},
        'assertions': {
            'signing_name': 's3-outposts',
            'netloc': 's3-outposts-fips.us-gov-east-1.amazonaws.com',
            'headers': {
                'x-amz-outpost-id': 'op-01234567890123456',
                'x-amz-account-id': '123456789012',
            },
        },
    },
    {
        'arn': 'arn:aws-us-gov:s3-outposts:fips-us-gov-east-1:123456789012:outpost:op-01234567890123456:accesspoint:myaccesspoint',
        'region': 'fips-us-gov-east-1',
        'config': {'s3': {'use_arn_region': True}},
        'assertions': {
            'exception': 'UnsupportedS3ControlArnError',
        },
    },
    {
        'arn': 'arn:aws-us-gov:s3-outposts:us-gov-east-1:123456789012:outpost:op-01234567890123456:accesspoint:myaccesspoint',
        'region': 'us-gov-east-1-fips',
        'config': {'s3': {'use_arn_region': True}},
        'assertions': {
            'signing_name': 's3-outposts',
            'netloc': 's3-outposts-fips.us-gov-east-1.amazonaws.com',
            'headers': {
                'x-amz-outpost-id': 'op-01234567890123456',
                'x-amz-account-id': '123456789012',
            },
        },
    },
    {
        'arn': 'arn:aws:s3-outposts:us-west-2:123456789012:outpost:op-01234567890123456:accesspoint:myaccesspoint',
        'config': {'s3': {'use_dualstack_endpoint': True}},
        'assertions': {
            'signing_name': 's3-outposts',
            'netloc': 's3-outposts.us-west-2.api.aws',
            'headers': {
                'x-amz-outpost-id': 'op-01234567890123456',
                'x-amz-account-id': '123456789012',
            },
        },
    },
    {
        'arn': 'arn:aws:s3-outposts:us-west-2:123456789012:outpost:op-01234567890123456:accesspoint:myaccesspoint',
        'config': {'s3': {'use_accelerate_endpoint': True}},
        'assertions': {
            'exception': 'UnsupportedS3ControlConfigurationError',
        },
    },
    {
        'arn': 'arn:aws:s3-outposts:us-west-2:123456789012:outpost',
        'assertions': {
            'exception': 'UnsupportedS3ControlArnError',
        },
    },
    {
        'arn': 'arn:aws:s3-outposts:us-west-2:123456789012:outpost:op-01234567890123456',
        'assertions': {
            'exception': 'UnsupportedS3ControlArnError',
        },
    },
    {
        'arn': 'arn:aws:s3-outposts:us-west-2:123456789012:outpost:myaccesspoint',
        'assertions': {
            'exception': 'UnsupportedS3ControlArnError',
        },
    },
]


BUCKET_ARN_TEST_CASES = [
    # Outpost bucket arn test cases
    {
        'arn': 'arn:aws:s3-outposts:us-west-2:123456789012:outpost:op-01234567890123456:bucket:mybucket',
        'region': 'us-west-2',
        'config': {},
        'assertions': {
            'signing_name': 's3-outposts',
            'netloc': 's3-outposts.us-west-2.amazonaws.com',
            'headers': {
                'x-amz-outpost-id': 'op-01234567890123456',
                'x-amz-account-id': '123456789012',
            },
        },
    },
    {
        'arn': 'arn:aws:s3-outposts:us-east-1:123456789012:outpost:op-01234567890123456:bucket:mybucket',
        'region': 'us-west-2',
        'config': {'s3': {'use_arn_region': True}},
        'assertions': {
            'signing_name': 's3-outposts',
            'netloc': 's3-outposts.us-east-1.amazonaws.com',
            'headers': {
                'x-amz-outpost-id': 'op-01234567890123456',
                'x-amz-account-id': '123456789012',
            },
        },
    },
    {
        'arn': 'arn:aws:s3-outposts:us-east-1:123456789012:outpost:op-01234567890123456:bucket:mybucket',
        'region': 'us-west-2',
        'config': {'s3': {'use_arn_region': False}},
        'assertions': {
            'exception': 'UnsupportedS3ControlConfigurationError',
        },
    },
    {
        'arn': 'arn:aws-cn:s3-outposts:cn-north-1:123456789012:outpost:op-01234567890123456:bucket:mybucket',
        'region': 'us-west-2',
        'config': {'s3': {'use_arn_region': True}},
        'assertions': {
            'exception': 'UnsupportedS3ControlConfigurationError',
        },
    },
    {
        'arn': 'arn:aws-us-gov:s3-outposts:us-gov-east-1:123456789012:outpost:op-01234567890123456:bucket:mybucket',
        'region': 'us-gov-east-1',
        'config': {'s3': {'use_arn_region': True}},
        'assertions': {
            'signing_name': 's3-outposts',
            'netloc': 's3-outposts.us-gov-east-1.amazonaws.com',
            'headers': {
                'x-amz-outpost-id': 'op-01234567890123456',
                'x-amz-account-id': '123456789012',
            },
        },
    },
    {
        'arn': 'arn:aws-us-gov:s3-outposts:us-gov-east-1:123456789012:outpost:op-01234567890123456:bucket:mybucket',
        'region': 'us-gov-east-1-fips',
        'config': {'s3': {'use_arn_region': False}},
        'assertions': {
            'signing_name': 's3-outposts',
            'netloc': 's3-outposts-fips.us-gov-east-1.amazonaws.com',
            'headers': {
                'x-amz-outpost-id': 'op-01234567890123456',
                'x-amz-account-id': '123456789012',
            },
        },
    },
    {
        'arn': 'arn:aws-us-gov:s3-outposts:fips-us-gov-east-1:123456789012:outpost:op-01234567890123456:bucket:mybucket',
        'region': 'fips-us-gov-east-1',
        'config': {'s3': {'use_arn_region': True}},
        'assertions': {
            'exception': 'UnsupportedS3ControlArnError',
        },
    },
    {
        'arn': 'arn:aws-us-gov:s3-outposts:us-gov-east-1:123456789012:outpost:op-01234567890123456:bucket:mybucket',
        'region': 'us-gov-east-1-fips',
        'config': {'s3': {'use_arn_region': True}},
        'assertions': {
            'signing_name': 's3-outposts',
            'netloc': 's3-outposts-fips.us-gov-east-1.amazonaws.com',
            'headers': {
                'x-amz-outpost-id': 'op-01234567890123456',
                'x-amz-account-id': '123456789012',
            },
        },
    },
    {
        'arn': 'arn:aws:s3-outposts:us-west-2:123456789012:outpost:op-01234567890123456:bucket:mybucket',
        'region': 'us-west-2',
        'config': {'s3': {'use_dualstack_endpoint': True}},
        'assertions': {
            'signing_name': 's3-outposts',
            'netloc': 's3-outposts.us-west-2.api.aws',
            'headers': {
                'x-amz-outpost-id': 'op-01234567890123456',
                'x-amz-account-id': '123456789012',
            },
        },
    },
    {
        'arn': 'arn:aws:s3-outposts:us-west-2:123456789012:outpost',
        'assertions': {
            'exception': 'UnsupportedS3ControlArnError',
        },
    },
    {
        'arn': 'arn:aws:s3-outposts:us-west-2:123456789012:outpost:op-01234567890123456',
        'assertions': {
            'exception': 'UnsupportedS3ControlArnError',
        },
    },
    {
        'arn': 'arn:aws:s3-outposts:us-west-2:123456789012:outpost:bucket',
        'assertions': {
            'exception': 'UnsupportedS3ControlArnError',
        },
    },
    {
        'arn': 'arn:aws:s3-outposts:us-west-2:123456789012:outpost:op-01234567890123456:bucket',
        'assertions': {
            'exception': 'UnsupportedS3ControlArnError',
        },
    },
]


V4_AUTH_REGEX = re.compile(
    r'AWS4-HMAC-SHA256 Credential=\w+/\d+/'
    r'(?P<region>[a-z0-9-]+)/(?P<name>[a-z0-9-]+)/'
)


def _assert_signing_name(stubber, expected_name):
    request = stubber.requests[0]
    auth_header = request.headers['Authorization'].decode('utf-8')
    actual_name = V4_AUTH_REGEX.match(auth_header).group('name')
    assert expected_name == actual_name


def _assert_netloc(stubber, expected_netloc):
    request = stubber.requests[0]
    url_parts = urlsplit(request.url)
    assert expected_netloc == url_parts.netloc


def _assert_header(stubber, key, value):
    request = stubber.requests[0]
    assert key in request.headers
    actual_value = request.headers[key]
    if isinstance(actual_value, bytes):
        actual_value = actual_value.decode('utf-8')
    assert value == actual_value


def _assert_headers(stubber, headers):
    for key, value in headers.items():
        _assert_header(stubber, key, value)


def _bootstrap_session():
    session = Session()
    session.set_credentials('access_key', 'secret_key')
    return session


def _bootstrap_client(session, region, **kwargs):
    client = session.create_client('s3control', region, **kwargs)
    stubber = ClientHTTPStubber(client)
    return client, stubber


def _bootstrap_test_case_client(session, test_case):
    region = test_case.get('region', 'us-west-2')
    config = test_case.get('config', {})
    config = Config(**config)
    return _bootstrap_client(session, region, config=config)


@pytest.mark.parametrize("test_case", ACCESSPOINT_ARN_TEST_CASES)
def test_accesspoint_arn_redirection(test_case):
    session = _bootstrap_session()
    client, stubber = _bootstrap_test_case_client(session, test_case)
    with _assert_test_case(test_case, client, stubber):
        client.get_access_point_policy(Name=test_case['arn'])


@pytest.mark.parametrize("test_case", BUCKET_ARN_TEST_CASES)
def test_bucket_arn_redirection(test_case):
    session = _bootstrap_session()
    client, stubber = _bootstrap_test_case_client(session, test_case)
    with _assert_test_case(test_case, client, stubber):
        client.get_bucket(Bucket=test_case['arn'])


@contextmanager
def _assert_test_case(test_case, client, stubber):
    stubber.add_response()
    assertions = test_case['assertions']
    exception_raised = None
    try:
        with stubber:
            yield
    except Exception as e:
        if 'exception' not in assertions:
            raise
        exception_raised = e
    if 'exception' in assertions:
        exception_cls = getattr(exceptions, assertions['exception'])
        if exception_raised is None:
            raise RuntimeError(
                f'Expected exception "{exception_cls}" was not raised'
            )
        error_msg = f'Expected exception "{exception_cls}", got "{type(exception_raised)}"'
        assert isinstance(exception_raised, exception_cls), error_msg
    else:
        assert len(stubber.requests) == 1
        if 'signing_name' in assertions:
            _assert_signing_name(stubber, assertions['signing_name'])
        if 'headers' in assertions:
            _assert_headers(stubber, assertions['headers'])
        if 'netloc' in assertions:
            _assert_netloc(stubber, assertions['netloc'])


class TestS3ControlRedirection(unittest.TestCase):
    def setUp(self):
        self.session = _bootstrap_session()
        self.region = 'us-west-2'
        self._bootstrap_client()

    def _bootstrap_client(self, **kwargs):
        client, stubber = _bootstrap_client(
            self.session, self.region, **kwargs
        )
        self.client = client
        self.stubber = stubber

    def test_outpost_id_redirection_dualstack(self):
        config = Config(s3={'use_dualstack_endpoint': True})
        self._bootstrap_client(config=config)
        self.stubber.add_response()
        with self.stubber:
            self.client.create_bucket(Bucket='foo', OutpostId='op-123')
        _assert_netloc(self.stubber, 's3-outposts.us-west-2.api.aws')
        _assert_header(self.stubber, 'x-amz-outpost-id', 'op-123')

    def test_outpost_id_redirection_create_bucket(self):
        self.stubber.add_response()
        with self.stubber:
            self.client.create_bucket(Bucket='foo', OutpostId='op-123')
        _assert_netloc(self.stubber, 's3-outposts.us-west-2.amazonaws.com')
        _assert_header(self.stubber, 'x-amz-outpost-id', 'op-123')

    def test_outpost_id_redirection_list_regional_buckets(self):
        self.stubber.add_response()
        with self.stubber:
            self.client.list_regional_buckets(
                OutpostId='op-123',
                AccountId='1234',
            )
        _assert_netloc(self.stubber, 's3-outposts.us-west-2.amazonaws.com')
        _assert_header(self.stubber, 'x-amz-outpost-id', 'op-123')

    def test_outpost_redirection_custom_endpoint(self):
        self._bootstrap_client(endpoint_url='https://outpost.foo.com/')
        self.stubber.add_response()
        with self.stubber:
            self.client.create_bucket(Bucket='foo', OutpostId='op-123')
        _assert_netloc(self.stubber, 'outpost.foo.com')
        _assert_header(self.stubber, 'x-amz-outpost-id', 'op-123')

    def test_normal_ap_request_has_correct_endpoint(self):
        self.stubber.add_response()
        with self.stubber:
            self.client.get_access_point_policy(Name='MyAp', AccountId='1234')
        _assert_netloc(self.stubber, '1234.s3-control.us-west-2.amazonaws.com')

    def test_normal_ap_request_custom_endpoint(self):
        self._bootstrap_client(endpoint_url='https://example.com/')
        self.stubber.add_response()
        with self.stubber:
            self.client.get_access_point_policy(Name='MyAp', AccountId='1234')
        _assert_netloc(self.stubber, '1234.example.com')

    def test_normal_bucket_request_has_correct_endpoint(self):
        self.stubber.add_response()
        with self.stubber:
            self.client.create_bucket(Bucket='foo')
        _assert_netloc(self.stubber, 's3-control.us-west-2.amazonaws.com')

    def test_arn_account_id_mismatch(self):
        arn = (
            'arn:aws:s3-outposts:us-west-2:123456789012:outpost:'
            'op-01234567890123456:accesspoint:myaccesspoint'
        )
        with self.assertRaises(UnsupportedS3ControlArnError):
            self.client.get_access_point_policy(Name=arn, AccountId='1234')

    def test_create_access_point_does_not_expand_name(self):
        arn = (
            'arn:aws:s3-outposts:us-west-2:123456789012:outpost:'
            'op-01234567890123456:accesspoint:myaccesspoint'
        )
        # AccountId will not be backfilled by the arn expansion and thus
        # fail parameter validation
        with self.assertRaises(ParamValidationError):
            self.client.create_access_point(Name=arn, Bucket='foo')

    def test_arn_invalid_host_label(self):
        config = Config(s3={'use_arn_region': True})
        self._bootstrap_client(config=config)
        arn = (
            'arn:aws:s3-outposts:us-we$t-2:123456789012:outpost:'
            'op-01234567890123456:accesspoint:myaccesspoint'
        )
        with self.assertRaises(InvalidHostLabelError):
            self.client.get_access_point_policy(Name=arn)

    def test_unknown_arn_format(self):
        arn = 'arn:aws:foo:us-west-2:123456789012:bar:myresource'
        with self.assertRaises(UnsupportedS3ControlArnError):
            self.client.get_access_point_policy(Name=arn)
