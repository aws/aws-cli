# Copyright 2012-2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import json
import time
from base64 import b64decode
from uuid import uuid4
from tests import unittest, BaseSessionTest, ClientHTTPStubber


class TestKinesisListStreams(BaseSessionTest):
    def setUp(self):
        super(TestKinesisListStreams, self).setUp()
        self.stream_name = "kinesis-test-stream"
        self.region = "us-east-1"
        self.client = self.session.create_client("kinesis", self.region)
        self.http_stubber = ClientHTTPStubber(self.client)
        self.http_stubber.add_response()

    def assert_base64encoded_str_equals(self, encoded_str, expected_value):
        """Validate a value can be base64 decoded and equals expected value"""
        try:
            decoded_str = b64decode(encoded_str).decode("utf-8")
        except UnicodeDecodeError:
            self.fail("Base64 encoded record is not a valid utf-8 string")
        self.assertEqual(decoded_str, expected_value)

    def test_can_put_stream_blob(self):
        unique_data = str(uuid4())
        with self.http_stubber as stub:
            self.client.put_record(
                StreamName=self.stream_name, PartitionKey="foo", Data=unique_data
            )
            self.assertEqual(len(stub.requests), 1)
            request = json.loads(stub.requests[0].body.decode("utf-8"))
            self.assertEqual(request["StreamName"], self.stream_name)
            self.assertEqual(request["PartitionKey"], "foo")
            self.assert_base64encoded_str_equals(
                request["Data"], unique_data
            )

    def test_can_put_records_single_blob(self):
        unique_data = str(uuid4())
        with self.http_stubber as stub:
            self.client.put_records(
                StreamName=self.stream_name,
                Records=[{"Data": unique_data, "PartitionKey": "foo"}],
            )
            self.assertEqual(len(stub.requests), 1)
            request = json.loads(stub.requests[0].body.decode("utf-8"))
            self.assertEqual(len(request["Records"]), 1)
            self.assertEqual(request["StreamName"], self.stream_name)

            record = request["Records"][0]
            self.assertEqual(record["PartitionKey"], "foo")
            self.assert_base64encoded_str_equals(
                record["Data"], unique_data
            )

    def test_can_put_records_multiple_blob(self):
        with self.http_stubber as stub:
            self.client.put_records(
                StreamName=self.stream_name,
                Records=[
                    {"Data": "foobar", "PartitionKey": "foo"},
                    {"Data": "barfoo", "PartitionKey": "foo"},
                ],
            )
            self.assertEqual(len(stub.requests), 1)
            request = json.loads(stub.requests[0].body.decode("utf-8"))
            self.assertEqual(len(request["Records"]), 2)

            record_foobar = request["Records"][0]
            record_barfoo = request["Records"][1]
            self.assert_base64encoded_str_equals(
                record_foobar["Data"], "foobar"
            )
            self.assert_base64encoded_str_equals(
                record_barfoo["Data"], "barfoo"
            )
