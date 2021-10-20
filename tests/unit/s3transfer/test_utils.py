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
import os.path
import shutil
import tempfile
import threading
import random
import re
import time
import io


from tests import mock, unittest, RecordingSubscriber, NonSeekableWriter
from s3transfer.compat import six
from s3transfer.futures import TransferFuture
from s3transfer.futures import TransferMeta
from s3transfer.utils import get_callbacks
from s3transfer.utils import random_file_extension
from s3transfer.utils import invoke_progress_callbacks
from s3transfer.utils import calculate_num_parts
from s3transfer.utils import calculate_range_parameter
from s3transfer.utils import get_filtered_dict
from s3transfer.utils import CallArgs
from s3transfer.utils import FunctionContainer
from s3transfer.utils import CountCallbackInvoker
from s3transfer.utils import OSUtils
from s3transfer.utils import DeferredOpenFile
from s3transfer.utils import ReadFileChunk
from s3transfer.utils import StreamReaderProgress
from s3transfer.utils import TaskSemaphore
from s3transfer.utils import SlidingWindowSemaphore
from s3transfer.utils import NoResourcesAvailable
from s3transfer.utils import ChunksizeAdjuster
from s3transfer.utils import MIN_UPLOAD_CHUNKSIZE, MAX_SINGLE_UPLOAD_SIZE
from s3transfer.utils import MAX_PARTS


class TestGetCallbacks(unittest.TestCase):
    def setUp(self):
        self.subscriber = RecordingSubscriber()
        self.second_subscriber = RecordingSubscriber()
        self.call_args = CallArgs(subscribers=[
            self.subscriber, self.second_subscriber]
        )
        self.transfer_meta = TransferMeta(self.call_args)
        self.transfer_future = TransferFuture(self.transfer_meta)

    def test_get_callbacks(self):
        callbacks = get_callbacks(self.transfer_future, 'queued')
        # Make sure two callbacks were added as both subscribers had
        # an on_queued method.
        self.assertEqual(len(callbacks), 2)

        # Ensure that the callback was injected with the future by calling
        # one of them and checking that the future was used in the call.
        callbacks[0]()
        self.assertEqual(
            self.subscriber.on_queued_calls,
            [{'future': self.transfer_future}]
        )

    def test_get_callbacks_for_missing_type(self):
        callbacks = get_callbacks(self.transfer_future, 'fake_state')
        # There should be no callbacks as the subscribers will not have the
        # on_fake_state method
        self.assertEqual(len(callbacks), 0)


class TestGetFilteredDict(unittest.TestCase):
    def test_get_filtered_dict(self):
        original = {
            'Include': 'IncludeValue',
            'NotInlude': 'NotIncludeValue'
        }
        whitelist = ['Include']
        self.assertEqual(
            get_filtered_dict(original, whitelist),
            {'Include': 'IncludeValue'}
        )


class TestCallArgs(unittest.TestCase):
    def test_call_args(self):
        call_args = CallArgs(foo='bar', biz='baz')
        self.assertEqual(call_args.foo, 'bar')
        self.assertEqual(call_args.biz, 'baz')


class TestFunctionContainer(unittest.TestCase):
    def get_args_kwargs(self, *args, **kwargs):
        return args, kwargs

    def test_call(self):
        func_container = FunctionContainer(
            self.get_args_kwargs, 'foo', bar='baz')
        self.assertEqual(func_container(), (('foo',), {'bar': 'baz'}))

    def test_repr(self):
        func_container = FunctionContainer(
            self.get_args_kwargs, 'foo', bar='baz')
        self.assertEqual(
            str(func_container), 'Function: %s with args %s and kwargs %s' % (
                self.get_args_kwargs, ('foo',), {'bar': 'baz'}))


class TestCountCallbackInvoker(unittest.TestCase):
    def invoke_callback(self):
        self.ref_results.append('callback invoked')

    def assert_callback_invoked(self):
        self.assertEqual(self.ref_results, ['callback invoked'])

    def assert_callback_not_invoked(self):
        self.assertEqual(self.ref_results, [])

    def setUp(self):
        self.ref_results = []
        self.invoker = CountCallbackInvoker(self.invoke_callback)

    def test_increment(self):
        self.invoker.increment()
        self.assertEqual(self.invoker.current_count, 1)

    def test_decrement(self):
        self.invoker.increment()
        self.invoker.increment()
        self.invoker.decrement()
        self.assertEqual(self.invoker.current_count, 1)

    def test_count_cannot_go_below_zero(self):
        with self.assertRaises(RuntimeError):
            self.invoker.decrement()

    def test_callback_invoked_only_once_finalized(self):
        self.invoker.increment()
        self.invoker.decrement()
        self.assert_callback_not_invoked()
        self.invoker.finalize()
        # Callback should only be invoked once finalized
        self.assert_callback_invoked()

    def test_callback_invoked_after_finalizing_and_count_reaching_zero(self):
        self.invoker.increment()
        self.invoker.finalize()
        # Make sure that it does not get invoked immediately after
        # finalizing as the count is currently one
        self.assert_callback_not_invoked()
        self.invoker.decrement()
        self.assert_callback_invoked()

    def test_cannot_increment_after_finalization(self):
        self.invoker.finalize()
        with self.assertRaises(RuntimeError):
            self.invoker.increment()


class TestRandomFileExtension(unittest.TestCase):
    def test_has_proper_length(self):
        self.assertEqual(
            len(random_file_extension(num_digits=4)), 4)


class TestInvokeProgressCallbacks(unittest.TestCase):
    def test_invoke_progress_callbacks(self):
        recording_subscriber = RecordingSubscriber()
        invoke_progress_callbacks([recording_subscriber.on_progress], 2)
        self.assertEqual(recording_subscriber.calculate_bytes_seen(), 2)

    def test_invoke_progress_callbacks_with_no_progress(self):
        recording_subscriber = RecordingSubscriber()
        invoke_progress_callbacks([recording_subscriber.on_progress], 0)
        self.assertEqual(len(recording_subscriber.on_progress_calls), 0)


class TestCalculateNumParts(unittest.TestCase):
    def test_calculate_num_parts_divisible(self):
        self.assertEqual(calculate_num_parts(size=4, part_size=2), 2)

    def test_calculate_num_parts_not_divisible(self):
        self.assertEqual(calculate_num_parts(size=3, part_size=2), 2)


class TestCalculateRangeParameter(unittest.TestCase):
    def setUp(self):
        self.part_size = 5
        self.part_index = 1
        self.num_parts = 3

    def test_calculate_range_paramter(self):
        range_val = calculate_range_parameter(
            self.part_size, self.part_index, self.num_parts)
        self.assertEqual(range_val, 'bytes=5-9')

    def test_last_part_with_no_total_size(self):
        range_val = calculate_range_parameter(
            self.part_size, self.part_index, num_parts=2)
        self.assertEqual(range_val, 'bytes=5-')

    def test_last_part_with_total_size(self):
        range_val = calculate_range_parameter(
            self.part_size, self.part_index, num_parts=2, total_size=8)
        self.assertEqual(range_val, 'bytes=5-7')


class BaseUtilsTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.filename = os.path.join(self.tempdir, 'foo')
        self.content = b'abc'
        with open(self.filename, 'wb') as f:
            f.write(self.content)
        self.amounts_seen = []
        self.num_close_callback_calls = 0

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def callback(self, bytes_transferred):
        self.amounts_seen.append(bytes_transferred)

    def close_callback(self):
        self.num_close_callback_calls += 1


class TestOSUtils(BaseUtilsTest):
    def test_get_file_size(self):
        self.assertEqual(
            OSUtils().get_file_size(self.filename), len(self.content))

    def test_open_file_chunk_reader(self):
        reader = OSUtils().open_file_chunk_reader(
            self.filename, 0, 3, [self.callback])

        # The returned reader should be a ReadFileChunk.
        self.assertIsInstance(reader, ReadFileChunk)
        # The content of the reader should be correct.
        self.assertEqual(reader.read(), self.content)
        # Callbacks should be disabled depspite being passed in.
        self.assertEqual(self.amounts_seen, [])

    def test_open_file_chunk_reader_from_fileobj(self):
        with open(self.filename, 'rb') as f:
            reader = OSUtils().open_file_chunk_reader_from_fileobj(
                f, len(self.content), len(self.content), [self.callback])

            # The returned reader should be a ReadFileChunk.
            self.assertIsInstance(reader, ReadFileChunk)
            # The content of the reader should be correct.
            self.assertEqual(reader.read(), self.content)
            reader.close()
            # Callbacks should be disabled depspite being passed in.
            self.assertEqual(self.amounts_seen, [])
            self.assertEqual(self.num_close_callback_calls, 0)

    def test_open_file(self):
        fileobj = OSUtils().open(os.path.join(self.tempdir, 'foo'), 'w')
        self.assertTrue(hasattr(fileobj, 'write'))

    def test_remove_file_ignores_errors(self):
        non_existent_file = os.path.join(self.tempdir, 'no-exist')
        # This should not exist to start.
        self.assertFalse(os.path.exists(non_existent_file))
        try:
            OSUtils().remove_file(non_existent_file)
        except OSError as e:
            self.fail('OSError should have been caught: %s' % e)

    def test_remove_file_proxies_remove_file(self):
        OSUtils().remove_file(self.filename)
        self.assertFalse(os.path.exists(self.filename))

    def test_rename_file(self):
        new_filename = os.path.join(self.tempdir, 'newfoo')
        OSUtils().rename_file(self.filename, new_filename)
        self.assertFalse(os.path.exists(self.filename))
        self.assertTrue(os.path.exists(new_filename))

    def test_is_special_file_for_normal_file(self):
        self.assertFalse(OSUtils().is_special_file(self.filename))

    def test_is_special_file_for_non_existant_file(self):
        non_existant_filename = os.path.join(self.tempdir, 'no-exist')
        self.assertFalse(os.path.exists(non_existant_filename))
        self.assertFalse(OSUtils().is_special_file(non_existant_filename))

    def test_get_temp_filename(self):
        filename = 'myfile'
        self.assertIsNotNone(
            re.match(
                r'%s\.[0-9A-Fa-f]{8}$' % filename,
                OSUtils().get_temp_filename(filename)
            )
        )

    def test_get_temp_filename_len_255(self):
        filename = 'a'*255
        temp_filename = OSUtils().get_temp_filename(filename)
        self.assertLessEqual(len(temp_filename), 255)

    def test_get_temp_filename_len_gt_255(self):
        filename = 'a'*280
        temp_filename = OSUtils().get_temp_filename(filename)
        self.assertLessEqual(len(temp_filename), 255)

    def test_allocate(self):
        truncate_size = 1
        OSUtils().allocate(self.filename, truncate_size)
        with open(self.filename, 'rb') as f:
            self.assertEqual(len(f.read()), truncate_size)

    @mock.patch('s3transfer.utils.fallocate')
    def test_allocate_with_io_error(self, mock_fallocate):
        mock_fallocate.side_effect = IOError()
        with self.assertRaises(IOError):
            OSUtils().allocate(self.filename, 1)
        self.assertFalse(os.path.exists(self.filename))

    @mock.patch('s3transfer.utils.fallocate')
    def test_allocate_with_os_error(self, mock_fallocate):
        mock_fallocate.side_effect = OSError()
        with self.assertRaises(OSError):
            OSUtils().allocate(self.filename, 1)
        self.assertFalse(os.path.exists(self.filename))


class TestDeferredOpenFile(BaseUtilsTest):
    def setUp(self):
        super(TestDeferredOpenFile, self).setUp()
        self.filename = os.path.join(self.tempdir, 'foo')
        self.contents = b'my contents'
        with open(self.filename, 'wb') as f:
            f.write(self.contents)
        self.deferred_open_file = DeferredOpenFile(
            self.filename, open_function=self.recording_open_function)
        self.open_call_args = []

    def tearDown(self):
        self.deferred_open_file.close()
        super(TestDeferredOpenFile, self).tearDown()

    def recording_open_function(self, filename, mode):
        self.open_call_args.append((filename, mode))
        return open(filename, mode)

    def open_nonseekable(self, filename, mode):
        self.open_call_args.append((filename, mode))
        return NonSeekableWriter(six.BytesIO(self.content))

    def test_instantiation_does_not_open_file(self):
        DeferredOpenFile(
            self.filename, open_function=self.recording_open_function)
        self.assertEqual(len(self.open_call_args), 0)

    def test_name(self):
        self.assertEqual(self.deferred_open_file.name, self.filename)

    def test_read(self):
        content = self.deferred_open_file.read(2)
        self.assertEqual(content, self.contents[0:2])
        content = self.deferred_open_file.read(2)
        self.assertEqual(content, self.contents[2:4])
        self.assertEqual(len(self.open_call_args), 1)

    def test_write(self):
        self.deferred_open_file = DeferredOpenFile(
            self.filename, mode='wb',
            open_function=self.recording_open_function)

        write_content = b'foo'
        self.deferred_open_file.write(write_content)
        self.deferred_open_file.write(write_content)
        self.deferred_open_file.close()
        # Both of the writes should now be in the file.
        with open(self.filename, 'rb') as f:
            self.assertEqual(f.read(), write_content*2)
        # Open should have only been called once.
        self.assertEqual(len(self.open_call_args), 1)

    def test_seek(self):
        self.deferred_open_file.seek(2)
        content = self.deferred_open_file.read(2)
        self.assertEqual(content, self.contents[2:4])
        self.assertEqual(len(self.open_call_args), 1)

    def test_open_does_not_seek_with_zero_start_byte(self):
        self.deferred_open_file = DeferredOpenFile(
            self.filename, mode='wb', start_byte=0,
            open_function=self.open_nonseekable)

        try:
            # If this seeks, an UnsupportedOperation error will be raised.
            self.deferred_open_file.write(b'data')
        except io.UnsupportedOperation:
            self.fail('DeferredOpenFile seeked upon opening')

    def test_open_seeks_with_nonzero_start_byte(self):
        self.deferred_open_file = DeferredOpenFile(
            self.filename, mode='wb', start_byte=5,
            open_function=self.open_nonseekable)

        # Since a non-seekable file is being opened, calling Seek will raise
        # an UnsupportedOperation error.
        with self.assertRaises(io.UnsupportedOperation):
            self.deferred_open_file.write(b'data')

    def test_tell(self):
        self.deferred_open_file.tell()
        # tell() should not have opened the file if it has not been seeked
        # or read because we know the start bytes upfront.
        self.assertEqual(len(self.open_call_args), 0)

        self.deferred_open_file.seek(2)
        self.assertEqual(self.deferred_open_file.tell(), 2)
        self.assertEqual(len(self.open_call_args), 1)

    def test_open_args(self):
        self.deferred_open_file = DeferredOpenFile(
            self.filename, mode='ab+',
            open_function=self.recording_open_function)
        # Force an open
        self.deferred_open_file.write(b'data')
        self.assertEqual(len(self.open_call_args), 1)
        self.assertEqual(self.open_call_args[0], (self.filename, 'ab+'))

    def test_context_handler(self):
        with self.deferred_open_file:
            self.assertEqual(len(self.open_call_args), 1)


class TestReadFileChunk(BaseUtilsTest):
    def test_read_entire_chunk(self):
        filename = os.path.join(self.tempdir, 'foo')
        with open(filename, 'wb') as f:
            f.write(b'onetwothreefourfivesixseveneightnineten')
        chunk = ReadFileChunk.from_filename(
            filename, start_byte=0, chunk_size=3)
        self.assertEqual(chunk.read(), b'one')
        self.assertEqual(chunk.read(), b'')

    def test_read_with_amount_size(self):
        filename = os.path.join(self.tempdir, 'foo')
        with open(filename, 'wb') as f:
            f.write(b'onetwothreefourfivesixseveneightnineten')
        chunk = ReadFileChunk.from_filename(
            filename, start_byte=11, chunk_size=4)
        self.assertEqual(chunk.read(1), b'f')
        self.assertEqual(chunk.read(1), b'o')
        self.assertEqual(chunk.read(1), b'u')
        self.assertEqual(chunk.read(1), b'r')
        self.assertEqual(chunk.read(1), b'')

    def test_reset_stream_emulation(self):
        filename = os.path.join(self.tempdir, 'foo')
        with open(filename, 'wb') as f:
            f.write(b'onetwothreefourfivesixseveneightnineten')
        chunk = ReadFileChunk.from_filename(
            filename, start_byte=11, chunk_size=4)
        self.assertEqual(chunk.read(), b'four')
        chunk.seek(0)
        self.assertEqual(chunk.read(), b'four')

    def test_read_past_end_of_file(self):
        filename = os.path.join(self.tempdir, 'foo')
        with open(filename, 'wb') as f:
            f.write(b'onetwothreefourfivesixseveneightnineten')
        chunk = ReadFileChunk.from_filename(
            filename, start_byte=36, chunk_size=100000)
        self.assertEqual(chunk.read(), b'ten')
        self.assertEqual(chunk.read(), b'')
        self.assertEqual(len(chunk), 3)

    def test_tell_and_seek(self):
        filename = os.path.join(self.tempdir, 'foo')
        with open(filename, 'wb') as f:
            f.write(b'onetwothreefourfivesixseveneightnineten')
        chunk = ReadFileChunk.from_filename(
            filename, start_byte=36, chunk_size=100000)
        self.assertEqual(chunk.tell(), 0)
        self.assertEqual(chunk.read(), b'ten')
        self.assertEqual(chunk.tell(), 3)
        chunk.seek(0)
        self.assertEqual(chunk.tell(), 0)
        chunk.seek(1, whence=1)
        self.assertEqual(chunk.tell(), 1)
        chunk.seek(-1, whence=1)
        self.assertEqual(chunk.tell(), 0)
        chunk.seek(-1, whence=2)
        self.assertEqual(chunk.tell(), 2)

    def test_tell_and_seek_boundaries(self):
        # Test to ensure ReadFileChunk behaves the same as the
        # Python standard library around seeking and reading out
        # of bounds in a file object.
        data = b'abcdefghij12345678klmnopqrst'
        start_pos = 10
        chunk_size = 8

        # Create test file
        filename = os.path.join(self.tempdir, 'foo')
        with open(filename, 'wb') as f:
            f.write(data)

        # ReadFileChunk should be a substring of only numbers
        file_objects = [
            ReadFileChunk.from_filename(
                filename, start_byte=start_pos, chunk_size=chunk_size
            )]

        # Uncomment next line to validate we match Python's io.BytesIO
        # file_objects.append(io.BytesIO(data[start_pos:start_pos+chunk_size]))

        for obj in file_objects:
            self._assert_whence_start_behavior(obj)
            self._assert_whence_end_behavior(obj)
            self._assert_whence_relative_behavior(obj)
            self._assert_boundary_behavior(obj)

    def _assert_whence_start_behavior(self, file_obj):
        self.assertEqual(file_obj.tell(), 0)

        file_obj.seek(1, 0)
        self.assertEqual(file_obj.tell(), 1)

        file_obj.seek(1)
        self.assertEqual(file_obj.tell(), 1)
        self.assertEqual(file_obj.read(), b'2345678')

        file_obj.seek(3, 0)
        self.assertEqual(file_obj.tell(), 3)

        file_obj.seek(0, 0)
        self.assertEqual(file_obj.tell(), 0)

    def _assert_whence_relative_behavior(self, file_obj):
        self.assertEqual(file_obj.tell(), 0)

        file_obj.seek(2, 1)
        self.assertEqual(file_obj.tell(), 2)

        file_obj.seek(1, 1)
        self.assertEqual(file_obj.tell(), 3)
        self.assertEqual(file_obj.read(), b'45678')

        file_obj.seek(20, 1)
        self.assertEqual(file_obj.tell(), 28)

        file_obj.seek(-30, 1)
        self.assertEqual(file_obj.tell(), 0)
        self.assertEqual(file_obj.read(), b'12345678')

        file_obj.seek(-8, 1)
        self.assertEqual(file_obj.tell(), 0)

    def _assert_whence_end_behavior(self, file_obj):
        self.assertEqual(file_obj.tell(), 0)

        file_obj.seek(-1, 2)
        self.assertEqual(file_obj.tell(), 7)

        file_obj.seek(1, 2)
        self.assertEqual(file_obj.tell(), 9)

        file_obj.seek(3, 2)
        self.assertEqual(file_obj.tell(), 11)
        self.assertEqual(file_obj.read(), b'')

        file_obj.seek(-15, 2)
        self.assertEqual(file_obj.tell(), 0)
        self.assertEqual(file_obj.read(), b'12345678')

        file_obj.seek(-8, 2)
        self.assertEqual(file_obj.tell(), 0)

    def _assert_boundary_behavior(self, file_obj):
        # Verify we're at the start
        self.assertEqual(file_obj.tell(), 0)

        # Verify we can't move backwards beyond start of file
        file_obj.seek(-10, 1)
        self.assertEqual(file_obj.tell(), 0)

        # Verify we *can* move after end of file, but return nothing
        file_obj.seek(10, 2)
        self.assertEqual(file_obj.tell(), 18)
        self.assertEqual(file_obj.read(), b'')
        self.assertEqual(file_obj.read(10), b'')

        # Verify we can partially rewind
        file_obj.seek(-12, 1)
        self.assertEqual(file_obj.tell(), 6)
        self.assertEqual(file_obj.read(), b'78')
        self.assertEqual(file_obj.tell(), 8)

        # Verify we can rewind to start
        file_obj.seek(0)
        self.assertEqual(file_obj.tell(), 0)

    def test_file_chunk_supports_context_manager(self):
        filename = os.path.join(self.tempdir, 'foo')
        with open(filename, 'wb') as f:
            f.write(b'abc')
        with ReadFileChunk.from_filename(filename,
                                         start_byte=0,
                                         chunk_size=2) as chunk:
            val = chunk.read()
            self.assertEqual(val, b'ab')

    def test_iter_is_always_empty(self):
        # This tests the workaround for the httplib bug (see
        # the source for more info).
        filename = os.path.join(self.tempdir, 'foo')
        open(filename, 'wb').close()
        chunk = ReadFileChunk.from_filename(
            filename, start_byte=0, chunk_size=10)
        self.assertEqual(list(chunk), [])

    def test_callback_is_invoked_on_read(self):
        chunk = ReadFileChunk.from_filename(
            self.filename, start_byte=0, chunk_size=3,
            callbacks=[self.callback])
        chunk.read(1)
        chunk.read(1)
        chunk.read(1)
        self.assertEqual(self.amounts_seen, [1, 1, 1])

    def test_all_callbacks_invoked_on_read(self):
        chunk = ReadFileChunk.from_filename(
            self.filename, start_byte=0, chunk_size=3,
            callbacks=[self.callback, self.callback])
        chunk.read(1)
        chunk.read(1)
        chunk.read(1)
        # The list should be twice as long because there are two callbacks
        # recording the amount read.
        self.assertEqual(self.amounts_seen, [1, 1, 1, 1, 1, 1])

    def test_callback_can_be_disabled(self):
        chunk = ReadFileChunk.from_filename(
            self.filename, start_byte=0, chunk_size=3,
            callbacks=[self.callback])
        chunk.disable_callback()
        # Now reading from the ReadFileChunk should not invoke
        # the callback.
        chunk.read()
        self.assertEqual(self.amounts_seen, [])

    def test_callback_will_also_be_triggered_by_seek(self):
        chunk = ReadFileChunk.from_filename(
            self.filename, start_byte=0, chunk_size=3,
            callbacks=[self.callback])
        chunk.read(2)
        chunk.seek(0)
        chunk.read(2)
        chunk.seek(1)
        chunk.read(2)
        self.assertEqual(self.amounts_seen, [2, -2, 2, -1, 2])

    def test_callback_triggered_by_out_of_bound_seeks(self):
        data = b'abcdefghij1234567890klmnopqr'

        # Create test file
        filename = os.path.join(self.tempdir, 'foo')
        with open(filename, 'wb') as f:
            f.write(data)
        chunk = ReadFileChunk.from_filename(
            filename, start_byte=10, chunk_size=10,
            callbacks=[self.callback])

        # Seek calls that generate "0" progress are skipped by
        # invoke_progress_callbacks and won't appear in the list.
        expected_callback_prog = [10, -5, 5, -1, 1, -1, 1, -5, 5, -10]

        self._assert_out_of_bound_start_seek(chunk, expected_callback_prog)
        self._assert_out_of_bound_relative_seek(chunk, expected_callback_prog)
        self._assert_out_of_bound_end_seek(chunk, expected_callback_prog)

    def _assert_out_of_bound_start_seek(self, chunk, expected):
        # clear amounts_seen
        self.amounts_seen = []
        self.assertEqual(self.amounts_seen, [])

        # (position, change)
        chunk.seek(20)  # (20, 10)
        chunk.seek(5)   # (5, -5)
        chunk.seek(20)  # (20, 5)
        chunk.seek(9)   # (9, -1)
        chunk.seek(20)  # (20, 1)
        chunk.seek(11)  # (11, 0)
        chunk.seek(20)  # (20, 0)
        chunk.seek(9)   # (9, -1)
        chunk.seek(20)  # (20, 1)
        chunk.seek(5)   # (5, -5)
        chunk.seek(20)  # (20, 5)
        chunk.seek(0)   # (0, -10)
        chunk.seek(0)   # (0, 0)

        self.assertEqual(self.amounts_seen, expected)

    def _assert_out_of_bound_relative_seek(self, chunk, expected):
        # clear amounts_seen
        self.amounts_seen = []
        self.assertEqual(self.amounts_seen, [])

        # (position, change)
        chunk.seek(20, 1)     # (20, 10)
        chunk.seek(-15, 1)    # (5, -5)
        chunk.seek(15, 1)     # (20, 5)
        chunk.seek(-11, 1)    # (9, -1)
        chunk.seek(11, 1)     # (20, 1)
        chunk.seek(-9, 1)     # (11, 0)
        chunk.seek(9, 1)      # (20, 0)
        chunk.seek(-11, 1)    # (9, -1)
        chunk.seek(11, 1)     # (20, 1)
        chunk.seek(-15, 1)    # (5, -5)
        chunk.seek(15, 1)     # (20, 5)
        chunk.seek(-20, 1)    # (0, -10)
        chunk.seek(-1000, 1)  # (0, 0)

        self.assertEqual(self.amounts_seen, expected)

    def _assert_out_of_bound_end_seek(self, chunk, expected):
        # clear amounts_seen
        self.amounts_seen = []
        self.assertEqual(self.amounts_seen, [])

        # (position, change)
        chunk.seek(10, 2)     # (20, 10)
        chunk.seek(-5, 2)     # (5, -5)
        chunk.seek(10, 2)     # (20, 5)
        chunk.seek(-1, 2)     # (9, -1)
        chunk.seek(10, 2)     # (20, 1)
        chunk.seek(1, 2)      # (11, 0)
        chunk.seek(10, 2)     # (20, 0)
        chunk.seek(-1, 2)     # (9, -1)
        chunk.seek(10, 2)     # (20, 1)
        chunk.seek(-5, 2)     # (5, -5)
        chunk.seek(10, 2)     # (20, 5)
        chunk.seek(-10, 2)    # (0, -10)
        chunk.seek(-1000, 2)  # (0, 0)

        self.assertEqual(self.amounts_seen, expected)

    def test_close_callbacks(self):
        with open(self.filename) as f:
            chunk = ReadFileChunk(f, chunk_size=1, full_file_size=3,
                                  close_callbacks=[self.close_callback])
            chunk.close()
            self.assertEqual(self.num_close_callback_calls, 1)

    def test_close_callbacks_when_not_enabled(self):
        with open(self.filename) as f:
            chunk = ReadFileChunk(f, chunk_size=1, full_file_size=3,
                                  enable_callbacks=False,
                                  close_callbacks=[self.close_callback])
            chunk.close()
            self.assertEqual(self.num_close_callback_calls, 0)

    def test_close_callbacks_when_context_handler_is_used(self):
        with open(self.filename) as f:
            with ReadFileChunk(f, chunk_size=1, full_file_size=3,
                               close_callbacks=[self.close_callback]) as chunk:
                chunk.read(1)
            self.assertEqual(self.num_close_callback_calls, 1)

    def test_signal_transferring(self):
        chunk = ReadFileChunk.from_filename(
            self.filename, start_byte=0, chunk_size=3,
            callbacks=[self.callback])
        chunk.signal_not_transferring()
        chunk.read(1)
        self.assertEqual(self.amounts_seen, [])
        chunk.signal_transferring()
        chunk.read(1)
        self.assertEqual(self.amounts_seen, [1])

    def test_signal_transferring_to_underlying_fileobj(self):
        underlying_stream = mock.Mock()
        underlying_stream.tell.return_value = 0
        chunk = ReadFileChunk(underlying_stream, 3, 3)
        chunk.signal_transferring()
        self.assertTrue(underlying_stream.signal_transferring.called)

    def test_no_call_signal_transferring_to_underlying_fileobj(self):
        underlying_stream = mock.Mock(io.RawIOBase)
        underlying_stream.tell.return_value = 0
        chunk = ReadFileChunk(underlying_stream, 3, 3)
        try:
            chunk.signal_transferring()
        except AttributeError:
            self.fail(
                'The stream should not have tried to call signal_transferring '
                'to the underlying stream.'
            )

    def test_signal_not_transferring_to_underlying_fileobj(self):
        underlying_stream = mock.Mock()
        underlying_stream.tell.return_value = 0
        chunk = ReadFileChunk(underlying_stream, 3, 3)
        chunk.signal_not_transferring()
        self.assertTrue(underlying_stream.signal_not_transferring.called)

    def test_no_call_signal_not_transferring_to_underlying_fileobj(self):
        underlying_stream = mock.Mock(io.RawIOBase)
        underlying_stream.tell.return_value = 0
        chunk = ReadFileChunk(underlying_stream, 3, 3)
        try:
            chunk.signal_not_transferring()
        except AttributeError:
            self.fail(
                'The stream should not have tried to call '
                'signal_not_transferring to the underlying stream.'
            )


class TestStreamReaderProgress(BaseUtilsTest):
    def test_proxies_to_wrapped_stream(self):
        original_stream = six.StringIO('foobarbaz')
        wrapped = StreamReaderProgress(original_stream)
        self.assertEqual(wrapped.read(), 'foobarbaz')

    def test_callback_invoked(self):
        original_stream = six.StringIO('foobarbaz')
        wrapped = StreamReaderProgress(
            original_stream, [self.callback, self.callback])
        self.assertEqual(wrapped.read(), 'foobarbaz')
        self.assertEqual(self.amounts_seen, [9, 9])


class TestTaskSemaphore(unittest.TestCase):
    def setUp(self):
        self.semaphore = TaskSemaphore(1)

    def test_should_block_at_max_capacity(self):
        self.semaphore.acquire('a', blocking=False)
        with self.assertRaises(NoResourcesAvailable):
            self.semaphore.acquire('a', blocking=False)

    def test_release_capacity(self):
        acquire_token = self.semaphore.acquire('a', blocking=False)
        self.semaphore.release('a', acquire_token)
        try:
            self.semaphore.acquire('a', blocking=False)
        except NoResourcesAvailable:
            self.fail(
                'The release of the semaphore should have allowed for '
                'the second acquire to not be blocked'
            )


class TestSlidingWindowSemaphore(unittest.TestCase):
    # These tests use block=False to tests will fail
    # instead of hang the test runner in the case of x
    # incorrect behavior.
    def test_acquire_release_basic_case(self):
        sem = SlidingWindowSemaphore(1)
        # Count is 1

        num = sem.acquire('a', blocking=False)
        self.assertEqual(num, 0)
        sem.release('a', 0)
        # Count now back to 1.

    def test_can_acquire_release_multiple_times(self):
        sem = SlidingWindowSemaphore(1)
        num = sem.acquire('a', blocking=False)
        self.assertEqual(num, 0)
        sem.release('a', num)

        num = sem.acquire('a', blocking=False)
        self.assertEqual(num, 1)
        sem.release('a', num)

    def test_can_acquire_a_range(self):
        sem = SlidingWindowSemaphore(3)
        self.assertEqual(sem.acquire('a', blocking=False), 0)
        self.assertEqual(sem.acquire('a', blocking=False), 1)
        self.assertEqual(sem.acquire('a', blocking=False), 2)
        sem.release('a', 0)
        sem.release('a', 1)
        sem.release('a', 2)
        # Now we're reset so we should be able to acquire the same
        # sequence again.
        self.assertEqual(sem.acquire('a', blocking=False), 3)
        self.assertEqual(sem.acquire('a', blocking=False), 4)
        self.assertEqual(sem.acquire('a', blocking=False), 5)
        self.assertEqual(sem.current_count(), 0)

    def test_counter_release_only_on_min_element(self):
        sem = SlidingWindowSemaphore(3)
        sem.acquire('a', blocking=False)
        sem.acquire('a', blocking=False)
        sem.acquire('a', blocking=False)

        # The count only increases when we free the min
        # element.  This means if we're currently failing to
        # acquire now:
        with self.assertRaises(NoResourcesAvailable):
            sem.acquire('a', blocking=False)

        # Then freeing a non-min element:
        sem.release('a', 1)

        # doesn't change anything.  We still fail to acquire.
        with self.assertRaises(NoResourcesAvailable):
            sem.acquire('a', blocking=False)
        self.assertEqual(sem.current_count(), 0)

    def test_raises_error_when_count_is_zero(self):
        sem = SlidingWindowSemaphore(3)
        sem.acquire('a', blocking=False)
        sem.acquire('a', blocking=False)
        sem.acquire('a', blocking=False)

        # Count is now 0 so trying to acquire should fail.
        with self.assertRaises(NoResourcesAvailable):
            sem.acquire('a', blocking=False)

    def test_release_counters_can_increment_counter_repeatedly(self):
        sem = SlidingWindowSemaphore(3)
        sem.acquire('a', blocking=False)
        sem.acquire('a', blocking=False)
        sem.acquire('a', blocking=False)

        # These two releases don't increment the counter
        # because we're waiting on 0.
        sem.release('a', 1)
        sem.release('a', 2)
        self.assertEqual(sem.current_count(), 0)
        # But as soon as we release 0, we free up 0, 1, and 2.
        sem.release('a', 0)
        self.assertEqual(sem.current_count(), 3)
        sem.acquire('a', blocking=False)
        sem.acquire('a', blocking=False)
        sem.acquire('a', blocking=False)

    def test_error_to_release_unknown_tag(self):
        sem = SlidingWindowSemaphore(3)
        with self.assertRaises(ValueError):
            sem.release('a', 0)

    def test_can_track_multiple_tags(self):
        sem = SlidingWindowSemaphore(3)
        self.assertEqual(sem.acquire('a', blocking=False), 0)
        self.assertEqual(sem.acquire('b', blocking=False), 0)
        self.assertEqual(sem.acquire('a', blocking=False), 1)

        # We're at our max of 3 even though 2 are for A and 1 is for B.
        with self.assertRaises(NoResourcesAvailable):
            sem.acquire('a', blocking=False)
        with self.assertRaises(NoResourcesAvailable):
            sem.acquire('b', blocking=False)

    def test_can_handle_multiple_tags_released(self):
        sem = SlidingWindowSemaphore(4)
        sem.acquire('a', blocking=False)
        sem.acquire('a', blocking=False)
        sem.acquire('b', blocking=False)
        sem.acquire('b', blocking=False)

        sem.release('b', 1)
        sem.release('a', 1)
        self.assertEqual(sem.current_count(), 0)

        sem.release('b', 0)
        self.assertEqual(sem.acquire('a', blocking=False), 2)

        sem.release('a', 0)
        self.assertEqual(sem.acquire('b', blocking=False), 2)

    def test_is_error_to_release_unknown_sequence_number(self):
        sem = SlidingWindowSemaphore(3)
        sem.acquire('a', blocking=False)
        with self.assertRaises(ValueError):
            sem.release('a', 1)

    def test_is_error_to_double_release(self):
        # This is different than other error tests because
        # we're verifying we can reset the state after an
        # acquire/release cycle.
        sem = SlidingWindowSemaphore(2)
        sem.acquire('a', blocking=False)
        sem.acquire('a', blocking=False)
        sem.release('a', 0)
        sem.release('a', 1)
        self.assertEqual(sem.current_count(), 2)
        with self.assertRaises(ValueError):
            sem.release('a', 0)

    def test_can_check_in_partial_range(self):
        sem = SlidingWindowSemaphore(4)
        sem.acquire('a', blocking=False)
        sem.acquire('a', blocking=False)
        sem.acquire('a', blocking=False)
        sem.acquire('a', blocking=False)

        sem.release('a', 1)
        sem.release('a', 3)
        sem.release('a', 0)
        self.assertEqual(sem.current_count(), 2)


class TestThreadingPropertiesForSlidingWindowSemaphore(unittest.TestCase):
    # These tests focus on mutithreaded properties of the range
    # semaphore.  Basic functionality is tested in TestSlidingWindowSemaphore.
    def setUp(self):
        self.threads = []

    def tearDown(self):
        self.join_threads()

    def join_threads(self):
        for thread in self.threads:
            thread.join()
        self.threads = []

    def start_threads(self):
        for thread in self.threads:
            thread.start()

    def test_acquire_blocks_until_release_is_called(self):
        sem = SlidingWindowSemaphore(2)
        sem.acquire('a', blocking=False)
        sem.acquire('a', blocking=False)

        def acquire():
            # This next call to acquire will block.
            self.assertEqual(sem.acquire('a', blocking=True), 2)

        t = threading.Thread(target=acquire)
        self.threads.append(t)
        # Starting the thread will block the sem.acquire()
        # in the acquire function above.
        t.start()
        # This still will keep the thread blocked.
        sem.release('a', 1)
        # Releasing the min element will unblock the thread.
        sem.release('a', 0)
        t.join()
        sem.release('a', 2)

    def test_stress_invariants_random_order(self):
        sem = SlidingWindowSemaphore(100)
        for _ in range(10):
            recorded = []
            for _ in range(100):
                recorded.append(sem.acquire('a', blocking=False))
            # Release them in randomized order.  As long as we
            # eventually free all 100, we should have all the
            # resources released.
            random.shuffle(recorded)
            for i in recorded:
                sem.release('a', i)

        # Everything's freed so should be back at count == 100
        self.assertEqual(sem.current_count(), 100)

    def test_blocking_stress(self):
        sem = SlidingWindowSemaphore(5)
        num_threads = 10
        num_iterations = 50

        def acquire():
            for _ in range(num_iterations):
                num = sem.acquire('a', blocking=True)
                time.sleep(0.001)
                sem.release('a', num)

        for i in range(num_threads):
            t = threading.Thread(target=acquire)
            self.threads.append(t)
        self.start_threads()
        self.join_threads()
        # Should have all the available resources freed.
        self.assertEqual(sem.current_count(), 5)
        # Should have acquired num_threads * num_iterations
        self.assertEqual(sem.acquire('a', blocking=False),
                         num_threads * num_iterations)


class TestAdjustChunksize(unittest.TestCase):
    def setUp(self):
        self.adjuster = ChunksizeAdjuster()

    def test_valid_chunksize(self):
        chunksize = 7 * (1024 ** 2)
        file_size = 8 * (1024 ** 2)
        new_size = self.adjuster.adjust_chunksize(chunksize, file_size)
        self.assertEqual(new_size, chunksize)

    def test_chunksize_below_minimum(self):
        chunksize = MIN_UPLOAD_CHUNKSIZE - 1
        file_size = 3 * MIN_UPLOAD_CHUNKSIZE
        new_size = self.adjuster.adjust_chunksize(chunksize, file_size)
        self.assertEqual(new_size, MIN_UPLOAD_CHUNKSIZE)

    def test_chunksize_above_maximum(self):
        chunksize = MAX_SINGLE_UPLOAD_SIZE + 1
        file_size = MAX_SINGLE_UPLOAD_SIZE * 2
        new_size = self.adjuster.adjust_chunksize(chunksize, file_size)
        self.assertEqual(new_size, MAX_SINGLE_UPLOAD_SIZE)

    def test_chunksize_too_small(self):
        chunksize = 7 * (1024 ** 2)
        file_size = 5 * (1024 ** 4)
        # If we try to upload a 5TB file, we'll need to use 896MB part
        # sizes.
        new_size = self.adjuster.adjust_chunksize(chunksize, file_size)
        self.assertEqual(new_size, 896 * (1024 ** 2))
        num_parts = file_size / new_size
        self.assertLessEqual(num_parts, MAX_PARTS)

    def test_unknown_file_size_with_valid_chunksize(self):
        chunksize = 7 * (1024 ** 2)
        new_size = self.adjuster.adjust_chunksize(chunksize)
        self.assertEqual(new_size, chunksize)

    def test_unknown_file_size_below_minimum(self):
        chunksize = MIN_UPLOAD_CHUNKSIZE - 1
        new_size = self.adjuster.adjust_chunksize(chunksize)
        self.assertEqual(new_size, MIN_UPLOAD_CHUNKSIZE)

    def test_unknown_file_size_above_maximum(self):
        chunksize = MAX_SINGLE_UPLOAD_SIZE + 1
        new_size = self.adjuster.adjust_chunksize(chunksize)
        self.assertEqual(new_size, MAX_SINGLE_UPLOAD_SIZE)
