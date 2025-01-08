# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import glob
import io
import os
from uuid import uuid4

from botocore.exceptions import ClientError

from s3transfer.subscribers import BaseSubscriber
from s3transfer.utils import OSUtils
from tests import (
    HAS_CRT,
    NonSeekableReader,
    NonSeekableWriter,
    assert_files_equal,
    requires_crt,
)
from tests.integration.s3transfer import BaseTransferManagerIntegTest

if HAS_CRT:
    from awscrt.exceptions import AwsCrtError

    import s3transfer.crt


class RecordingSubscriber(BaseSubscriber):
    def __init__(self):
        self.on_queued_called = False
        self.on_done_called = False
        self.bytes_transferred = 0

    def on_queued(self, **kwargs):
        self.on_queued_called = True

    def on_progress(self, future, bytes_transferred, **kwargs):
        self.bytes_transferred += bytes_transferred

    def on_done(self, **kwargs):
        self.on_done_called = True


@requires_crt
class TestCRTS3Transfers(BaseTransferManagerIntegTest):
    """Tests for the high level s3transfer based on CRT implementation."""

    def setUp(self):
        super().setUp()
        self.s3_key = 's3key.txt'
        self.download_path = os.path.join(self.files.rootdir, 'download.txt')

    def _create_s3_transfer(self):
        self.request_serializer = s3transfer.crt.BotocoreCRTRequestSerializer(
            self.session, client_kwargs={'region_name': self.region}
        )
        self.s3_crt_client = s3transfer.crt.create_s3_crt_client(
            self.region, self._get_crt_credentials_provider()
        )
        self.record_subscriber = RecordingSubscriber()
        self.osutil = OSUtils()
        return s3transfer.crt.CRTTransferManager(
            self.s3_crt_client, self.request_serializer
        )

    def _get_crt_credentials_provider(self):
        botocore_credentials = self.session.get_credentials()
        wrapper = s3transfer.crt.BotocoreCRTCredentialsWrapper(
            botocore_credentials
        )
        return wrapper.to_crt_credentials_provider()

    def _upload_with_crt_transfer_manager(self, fileobj, key=None):
        if key is None:
            key = self.s3_key
        self.addCleanup(self.delete_object, key)
        with self._create_s3_transfer() as transfer:
            future = transfer.upload(
                fileobj,
                self.bucket_name,
                key,
                subscribers=[self.record_subscriber],
            )
            future.result()

    def _download_with_crt_transfer_manager(self, fileobj, key=None):
        if key is None:
            key = self.s3_key
        self.addCleanup(self.delete_object, key)
        with self._create_s3_transfer() as transfer:
            future = transfer.download(
                self.bucket_name,
                key,
                fileobj,
                subscribers=[self.record_subscriber],
            )
            future.result()

    def _assert_expected_s3_object(self, key, expected_size=None):
        self.assertTrue(self.object_exists(key))
        if expected_size is not None:
            response = self.client.head_object(
                Bucket=self.bucket_name, Key=key
            )
            self.assertEqual(response['ContentLength'], expected_size)

    def _assert_has_public_read_acl(self, response):
        grants = response['Grants']
        public_read = [
            g['Grantee'].get('URI', '')
            for g in grants
            if g['Permission'] == 'READ'
        ]
        self.assertIn('groups/global/AllUsers', public_read[0])

    def _assert_subscribers_called(self, expected_bytes_transferred=None):
        self.assertTrue(self.record_subscriber.on_queued_called)
        self.assertTrue(self.record_subscriber.on_done_called)
        if expected_bytes_transferred:
            self.assertEqual(
                self.record_subscriber.bytes_transferred,
                expected_bytes_transferred,
            )

    def test_upload_below_multipart_chunksize(self):
        transfer = self._create_s3_transfer()
        file_size = 1024 * 1024
        filename = self.files.create_file_with_size(
            'foo.txt', filesize=file_size
        )
        self.addCleanup(self.delete_object, 'foo.txt')

        with transfer:
            future = transfer.upload(
                filename,
                self.bucket_name,
                'foo.txt',
                subscribers=[self.record_subscriber],
            )
            future.result()

        self.assertTrue(self.object_exists('foo.txt'))
        self._assert_subscribers_called(file_size)

    def test_upload_above_multipart_chunksize(self):
        transfer = self._create_s3_transfer()
        file_size = 20 * 1024 * 1024
        filename = self.files.create_file_with_size(
            '20mb.txt', filesize=file_size
        )
        self.addCleanup(self.delete_object, '20mb.txt')

        with transfer:
            future = transfer.upload(
                filename,
                self.bucket_name,
                '20mb.txt',
                subscribers=[self.record_subscriber],
            )
            future.result()
        self.assertTrue(self.object_exists('20mb.txt'))
        self._assert_subscribers_called(file_size)

    def test_upload_file_above_threshold_with_acl(self):
        transfer = self._create_s3_transfer()
        file_size = 6 * 1024 * 1024
        filename = self.files.create_file_with_size(
            '6mb.txt', filesize=file_size
        )
        extra_args = {'ACL': 'public-read'}
        self.addCleanup(self.delete_object, '6mb.txt')

        with transfer:
            future = transfer.upload(
                filename,
                self.bucket_name,
                '6mb.txt',
                extra_args=extra_args,
                subscribers=[self.record_subscriber],
            )
            future.result()

        self.assertTrue(self.object_exists('6mb.txt'))
        response = self.client.get_object_acl(
            Bucket=self.bucket_name, Key='6mb.txt'
        )
        self._assert_has_public_read_acl(response)
        self._assert_subscribers_called(file_size)

    def test_upload_file_above_threshold_with_ssec(self):
        key_bytes = os.urandom(32)
        extra_args = {
            'SSECustomerKey': key_bytes,
            'SSECustomerAlgorithm': 'AES256',
        }
        file_size = 6 * 1024 * 1024
        transfer = self._create_s3_transfer()
        filename = self.files.create_file_with_size(
            '6mb.txt', filesize=file_size
        )
        self.addCleanup(self.delete_object, '6mb.txt')
        with transfer:
            future = transfer.upload(
                filename,
                self.bucket_name,
                '6mb.txt',
                extra_args=extra_args,
                subscribers=[self.record_subscriber],
            )
            future.result()
        # A head object will fail if it has a customer key
        # associated with it and it's not provided in the HeadObject
        # request so we can use this to verify our functionality.
        oringal_extra_args = {
            'SSECustomerKey': key_bytes,
            'SSECustomerAlgorithm': 'AES256',
        }
        self.wait_object_exists('6mb.txt', oringal_extra_args)
        response = self.client.head_object(
            Bucket=self.bucket_name, Key='6mb.txt', **oringal_extra_args
        )
        self.assertEqual(response['SSECustomerAlgorithm'], 'AES256')
        self._assert_subscribers_called(file_size)

    def test_upload_seekable_stream(self):
        size = 1024 * 1024
        self._upload_with_crt_transfer_manager(io.BytesIO(b'0' * size))
        self._assert_expected_s3_object(self.s3_key, expected_size=size)
        self._assert_subscribers_called(size)

    def test_multipart_upload_seekable_stream(self):
        size = 20 * 1024 * 1024
        self._upload_with_crt_transfer_manager(io.BytesIO(b'0' * size))
        self._assert_expected_s3_object(self.s3_key, expected_size=size)
        self._assert_subscribers_called(size)

    def test_upload_nonseekable_stream(self):
        size = 1024 * 1024
        self._upload_with_crt_transfer_manager(NonSeekableReader(b'0' * size))
        self._assert_expected_s3_object(self.s3_key, expected_size=size)
        self._assert_subscribers_called(size)

    def test_multipart_upload_nonseekable_stream(self):
        size = 20 * 1024 * 1024
        self._upload_with_crt_transfer_manager(NonSeekableReader(b'0' * size))
        self._assert_expected_s3_object(self.s3_key, expected_size=size)
        self._assert_subscribers_called(size)

    def test_upload_empty_file(self):
        size = 0
        filename = self.files.create_file_with_size(self.s3_key, filesize=size)
        self._upload_with_crt_transfer_manager(filename)
        self._assert_expected_s3_object(self.s3_key, expected_size=size)
        self._assert_subscribers_called(size)

    def test_upload_empty_stream(self):
        size = 0
        self._upload_with_crt_transfer_manager(io.BytesIO(b''))
        self._assert_expected_s3_object(self.s3_key, expected_size=size)
        self._assert_subscribers_called(size)

    def test_can_send_extra_params_on_download(self):
        # We're picking the customer provided sse feature
        # of S3 to test the extra_args functionality of
        # S3.
        key_bytes = os.urandom(32)
        extra_args = {
            'SSECustomerKey': key_bytes,
            'SSECustomerAlgorithm': 'AES256',
        }
        filename = self.files.create_file('foo.txt', 'hello world')
        self.upload_file(filename, 'foo.txt', extra_args)
        transfer = self._create_s3_transfer()

        download_path = os.path.join(self.files.rootdir, 'downloaded.txt')
        with transfer:
            future = transfer.download(
                self.bucket_name,
                'foo.txt',
                download_path,
                extra_args=extra_args,
                subscribers=[self.record_subscriber],
            )
            future.result()
        file_size = self.osutil.get_file_size(download_path)
        self._assert_subscribers_called(file_size)
        with open(download_path, 'rb') as f:
            self.assertEqual(f.read(), b'hello world')

    def test_download_below_threshold(self):
        transfer = self._create_s3_transfer()
        filename = self.files.create_file_with_size(
            'foo.txt', filesize=1024 * 1024
        )
        self.upload_file(filename, 'foo.txt')

        download_path = os.path.join(self.files.rootdir, 'downloaded.txt')
        with transfer:
            future = transfer.download(
                self.bucket_name,
                'foo.txt',
                download_path,
                subscribers=[self.record_subscriber],
            )
            future.result()
        file_size = self.osutil.get_file_size(download_path)
        self._assert_subscribers_called(file_size)
        assert_files_equal(filename, download_path)

    def test_download_above_threshold(self):
        transfer = self._create_s3_transfer()
        filename = self.files.create_file_with_size(
            'foo.txt', filesize=20 * 1024 * 1024
        )
        self.upload_file(filename, 'foo.txt')

        download_path = os.path.join(self.files.rootdir, 'downloaded.txt')
        with transfer:
            future = transfer.download(
                self.bucket_name,
                'foo.txt',
                download_path,
                subscribers=[self.record_subscriber],
            )
            future.result()
        assert_files_equal(filename, download_path)
        file_size = self.osutil.get_file_size(download_path)
        self._assert_subscribers_called(file_size)

    def test_download_seekable_stream(self):
        size = 1024 * 1024
        filename = self.files.create_file_with_size(self.s3_key, filesize=size)
        self.upload_file(filename, self.s3_key)

        with open(self.download_path, 'wb') as f:
            self._download_with_crt_transfer_manager(f)
        self._assert_subscribers_called(size)
        assert_files_equal(filename, self.download_path)

    def test_multipart_download_seekable_stream(self):
        size = 20 * 1024 * 1024
        filename = self.files.create_file_with_size(self.s3_key, filesize=size)
        self.upload_file(filename, self.s3_key)

        with open(self.download_path, 'wb') as f:
            self._download_with_crt_transfer_manager(f)
        self._assert_subscribers_called(size)
        assert_files_equal(filename, self.download_path)

    def test_download_nonseekable_stream(self):
        size = 1024 * 1024
        filename = self.files.create_file_with_size(self.s3_key, filesize=size)
        self.upload_file(filename, self.s3_key)

        with open(self.download_path, 'wb') as f:
            self._download_with_crt_transfer_manager(NonSeekableWriter(f))
        self._assert_subscribers_called(size)
        assert_files_equal(filename, self.download_path)

    def test_multipart_download_nonseekable_stream(self):
        size = 20 * 1024 * 1024
        filename = self.files.create_file_with_size(self.s3_key, filesize=size)
        self.upload_file(filename, self.s3_key)

        with open(self.download_path, 'wb') as f:
            self._download_with_crt_transfer_manager(NonSeekableWriter(f))
        self._assert_subscribers_called(size)
        assert_files_equal(filename, self.download_path)

    def test_download_empty_file(self):
        size = 0
        filename = self.files.create_file_with_size(self.s3_key, filesize=size)
        self.upload_file(filename, self.s3_key)

        self._download_with_crt_transfer_manager(self.download_path)
        self._assert_subscribers_called(size)
        assert_files_equal(filename, self.download_path)

    def test_download_empty_stream(self):
        size = 0
        filename = self.files.create_file_with_size(self.s3_key, filesize=size)
        self.upload_file(filename, self.s3_key)

        with open(self.download_path, 'wb') as f:
            self._download_with_crt_transfer_manager(f)
        self._assert_subscribers_called(size)
        assert_files_equal(filename, self.download_path)

    def test_delete(self):
        transfer = self._create_s3_transfer()
        filename = self.files.create_file_with_size(
            'foo.txt', filesize=1024 * 1024
        )
        self.upload_file(filename, 'foo.txt')

        with transfer:
            future = transfer.delete(self.bucket_name, 'foo.txt')
            future.result()
        self.assertTrue(self.object_not_exists('foo.txt'))

    def test_many_files_download(self):
        transfer = self._create_s3_transfer()

        filename = self.files.create_file_with_size(
            '1mb.txt', filesize=1024 * 1024
        )
        self.upload_file(filename, '1mb.txt')

        filenames = []
        base_filename = os.path.join(self.files.rootdir, 'file')
        for i in range(10):
            filenames.append(base_filename + str(i))

        with transfer:
            for filename in filenames:
                transfer.download(self.bucket_name, '1mb.txt', filename)
        for download_path in filenames:
            assert_files_equal(filename, download_path)

    def test_many_files_upload(self):
        transfer = self._create_s3_transfer()
        keys = []
        filenames = []
        base_key = 'foo'
        sufix = '.txt'
        for i in range(10):
            key = base_key + str(i) + sufix
            keys.append(key)
            filename = self.files.create_file_with_size(
                key, filesize=1024 * 1024
            )
            filenames.append(filename)
            self.addCleanup(self.delete_object, key)
        with transfer:
            for filename, key in zip(filenames, keys):
                transfer.upload(filename, self.bucket_name, key)

        for key in keys:
            self.assertTrue(self.object_exists(key))

    def test_many_files_delete(self):
        transfer = self._create_s3_transfer()
        keys = []
        base_key = 'foo'
        sufix = '.txt'
        filename = self.files.create_file_with_size(
            '1mb.txt', filesize=1024 * 1024
        )
        for i in range(10):
            key = base_key + str(i) + sufix
            keys.append(key)
            self.upload_file(filename, key)

        with transfer:
            for key in keys:
                transfer.delete(self.bucket_name, key)
        for key in keys:
            self.assertTrue(self.object_not_exists(key))

    def test_upload_cancel(self):
        transfer = self._create_s3_transfer()
        filename = self.files.create_file_with_size(
            '20mb.txt', filesize=20 * 1024 * 1024
        )
        future = None
        try:
            with transfer:
                future = transfer.upload(
                    filename, self.bucket_name, '20mb.txt'
                )
                raise KeyboardInterrupt()
        except KeyboardInterrupt:
            pass

        with self.assertRaises(AwsCrtError) as cm:
            future.result()
            self.assertEqual(cm.name, 'AWS_ERROR_S3_CANCELED')
        self.assertTrue(self.object_not_exists('20mb.txt'))

    def test_download_cancel(self):
        transfer = self._create_s3_transfer()
        filename = self.files.create_file_with_size(
            'foo.txt', filesize=20 * 1024 * 1024
        )
        self.upload_file(filename, 'foo.txt')

        download_path = os.path.join(self.files.rootdir, 'downloaded.txt')
        future = None
        try:
            with transfer:
                future = transfer.download(
                    self.bucket_name,
                    'foo.txt',
                    download_path,
                    subscribers=[self.record_subscriber],
                )
                raise KeyboardInterrupt()
        except KeyboardInterrupt:
            pass

        with self.assertRaises(AwsCrtError) as err:
            future.result()
            self.assertEqual(err.name, 'AWS_ERROR_S3_CANCELED')

        possible_matches = glob.glob('%s*' % download_path)
        self.assertEqual(possible_matches, [])
        self._assert_subscribers_called()
