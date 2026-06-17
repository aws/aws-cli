# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import os
from unittest import mock

import pytest
from dateutil.tz import tzutc

from botocore.config import Config
from tests import ClientHTTPStubber, temporary_file


class TestDisableS3ExpressAuth:
    DATE = datetime.datetime(2024, 11, 30, 23, 59, 59, tzinfo=tzutc())
    BUCKET_NAME = 'mybucket--usw2-az1--x-s3'

    CREATE_SESSION_RESPONSE = b'<?xml version="1.0" encoding="UTF-8"?>\n<CreateSessionResult><Credentials><AccessKeyId>test-key</AccessKeyId><Expiration>2024-12-31T23:59:59Z</Expiration><SecretAccessKey>test-secret</SecretAccessKey><SessionToken>test-token</SessionToken></Credentials></CreateSessionResult>'
    LIST_OBJECTS_RESPONSE = b'<?xml version="1.0" encoding="UTF-8"?>\n<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/"><Name>mybucket--usw2-az1--x-s3</Name><Prefix/><KeyCount>0</KeyCount><MaxKeys>1000</MaxKeys><EncodingType>url</EncodingType><IsTruncated>false</IsTruncated></ListBucketResult>'

    @pytest.fixture
    def mock_datetime(self):
        with mock.patch('datetime.datetime', spec=True) as mock_dt:
            mock_dt.now.return_value = self.DATE
            yield mock_dt

    def test_disable_s3_express_auth_enabled(
        self, patched_session, mock_datetime
    ):
        config = Config(s3={'disable_s3_express_session_auth': True})
        s3_client = patched_session.create_client(
            's3',
            config=config,
            region_name='us-west-2',
        )

        with ClientHTTPStubber(s3_client, strict=True) as stubber:
            stubber.add_response(body=self.LIST_OBJECTS_RESPONSE)
            s3_client.list_objects_v2(Bucket=self.BUCKET_NAME)

        assert len(stubber.requests) == 1

    def test_disable_s3_express_auth_enabled_env_var(
        self, patched_session, mock_datetime
    ):
        env = {'AWS_S3_DISABLE_EXPRESS_SESSION_AUTH': 'true'}
        with mock.patch.dict(os.environ, env):
            s3_client = patched_session.create_client(
                's3',
                region_name='us-west-2',
            )

            with ClientHTTPStubber(s3_client, strict=True) as stubber:
                stubber.add_response(body=self.LIST_OBJECTS_RESPONSE)
                s3_client.list_objects_v2(Bucket=self.BUCKET_NAME)

            assert len(stubber.requests) == 1

    def test_disable_s3_express_auth_enabled_shared_config(
        self, patched_session, mock_datetime
    ):
        with temporary_file('w') as f:
            f.write('[default]\n')
            f.write('s3_disable_express_session_auth = true\n')
            f.flush()

            with mock.patch.dict(os.environ, {'AWS_CONFIG_FILE': f.name}):
                s3_client = patched_session.create_client(
                    's3',
                    region_name='us-west-2',
                )

                with ClientHTTPStubber(s3_client, strict=True) as stubber:
                    stubber.add_response(body=self.LIST_OBJECTS_RESPONSE)
                    s3_client.list_objects_v2(Bucket=self.BUCKET_NAME)

                assert len(stubber.requests) == 1

    def test_disable_s3_express_auth_disabled(
        self, patched_session, mock_datetime
    ):
        config = Config(s3={'disable_s3_express_session_auth': False})
        s3_client = patched_session.create_client(
            's3',
            config=config,
            region_name='us-west-2',
        )

        with ClientHTTPStubber(s3_client, strict=True) as stubber:
            stubber.add_response(body=self.CREATE_SESSION_RESPONSE)
            stubber.add_response(body=self.LIST_OBJECTS_RESPONSE)
            s3_client.list_objects_v2(Bucket=self.BUCKET_NAME)

        assert len(stubber.requests) == 2
