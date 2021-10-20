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
import os
import threading
import math
import tempfile
import shutil
import hashlib
import string

from tests.integration import BaseTransferManagerIntegTest
from botocore.compat import six
from botocore.client import Config

import s3transfer


urlopen = six.moves.urllib.request.urlopen


def assert_files_equal(first, second):
    if os.path.getsize(first) != os.path.getsize(second):
        raise AssertionError("Files are not equal: %s, %s" % (first, second))
    first_md5 = md5_checksum(first)
    second_md5 = md5_checksum(second)
    if first_md5 != second_md5:
        raise AssertionError(
            "Files are not equal: %s(md5=%s) != %s(md5=%s)" % (
                first, first_md5, second, second_md5))


def md5_checksum(filename):
    checksum = hashlib.md5()
    with open(filename, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            checksum.update(chunk)
    return checksum.hexdigest()


def random_bucket_name(prefix='boto3-transfer', num_chars=10):
    base = string.ascii_lowercase + string.digits
    random_bytes = bytearray(os.urandom(num_chars))
    return prefix + ''.join([base[b % len(base)] for b in random_bytes])


class FileCreator(object):
    def __init__(self):
        self.rootdir = tempfile.mkdtemp()

    def remove_all(self):
        shutil.rmtree(self.rootdir)

    def create_file(self, filename, contents, mode='w'):
        """Creates a file in a tmpdir
        ``filename`` should be a relative path, e.g. "foo/bar/baz.txt"
        It will be translated into a full path in a tmp dir.
        ``mode`` is the mode the file should be opened either as ``w`` or
        `wb``.
        Returns the full path to the file.
        """
        full_path = os.path.join(self.rootdir, filename)
        if not os.path.isdir(os.path.dirname(full_path)):
            os.makedirs(os.path.dirname(full_path))
        with open(full_path, mode) as f:
            f.write(contents)
        return full_path

    def create_file_with_size(self, filename, filesize):
        filename = self.create_file(filename, contents='')
        chunksize = 8192
        with open(filename, 'wb') as f:
            for i in range(int(math.ceil(filesize / float(chunksize)))):
                f.write(b'a' * chunksize)
        return filename

    def append_file(self, filename, contents):
        """Append contents to a file
        ``filename`` should be a relative path, e.g. "foo/bar/baz.txt"
        It will be translated into a full path in a tmp dir.
        Returns the full path to the file.
        """
        full_path = os.path.join(self.rootdir, filename)
        if not os.path.isdir(os.path.dirname(full_path)):
            os.makedirs(os.path.dirname(full_path))
        with open(full_path, 'a') as f:
            f.write(contents)
        return full_path

    def full_path(self, filename):
        """Translate relative path to full path in temp dir.
        f.full_path('foo/bar.txt') -> /tmp/asdfasd/foo/bar.txt
        """
        return os.path.join(self.rootdir, filename)


class TestS3Transfers(BaseTransferManagerIntegTest):
    """Tests for the high level s3transfer module."""

    def create_s3_transfer(self, config=None):
        return s3transfer.S3Transfer(
            self.client, config=config
        )

    def assert_has_public_read_acl(self, response):
        grants = response['Grants']
        public_read = [g['Grantee'].get('URI', '') for g in grants
                       if g['Permission'] == 'READ']
        self.assertIn('groups/global/AllUsers', public_read[0])

    def test_upload_below_threshold(self):
        config = s3transfer.TransferConfig(
            multipart_threshold=2 * 1024 * 1024)
        transfer = self.create_s3_transfer(config)
        filename = self.files.create_file_with_size(
            'foo.txt', filesize=1024 * 1024)
        transfer.upload_file(filename, self.bucket_name,
                             'foo.txt')
        self.addCleanup(self.delete_object, 'foo.txt')

        self.assertTrue(self.object_exists('foo.txt'))

    def test_upload_above_threshold(self):
        config = s3transfer.TransferConfig(
            multipart_threshold=2 * 1024 * 1024)
        transfer = self.create_s3_transfer(config)
        filename = self.files.create_file_with_size(
            '20mb.txt', filesize=20 * 1024 * 1024)
        transfer.upload_file(filename, self.bucket_name,
                             '20mb.txt')
        self.addCleanup(self.delete_object, '20mb.txt')
        self.assertTrue(self.object_exists('20mb.txt'))

    def test_upload_file_above_threshold_with_acl(self):
        config = s3transfer.TransferConfig(
            multipart_threshold=5 * 1024 * 1024)
        transfer = self.create_s3_transfer(config)
        filename = self.files.create_file_with_size(
            '6mb.txt', filesize=6 * 1024 * 1024)
        extra_args = {'ACL': 'public-read'}
        transfer.upload_file(filename, self.bucket_name,
                             '6mb.txt', extra_args=extra_args)
        self.addCleanup(self.delete_object, '6mb.txt')

        self.assertTrue(self.object_exists('6mb.txt'))
        response = self.client.get_object_acl(
            Bucket=self.bucket_name, Key='6mb.txt')
        self.assert_has_public_read_acl(response)

    def test_upload_file_above_threshold_with_ssec(self):
        key_bytes = os.urandom(32)
        extra_args = {
            'SSECustomerKey': key_bytes,
            'SSECustomerAlgorithm': 'AES256',
        }
        config = s3transfer.TransferConfig(
            multipart_threshold=5 * 1024 * 1024)
        transfer = self.create_s3_transfer(config)
        filename = self.files.create_file_with_size(
            '6mb.txt', filesize=6 * 1024 * 1024)
        transfer.upload_file(filename, self.bucket_name,
                             '6mb.txt', extra_args=extra_args)
        self.addCleanup(self.delete_object, '6mb.txt')
        self.wait_object_exists('6mb.txt', extra_args)
        # A head object will fail if it has a customer key
        # associated with it and it's not provided in the HeadObject
        # request so we can use this to verify our functionality.
        response = self.client.head_object(
            Bucket=self.bucket_name,
            Key='6mb.txt', **extra_args)
        self.assertEqual(response['SSECustomerAlgorithm'], 'AES256')

    def test_progress_callback_on_upload(self):
        self.amount_seen = 0
        lock = threading.Lock()

        def progress_callback(amount):
            with lock:
                self.amount_seen += amount

        transfer = self.create_s3_transfer()
        filename = self.files.create_file_with_size(
            '20mb.txt', filesize=20 * 1024 * 1024)
        transfer.upload_file(filename, self.bucket_name,
                             '20mb.txt', callback=progress_callback)
        self.addCleanup(self.delete_object, '20mb.txt')

        # The callback should have been called enough times such that
        # the total amount of bytes we've seen (via the "amount"
        # arg to the callback function) should be the size
        # of the file we uploaded.
        self.assertEqual(self.amount_seen, 20 * 1024 * 1024)

    def test_callback_called_once_with_sigv4(self):
        # Verify #98, where the callback was being invoked
        # twice when using signature version 4.
        self.amount_seen = 0
        lock = threading.Lock()

        def progress_callback(amount):
            with lock:
                self.amount_seen += amount

        client = self.session.create_client(
            's3', self.region,
            config=Config(signature_version='s3v4'))
        transfer = s3transfer.S3Transfer(client)
        filename = self.files.create_file_with_size(
            '10mb.txt', filesize=10 * 1024 * 1024)
        transfer.upload_file(filename, self.bucket_name,
                             '10mb.txt', callback=progress_callback)
        self.addCleanup(self.delete_object, '10mb.txt')

        self.assertEqual(self.amount_seen, 10 * 1024 * 1024)

    def test_can_send_extra_params_on_upload(self):
        transfer = self.create_s3_transfer()
        filename = self.files.create_file_with_size('foo.txt', filesize=1024)
        transfer.upload_file(filename, self.bucket_name,
                             'foo.txt', extra_args={'ACL': 'public-read'})
        self.addCleanup(self.delete_object, 'foo.txt')

        self.wait_object_exists('foo.txt')
        response = self.client.get_object_acl(
            Bucket=self.bucket_name, Key='foo.txt')
        self.assert_has_public_read_acl(response)

    def test_can_configure_threshold(self):
        config = s3transfer.TransferConfig(
            multipart_threshold=6 * 1024 * 1024
        )
        transfer = self.create_s3_transfer(config)
        filename = self.files.create_file_with_size(
            'foo.txt', filesize=8 * 1024 * 1024)
        transfer.upload_file(filename, self.bucket_name,
                             'foo.txt')
        self.addCleanup(self.delete_object, 'foo.txt')

        self.assertTrue(self.object_exists('foo.txt'))

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
        transfer = self.create_s3_transfer()

        download_path = os.path.join(self.files.rootdir, 'downloaded.txt')
        transfer.download_file(self.bucket_name, 'foo.txt',
                               download_path, extra_args=extra_args)
        with open(download_path, 'rb') as f:
            self.assertEqual(f.read(), b'hello world')

    def test_progress_callback_on_download(self):
        self.amount_seen = 0
        lock = threading.Lock()

        def progress_callback(amount):
            with lock:
                self.amount_seen += amount

        transfer = self.create_s3_transfer()
        filename = self.files.create_file_with_size(
            '20mb.txt', filesize=20 * 1024 * 1024)
        self.upload_file(filename, '20mb.txt')

        download_path = os.path.join(self.files.rootdir, 'downloaded.txt')
        transfer.download_file(self.bucket_name, '20mb.txt',
                               download_path, callback=progress_callback)

        self.assertEqual(self.amount_seen, 20 * 1024 * 1024)

    def test_download_below_threshold(self):
        transfer = self.create_s3_transfer()
        filename = self.files.create_file_with_size(
            'foo.txt', filesize=1024 * 1024)
        self.upload_file(filename, 'foo.txt')

        download_path = os.path.join(self.files.rootdir, 'downloaded.txt')
        transfer.download_file(self.bucket_name, 'foo.txt',
                               download_path)
        assert_files_equal(filename, download_path)

    def test_download_above_threshold(self):
        transfer = self.create_s3_transfer()
        filename = self.files.create_file_with_size(
            'foo.txt', filesize=20 * 1024 * 1024)
        self.upload_file(filename, 'foo.txt')

        download_path = os.path.join(self.files.rootdir, 'downloaded.txt')
        transfer.download_file(self.bucket_name, 'foo.txt',
                               download_path)
        assert_files_equal(filename, download_path)
