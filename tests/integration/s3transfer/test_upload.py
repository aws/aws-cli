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
import time
import threading

from concurrent.futures import CancelledError

from botocore.compat import six
from tests import skip_if_using_serial_implementation
from tests import RecordingSubscriber, NonSeekableReader
from tests.integration import BaseTransferManagerIntegTest
from tests.integration import WaitForTransferStart
from s3transfer.manager import TransferConfig


class TestUpload(BaseTransferManagerIntegTest):
    def setUp(self):
        super(TestUpload, self).setUp()
        self.multipart_threshold = 5 * 1024 * 1024
        self.config = TransferConfig(
            multipart_threshold=self.multipart_threshold)

    def get_input_fileobj(self, size, name=''):
        return self.files.create_file_with_size(name, size)

    def test_upload_below_threshold(self):
        transfer_manager = self.create_transfer_manager(self.config)
        file = self.get_input_fileobj(size=1024 * 1024, name='1mb.txt')
        future = transfer_manager.upload(file, self.bucket_name, '1mb.txt')
        self.addCleanup(self.delete_object, '1mb.txt')

        future.result()
        self.assertTrue(self.object_exists('1mb.txt'))

    def test_upload_above_threshold(self):
        transfer_manager = self.create_transfer_manager(self.config)
        file = self.get_input_fileobj(size=20 * 1024 * 1024, name='20mb.txt')
        future = transfer_manager.upload(
            file, self.bucket_name, '20mb.txt')
        self.addCleanup(self.delete_object, '20mb.txt')

        future.result()
        self.assertTrue(self.object_exists('20mb.txt'))

    @skip_if_using_serial_implementation(
        'Exception is thrown once the transfer is submitted. '
        'However for the serial implementation, transfers are performed '
        'in main thread meaning the transfer will complete before the '
        'KeyboardInterrupt being thrown.'
    )
    def test_large_upload_exits_quicky_on_exception(self):
        transfer_manager = self.create_transfer_manager(self.config)

        filename = self.get_input_fileobj(
            name='foo.txt', size=20 * 1024 * 1024)

        timeout = 10
        bytes_transferring = threading.Event()
        subscriber = WaitForTransferStart(bytes_transferring)
        try:
            with transfer_manager:
                future = transfer_manager.upload(
                    filename, self.bucket_name, '20mb.txt',
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

        try:
            future.result()
            self.skipTest(
                'Upload completed before interrupted and therefore '
                'could not cancel the upload')
        except CancelledError as e:
            self.assertEqual(str(e), 'KeyboardInterrupt()')
            # If the transfer did get cancelled,
            # make sure the object does not exist.
            self.assertTrue(self.object_not_exists('20mb.txt'))

    @skip_if_using_serial_implementation(
        'Exception is thrown once the transfers are submitted. '
        'However for the serial implementation, transfers are performed '
        'in main thread meaning the transfers will complete before the '
        'KeyboardInterrupt being thrown.'
    )
    def test_many_files_exits_quicky_on_exception(self):
        # Set the max request queue size and number of submission threads
        # to something small to simulate having a large queue
        # of transfer requests to complete and it is backed up.
        self.config.max_request_queue_size = 1
        self.config.max_submission_concurrency = 1
        transfer_manager = self.create_transfer_manager(self.config)

        fileobjs = []
        keynames = []
        futures = []
        for i in range(10):
            filename = 'file' + str(i)
            keynames.append(filename)
            fileobjs.append(
                self.get_input_fileobj(name=filename, size=1024 * 1024))

        try:
            with transfer_manager:
                for i, fileobj in enumerate(fileobjs):
                    futures.append(transfer_manager.upload(
                        fileobj, self.bucket_name, keynames[i]))
                # Raise an exception which should cause the preceeding
                # transfer to cancel and exit quickly
                start_time = time.time()
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
        # For the transfer that did get cancelled, make sure the object
        # does not exist.
        self.assertTrue(self.object_not_exists(future.meta.call_args.key))

    def test_progress_subscribers_on_upload(self):
        subscriber = RecordingSubscriber()
        transfer_manager = self.create_transfer_manager(self.config)
        file = self.get_input_fileobj(size=20 * 1024 * 1024, name='20mb.txt')
        future = transfer_manager.upload(
            file, self.bucket_name, '20mb.txt',
            subscribers=[subscriber])
        self.addCleanup(self.delete_object, '20mb.txt')

        future.result()
        # The callback should have been called enough times such that
        # the total amount of bytes we've seen (via the "amount"
        # arg to the callback function) should be the size
        # of the file we uploaded.
        self.assertEqual(subscriber.calculate_bytes_seen(), 20 * 1024 * 1024)


class TestUploadSeekableStream(TestUpload):
    def get_input_fileobj(self, size, name=''):
        return six.BytesIO(b'0' * size)


class TestUploadNonSeekableStream(TestUpload):
    def get_input_fileobj(self, size, name=''):
        return NonSeekableReader(b'0' * size)
