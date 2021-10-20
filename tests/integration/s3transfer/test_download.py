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
import glob
import os
import time
import threading

from concurrent.futures import CancelledError

from tests import assert_files_equal
from tests import skip_if_windows
from tests import skip_if_using_serial_implementation
from tests import RecordingSubscriber
from tests import NonSeekableWriter
from tests.integration import BaseTransferManagerIntegTest
from tests.integration import WaitForTransferStart
from s3transfer.manager import TransferConfig


class TestDownload(BaseTransferManagerIntegTest):
    def setUp(self):
        super(TestDownload, self).setUp()
        self.multipart_threshold = 5 * 1024 * 1024
        self.config = TransferConfig(
            multipart_threshold=self.multipart_threshold
        )

    def test_below_threshold(self):
        transfer_manager = self.create_transfer_manager(self.config)

        filename = self.files.create_file_with_size(
            'foo.txt', filesize=1024 * 1024)
        self.upload_file(filename, '1mb.txt')

        download_path = os.path.join(self.files.rootdir, '1mb.txt')
        future = transfer_manager.download(
            self.bucket_name, '1mb.txt', download_path)
        future.result()
        assert_files_equal(filename, download_path)

    def test_above_threshold(self):
        transfer_manager = self.create_transfer_manager(self.config)

        filename = self.files.create_file_with_size(
            'foo.txt', filesize=20 * 1024 * 1024)
        self.upload_file(filename, '20mb.txt')

        download_path = os.path.join(self.files.rootdir, '20mb.txt')
        future = transfer_manager.download(
            self.bucket_name, '20mb.txt', download_path)
        future.result()
        assert_files_equal(filename, download_path)

    @skip_if_using_serial_implementation(
        'Exception is thrown once the transfer is submitted. '
        'However for the serial implementation, transfers are performed '
        'in main thread meaning the transfer will complete before the '
        'KeyboardInterrupt being thrown.'
    )
    def test_large_download_exits_quicky_on_exception(self):
        transfer_manager = self.create_transfer_manager(self.config)

        filename = self.files.create_file_with_size(
            'foo.txt', filesize=60 * 1024 * 1024)
        self.upload_file(filename, '60mb.txt')

        download_path = os.path.join(self.files.rootdir, '60mb.txt')
        timeout = 10
        bytes_transferring = threading.Event()
        subscriber = WaitForTransferStart(bytes_transferring)
        try:
            with transfer_manager:
                future = transfer_manager.download(
                    self.bucket_name, '60mb.txt', download_path,
                    subscribers=[subscriber]
                )
                if not bytes_transferring.wait(timeout):
                    future.cancel()
                    raise RuntimeError(
                        "Download transfer did not start after waiting for "
                        "%s seconds." % timeout)
                # Raise an exception which should cause the preceeding
                # download to cancel and exit quickly
                start_time = time.time()
                raise KeyboardInterrupt()
        except KeyboardInterrupt:
            pass
        end_time = time.time()
        # The maximum time allowed for the transfer manager to exit.
        # This means that it should take less than a couple second after
        # sleeping to exit.
        max_allowed_exit_time = 5
        actual_time_to_exit = end_time - start_time
        self.assertLess(
            actual_time_to_exit, max_allowed_exit_time,
            "Failed to exit under %s. Instead exited in %s." % (
                max_allowed_exit_time, actual_time_to_exit)
        )

        # Make sure the future was cancelled because of the KeyboardInterrupt
        with self.assertRaisesRegex(CancelledError, 'KeyboardInterrupt()'):
            future.result()

        # Make sure the actual file and the temporary do not exist
        # by globbing for the file and any of its extensions
        possible_matches = glob.glob('%s*' % download_path)
        self.assertEqual(possible_matches, [])

    @skip_if_using_serial_implementation(
        'Exception is thrown once the transfer is submitted. '
        'However for the serial implementation, transfers are performed '
        'in main thread meaning the transfer will complete before the '
        'KeyboardInterrupt being thrown.'
    )
    def test_many_files_exits_quicky_on_exception(self):
        # Set the max request queue size and number of submission threads
        # to something small to simulate having a large queue
        # of transfer requests to complete and it is backed up.
        self.config.max_request_queue_size = 1
        self.config.max_submission_concurrency = 1
        transfer_manager = self.create_transfer_manager(self.config)

        filename = self.files.create_file_with_size(
            'foo.txt', filesize=1024 * 1024)
        self.upload_file(filename, '1mb.txt')

        filenames = []
        futures = []
        for i in range(10):
            filenames.append(
                os.path.join(self.files.rootdir, 'file'+str(i)))

        try:
            with transfer_manager:
                start_time = time.time()
                for filename in filenames:
                    futures.append(transfer_manager.download(
                        self.bucket_name, '1mb.txt', filename))
                # Raise an exception which should cause the preceeding
                # transfer to cancel and exit quickly
                raise KeyboardInterrupt()
        except KeyboardInterrupt:
            pass
        end_time = time.time()
        # The maximum time allowed for the transfer manager to exit.
        # This means that it should take less than a couple seconds to exit.
        max_allowed_exit_time = 5
        self.assertLess(
            end_time - start_time, max_allowed_exit_time,
            "Failed to exit under %s. Instead exited in %s." % (
                max_allowed_exit_time, end_time - start_time)
        )

        # Make sure at least one of the futures got cancelled
        with self.assertRaisesRegex(CancelledError, 'KeyboardInterrupt()'):
            for future in futures:
                future.result()

        # For the transfer that did get cancelled, make sure the temporary
        # file got removed.
        possible_matches = glob.glob('%s*' % future.meta.call_args.fileobj)
        self.assertEqual(possible_matches, [])

    def test_progress_subscribers_on_download(self):
        subscriber = RecordingSubscriber()
        transfer_manager = self.create_transfer_manager(self.config)

        filename = self.files.create_file_with_size(
            'foo.txt', filesize=20 * 1024 * 1024)
        self.upload_file(filename, '20mb.txt')

        download_path = os.path.join(self.files.rootdir, '20mb.txt')

        future = transfer_manager.download(
            self.bucket_name, '20mb.txt', download_path,
            subscribers=[subscriber])
        future.result()
        self.assertEqual(subscriber.calculate_bytes_seen(), 20 * 1024 * 1024)

    def test_below_threshold_for_fileobj(self):
        transfer_manager = self.create_transfer_manager(self.config)

        filename = self.files.create_file_with_size(
            'foo.txt', filesize=1024 * 1024)
        self.upload_file(filename, '1mb.txt')

        download_path = os.path.join(self.files.rootdir, '1mb.txt')
        with open(download_path, 'wb') as f:
            future = transfer_manager.download(
                self.bucket_name, '1mb.txt', f)
            future.result()
        assert_files_equal(filename, download_path)

    def test_above_threshold_for_fileobj(self):
        transfer_manager = self.create_transfer_manager(self.config)

        filename = self.files.create_file_with_size(
            'foo.txt', filesize=20 * 1024 * 1024)
        self.upload_file(filename, '20mb.txt')

        download_path = os.path.join(self.files.rootdir, '20mb.txt')
        with open(download_path, 'wb') as f:
            future = transfer_manager.download(
                self.bucket_name, '20mb.txt', f)
            future.result()
        assert_files_equal(filename, download_path)

    def test_below_threshold_for_nonseekable_fileobj(self):
        transfer_manager = self.create_transfer_manager(self.config)

        filename = self.files.create_file_with_size(
            'foo.txt', filesize=1024 * 1024)
        self.upload_file(filename, '1mb.txt')

        download_path = os.path.join(self.files.rootdir, '1mb.txt')
        with open(download_path, 'wb') as f:
            future = transfer_manager.download(
                self.bucket_name, '1mb.txt', NonSeekableWriter(f))
            future.result()
        assert_files_equal(filename, download_path)

    def test_above_threshold_for_nonseekable_fileobj(self):
        transfer_manager = self.create_transfer_manager(self.config)

        filename = self.files.create_file_with_size(
            'foo.txt', filesize=20 * 1024 * 1024)
        self.upload_file(filename, '20mb.txt')

        download_path = os.path.join(self.files.rootdir, '20mb.txt')
        with open(download_path, 'wb') as f:
            future = transfer_manager.download(
                self.bucket_name, '20mb.txt', NonSeekableWriter(f))
            future.result()
        assert_files_equal(filename, download_path)

    @skip_if_windows('Windows does not support UNIX special files')
    def test_download_to_special_file(self):
        transfer_manager = self.create_transfer_manager(self.config)
        filename = self.files.create_file_with_size(
            'foo.txt', filesize=1024 * 1024)
        self.upload_file(filename, '1mb.txt')
        future = transfer_manager.download(
            self.bucket_name, '1mb.txt', '/dev/null')
        try:
            future.result()
        except Exception as e:
            self.fail(
                'Should have been able to download to /dev/null but received '
                'following exception %s' % e)
