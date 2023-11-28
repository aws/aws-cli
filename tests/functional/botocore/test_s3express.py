# Copyright 2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import datetime

import pytest
from dateutil.tz import tzutc

import botocore.session
from botocore.auth import S3ExpressAuth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials, RefreshableCredentials
from botocore.utils import S3ExpressIdentityCache
from tests import ClientHTTPStubber, mock

ACCESS_KEY = "AKIDEXAMPLE"
SECRET_KEY = "wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY"
TOKEN = "TOKEN"

EXPRESS_ACCESS_KEY = "EXPRESS_AKIDEXAMPLE"
EXPRESS_SECRET_KEY = "EXPRESS_53cr37"
EXPRESS_TOKEN = "EXPRESS_TOKEN"

CREDENTIALS = Credentials(ACCESS_KEY, SECRET_KEY, TOKEN)
ENDPOINT = "https://s3.us-west-2.amazonaws.com"

S3EXPRESS_BUCKET = "mytestbucket--usw2-az5--x-s3"


DATE = datetime.datetime(2023, 11, 26, 0, 0, 0, tzinfo=tzutc())


CREATE_SESSION_RESPONSE = (
    b"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
    b"<CreateSessionResult xmlns=\"http://s3.amazonaws.com/doc/2006-03-01/\">"
    b"<Credentials><SessionToken>EXPRESS_TOKEN</SessionToken>"
    b"<SecretAccessKey>EXPRESS_53cr37</SecretAccessKey>"
    b"<AccessKeyId>EXPRESS_AKIDEXAMPLE</AccessKeyId>"
    b"<Expiration>2023-11-28T01:46:39Z</Expiration>"
    b"</Credentials></CreateSessionResult>"
)


@pytest.fixture
def default_s3_client():
    session = botocore.session.Session()
    return session.create_client(
        's3',
        'us-west-2',
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        aws_session_token=TOKEN,
    )


@pytest.fixture
def mock_datetime():
    with mock.patch('datetime.datetime', spec=True) as mock_datetime:
        yield mock_datetime


def _assert_expected_create_session_call(request, bucket):
    assert bucket in request.url
    assert request.url.endswith('?session')
    assert request.method == "GET"


class TestS3ExpressAuth:
    def _assert_has_expected_headers(self, request, header_list=None):
        if header_list is None:
            header_list = ["Authorization", "X-Amz-S3Session-Token"]

        for header in header_list:
            assert header in request.headers

    def test_s3express_auth_requires_instance_cache(self):
        assert hasattr(S3ExpressAuth, "REQUIRES_IDENTITY_CACHE")
        assert S3ExpressAuth.REQUIRES_IDENTITY_CACHE is True

    def test_s3_express_auth_headers(self):
        request = AWSRequest(
            method='GET',
            url=ENDPOINT,
        )
        auth_instance = S3ExpressAuth(
            CREDENTIALS, "s3", "us-west-2", identity_cache={}
        )

        # Confirm there is no existing auth info on request
        assert 'Authorization' not in request.headers
        auth_instance.add_auth(request)
        self._assert_has_expected_headers(request)

        # Confirm we're not including the unsupported X-Amz-Security-Token
        # header for S3Express.
        assert 'X-Amz-Security-Token' not in request.headers


class TestS3ExpressIdentityCache:
    def test_default_s3_express_cache(self, default_s3_client, mock_datetime):
        mock_datetime.now.return_value = DATE
        mock_datetime.utcnow.return_value = DATE

        identity_cache = S3ExpressIdentityCache(
            default_s3_client,
            RefreshableCredentials,
        )
        with ClientHTTPStubber(default_s3_client) as stubber:
            stubber.add_response(body=CREATE_SESSION_RESPONSE)
            credentials = identity_cache.get_credentials('my_bucket')

            assert credentials.access_key == EXPRESS_ACCESS_KEY
            assert credentials.secret_key == EXPRESS_SECRET_KEY
            assert credentials.token == EXPRESS_TOKEN

    def test_s3_express_cache_one_network_call(
        self, default_s3_client, mock_datetime
    ):
        mock_datetime.now.return_value = DATE
        mock_datetime.utcnow.return_value = DATE
        bucket = 'my_bucket'

        identity_cache = S3ExpressIdentityCache(
            default_s3_client,
            RefreshableCredentials,
        )
        with ClientHTTPStubber(default_s3_client) as stubber:
            # Only set one response
            stubber.add_response(body=CREATE_SESSION_RESPONSE)

            first_creds = identity_cache.get_credentials(bucket)
            second_creds = identity_cache.get_credentials(bucket)

            # Confirm we got back the same credentials
            assert first_creds == second_creds

            # Confirm we didn't hit the API twice
            assert len(stubber.requests) == 1
            _assert_expected_create_session_call(stubber.requests[0], bucket)

    def test_s3_express_cache_multiple_buckets(
        self, default_s3_client, mock_datetime
    ):
        mock_datetime.now.return_value = DATE
        mock_datetime.utcnow.return_value = DATE
        bucket = 'my_bucket'
        other_bucket = 'other_bucket'

        identity_cache = S3ExpressIdentityCache(
            default_s3_client,
            RefreshableCredentials,
        )
        with ClientHTTPStubber(default_s3_client) as stubber:
            stubber.add_response(body=CREATE_SESSION_RESPONSE)
            stubber.add_response(body=CREATE_SESSION_RESPONSE)

            identity_cache.get_credentials(bucket)
            identity_cache.get_credentials(other_bucket)

            # Confirm we hit the API for each bucket
            assert len(stubber.requests) == 2
            _assert_expected_create_session_call(stubber.requests[0], bucket)
            _assert_expected_create_session_call(
                stubber.requests[1], other_bucket
            )


class TestS3ExpressRequests:
    def _assert_standard_sigv4_signature(self, headers):
        sigv4_auth_preamble = (
            b'AWS4-HMAC-SHA256 Credential='
            b'AKIDEXAMPLE/20231126/us-west-2/s3express/aws4_request'
        )
        assert 'Authorization' in headers
        assert headers['Authorization'].startswith(sigv4_auth_preamble)

    def _assert_s3express_credentials(self, headers):
        s3express_auth_preamble = (
            b'AWS4-HMAC-SHA256 Credential='
            b'EXPRESS_AKIDEXAMPLE/20231126/us-west-2/s3express/aws4_request'
        )
        assert 'Authorization' in headers
        assert 'x-amz-s3session-token' in headers
        assert headers['Authorization'].startswith(s3express_auth_preamble)
        assert headers['x-amz-s3session-token'] == b'EXPRESS_TOKEN'

    def _assert_checksum_algorithm_added(self, algorithm, headers):
        algorithm_header_name = f"x-amz-checksum-{algorithm}"
        assert algorithm_header_name in headers

    def _call_get_object(self, client):
        return client.get_object(
            Bucket=S3EXPRESS_BUCKET,
            Key='my-test-object',
        )

    def test_create_bucket(self, default_s3_client, mock_datetime):
        mock_datetime.utcnow.return_value = DATE

        with ClientHTTPStubber(default_s3_client) as stubber:
            stubber.add_response()

            default_s3_client.create_bucket(
                Bucket=S3EXPRESS_BUCKET,
                CreateBucketConfiguration={
                    'Location': {
                        'Name': 'usw2-az5',
                        'Type': 'AvailabilityZone',
                    },
                    'Bucket': {
                        "DataRedundancy": "SingleAvailabilityZone",
                        "Type": "Directory",
                    },
                },
            )

        # Confirm we don't call CreateSession for create_bucket
        assert len(stubber.requests) == 1
        self._assert_standard_sigv4_signature(stubber.requests[0].headers)

    def test_get_object(self, default_s3_client, mock_datetime):
        mock_datetime.utcnow.return_value = DATE
        mock_datetime.now.return_value = DATE

        with ClientHTTPStubber(default_s3_client) as stubber:
            stubber.add_response(body=CREATE_SESSION_RESPONSE)
            stubber.add_response()

            self._call_get_object(default_s3_client)

        # Confirm we called CreateSession for create_bucket
        assert len(stubber.requests) == 2
        _assert_expected_create_session_call(
            stubber.requests[0], S3EXPRESS_BUCKET
        )
        self._assert_standard_sigv4_signature(stubber.requests[0].headers)

        # Confirm actual PutObject request was signed with Session credentials
        self._assert_s3express_credentials(stubber.requests[1].headers)

    def test_cache_with_multiple_requests(
        self, default_s3_client, mock_datetime
    ):
        mock_datetime.utcnow.return_value = DATE
        mock_datetime.now.return_value = DATE

        with ClientHTTPStubber(default_s3_client) as stubber:
            stubber.add_response(body=CREATE_SESSION_RESPONSE)
            stubber.add_response()
            stubber.add_response()

            self._call_get_object(default_s3_client)
            self._call_get_object(default_s3_client)

        # Confirm we called CreateSession for create_bucket once
        assert len(stubber.requests) == 3
        _assert_expected_create_session_call(
            stubber.requests[0], S3EXPRESS_BUCKET
        )
        self._assert_standard_sigv4_signature(stubber.requests[0].headers)

        # Confirm we signed both called with S3Express credentials
        self._assert_s3express_credentials(stubber.requests[1].headers)
        self._assert_s3express_credentials(stubber.requests[2].headers)

    def test_delete_objects_injects_correct_checksum(
        self, default_s3_client, mock_datetime
    ):
        mock_datetime.utcnow.return_value = DATE
        mock_datetime.now.return_value = DATE

        with ClientHTTPStubber(default_s3_client) as stubber:
            stubber.add_response(body=CREATE_SESSION_RESPONSE)
            stubber.add_response()

            default_s3_client.delete_objects(
                Bucket=S3EXPRESS_BUCKET,
                Delete={
                    "Objects": [
                        {
                            "Key": "my-obj",
                            "VersionId": "1",
                        }
                    ]
                },
            )

        # Confirm we called CreateSession for create_bucket
        assert len(stubber.requests) == 2
        _assert_expected_create_session_call(
            stubber.requests[0], S3EXPRESS_BUCKET
        )
        self._assert_standard_sigv4_signature(stubber.requests[0].headers)

        # Confirm we signed both called with S3Express credentials
        self._assert_s3express_credentials(stubber.requests[1].headers)
        self._assert_checksum_algorithm_added(
            'crc32', stubber.requests[1].headers
        )
