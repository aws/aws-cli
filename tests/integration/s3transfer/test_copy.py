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
from tests import RecordingSubscriber
from tests.integration import BaseTransferManagerIntegTest
from s3transfer.manager import TransferConfig


class TestCopy(BaseTransferManagerIntegTest):
    def setUp(self):
        super(TestCopy, self).setUp()
        self.multipart_threshold = 5 * 1024 * 1024
        self.config = TransferConfig(
            multipart_threshold=self.multipart_threshold)

    def test_copy_below_threshold(self):
        transfer_manager = self.create_transfer_manager(self.config)
        key = '1mb.txt'
        new_key = '1mb-copy.txt'

        filename = self.files.create_file_with_size(
            key, filesize=1024 * 1024)
        self.upload_file(filename, key)

        future = transfer_manager.copy(
            copy_source={'Bucket': self.bucket_name, 'Key': key},
            bucket=self.bucket_name,
            key=new_key
        )

        future.result()
        self.assertTrue(self.object_exists(new_key))

    def test_copy_above_threshold(self):
        transfer_manager = self.create_transfer_manager(self.config)
        key = '20mb.txt'
        new_key = '20mb-copy.txt'

        filename = self.files.create_file_with_size(
            key, filesize=20 * 1024 * 1024)
        self.upload_file(filename, key)

        future = transfer_manager.copy(
            copy_source={'Bucket': self.bucket_name, 'Key': key},
            bucket=self.bucket_name,
            key=new_key
        )

        future.result()
        self.assertTrue(self.object_exists(new_key))

    def test_progress_subscribers_on_copy(self):
        subscriber = RecordingSubscriber()
        transfer_manager = self.create_transfer_manager(self.config)
        key = '20mb.txt'
        new_key = '20mb-copy.txt'

        filename = self.files.create_file_with_size(
            key, filesize=20 * 1024 * 1024)
        self.upload_file(filename, key)

        future = transfer_manager.copy(
            copy_source={'Bucket': self.bucket_name, 'Key': key},
            bucket=self.bucket_name,
            key=new_key,
            subscribers=[subscriber]
        )

        future.result()
        # The callback should have been called enough times such that
        # the total amount of bytes we've seen (via the "amount"
        # arg to the callback function) should be the size
        # of the file we uploaded.
        self.assertEqual(subscriber.calculate_bytes_seen(), 20 * 1024 * 1024)
