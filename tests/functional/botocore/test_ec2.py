# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from tests import mock, unittest, ClientHTTPStubber, BaseSessionTest
from botocore.compat import parse_qs, urlparse
from botocore.stub import Stubber, ANY
import botocore.session


class TestIdempotencyToken(unittest.TestCase):
    def setUp(self):
        self.function_name = 'purchase_scheduled_instances'
        self.region = 'us-west-2'
        self.session = botocore.session.get_session()
        self.client = self.session.create_client(
            'ec2', self.region)
        self.stubber = Stubber(self.client)
        self.service_response = {}
        self.params_seen = []

        # Record all the parameters that get seen
        self.client.meta.events.register_first(
            'before-call.*.*',
            self.collect_params,
            unique_id='TestIdempotencyToken')

    def collect_params(self, model, params, *args, **kwargs):
        self.params_seen.extend(params['body'].keys())

    def test_provided_idempotency_token(self):
        expected_params = {
            'PurchaseRequests': [
                {'PurchaseToken': 'foo',
                 'InstanceCount': 123}],
            'ClientToken': ANY
        }
        self.stubber.add_response(
            self.function_name, self.service_response, expected_params)

        with self.stubber:
            self.client.purchase_scheduled_instances(
                PurchaseRequests=[{'PurchaseToken': 'foo',
                                   'InstanceCount': 123}],
                ClientToken='foobar')
            self.assertIn('ClientToken', self.params_seen)

    def test_insert_idempotency_token(self):
        expected_params = {
            'PurchaseRequests': [
                {'PurchaseToken': 'foo',
                 'InstanceCount': 123}],
        }

        self.stubber.add_response(
            self.function_name, self.service_response, expected_params)

        with self.stubber:
            self.client.purchase_scheduled_instances(
                PurchaseRequests=[{'PurchaseToken': 'foo',
                                   'InstanceCount': 123}])
            self.assertIn('ClientToken', self.params_seen)


class TestCopySnapshotCustomization(BaseSessionTest):
    def setUp(self):
        super(TestCopySnapshotCustomization, self).setUp()
        self.session = botocore.session.get_session()
        self.client = self.session.create_client('ec2', 'us-east-1')
        self.http_stubber = ClientHTTPStubber(self.client)
        self.snapshot_id = 'snap-0123abc'
        self.copy_response = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<CopySnapshotResponse>\n'
            '<snapshotId>%s</snapshotId>\n'
            '</CopySnapshotResponse>\n'
        )
        self.now = datetime.datetime(2011, 9, 9, 23, 36)
        self.datetime_patch = mock.patch.object(
            botocore.auth.datetime, 'datetime',
            mock.Mock(wraps=datetime.datetime)
        )
        self.mocked_datetime = self.datetime_patch.start()
        self.mocked_datetime.utcnow.return_value = self.now

    def tearDown(self):
        super(TestCopySnapshotCustomization, self).tearDown()
        self.datetime_patch.stop()

    def add_copy_snapshot_response(self, snapshot_id):
        body = (self.copy_response % snapshot_id).encode('utf-8')
        self.http_stubber.add_response(body=body)

    def test_copy_snapshot_injects_presigned_url(self):
        self.add_copy_snapshot_response(self.snapshot_id)
        with self.http_stubber:
            result = self.client.copy_snapshot(
                SourceRegion='us-west-2',
                SourceSnapshotId=self.snapshot_id,
            )
        self.assertEqual(result['SnapshotId'], self.snapshot_id)
        self.assertEqual(len(self.http_stubber.requests), 1)
        snapshot_request = self.http_stubber.requests[0]
        body = parse_qs(snapshot_request.body)
        self.assertIn('PresignedUrl', body)
        presigned_url = urlparse(body['PresignedUrl'][0])
        self.assertEqual(presigned_url.scheme, 'https')
        self.assertEqual(presigned_url.netloc, 'ec2.us-west-2.amazonaws.com')
        query_args = parse_qs(presigned_url.query)
        self.assertEqual(query_args['Action'], ['CopySnapshot'])
        self.assertEqual(query_args['Version'], ['2016-11-15'])
        self.assertEqual(query_args['SourceRegion'], ['us-west-2'])
        self.assertEqual(query_args['DestinationRegion'], ['us-east-1'])
        self.assertEqual(query_args['SourceSnapshotId'], [self.snapshot_id])
        self.assertEqual(query_args['X-Amz-Algorithm'], ['AWS4-HMAC-SHA256'])
        expected_credential = 'access_key/20110909/us-west-2/ec2/aws4_request'
        self.assertEqual(query_args['X-Amz-Credential'], [expected_credential])
        self.assertEqual(query_args['X-Amz-Date'], ['20110909T233600Z'])
        self.assertEqual(query_args['X-Amz-Expires'], ['3600'])
        self.assertEqual(query_args['X-Amz-SignedHeaders'], ['host'])
        expected_signature = (
            'a94a6b52afdf3daa34c2e2a38a62b72c8dac129c9904c61aa1a5d86e38628537'
        )
        self.assertEqual(query_args['X-Amz-Signature'], [expected_signature])
