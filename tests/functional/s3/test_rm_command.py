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
from tests.functional.s3 import BaseS3TransferCommandTest


class TestRmCommand(BaseS3TransferCommandTest):
    prefix = 's3 rm'

    def test_operations_used(self):
        cmdline = '%s s3://bucket/key.txt' % self.prefix
        self.run_cmd(cmdline, expected_rc=0)
        # The only operation we should have called is DeleteObject.
        self.assertEqual(
            len(self.operations_called), 1, self.operations_called)
        self.assertEqual(self.operations_called[0][0].name, 'DeleteObject')

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
            {
                'Contents': [
                    {'Key': 'mykey',
                     'LastModified': '00:00:00Z',
                     'Size': 100},
                ],
                'CommonPrefixes': []
            },
            {},
        ]

        self.run_cmd(cmdline, expected_rc=0)
        self.assert_operations_called(
            [
                ('ListObjectsV2', {
                    'Bucket': 'mybucket',
                    'Prefix': '',
                    'EncodingType': 'url',
                    'RequestPayer': 'requester'
                }),
                ('DeleteObject', {
                    'Bucket': 'mybucket',
                    'Key': 'mykey',
                    'RequestPayer': 'requester'
                })
            ]

        )
