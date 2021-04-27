# Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscrt.s3 import S3RequestType

from tests.functional.s3 import (
    BaseS3TransferCommandTest, BaseCRTTransferClientTest
)


class TestRmCommand(BaseS3TransferCommandTest):
    prefix = 's3 rm'

    def test_operations_used(self):
        cmdline = '%s s3://bucket/key.txt' % self.prefix
        self.run_cmd(cmdline, expected_rc=0)
        # The only operation we should have called is DeleteObject.
        self.assertEqual(
            len(self.operations_called), 1, self.operations_called)
        self.assertEqual(self.operations_called[0][0].name, 'DeleteObject')

    def test_dryrun_delete(self):
        self.parsed_responses = [self.head_object_response()]
        cmdline = (
            f'{self.prefix} s3://bucket/key.txt --dryrun'
        )
        stdout, _, _ = self.run_cmd(cmdline, expected_rc=0)
        self.assert_operations_called([])
        self.assertIn(
            '(dryrun) delete: s3://bucket/key.txt',
            stdout
        )

    def test_delete_with_request_payer(self):
        cmdline = '%s s3://mybucket/mykey --request-payer' % self.prefix
        self.run_cmd(cmdline, expected_rc=0)
        self.assert_operations_called(
            [
                ('DeleteObject', {
                    'Bucket': 'mybucket',
                    'Key': 'mykey',
                    'RequestPayer': 'requester'
                })
            ]

        )

    def test_recursive_delete_with_requests(self):
        cmdline = '%s s3://mybucket/ --recursive --request-payer' % self.prefix
        self.parsed_responses = [
            self.list_objects_response(['mykey']),
            self.empty_response(),
        ]
        self.run_cmd(cmdline, expected_rc=0)
        self.assert_operations_called(
            [
                self.list_objects_request(
                    'mybucket', RequestPayer='requester'),
                self.delete_object_request(
                    'mybucket', 'mykey', RequestPayer='requester'),
            ]

        )


class TestRmWithCRTClient(BaseCRTTransferClientTest):
    def test_delete_using_crt_client(self):
        cmdline = [
            's3', 'rm', 's3://bucket/key'
        ]
        self.run_command(cmdline)
        crt_requests = self.get_crt_make_request_calls()
        self.assertEqual(len(crt_requests), 1)
        self.assert_crt_make_request_call(
            crt_requests[0],
            expected_type=S3RequestType.DEFAULT,
            expected_host=self.get_virtual_s3_host('bucket'),
            expected_path='/key',
            expected_http_method='DELETE'
        )

    def test_recursive_delete_using_crt_client(self):
        cmdline = [
            's3', 'rm', 's3://bucket/', '--recursive'
        ]
        self.add_botocore_list_objects_response(['key1', 'key2'])
        self.run_command(cmdline)
        crt_requests = self.get_crt_make_request_calls()
        self.assertEqual(len(crt_requests), 2)
        self.assert_crt_make_request_call(
            crt_requests[0],
            expected_type=S3RequestType.DEFAULT,
            expected_host=self.get_virtual_s3_host('bucket'),
            expected_path='/key1',
            expected_http_method='DELETE'
        )
        self.assert_crt_make_request_call(
            crt_requests[1],
            expected_type=S3RequestType.DEFAULT,
            expected_host=self.get_virtual_s3_host('bucket'),
            expected_path='/key2',
            expected_http_method='DELETE'
        )
