# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import os
import shutil
import tempfile

from urllib3.exceptions import LocationParseError

from botocore.exceptions import (
    ConnectionClosedError,
    HTTPClientError,
    InvalidIMDSEndpointError,
)
from botocore.utils import FileWebIdentityTokenLoader, InstanceMetadataFetcher
from tests import mock, unittest


class TestFileWebIdentityTokenLoader(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.tempdir = tempfile.mkdtemp()
        self.token = 'totally.a.token'
        self.token_file = os.path.join(self.tempdir, 'token.jwt')
        self.write_token(self.token)

    def tearDown(self):
        shutil.rmtree(self.tempdir)
        super().tearDown()

    def write_token(self, token, path=None):
        if path is None:
            path = self.token_file
        with open(path, 'w') as f:
            f.write(token)

    def test_can_load_token(self):
        loader = FileWebIdentityTokenLoader(self.token_file)
        token = loader()
        self.assertEqual(self.token, token)


class TestInstanceMetadataFetcher(unittest.TestCase):
    def test_catch_retryable_http_errors(self):
        with mock.patch(
            'botocore.httpsession.URLLib3Session.send'
        ) as send_mock:
            fetcher = InstanceMetadataFetcher()
            send_mock.side_effect = ConnectionClosedError(endpoint_url="foo")
            creds = fetcher.retrieve_iam_role_credentials()
        self.assertEqual(send_mock.call_count, 2)
        for call_instance in send_mock.call_args_list:
            self.assertTrue(
                call_instance[0][0].url.startswith(fetcher.get_base_url())
            )
        self.assertEqual(creds, {})

    def test_catch_invalid_imds_error(self):
        with mock.patch(
            'botocore.httpsession.URLLib3Session.send'
        ) as send_mock:
            fetcher = InstanceMetadataFetcher()
            e = LocationParseError(location="foo")
            send_mock.side_effect = HTTPClientError(error=e)
            with self.assertRaises(InvalidIMDSEndpointError):
                fetcher.retrieve_iam_role_credentials()
