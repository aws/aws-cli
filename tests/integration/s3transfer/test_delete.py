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
from tests.integration.s3transfer import BaseTransferManagerIntegTest


class TestDeleteObject(BaseTransferManagerIntegTest):
    def test_can_delete_object(self):
        key_name = 'mykey'
        self.client.put_object(
            Bucket=self.bucket_name, Key=key_name, Body=b'hello world'
        )
        self.assertTrue(self.object_exists(key_name))

        transfer_manager = self.create_transfer_manager()
        future = transfer_manager.delete(bucket=self.bucket_name, key=key_name)
        future.result()

        self.assertTrue(self.object_not_exists(key_name))


class TestBatchDeleteObject(BaseTransferManagerIntegTest):
    def test_can_delete_versioned_objects(self):
        key_name = 'mykey'
        self.client.put_object(
            Bucket=self.bucket_name, Key=key_name, Body=b'hello world'
        )
        response = self.client.list_object_versions(Bucket=self.bucket_name)
        version_id = response['Versions'][0]['VersionId']
        objects = [{'Key': key_name, 'VersionId': version_id}]
        transfer_manager = self.create_transfer_manager()
        future = transfer_manager.batch_delete(
            bucket=self.bucket_name, objects=objects
        )

        future.result()

        self.assertTrue(self.object_not_exists(key_name))
