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

from tests import BaseSessionTest, ClientHTTPStubber


class BaseSQSOperationTest(BaseSessionTest):
    def setUp(self):
        super().setUp()
        self.region = "us-west-2"
        self.client = self.session.create_client("sqs", self.region)
        self.http_stubber = ClientHTTPStubber(self.client)


class SQSQueryCompatibleTest(BaseSQSOperationTest):
    def test_query_compatibility_mode_header_sent(self):
        with self.http_stubber as stub:
            stub.add_response()
            self.client.delete_queue(QueueUrl="not-a-real-queue-botocore")
            request = self.http_stubber.requests[0]
            assert 'x-amzn-query-mode' in request.headers
            assert request.headers['x-amzn-query-mode'] == b'true'
