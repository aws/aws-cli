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
from botocore.stub import Stubber
from tests import BaseSessionTest, ClientHTTPStubber


class TestRDSPresignUrlInjection(BaseSessionTest):
    def setUp(self):
        super().setUp()
        self.client = self.session.create_client('rds', 'us-west-2')
        self.http_stubber = ClientHTTPStubber(self.client)

    def assert_presigned_url_injected_in_request(self, body):
        self.assertIn('PreSignedUrl', body)
        self.assertNotIn('SourceRegion', body)

    def test_copy_snapshot(self):
        params = {
            'SourceDBSnapshotIdentifier': 'source-db',
            'TargetDBSnapshotIdentifier': 'target-db',
            'SourceRegion': 'us-east-1',
        }
        response_body = (
            b'<CopyDBSnapshotResponse>'
            b'<CopyDBSnapshotResult></CopyDBSnapshotResult>'
            b'</CopyDBSnapshotResponse>'
        )
        self.http_stubber.add_response(body=response_body)
        with self.http_stubber:
            self.client.copy_db_snapshot(**params)
            sent_request = self.http_stubber.requests[0]
            self.assert_presigned_url_injected_in_request(sent_request.body)

    def test_create_db_instance_read_replica(self):
        params = {
            'SourceDBInstanceIdentifier': 'source-db',
            'DBInstanceIdentifier': 'target-db',
            'SourceRegion': 'us-east-1',
        }
        response_body = (
            b'<CreateDBInstanceReadReplicaResponse>'
            b'<CreateDBInstanceReadReplicaResult>'
            b'</CreateDBInstanceReadReplicaResult>'
            b'</CreateDBInstanceReadReplicaResponse>'
        )
        self.http_stubber.add_response(body=response_body)
        with self.http_stubber:
            self.client.create_db_instance_read_replica(**params)
            sent_request = self.http_stubber.requests[0]
            self.assert_presigned_url_injected_in_request(sent_request.body)

    def test_start_db_instance_automated_backups_replication(self):
        params = {
            'SourceDBInstanceArn': 'arn:aws:rds:us-east-1:123456789012:db:source-db-instance',
            'SourceRegion': 'us-east-1',
        }
        response_body = (
            b'<StartDBInstanceAutomatedBackupsReplicationResponse>'
            b'<StartDBInstanceAutomatedBackupsReplicationResult>'
            b'</StartDBInstanceAutomatedBackupsReplicationResult>'
            b'</StartDBInstanceAutomatedBackupsReplicationResponse>'
        )
        self.http_stubber.add_response(body=response_body)
        with self.http_stubber:
            self.client.start_db_instance_automated_backups_replication(
                **params
            )
            sent_request = self.http_stubber.requests[0]
            self.assert_presigned_url_injected_in_request(sent_request.body)


class TestRDS(BaseSessionTest):
    def setUp(self):
        super().setUp()
        self.client = self.session.create_client('rds', 'us-west-2')
        self.stubber = Stubber(self.client)
        self.stubber.activate()

    def test_generate_db_auth_token(self):
        hostname = 'host.us-east-1.rds.amazonaws.com'
        port = 3306
        username = 'mySQLUser'
        auth_token = self.client.generate_db_auth_token(
            DBHostname=hostname, Port=port, DBUsername=username
        )

        endpoint_url = 'host.us-east-1.rds.amazonaws.com:3306'
        self.assertIn(endpoint_url, auth_token)
        self.assertIn('Action=connect', auth_token)

        # Asserts that there is no scheme in the url
        self.assertTrue(auth_token.startswith(hostname))
