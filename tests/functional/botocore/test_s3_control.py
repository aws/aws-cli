# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from tests import unittest, mock, BaseSessionTest, create_session

from botocore.config import Config
from botocore.awsrequest import AWSResponse


class S3ControlOperationTest(BaseSessionTest):
    def setUp(self):
        super(S3ControlOperationTest, self).setUp()
        self.region = 'us-west-2'
        self.client = self.session.create_client(
            's3control', self.region)
        self.session_send_patch = mock.patch(
            'botocore.endpoint.Endpoint._send')
        self.http_session_send_mock = self.session_send_patch.start()
        self.http_response = mock.Mock(spec=AWSResponse)
        self.http_response.status_code = 200
        self.http_response.headers = {}
        self.http_response.content = ''
        self.http_session_send_mock.return_value = self.http_response

    def tearDown(self):
        super(BaseSessionTest, self).tearDown()
        self.session_send_patch.stop()

    def test_does_add_account_id_to_host(self):
        self.client.get_public_access_block(AccountId='123')
        self.assertEqual(self.http_session_send_mock.call_count, 1)
        request = self.http_session_send_mock.call_args_list[0][0][0]

        self.assertTrue(request.url.startswith(
            'https://123.s3-control.us-west-2.amazonaws.com'))

    def test_does_not_remove_account_id_from_headers(self):
        self.client.get_public_access_block(AccountId='123')
        self.assertEqual(self.http_session_send_mock.call_count, 1)
        request = self.http_session_send_mock.call_args_list[0][0][0]

        self.assertIn('x-amz-account-id', request.headers)

    def test_does_support_dualstack_endpoint(self):
        # Re-create the client with the use_dualstack_endpoint configuration
        # option set to True.
        self.client = self.session.create_client(
            's3control', self.region, config=Config(
                s3={'use_dualstack_endpoint': True}
            )
        )
        self.client.get_public_access_block(AccountId='123')

        self.assertEqual(self.http_session_send_mock.call_count, 1)
        request = self.http_session_send_mock.call_args_list[0][0][0]
        self.assertTrue(request.url.startswith(
            'https://123.s3-control.dualstack.us-west-2.amazonaws.com'))
