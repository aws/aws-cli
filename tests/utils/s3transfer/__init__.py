# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import io
import hashlib
import math
import os
import platform
import shutil
import string
import tempfile
import unittest
from unittest import mock  # noqa: F401

import botocore.session
from botocore.stub import Stubber
from botocore.compat import six

from s3transfer.manager import TransferConfig
from s3transfer.futures import IN_MEMORY_UPLOAD_TAG
from s3transfer.futures import IN_MEMORY_DOWNLOAD_TAG
from s3transfer.futures import TransferCoordinator
from s3transfer.futures import TransferMeta
from s3transfer.futures import TransferFuture
from s3transfer.futures import BoundedExecutor
from s3transfer.futures import NonThreadedExecutor
from s3transfer.subscribers import BaseSubscriber
from s3transfer.utils import OSUtils
from s3transfer.utils import CallArgs
from s3transfer.utils import TaskSemaphore
from s3transfer.utils import SlidingWindowSemaphore


ORIGINAL_EXECUTOR_CLS = BoundedExecutor.EXECUTOR_CLS
# Detect if CRT is available for use
try:
    import awscrt.s3  # noqa: F401
    HAS_CRT = True
except ImportError:
    HAS_CRT = False


def setup_package():
    if is_serial_implementation():
        BoundedExecutor.EXECUTOR_CLS = NonThreadedExecutor


def teardown_package():
    BoundedExecutor.EXECUTOR_CLS = ORIGINAL_EXECUTOR_CLS


def is_serial_implementation():
    return os.environ.get('USE_SERIAL_EXECUTOR', False)


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


def random_bucket_name(prefix='s3transfer', num_chars=10):
    base = string.ascii_lowercase + string.digits
    random_bytes = bytearray(os.urandom(num_chars))
    return prefix + ''.join([base[b % len(base)] for b in random_bytes])


def skip_if_windows(reason):
    """Decorator to skip tests that should not be run on windows.

    Example usage:

        @skip_if_windows("Not valid")
        def test_some_non_windows_stuff(self):
            self.assertEqual(...)

    """
    def decorator(func):
        return unittest.skipIf(
            platform.system() not in ['Darwin', 'Linux'], reason)(func)
    return decorator


def skip_if_using_serial_implementation(reason):
    """Decorator to skip tests when running as the serial implementation"""
    def decorator(func):
        return unittest.skipIf(
            is_serial_implementation(), reason)(func)
    return decorator


def requires_crt(cls, reason=None):
    if reason is None:
        reason = "Test requires awscrt to be installed."
    return unittest.skipIf(not HAS_CRT, reason)(cls)


class StreamWithError(object):
    """A wrapper to simulate errors while reading from a stream

    :param stream: The underlying stream to read from
    :param exception_type: The exception type to throw
    :param num_reads: The number of times to allow a read before raising
        the exception. A value of zero indicates to raise the error on the
        first read.
    """

    def __init__(self, stream, exception_type, num_reads=0):
        self._stream = stream
        self._exception_type = exception_type
        self._num_reads = num_reads
        self._count = 0

    def read(self, n=-1):
        if self._count == self._num_reads:
            raise self._exception_type
        self._count += 1
        return self._stream.read(n)


class FileSizeProvider(object):
    def __init__(self, file_size):
        self.file_size = file_size

    def on_queued(self, future, **kwargs):
        future.meta.provide_transfer_size(self.file_size)


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


class RecordingOSUtils(OSUtils):
    """An OSUtil abstraction that records openings and renamings"""

    def __init__(self):
        super(RecordingOSUtils, self).__init__()
        self.open_records = []
        self.rename_records = []

    def open(self, filename, mode):
        self.open_records.append((filename, mode))
        return super(RecordingOSUtils, self).open(filename, mode)

    def rename_file(self, current_filename, new_filename):
        self.rename_records.append((current_filename, new_filename))
        super(RecordingOSUtils, self).rename_file(
            current_filename, new_filename)


class RecordingSubscriber(BaseSubscriber):
    def __init__(self):
        self.on_queued_calls = []
        self.on_progress_calls = []
        self.on_done_calls = []

    def on_queued(self, **kwargs):
        self.on_queued_calls.append(kwargs)

    def on_progress(self, **kwargs):
        self.on_progress_calls.append(kwargs)

    def on_done(self, **kwargs):
        self.on_done_calls.append(kwargs)

    def calculate_bytes_seen(self, **kwargs):
        amount_seen = 0
        for call in self.on_progress_calls:
            amount_seen += call['bytes_transferred']
        return amount_seen


class TransferCoordinatorWithInterrupt(TransferCoordinator):
    """Used to inject keyboard interrupts"""

    def result(self):
        raise KeyboardInterrupt()


class RecordingExecutor(object):
    """A wrapper on an executor to record calls made to submit()

    You can access the submissions property to receive a list of dictionaries
    that represents all submissions where the dictionary is formatted::

        {
            'fn': function
            'args': positional args (as tuple)
            'kwargs': keyword args (as dict)
        }
    """

    def __init__(self, executor):
        self._executor = executor
        self.submissions = []

    def submit(self, task, tag=None, block=True):
        future = self._executor.submit(task, tag, block)
        self.submissions.append(
            {
                'task': task,
                'tag': tag,
                'block': block
            }
        )
        return future

    def shutdown(self):
        self._executor.shutdown()


class StubbedClientTest(unittest.TestCase):
    def setUp(self):
        self.session = botocore.session.get_session()
        self.region = 'us-west-2'
        self.client = self.session.create_client(
            's3', self.region, aws_access_key_id='foo',
            aws_secret_access_key='bar')
        self.stubber = Stubber(self.client)
        self.stubber.activate()

    def tearDown(self):
        self.stubber.deactivate()

    def reset_stubber_with_new_client(self, override_client_kwargs):
        client_kwargs = {
            'service_name': 's3',
            'region_name': self.region,
            'aws_access_key_id': 'foo',
            'aws_secret_access_key': 'bar'
        }
        client_kwargs.update(override_client_kwargs)
        self.client = self.session.create_client(**client_kwargs)
        self.stubber = Stubber(self.client)
        self.stubber.activate()


class BaseTaskTest(StubbedClientTest):
    def setUp(self):
        super(BaseTaskTest, self).setUp()
        self.transfer_coordinator = TransferCoordinator()

    def get_task(self, task_cls, **kwargs):
        if 'transfer_coordinator' not in kwargs:
            kwargs['transfer_coordinator'] = self.transfer_coordinator
        return task_cls(**kwargs)

    def get_transfer_future(self, call_args=None):
        return TransferFuture(
            meta=TransferMeta(call_args),
            coordinator=self.transfer_coordinator
        )


class BaseSubmissionTaskTest(BaseTaskTest):
    def setUp(self):
        super(BaseSubmissionTaskTest, self).setUp()
        self.config = TransferConfig()
        self.osutil = OSUtils()
        self.executor = BoundedExecutor(
            1000,
            1,
            {
                IN_MEMORY_UPLOAD_TAG: TaskSemaphore(10),
                IN_MEMORY_DOWNLOAD_TAG: SlidingWindowSemaphore(10)
            }
        )

    def tearDown(self):
        super(BaseSubmissionTaskTest, self).tearDown()
        self.executor.shutdown()


class BaseGeneralInterfaceTest(StubbedClientTest):
    """A general test class to ensure consistency across TransferManger methods

    This test should never be called and should be subclassed from to pick up
    the various tests that all TransferManager method must pass from a
    functionality standpoint.
    """
    __test__ = False

    def manager(self):
        """The transfer manager to use"""
        raise NotImplementedError('method is not implemented')

    @property
    def method(self):
        """The transfer manager method to invoke i.e. upload()"""
        raise NotImplementedError('method is not implemented')

    def create_call_kwargs(self):
        """The kwargs to be passed to the transfer manager method"""
        raise NotImplementedError('create_call_kwargs is not implemented')

    def create_invalid_extra_args(self):
        """A value for extra_args that will cause validation errors"""
        raise NotImplementedError(
            'create_invalid_extra_args is not implemented')

    def create_stubbed_responses(self):
        """A list of stubbed responses that will cause the request to succeed

        The elements of this list is a dictionary that will be used as key
        word arguments to botocore.Stubber.add_response(). For example::

            [{'method': 'put_object', 'service_response': {}}]
        """
        raise NotImplementedError(
            'create_stubbed_responses is not implemented')

    def create_expected_progress_callback_info(self):
        """A list of kwargs expected to be passed to each progress callback

        Note that the future kwargs does not need to be added to each
        dictionary provided in the list. This is injected for you. An example
        is::

            [
                {'bytes_transferred': 4},
                {'bytes_transferred': 4},
                {'bytes_transferred': 2}
            ]

        This indicates that the progress callback will be called three
        times and pass along the specified keyword arguments and corresponding
        values.
        """
        raise NotImplementedError(
            'create_expected_progress_callback_info is not implemented')

    def _setup_default_stubbed_responses(self):
        for stubbed_response in self.create_stubbed_responses():
            self.stubber.add_response(**stubbed_response)

    def test_returns_future_with_meta(self):
        self._setup_default_stubbed_responses()
        future = self.method(**self.create_call_kwargs())
        # The result is called so we ensure that the entire process executes
        # before we try to clean up resources in the tearDown.
        future.result()

        # Assert the return value is a future with metadata associated to it.
        self.assertIsInstance(future, TransferFuture)
        self.assertIsInstance(future.meta, TransferMeta)

    def test_returns_correct_call_args(self):
        self._setup_default_stubbed_responses()
        call_kwargs = self.create_call_kwargs()
        future = self.method(**call_kwargs)
        # The result is called so we ensure that the entire process executes
        # before we try to clean up resources in the tearDown.
        future.result()

        # Assert that there are call args associated to the metadata
        self.assertIsInstance(future.meta.call_args, CallArgs)
        # Assert that all of the arguments passed to the method exist and
        # are of the correct value in call_args.
        for param, value in call_kwargs.items():
            self.assertEqual(value, getattr(future.meta.call_args, param))

    def test_has_transfer_id_associated_to_future(self):
        self._setup_default_stubbed_responses()
        call_kwargs = self.create_call_kwargs()
        future = self.method(**call_kwargs)
        # The result is called so we ensure that the entire process executes
        # before we try to clean up resources in the tearDown.
        future.result()

        # Assert that an transfer id was associated to the future.
        # Since there is only one transfer request is made for that transfer
        # manager the id will be zero since it will be the first transfer
        # request made for that transfer manager.
        self.assertEqual(future.meta.transfer_id, 0)

        # If we make a second request, the transfer id should have incremented
        # by one for that new TransferFuture.
        self._setup_default_stubbed_responses()
        future = self.method(**call_kwargs)
        future.result()
        self.assertEqual(future.meta.transfer_id, 1)

    def test_invalid_extra_args(self):
        with self.assertRaisesRegex(ValueError, 'Invalid extra_args'):
            self.method(
                extra_args=self.create_invalid_extra_args(),
                **self.create_call_kwargs()
            )

    def test_for_callback_kwargs_correctness(self):
        # Add the stubbed responses before invoking the method
        self._setup_default_stubbed_responses()

        subscriber = RecordingSubscriber()
        future = self.method(
            subscribers=[subscriber], **self.create_call_kwargs())
        # We call shutdown instead of result on future because the future
        # could be finished but the done callback could still be going.
        # The manager's shutdown method ensures everything completes.
        self.manager.shutdown()

        # Assert the various subscribers were called with the
        # expected kwargs
        expected_progress_calls = self.create_expected_progress_callback_info()
        for expected_progress_call in expected_progress_calls:
            expected_progress_call['future'] = future

        self.assertEqual(subscriber.on_queued_calls, [{'future': future}])
        self.assertEqual(subscriber.on_progress_calls, expected_progress_calls)
        self.assertEqual(subscriber.on_done_calls, [{'future': future}])


class NonSeekableReader(io.RawIOBase):
    def __init__(self, b=b''):
        super(NonSeekableReader, self).__init__()
        self._data = six.BytesIO(b)

    def seekable(self):
        return False

    def writable(self):
        return False

    def readable(self):
        return True

    def write(self, b):
        # This is needed because python will not always return the correct
        # kind of error even though writeable returns False.
        raise io.UnsupportedOperation("write")

    def read(self, n=-1):
        return self._data.read(n)

    def readinto(self, b):
        return self._data.readinto(b)


class NonSeekableWriter(io.RawIOBase):
    def __init__(self, fileobj):
        super(NonSeekableWriter, self).__init__()
        self._fileobj = fileobj

    def seekable(self):
        return False

    def writable(self):
        return True

    def readable(self):
        return False

    def write(self, b):
        self._fileobj.write(b)

    def read(self, n=-1):
        raise io.UnsupportedOperation("read")
