# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the 'License'). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the 'license' file accompanying this file. This file is
# distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import botocore
import botocore.session
from botocore.exceptions import WaiterError
from s3transfer.manager import TransferManager
from s3transfer.subscribers import BaseSubscriber

from tests import FileCreator, S3Utils, random_bucket_name, unittest


class BaseTransferManagerIntegTest(unittest.TestCase):
    """Tests for the high level s3transfer module."""

    @classmethod
    def setUpClass(cls):
        cls.region = 'us-west-2'
        cls.session = botocore.session.get_session()
        cls.client = cls.session.create_client('s3', cls.region)
        cls.bucket_name = random_bucket_name()
        cls.s3_utils = S3Utils(cls.session, cls.region)
        cls.s3_utils.create_bucket(cls.bucket_name)

    def setUp(self):
        self.files = FileCreator()

    def tearDown(self):
        self.files.remove_all()

    @classmethod
    def tearDownClass(cls):
        cls.s3_utils.delete_bucket(cls.bucket_name)

    def create_client(self, **override_kwargs):
        kwargs = {'region_name': self.region}
        kwargs.update(override_kwargs)
        return self.session.create_client('s3', **kwargs)

    def delete_object(self, key):
        self.client.delete_object(Bucket=self.bucket_name, Key=key)

    def object_exists(self, key, extra_args=None):
        try:
            self.wait_object_exists(key, extra_args)
            return True
        except WaiterError:
            return False

    def object_not_exists(self, key, extra_args=None):
        if extra_args is None:
            extra_args = {}
        try:
            self.client.get_waiter('object_not_exists').wait(
                Bucket=self.bucket_name, Key=key, **extra_args
            )
            return True
        except WaiterError:
            return False

    def wait_object_exists(self, key, extra_args=None):
        if extra_args is None:
            extra_args = {}
        for _ in range(5):
            self.client.get_waiter('object_exists').wait(
                Bucket=self.bucket_name, Key=key, **extra_args
            )

    def create_transfer_manager(self, config=None, client=None):
        if client is None:
            client = self.client
        return TransferManager(client, config=config)

    def upload_file(self, filename, key, extra_args=None):
        transfer = self.create_transfer_manager()
        with open(filename, 'rb') as f:
            transfer.upload(f, self.bucket_name, key, extra_args)
            self.wait_object_exists(key, extra_args)
            self.addCleanup(self.delete_object, key)


class WaitForTransferStart(BaseSubscriber):
    def __init__(self, bytes_transfer_started_event):
        self._bytes_transfer_started_event = bytes_transfer_started_event

    def on_progress(self, **kwargs):
        if not self._bytes_transfer_started_event.is_set():
            self._bytes_transfer_started_event.set()
