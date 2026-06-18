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
import os
import shutil
import tempfile
from concurrent import futures
from contextlib import closing
from io import BytesIO, StringIO

from s3transfer import (
    MultipartDownloader,
    MultipartUploader,
    OSUtils,
    QueueShutdownError,
    ReadFileChunk,
    S3Transfer,
    ShutdownQueue,
    StreamReaderProgress,
    TransferConfig,
    disable_upload_callbacks,
    enable_upload_callbacks,
    random_file_extension,
)
from s3transfer.exceptions import RetriesExceededError, S3UploadFailedError
from tests import mock, unittest


class InMemoryOSLayer(OSUtils):
    def __init__(self, filemap):
        self.filemap = filemap

    def get_file_size(self, filename):
        return len(self.filemap[filename])

    def open_file_chunk_reader(self, filename, start_byte, size, callback):
        return closing(BytesIO(self.filemap[filename]))

    def open(self, filename, mode):
        if 'wb' in mode:
            fileobj = BytesIO()
            self.filemap[filename] = fileobj
            return closing(fileobj)
        else:
            return closing(self.filemap[filename])

    def remove_file(self, filename):
        if filename in self.filemap:
            del self.filemap[filename]

    def rename_file(self, current_filename, new_filename):
        if current_filename in self.filemap:
            self.filemap[new_filename] = self.filemap.pop(current_filename)


class SequentialExecutor:
    def __init__(self, max_workers):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        pass

    # The real map() interface actually takes *args, but we specifically do
    # _not_ use this interface.
    def map(self, function, args):
        results = []
        for arg in args:
            results.append(function(arg))
        return results

    def submit(self, function):
        future = futures.Future()
        future.set_result(function())
        return future


class TestOSUtils(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_get_file_size(self):
        with mock.patch('os.path.getsize') as m:
            OSUtils().get_file_size('myfile')
            m.assert_called_with('myfile')

    def test_open_file_chunk_reader(self):
        with mock.patch('s3transfer.ReadFileChunk') as m:
            OSUtils().open_file_chunk_reader('myfile', 0, 100, None)
            m.from_filename.assert_called_with(
                'myfile', 0, 100, None, enable_callback=False
            )

    def test_open_file(self):
        fileobj = OSUtils().open(os.path.join(self.tempdir, 'foo'), 'w')
        self.assertTrue(hasattr(fileobj, 'write'))

    def test_remove_file_ignores_errors(self):
        with mock.patch('os.remove') as remove:
            remove.side_effect = OSError('fake error')
            OSUtils().remove_file('foo')
        remove.assert_called_with('foo')

    def test_remove_file_proxies_remove_file(self):
        with mock.patch('os.remove') as remove:
            OSUtils().remove_file('foo')
            remove.assert_called_with('foo')

    def test_rename_file(self):
        with mock.patch('s3transfer.compat.rename_file') as rename_file:
            OSUtils().rename_file('foo', 'newfoo')
            rename_file.assert_called_with('foo', 'newfoo')


class TestReadFileChunk(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_read_entire_chunk(self):
        filename = os.path.join(self.tempdir, 'foo')
        with open(filename, 'wb') as f:
            f.write(b'onetwothreefourfivesixseveneightnineten')
        chunk = ReadFileChunk.from_filename(
            filename, start_byte=0, chunk_size=3
        )
        self.assertEqual(chunk.read(), b'one')
        self.assertEqual(chunk.read(), b'')

    def test_read_with_amount_size(self):
        filename = os.path.join(self.tempdir, 'foo')
        with open(filename, 'wb') as f:
            f.write(b'onetwothreefourfivesixseveneightnineten')
        chunk = ReadFileChunk.from_filename(
            filename, start_byte=11, chunk_size=4
        )
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
            filename, start_byte=11, chunk_size=4
        )
        self.assertEqual(chunk.read(), b'four')
        chunk.seek(0)
        self.assertEqual(chunk.read(), b'four')

    def test_read_past_end_of_file(self):
        filename = os.path.join(self.tempdir, 'foo')
        with open(filename, 'wb') as f:
            f.write(b'onetwothreefourfivesixseveneightnineten')
        chunk = ReadFileChunk.from_filename(
            filename, start_byte=36, chunk_size=100000
        )
        self.assertEqual(chunk.read(), b'ten')
        self.assertEqual(chunk.read(), b'')
        self.assertEqual(len(chunk), 3)

    def test_tell_and_seek(self):
        filename = os.path.join(self.tempdir, 'foo')
        with open(filename, 'wb') as f:
            f.write(b'onetwothreefourfivesixseveneightnineten')
        chunk = ReadFileChunk.from_filename(
            filename, start_byte=36, chunk_size=100000
        )
        self.assertEqual(chunk.tell(), 0)
        self.assertEqual(chunk.read(), b'ten')
        self.assertEqual(chunk.tell(), 3)
        chunk.seek(0)
        self.assertEqual(chunk.tell(), 0)

    def test_file_chunk_supports_context_manager(self):
        filename = os.path.join(self.tempdir, 'foo')
        with open(filename, 'wb') as f:
            f.write(b'abc')
        with ReadFileChunk.from_filename(
            filename, start_byte=0, chunk_size=2
        ) as chunk:
            val = chunk.read()
            self.assertEqual(val, b'ab')

    def test_iter_is_always_empty(self):
        # This tests the workaround for the httplib bug (see
        # the source for more info).
        filename = os.path.join(self.tempdir, 'foo')
        open(filename, 'wb').close()
        chunk = ReadFileChunk.from_filename(
            filename, start_byte=0, chunk_size=10
        )
        self.assertEqual(list(chunk), [])


class TestReadFileChunkWithCallback(TestReadFileChunk):
    def setUp(self):
        super().setUp()
        self.filename = os.path.join(self.tempdir, 'foo')
        with open(self.filename, 'wb') as f:
            f.write(b'abc')
        self.amounts_seen = []

    def callback(self, amount):
        self.amounts_seen.append(amount)

    def test_callback_is_invoked_on_read(self):
        chunk = ReadFileChunk.from_filename(
            self.filename, start_byte=0, chunk_size=3, callback=self.callback
        )
        chunk.read(1)
        chunk.read(1)
        chunk.read(1)
        self.assertEqual(self.amounts_seen, [1, 1, 1])

    def test_callback_can_be_disabled(self):
        chunk = ReadFileChunk.from_filename(
            self.filename, start_byte=0, chunk_size=3, callback=self.callback
        )
        chunk.disable_callback()
        # Now reading from the ReadFileChunk should not invoke
        # the callback.
        chunk.read()
        self.assertEqual(self.amounts_seen, [])

    def test_callback_will_also_be_triggered_by_seek(self):
        chunk = ReadFileChunk.from_filename(
            self.filename, start_byte=0, chunk_size=3, callback=self.callback
        )
        chunk.read(2)
        chunk.seek(0)
        chunk.read(2)
        chunk.seek(1)
        chunk.read(2)
        self.assertEqual(self.amounts_seen, [2, -2, 2, -1, 2])


class TestStreamReaderProgress(unittest.TestCase):
    def test_proxies_to_wrapped_stream(self):
        original_stream = StringIO('foobarbaz')
        wrapped = StreamReaderProgress(original_stream)
        self.assertEqual(wrapped.read(), 'foobarbaz')

    def test_callback_invoked(self):
        amounts_seen = []

        def callback(amount):
            amounts_seen.append(amount)

        original_stream = StringIO('foobarbaz')
        wrapped = StreamReaderProgress(original_stream, callback)
        self.assertEqual(wrapped.read(), 'foobarbaz')
        self.assertEqual(amounts_seen, [9])


class TestMultipartUploader(unittest.TestCase):
    def test_multipart_upload_uses_correct_client_calls(self):
        client = mock.Mock()
        uploader = MultipartUploader(
            client,
            TransferConfig(),
            InMemoryOSLayer({'filename': b'foobar'}),
            SequentialExecutor,
        )
        client.create_multipart_upload.return_value = {'UploadId': 'upload_id'}
        client.upload_part.return_value = {'ETag': 'first'}

        uploader.upload_file('filename', 'bucket', 'key', None, {})

        # We need to check both the sequence of calls (create/upload/complete)
        # as well as the params passed between the calls, including
        # 1. The upload_id was plumbed through
        # 2. The collected etags were added to the complete call.
        client.create_multipart_upload.assert_called_with(
            Bucket='bucket', Key='key'
        )
        # Should be two parts.
        client.upload_part.assert_called_with(
            Body=mock.ANY,
            Bucket='bucket',
            UploadId='upload_id',
            Key='key',
            PartNumber=1,
        )
        client.complete_multipart_upload.assert_called_with(
            MultipartUpload={'Parts': [{'PartNumber': 1, 'ETag': 'first'}]},
            Bucket='bucket',
            UploadId='upload_id',
            Key='key',
        )

    def test_multipart_upload_injects_proper_kwargs(self):
        client = mock.Mock()
        uploader = MultipartUploader(
            client,
            TransferConfig(),
            InMemoryOSLayer({'filename': b'foobar'}),
            SequentialExecutor,
        )
        client.create_multipart_upload.return_value = {'UploadId': 'upload_id'}
        client.upload_part.return_value = {'ETag': 'first'}

        extra_args = {
            'SSECustomerKey': 'fakekey',
            'SSECustomerAlgorithm': 'AES256',
            'StorageClass': 'REDUCED_REDUNDANCY',
        }
        uploader.upload_file('filename', 'bucket', 'key', None, extra_args)

        client.create_multipart_upload.assert_called_with(
            Bucket='bucket',
            Key='key',
            # The initial call should inject all the storage class params.
            SSECustomerKey='fakekey',
            SSECustomerAlgorithm='AES256',
            StorageClass='REDUCED_REDUNDANCY',
        )
        client.upload_part.assert_called_with(
            Body=mock.ANY,
            Bucket='bucket',
            UploadId='upload_id',
            Key='key',
            PartNumber=1,
            # We only have to forward certain **extra_args in subsequent
            # UploadPart calls.
            SSECustomerKey='fakekey',
            SSECustomerAlgorithm='AES256',
        )
        client.complete_multipart_upload.assert_called_with(
            MultipartUpload={'Parts': [{'PartNumber': 1, 'ETag': 'first'}]},
            Bucket='bucket',
            UploadId='upload_id',
            Key='key',
        )

    def test_multipart_upload_is_aborted_on_error(self):
        # If the create_multipart_upload succeeds and any upload_part
        # fails, then abort_multipart_upload will be called.
        client = mock.Mock()
        uploader = MultipartUploader(
            client,
            TransferConfig(),
            InMemoryOSLayer({'filename': b'foobar'}),
            SequentialExecutor,
        )
        client.create_multipart_upload.return_value = {'UploadId': 'upload_id'}
        client.upload_part.side_effect = Exception(
            "Some kind of error occurred."
        )

        with self.assertRaises(S3UploadFailedError):
            uploader.upload_file('filename', 'bucket', 'key', None, {})

        client.abort_multipart_upload.assert_called_with(
            Bucket='bucket', Key='key', UploadId='upload_id'
        )


class TestMultipartDownloader(unittest.TestCase):
    maxDiff = None

    def test_multipart_download_uses_correct_client_calls(self):
        client = mock.Mock()
        response_body = b'foobarbaz'
        client.get_object.return_value = {'Body': BytesIO(response_body)}

        downloader = MultipartDownloader(
            client, TransferConfig(), InMemoryOSLayer({}), SequentialExecutor
        )
        downloader.download_file(
            'bucket', 'key', 'filename', len(response_body), {}
        )

        client.get_object.assert_called_with(
            Range='bytes=0-', Bucket='bucket', Key='key'
        )

    def test_multipart_download_with_multiple_parts(self):
        client = mock.Mock()
        response_body = b'foobarbaz'
        client.get_object.return_value = {'Body': BytesIO(response_body)}
        # For testing purposes, we're testing with a multipart threshold
        # of 4 bytes and a chunksize of 4 bytes.  Given b'foobarbaz',
        # this should result in 3 calls.  In python slices this would be:
        # r[0:4], r[4:8], r[8:9].  But the Range param will be slightly
        # different because they use inclusive ranges.
        config = TransferConfig(multipart_threshold=4, multipart_chunksize=4)

        downloader = MultipartDownloader(
            client, config, InMemoryOSLayer({}), SequentialExecutor
        )
        downloader.download_file(
            'bucket', 'key', 'filename', len(response_body), {}
        )

        # We're storing these in **extra because the assertEqual
        # below is really about verifying we have the correct value
        # for the Range param.
        extra = {'Bucket': 'bucket', 'Key': 'key'}
        self.assertEqual(
            client.get_object.call_args_list,
            # Note these are inclusive ranges.
            [
                mock.call(Range='bytes=0-3', **extra),
                mock.call(Range='bytes=4-7', **extra),
                mock.call(Range='bytes=8-', **extra),
            ],
        )

    def test_retry_on_failures_from_stream_reads(self):
        # If we get an exception during a call to the response body's .read()
        # method, we should retry the request.
        client = mock.Mock()
        response_body = b'foobarbaz'
        stream_with_errors = mock.Mock()
        stream_with_errors.read.side_effect = [
            OSError("fake error"),
            response_body,
        ]
        client.get_object.return_value = {'Body': stream_with_errors}
        config = TransferConfig(multipart_threshold=4, multipart_chunksize=4)

        downloader = MultipartDownloader(
            client, config, InMemoryOSLayer({}), SequentialExecutor
        )
        downloader.download_file(
            'bucket', 'key', 'filename', len(response_body), {}
        )

        # We're storing these in **extra because the assertEqual
        # below is really about verifying we have the correct value
        # for the Range param.
        extra = {'Bucket': 'bucket', 'Key': 'key'}
        self.assertEqual(
            client.get_object.call_args_list,
            # The first call to range=0-3 fails because of the
            # side_effect above where we make the .read() raise a
            # socket.error.
            # The second call to range=0-3 then succeeds.
            [
                mock.call(Range='bytes=0-3', **extra),
                mock.call(Range='bytes=0-3', **extra),
                mock.call(Range='bytes=4-7', **extra),
                mock.call(Range='bytes=8-', **extra),
            ],
        )

    def test_exception_raised_on_exceeded_retries(self):
        client = mock.Mock()
        response_body = b'foobarbaz'
        stream_with_errors = mock.Mock()
        stream_with_errors.read.side_effect = OSError("fake error")
        client.get_object.return_value = {'Body': stream_with_errors}
        config = TransferConfig(multipart_threshold=4, multipart_chunksize=4)

        downloader = MultipartDownloader(
            client, config, InMemoryOSLayer({}), SequentialExecutor
        )
        with self.assertRaises(RetriesExceededError):
            downloader.download_file(
                'bucket', 'key', 'filename', len(response_body), {}
            )

    def test_io_thread_failure_triggers_shutdown(self):
        client = mock.Mock()
        response_body = b'foobarbaz'
        client.get_object.return_value = {'Body': BytesIO(response_body)}
        os_layer = mock.Mock()
        mock_fileobj = mock.MagicMock()
        mock_fileobj.__enter__.return_value = mock_fileobj
        mock_fileobj.write.side_effect = Exception("fake IO error")
        os_layer.open.return_value = mock_fileobj

        downloader = MultipartDownloader(
            client, TransferConfig(), os_layer, SequentialExecutor
        )
        # We're verifying that the exception raised from the IO future
        # propagates back up via download_file().
        with self.assertRaisesRegex(Exception, "fake IO error"):
            downloader.download_file(
                'bucket', 'key', 'filename', len(response_body), {}
            )

    def test_download_futures_fail_triggers_shutdown(self):
        class FailedDownloadParts(SequentialExecutor):
            def __init__(self, max_workers):
                self.is_first = True

            def submit(self, function):
                future = futures.Future()
                if self.is_first:
                    # This is the download_parts_thread.
                    future.set_exception(
                        Exception("fake download parts error")
                    )
                    self.is_first = False
                return future

        client = mock.Mock()
        response_body = b'foobarbaz'
        client.get_object.return_value = {'Body': BytesIO(response_body)}

        downloader = MultipartDownloader(
            client, TransferConfig(), InMemoryOSLayer({}), FailedDownloadParts
        )
        with self.assertRaisesRegex(Exception, "fake download parts error"):
            downloader.download_file(
                'bucket', 'key', 'filename', len(response_body), {}
            )


class TestS3Transfer(unittest.TestCase):
    def setUp(self):
        self.client = mock.Mock()
        self.random_file_patch = mock.patch('s3transfer.random_file_extension')
        self.random_file = self.random_file_patch.start()
        self.random_file.return_value = 'RANDOM'

    def tearDown(self):
        self.random_file_patch.stop()

    def test_callback_handlers_register_on_put_item(self):
        osutil = InMemoryOSLayer({'smallfile': b'foobar'})
        transfer = S3Transfer(self.client, osutil=osutil)
        transfer.upload_file('smallfile', 'bucket', 'key')
        events = self.client.meta.events
        events.register_first.assert_called_with(
            'request-created.s3',
            disable_upload_callbacks,
            unique_id='s3upload-callback-disable',
        )
        events.register_last.assert_called_with(
            'request-created.s3',
            enable_upload_callbacks,
            unique_id='s3upload-callback-enable',
        )

    def test_upload_below_multipart_threshold_uses_put_object(self):
        fake_files = {
            'smallfile': b'foobar',
        }
        osutil = InMemoryOSLayer(fake_files)
        transfer = S3Transfer(self.client, osutil=osutil)
        transfer.upload_file('smallfile', 'bucket', 'key')
        self.client.put_object.assert_called_with(
            Bucket='bucket', Key='key', Body=mock.ANY
        )

    def test_extra_args_on_uploaded_passed_to_api_call(self):
        extra_args = {'ACL': 'public-read'}
        fake_files = {'smallfile': b'hello world'}
        osutil = InMemoryOSLayer(fake_files)
        transfer = S3Transfer(self.client, osutil=osutil)
        transfer.upload_file(
            'smallfile', 'bucket', 'key', extra_args=extra_args
        )
        self.client.put_object.assert_called_with(
            Bucket='bucket', Key='key', Body=mock.ANY, ACL='public-read'
        )

    def test_uses_multipart_upload_when_over_threshold(self):
        with mock.patch('s3transfer.MultipartUploader') as uploader:
            fake_files = {
                'smallfile': b'foobar',
            }
            osutil = InMemoryOSLayer(fake_files)
            config = TransferConfig(
                multipart_threshold=2, multipart_chunksize=2
            )
            transfer = S3Transfer(self.client, osutil=osutil, config=config)
            transfer.upload_file('smallfile', 'bucket', 'key')

            uploader.return_value.upload_file.assert_called_with(
                'smallfile', 'bucket', 'key', None, {}
            )

    def test_uses_multipart_download_when_over_threshold(self):
        with mock.patch('s3transfer.MultipartDownloader') as downloader:
            osutil = InMemoryOSLayer({})
            over_multipart_threshold = 100 * 1024 * 1024
            transfer = S3Transfer(self.client, osutil=osutil)
            callback = mock.sentinel.CALLBACK
            self.client.head_object.return_value = {
                'ContentLength': over_multipart_threshold,
            }
            transfer.download_file(
                'bucket', 'key', 'filename', callback=callback
            )

            downloader.return_value.download_file.assert_called_with(
                # Note how we're downloading to a temporary random file.
                'bucket',
                'key',
                'filename.RANDOM',
                over_multipart_threshold,
                {},
                callback,
            )

    def test_download_file_with_invalid_extra_args(self):
        below_threshold = 20
        osutil = InMemoryOSLayer({})
        transfer = S3Transfer(self.client, osutil=osutil)
        self.client.head_object.return_value = {
            'ContentLength': below_threshold
        }
        with self.assertRaises(ValueError):
            transfer.download_file(
                'bucket',
                'key',
                '/tmp/smallfile',
                extra_args={'BadValue': 'foo'},
            )

    def test_upload_file_with_invalid_extra_args(self):
        osutil = InMemoryOSLayer({})
        transfer = S3Transfer(self.client, osutil=osutil)
        bad_args = {"WebsiteRedirectLocation": "/foo"}
        with self.assertRaises(ValueError):
            transfer.upload_file(
                'bucket', 'key', '/tmp/smallfile', extra_args=bad_args
            )

    def test_download_file_fowards_extra_args(self):
        extra_args = {
            'SSECustomerKey': 'foo',
            'SSECustomerAlgorithm': 'AES256',
        }
        below_threshold = 20
        osutil = InMemoryOSLayer({'smallfile': b'hello world'})
        transfer = S3Transfer(self.client, osutil=osutil)
        self.client.head_object.return_value = {
            'ContentLength': below_threshold
        }
        self.client.get_object.return_value = {'Body': BytesIO(b'foobar')}
        transfer.download_file(
            'bucket', 'key', '/tmp/smallfile', extra_args=extra_args
        )

        # Note that we need to invoke the HeadObject call
        # and the PutObject call with the extra_args.
        # This is necessary.  Trying to HeadObject an SSE object
        # will return a 400 if you don't provide the required
        # params.
        self.client.get_object.assert_called_with(
            Bucket='bucket',
            Key='key',
            SSECustomerAlgorithm='AES256',
            SSECustomerKey='foo',
        )

    def test_get_object_stream_is_retried_and_succeeds(self):
        below_threshold = 20
        osutil = InMemoryOSLayer({'smallfile': b'hello world'})
        transfer = S3Transfer(self.client, osutil=osutil)
        self.client.head_object.return_value = {
            'ContentLength': below_threshold
        }
        self.client.get_object.side_effect = [
            # First request fails.
            OSError("fake error"),
            # Second succeeds.
            {'Body': BytesIO(b'foobar')},
        ]
        transfer.download_file('bucket', 'key', '/tmp/smallfile')

        self.assertEqual(self.client.get_object.call_count, 2)

    def test_get_object_stream_uses_all_retries_and_errors_out(self):
        below_threshold = 20
        osutil = InMemoryOSLayer({})
        transfer = S3Transfer(self.client, osutil=osutil)
        self.client.head_object.return_value = {
            'ContentLength': below_threshold
        }
        # Here we're raising an exception every single time, which
        # will exhaust our retry count and propagate a
        # RetriesExceededError.
        self.client.get_object.side_effect = OSError("fake error")
        with self.assertRaises(RetriesExceededError):
            transfer.download_file('bucket', 'key', 'smallfile')

        self.assertEqual(self.client.get_object.call_count, 5)
        # We should have also cleaned up the in progress file
        # we were downloading to.
        self.assertEqual(osutil.filemap, {})

    def test_download_below_multipart_threshold(self):
        below_threshold = 20
        osutil = InMemoryOSLayer({'smallfile': b'hello world'})
        transfer = S3Transfer(self.client, osutil=osutil)
        self.client.head_object.return_value = {
            'ContentLength': below_threshold
        }
        self.client.get_object.return_value = {'Body': BytesIO(b'foobar')}
        transfer.download_file('bucket', 'key', 'smallfile')

        self.client.get_object.assert_called_with(Bucket='bucket', Key='key')

    def test_can_create_with_just_client(self):
        transfer = S3Transfer(client=mock.Mock())
        self.assertIsInstance(transfer, S3Transfer)


class TestShutdownQueue(unittest.TestCase):
    def test_handles_normal_put_get_requests(self):
        q = ShutdownQueue()
        q.put('foo')
        self.assertEqual(q.get(), 'foo')

    def test_put_raises_error_on_shutdown(self):
        q = ShutdownQueue()
        q.trigger_shutdown()
        with self.assertRaises(QueueShutdownError):
            q.put('foo')


class TestRandomFileExtension(unittest.TestCase):
    def test_has_proper_length(self):
        self.assertEqual(len(random_file_extension(num_digits=4)), 4)


class TestCallbackHandlers(unittest.TestCase):
    def setUp(self):
        self.request = mock.Mock()

    def test_disable_request_on_put_object(self):
        disable_upload_callbacks(self.request, 'PutObject')
        self.request.body.disable_callback.assert_called_with()

    def test_disable_request_on_upload_part(self):
        disable_upload_callbacks(self.request, 'UploadPart')
        self.request.body.disable_callback.assert_called_with()

    def test_enable_object_on_put_object(self):
        enable_upload_callbacks(self.request, 'PutObject')
        self.request.body.enable_callback.assert_called_with()

    def test_enable_object_on_upload_part(self):
        enable_upload_callbacks(self.request, 'UploadPart')
        self.request.body.enable_callback.assert_called_with()

    def test_dont_disable_if_missing_interface(self):
        del self.request.body.disable_callback
        disable_upload_callbacks(self.request, 'PutObject')
        self.assertEqual(self.request.body.method_calls, [])

    def test_dont_enable_if_missing_interface(self):
        del self.request.body.enable_callback
        enable_upload_callbacks(self.request, 'PutObject')
        self.assertEqual(self.request.body.method_calls, [])

    def test_dont_disable_if_wrong_operation(self):
        disable_upload_callbacks(self.request, 'OtherOperation')
        self.assertFalse(self.request.body.disable_callback.called)

    def test_dont_enable_if_wrong_operation(self):
        enable_upload_callbacks(self.request, 'OtherOperation')
        self.assertFalse(self.request.body.enable_callback.called)
