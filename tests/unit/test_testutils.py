# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import mock

from awscli.testutils import create_bucket
from awscli.testutils import BaseCLIDriverTest


class TestCreateBucket(BaseCLIDriverTest):
    def test_bucket_already_owned_by_you(self):
        # TODO: fix this patch when we have a better way to stub out responses
        with mock.patch('botocore.endpoint.Endpoint._send') as _send:
            _send.side_effect = [
                mock.Mock(status_code=500, headers={}, content=b''),
                mock.Mock(
                    status_code=409, headers={},
                    content=b'''<?xml version="1.0" encoding="UTF-8"?>
                        <Error>
                        <Code>BucketAlreadyOwnedByYou</Code>
                        <Message>Your previous request to create the named
                            bucket succeeded and you already own it.</Message>
                        <BucketName>awscli-foo-bar</BucketName>
                        <RequestId>0123456789ABCDEF</RequestId>
                        <HostId>foo</HostId>
                        </Error>'''),
                ]
            self.assertEqual(create_bucket(self.session, 'bucket'), 'bucket')
