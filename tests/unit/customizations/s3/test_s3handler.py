# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import datetime
import os
import random
import sys

import mock
from s3transfer.manager import TransferManager

import awscli.customizations.s3.utils
from awscli.testutils import unittest
from awscli import EnvironmentVariables
from awscli.compat import six
from awscli.compat import queue
from awscli.customizations.s3.s3handler import S3Handler
from awscli.customizations.s3.s3handler import S3TransferHandler
from awscli.customizations.s3.s3handler import S3TransferHandlerFactory
from awscli.customizations.s3.s3handler import UploadRequestSubmitter
from awscli.customizations.s3.s3handler import DownloadRequestSubmitter
from awscli.customizations.s3.s3handler import CopyRequestSubmitter
from awscli.customizations.s3.s3handler import UploadStreamRequestSubmitter
from awscli.customizations.s3.s3handler import DownloadStreamRequestSubmitter
from awscli.customizations.s3.s3handler import DeleteRequestSubmitter
from awscli.customizations.s3.fileinfo import FileInfo
from awscli.customizations.s3.tasks import CreateMultipartUploadTask, \
    UploadPartTask, CreateLocalFileTask, CompleteMultipartUploadTask
from awscli.customizations.s3.results import UploadResultSubscriber
from awscli.customizations.s3.results import DownloadResultSubscriber
from awscli.customizations.s3.results import CopyResultSubscriber
from awscli.customizations.s3.results import UploadStreamResultSubscriber
from awscli.customizations.s3.results import DownloadStreamResultSubscriber
from awscli.customizations.s3.results import DeleteResultSubscriber
from awscli.customizations.s3.results import ResultRecorder
from awscli.customizations.s3.results import ResultProcessor
from awscli.customizations.s3.results import CommandResultRecorder
from awscli.customizations.s3.utils import MAX_PARTS, MAX_UPLOAD_SIZE
from awscli.customizations.s3.utils import StablePriorityQueue
from awscli.customizations.s3.utils import NonSeekableStream
from awscli.customizations.s3.utils import StdoutBytesWriter
from awscli.customizations.s3.utils import WarningResult
from awscli.customizations.s3.utils import ProvideSizeSubscriber
from awscli.customizations.s3.utils import ProvideUploadContentTypeSubscriber
from awscli.customizations.s3.utils import ProvideCopyContentTypeSubscriber
from awscli.customizations.s3.utils import ProvideLastModifiedTimeSubscriber
from awscli.customizations.s3.utils import DirectoryCreatorSubscriber
from awscli.customizations.s3.transferconfig import RuntimeConfig
from tests.unit.customizations.s3 import make_loc_files, clean_loc_files, \
    S3HandlerBaseTest


def runtime_config(**kwargs):
    return RuntimeConfig().build_config(**kwargs)


# The point of this class is some condition where an error
# occurs during the enqueueing of tasks.
class CompleteTaskNotAllowedQueue(StablePriorityQueue):
    def _put(self, item):
        if isinstance(item, CompleteMultipartUploadTask):
            # Raising this exception will trigger the
            # "error" case shutdown in the executor.
            raise RuntimeError(
                "Forced error on enqueue of complete task.")
        return StablePriorityQueue._put(self, item)


class S3HandlerTestDelete(S3HandlerBaseTest):
    """
    This tests the ability to delete both files locally and in s3.
    """
    def setUp(self):
        super(S3HandlerTestDelete, self).setUp()
        params = {'region': 'us-east-1'}
        self.s3_handler = S3Handler(self.session, params,
                                    runtime_config=runtime_config(
                                        max_concurrent_requests=1))
        self.loc_files = make_loc_files(self.file_creator)
        self.bucket = 'mybucket'

    def test_loc_delete(self):
        """
        Test delete local file tasks.  The local files are the same
        generated from filegenerator_test.py.
        """
        files = [self.loc_files[0], self.loc_files[1]]
        tasks = []
        for filename in files:
            self.assertTrue(os.path.exists(filename))
            tasks.append(FileInfo(
                src=filename, src_type='local',
                dest_type='s3', operation_name='delete', size=0,
                client=self.client))
        ref_calls = []
        self.assert_operations_for_s3_handler(self.s3_handler, tasks,
                                              ref_calls)
        for filename in files:
            self.assertFalse(os.path.exists(filename))

    def test_s3_delete(self):
        """
        Tests S3 deletes. The files used are the same generated from
        filegenerators_test.py.  This includes the create s3 file.
        """
        keys = [self.bucket + '/another_directory/text2.txt',
                self.bucket + '/text1.txt',
                self.bucket + '/another_directory/']
        tasks = []
        for key in keys:
            tasks.append(FileInfo(
                src=key, src_type='s3',
                dest_type='local', operation_name='delete',
                size=0,
                client=self.client,
                source_client=self.source_client))
        ref_calls = [
            ('DeleteObject',
             {'Bucket': self.bucket, 'Key': 'another_directory/text2.txt'}),
            ('DeleteObject',
             {'Bucket': self.bucket, 'Key': 'text1.txt'}),
            ('DeleteObject',
             {'Bucket': self.bucket, 'Key': 'another_directory/'})
        ]
        self.assert_operations_for_s3_handler(self.s3_handler, tasks,
                                              ref_calls)


class S3HandlerTestURLEncodeDeletes(S3HandlerBaseTest):
    def setUp(self):
        super(S3HandlerTestURLEncodeDeletes, self).setUp()
        params = {'region': 'us-east-1'}
        self.s3_handler = S3Handler(self.session, params)
        self.bucket = 'mybucket'

    def test_s3_delete_url_encode(self):
        """
        Tests S3 deletes. The files used are the same generated from
        filegenerators_test.py.  This includes the create s3 file.
        """
        key = self.bucket + '/a+b/foo'
        tasks = [FileInfo(
            src=key, src_type='s3', dest_type='local',
            operation_name='delete', size=0,
            client=self.client, source_client=self.source_client)]
        ref_calls = [
            ('DeleteObject', {'Bucket': self.bucket, 'Key': 'a+b/foo'})
        ]
        self.assert_operations_for_s3_handler(self.s3_handler, tasks,
                                              ref_calls)


class S3HandlerTestUpload(S3HandlerBaseTest):
    """
    This class tests the ability to upload objects into an S3 bucket as
    well as multipart uploads
    """
    def setUp(self):
        super(S3HandlerTestUpload, self).setUp()
        params = {'region': 'us-east-1', 'acl': 'private', 'quiet': True}
        self.s3_handler = S3Handler(
            self.session, params, runtime_config=runtime_config(
                max_concurrent_requests=1))
        self.s3_handler_multi = S3Handler(
            self.session, params=params,
            runtime_config=runtime_config(
                multipart_threshold=10, multipart_chunksize=10,
                max_concurrent_requests=1))
        self.bucket = 'mybucket'
        self.loc_files = make_loc_files(self.file_creator)
        self.s3_files = [self.bucket + '/text1.txt',
                         self.bucket + '/another_directory/text2.txt']

    def test_upload(self):
        # Create file info objects to perform upload.
        files = [self.loc_files[0], self.loc_files[1]]
        tasks = []
        for i in range(len(files)):
            tasks.append(FileInfo(
                src=self.loc_files[i],
                dest=self.s3_files[i],
                operation_name='upload', size=0,
                client=self.client))
        # Perform the upload.
        self.parsed_responses = [
            {'ETag': '"120ea8a25e5d487bf68b5f7096440019"'},
            {'ETag': '"120ea8a25e5d487bf68b5f7096440019"'}
        ]
        stdout, stderr, rc = self.run_s3_handler(self.s3_handler, tasks)
        self.assertEqual(rc.num_tasks_failed, 0)
        ref_calls = [
            ('PutObject',
             {'Bucket': self.bucket, 'Key': 'text1.txt', 'Body': mock.ANY,
              'ContentType': 'text/plain',  'ACL': 'private'}),
            ('PutObject',
             {'Bucket': self.bucket, 'Key': 'another_directory/text2.txt',
              'ContentType': 'text/plain', 'Body': mock.ANY, 'ACL': 'private'})
        ]
        self.assert_operations_for_s3_handler(self.s3_handler, tasks,
                                              ref_calls)

    def test_upload_fail(self):
        """
        One of the uploads will fail to upload in this test as
        the second s3 destination's bucket does not exist.
        """
        fail_s3_files = [self.bucket + '/text1.txt',
                         self.bucket[:-1] + '/another_directory/text2.txt']
        files = [self.loc_files[0], self.loc_files[1]]
        tasks = []
        for i in range(len(files)):
            tasks.append(FileInfo(
                src=self.loc_files[i],
                dest=fail_s3_files[i],
                compare_key=None,
                src_type='local',
                dest_type='s3',
                operation_name='upload', size=0,
                last_update=None,
                client=self.client))
        # Since there is only one parsed response. The process will fail
        # becasue it is expecting one more response.
        self.parsed_responses = [
            {'ETag': '"120ea8a25e5d487bf68b5f7096440019"'},
        ]
        stdout, stderr, rc = self.run_s3_handler(self.s3_handler, tasks)
        self.assertEqual(rc.num_tasks_failed, 1)

    def test_max_size_limit(self):
        """
        This test verifies that we're warning on file uploads which are greater
        than the max upload size (5TB currently).
        """
        tasks = [FileInfo(
            src=self.loc_files[0],
            dest=self.bucket + '/test1.txt',
            compare_key=None,
            src_type='local',
            dest_type='s3',
            operation_name='upload',
            size=MAX_UPLOAD_SIZE+1,
            last_update=None,
            client=self.client
        )]
        self.parsed_responses = []
        _, _, rc = self.run_s3_handler(self.s3_handler, tasks)
        # The task should *warn*, not fail
        self.assertEqual(rc.num_tasks_failed, 0)
        self.assertEqual(rc.num_tasks_warned, 1)

    def test_multi_upload(self):
        """
        This test only checks that the multipart upload process works.
        It confirms that the parts are properly formatted but does not
        perform any tests past checking the parts are uploaded correctly.
        """
        files = [self.loc_files[0]]
        tasks = []
        for i in range(len(files)):
            tasks.append(FileInfo(
                src=self.loc_files[i],
                dest=self.s3_files[i], size=15,
                operation_name='upload',
                client=self.client))
        self.parsed_responses = [
            {'UploadId': 'foo'},
            {'ETag': '"120ea8a25e5d487bf68b5f7096440019"'},
            {'ETag': '"120ea8a25e5d487bf68b5f7096440019"'},
            {}
        ]
        ref_calls = [
            ('CreateMultipartUpload',
             {'Bucket': 'mybucket', 'ContentType': 'text/plain',
              'Key': 'text1.txt', 'ACL': 'private'}),
            ('UploadPart',
             {'Body': mock.ANY, 'Bucket': 'mybucket', 'PartNumber': 1,
              'UploadId': 'foo', 'Key': 'text1.txt'}),
            ('UploadPart',
             {'Body': mock.ANY, 'Bucket': 'mybucket', 'PartNumber': 2,
              'UploadId': 'foo', 'Key': 'text1.txt'}),
            ('CompleteMultipartUpload',
             {'MultipartUpload': {'Parts': [{'PartNumber': 1,
                                             'ETag': mock.ANY},
                                            {'PartNumber': 2,
                                             'ETag': mock.ANY}]},
              'Bucket': 'mybucket', 'UploadId': 'foo', 'Key': 'text1.txt'})
        ]
        self.assert_operations_for_s3_handler(self.s3_handler_multi, tasks,
                                              ref_calls)

    def test_multiupload_fail(self):
        """
        This tests the ability to handle multipart upload exceptions.
        This includes a standard error stemming from an operation on
        a nonexisting bucket, connection error, and md5 error.
        """
        files = [self.loc_files[0]]
        tasks = []
        for i in range(len(files)):
            tasks.append(FileInfo(
                src=self.loc_files[i],
                dest=self.s3_files[i], size=15,
                operation_name='upload',
                client=self.client))
        self.parsed_responses = [
            {'UploadId': 'foo'},
            {'ETag': '"120ea8a25e5d487bf68b5f7096440019"'},
            # This will cause a failure for the second part upload because
            # it does not have an ETag.
            {},
            # This is for the final AbortMultipartUpload call.
            {},
        ]
        stdout, stderr, rc = self.run_s3_handler(self.s3_handler_multi, tasks)
        self.assertEqual(rc.num_tasks_failed, 1)

    def test_multiupload_abort_in_s3_handler(self):
        tasks = [
            FileInfo(src=self.loc_files[0],
                     dest=self.s3_files[0], size=15,
                     operation_name='upload',
                     client=self.client)
        ]
        self.parsed_responses = [
            {'UploadId': 'foo'},
            {'ETag': '"120ea8a25e5d487bf68b5f7096440019"'},
            # This will cause a failure for the second part upload because
            # it does not have an ETag.
            {},
            {}
        ]
        expected_calls = [
            ('CreateMultipartUpload',
             {'Bucket': 'mybucket', 'ContentType': 'text/plain',
              'Key': 'text1.txt', 'ACL': 'private'}),
            ('UploadPart',
             {'Body': mock.ANY, 'Bucket': 'mybucket', 'PartNumber': 1,
              'UploadId': 'foo', 'Key': 'text1.txt'}),
            # Here we'll see an error because of a msising ETag.
            ('UploadPart',
             {'Body': mock.ANY, 'Bucket': 'mybucket', 'PartNumber': 2,
              'UploadId': 'foo', 'Key': 'text1.txt'}),
            # And we should have the final call be an AbortMultipartUpload.
            ('AbortMultipartUpload',
             {'Bucket': 'mybucket', 'Key': 'text1.txt', 'UploadId': 'foo'}),
        ]
        self.assert_operations_for_s3_handler(self.s3_handler_multi, tasks,
                                              expected_calls,
                                              verify_no_failed_tasked=False)

    def test_multipart_abort_for_half_queues(self):
        self.s3_handler_multi.executor.queue = CompleteTaskNotAllowedQueue()
        tasks = [
            FileInfo(src=self.loc_files[0],
                     dest=self.s3_files[0], size=15,
                     operation_name='upload',
                     client=self.client)
        ]
        self.parsed_responses = [
            {'UploadId': 'foo'},
            {'ETag': 'abcd'},
            {'ETag': 'abcd'},
            {},
        ]
        self.run_s3_handler(self.s3_handler_multi, tasks)
        # There are several ways this code can be executed that will
        # vary every time the test is run.  Examples:
        # <exception propogates>
        # Create, <exception propogates>
        # Create, Upload, <exception propogates>
        # Create, Upload, Upload, <exception propogates>
        # We can't use assert_operation_for_s3_handler because the list of
        # API calls is not deterministic.
        # We can however assert an invariant on the test.  An exception
        # will always be raised on enqueuing, so if a CreateMultipartUpload was executed
        # we must *always* see an AbortMultipartUpload as the last operation
        if self.operations_called:
            self.assertEqual(self.operations_called[0][0].name, 'CreateMultipartUpload')
            self.assertEqual(self.operations_called[-1][0].name, 'AbortMultipartUpload')


class S3HandlerTestMvLocalS3(S3HandlerBaseTest):
    """
    This class tests the ability to move s3 objects.  The move
    operation uses a upload then delete.
    """
    def setUp(self):
        super(S3HandlerTestMvLocalS3, self).setUp()
        params = {'region': 'us-east-1', 'acl': 'private', 'quiet': True}
        self.s3_handler = S3Handler(self.session, params,
                                    runtime_config=runtime_config(
                                        max_concurrent_requests=1))
        self.bucket = 'mybucket'
        self.loc_files = make_loc_files(self.file_creator)
        self.s3_files = [self.bucket + '/text1.txt',
                         self.bucket + '/another_directory/text2.txt']

    def test_move(self):
        # Create file info objects to perform move.
        files = [self.loc_files[0], self.loc_files[1]]
        tasks = []
        for i in range(len(files)):
            tasks.append(FileInfo(
                src=self.loc_files[i], src_type='local',
                dest=self.s3_files[i], dest_type='s3',
                operation_name='move', size=0,
                client=self.client))
        self.parsed_responses = [
            {'ETag': '"120ea8a25e5d487bf68b5f7096440019"'},
            {'ETag': '"120ea8a25e5d487bf68b5f7096440019"'}
        ]

        ref_calls = [
            ('PutObject',
             {'Bucket': self.bucket, 'Key': 'text1.txt', 'Body': mock.ANY,
              'ContentType': 'text/plain', 'ACL': 'private'}),
            ('PutObject',
             {'Bucket': self.bucket, 'Key': 'another_directory/text2.txt',
              'ContentType': 'text/plain', 'Body': mock.ANY, 'ACL': 'private'})
        ]
        # Perform the move.
        self.assert_operations_for_s3_handler(self.s3_handler, tasks,
                                              ref_calls)
        # Confirm local files do not exist.
        for filename in files:
            self.assertFalse(os.path.exists(filename))


class S3HandlerTestMvS3S3(S3HandlerBaseTest):
    """
    This class tests the ability to move s3 objects.  The move
    operation uses a copy then delete.
    """
    def setUp(self):
        super(S3HandlerTestMvS3S3, self).setUp()
        params = {'region': 'us-east-1', 'acl': 'private'}
        self.s3_handler = S3Handler(self.session, params,
                                    runtime_config=runtime_config(
                                        max_concurrent_requests=1))
        self.bucket = 'mybucket'
        self.bucket2 = 'mybucket2'
        self.s3_files = [self.bucket + '/text1.txt',
                         self.bucket + '/another_directory/text2.txt']
        self.s3_files2 = [self.bucket2 + '/text1.txt',
                          self.bucket2 + '/another_directory/text2.txt']

    def test_move(self):
        # Create file info objects to perform move.
        tasks = []
        for i in range(len(self.s3_files)):
            tasks.append(FileInfo(
                src=self.s3_files[i], src_type='s3',
                dest=self.s3_files2[i], dest_type='s3',
                operation_name='move', size=0,
                client=self.client, source_client=self.source_client))
        ref_calls = [
            ('CopyObject',
             {'Bucket': self.bucket2, 'Key': 'text1.txt',
              'CopySource': self.bucket + '/text1.txt', 'ACL': 'private',
              'ContentType': 'text/plain'}),
            ('DeleteObject', {'Bucket': self.bucket, 'Key': 'text1.txt'}),
            ('CopyObject',
             {'Bucket': self.bucket2, 'Key': 'another_directory/text2.txt',
              'CopySource': self.bucket + '/another_directory/text2.txt',
              'ACL': 'private', 'ContentType': 'text/plain'}),
            ('DeleteObject',
             {'Bucket': self.bucket, 'Key': 'another_directory/text2.txt'}),
        ]
        # Perform the move.
        self.assert_operations_for_s3_handler(self.s3_handler, tasks,
                                              ref_calls)

    def test_move_unicode(self):
        tasks = [FileInfo(
            src=self.bucket2 + '/' + u'\u2713',
            src_type='s3',
            dest=self.bucket + '/' + u'\u2713',
            dest_type='s3', operation_name='move',
            size=0,
            client=self.client,
            source_client=self.source_client
        )]

        ref_calls = [
            ('CopyObject',
             {'Bucket': self.bucket, 'Key': u'\u2713',
              # Implementation detail, but the botocore handler
              # now fixes up CopySource in before-call so it will
              # show up in the operations_called.
              'CopySource': u'mybucket2/%E2%9C%93',
              'ACL': 'private'}),
            ('DeleteObject',
             {'Bucket': self.bucket2, 'Key': u'\u2713'})
        ]
        self.assert_operations_for_s3_handler(self.s3_handler, tasks,
                                              ref_calls)


class S3HandlerTestMvS3Local(S3HandlerBaseTest):
    """
    This class tests the ability to move s3 objects.  The move
    operation uses a download then delete.
    """
    def setUp(self):
        super(S3HandlerTestMvS3Local, self).setUp()
        params = {'region': 'us-east-1'}
        self.s3_handler = S3Handler(self.session, params,
                                    runtime_config=runtime_config(
                                        max_concurrent_requests=1))
        self.s3_handler_multi = S3Handler(
            self.session, params=params,
            runtime_config=runtime_config(
                multipart_threshold=10, multipart_chunksize=5,
                max_concurrent_requests=1))
        self.bucket = 'mybucket'
        self.s3_files = [self.bucket + '/text1.txt',
                         self.bucket + '/another_directory/text2.txt']
        directory1 = self.file_creator.rootdir + os.sep + 'some_directory' \
            + os.sep
        filename1 = directory1 + "text1.txt"
        directory2 = directory1 + 'another_directory' + os.sep
        filename2 = directory2 + "text2.txt"
        self.loc_files = [filename1, filename2]

    def test_move(self):
        # Create file info objects to perform move.
        tasks = []
        time = datetime.datetime.now()
        for i in range(len(self.s3_files)):
            tasks.append(FileInfo(
                src=self.s3_files[i], src_type='s3',
                dest=self.loc_files[i], dest_type='local',
                last_update=time, operation_name='move',
                size=0, client=self.client, source_client=self.source_client))
        self.parsed_responses = [
            {'ETag': '"120ea8a25e5d487bf68b5f7096440019"',
             'Body': six.BytesIO(b'This is a test.')},
            {},
            {'ETag': '"120ea8a25e5d487bf68b5f7096440019"',
             'Body': six.BytesIO(b'This is a test.')},
            {}
        ]
        ref_calls = [
            ('GetObject', {'Bucket': self.bucket, 'Key': 'text1.txt'}),
            ('DeleteObject', {'Bucket': self.bucket, 'Key': 'text1.txt'}),
            ('GetObject',
             {'Bucket': self.bucket, 'Key': 'another_directory/text2.txt'}),
            ('DeleteObject',
             {'Bucket': self.bucket, 'Key': 'another_directory/text2.txt'}),
        ]
        # Perform the move.
        self.assert_operations_for_s3_handler(self.s3_handler, tasks,
                                              ref_calls)

        # Confirm that the files now exist.
        for filename in self.loc_files:
            self.assertTrue(os.path.exists(filename))
        # Ensure the contents are as expected.
        with open(self.loc_files[0], 'rb') as filename:
            self.assertEqual(filename.read(), b'This is a test.')
        with open(self.loc_files[1], 'rb') as filename:
            self.assertEqual(filename.read(), b'This is a test.')

    def test_move_multi(self):
        tasks = []
        time = datetime.datetime.now()
        tasks.append(FileInfo(
            src=self.s3_files[0], src_type='s3',
            dest=self.loc_files[0], dest_type='local',
            last_update=time, operation_name='move',
            size=15, client=self.client, source_client=self.source_client))
        mock_stream = mock.Mock()
        mock_stream.read.side_effect = [
            b'This ', b'', b'is a ', b'', b'test.', b'',
        ]
        self.parsed_responses = [
            {'ETag': '"120ea8a25e5d487bf68b5f7096440019"',
             'Body': mock_stream},
            {'ETag': '"120ea8a25e5d487bf68b5f7096440019"',
             'Body': mock_stream},
            {'ETag': '"120ea8a25e5d487bf68b5f7096440019"',
             'Body': mock_stream},
            {}
        ]
        ref_calls = [
            ('GetObject',
             {'Bucket': self.bucket, 'Key': 'text1.txt',
              'Range': 'bytes=0-4'}),
            ('GetObject',
             {'Bucket': self.bucket, 'Key': 'text1.txt',
              'Range': 'bytes=5-9'}),
            ('GetObject',
             {'Bucket': self.bucket, 'Key': 'text1.txt',
              'Range': 'bytes=10-'}),
            ('DeleteObject',
             {'Bucket': self.bucket, 'Key': 'text1.txt'})
        ]
        # Perform the multipart  download.
        self.assert_operations_for_s3_handler(self.s3_handler_multi, tasks,
                                              ref_calls)
        # Confirm that the file now exist.
        self.assertTrue(os.path.exists(self.loc_files[0]))
        # Ensure the contents are as expected.
        with open(self.loc_files[0], 'rb') as filename:
            self.assertEqual(filename.read(), b'This is a test.')


class S3HandlerTestCpS3S3(S3HandlerBaseTest):
    """
    This class tests the ability to move s3 objects.  The move
    operation uses a copy then delete.
    """
    def setUp(self):
        super(S3HandlerTestCpS3S3, self).setUp()
        params = {'region': 'us-east-1'}
        self.s3_handler = S3Handler(self.session, params,
                                    runtime_config=runtime_config(
                                        max_concurrent_requests=1))
        self.s3_handler_multi = S3Handler(
            self.session, params=params,
            runtime_config=runtime_config(
                multipart_threshold=10, multipart_chunksize=5,
                max_concurrent_requests=1))
        self.bucket = 'mybucket'
        self.bucket2 = 'mybucket2'
        self.s3_files = [self.bucket + '/text1.txt',
                         self.bucket + '/another_directory/text2.txt']
        self.s3_files2 = [self.bucket2 + '/text1.txt',
                          self.bucket2 + '/another_directory/text2.txt']

    def test_multi_copy(self):
        # Create file info objects to perform move.
        tasks = []
        self.s3_files2[0] = 'mybucket2/destkey2.txt'
        tasks.append(FileInfo(src=self.s3_files[0], src_type='s3',
                              dest=self.s3_files2[0], dest_type='s3',
                              operation_name='copy', size=15,
                              client=self.client,
                              source_client=self.source_client))
        self.parsed_responses = [
            {'UploadId': 'foo'},
            {'CopyPartResult': {'ETag': '"120ea8a25e5d487bf68b5f7096440019"'}},
            {'CopyPartResult': {'ETag': '"120ea8a25e5d487bf68b5f7096440019"'}},
            {'CopyPartResult': {'ETag': '"120ea8a25e5d487bf68b5f7096440019"'}},
            {}
        ]

        ref_calls = [
            ('CreateMultipartUpload',
             {'Bucket': self.bucket2, 'Key': 'destkey2.txt',
              'ContentType': 'text/plain'}),
            ('UploadPartCopy',
             {'Bucket': self.bucket2, 'Key': 'destkey2.txt',
              'PartNumber': 1, 'UploadId': 'foo',
              'CopySourceRange': 'bytes=0-4',
              'CopySource': self.bucket + '/text1.txt'}),
            ('UploadPartCopy',
             {'Bucket': self.bucket2, 'Key': 'destkey2.txt',
              'PartNumber': 2, 'UploadId': 'foo',
              'CopySourceRange': 'bytes=5-9',
              'CopySource': self.bucket + '/text1.txt'}),
            ('UploadPartCopy',
             {'Bucket': self.bucket2, 'Key': 'destkey2.txt',
              'PartNumber': 3, 'UploadId': 'foo',
              'CopySourceRange': 'bytes=10-14',
              'CopySource': self.bucket + '/text1.txt'}),
            ('CompleteMultipartUpload',
             {'MultipartUpload': {'Parts': [{'PartNumber': 1,
                                             'ETag': mock.ANY},
                                            {'PartNumber': 2,
                                             'ETag': mock.ANY},
                                            {'PartNumber': 3,
                                             'ETag': mock.ANY}]},
              'Bucket': self.bucket2, 'UploadId': 'foo', 'Key': 'destkey2.txt'})
        ]

        # Perform the copy.
        self.assert_operations_for_s3_handler(self.s3_handler_multi, tasks,
                                              ref_calls)

    def test_multi_copy_fail(self):
        # Create file info objects to perform move.
        tasks = []
        for i in range(len(self.s3_files)):
            tasks.append(FileInfo(src=self.s3_files[i], src_type='s3',
                                  dest=self.s3_files2[i], dest_type='s3',
                                  operation_name='copy', size=15,
                                  client=self.client,
                                  source_client=self.source_client))

        self.parsed_responses = [
            {'UploadId': 'foo'},
            {'CopyPartResult': {'ETag': '"120ea8a25e5d487bf68b5f7096440019"'}},
            {'CopyPartResult': {'ETag': '"120ea8a25e5d487bf68b5f7096440019"'}},
            {'CopyPartResult': {'ETag': '"120ea8a25e5d487bf68b5f7096440019"'}},
            {},
            {'UploadId': 'bar'},
            # This will fail because some response is expected for multipart
            # upload copies.
            {},
            {},
            {},
            {}
        ]
        stdout, stderr, rc = self.run_s3_handler(self.s3_handler_multi, tasks)
        self.assertEqual(rc.num_tasks_failed, 1)


class S3HandlerTestDownload(S3HandlerBaseTest):
    """
    This class tests the ability to download s3 objects locally as well
    as using multipart downloads
    """
    def setUp(self):
        super(S3HandlerTestDownload, self).setUp()
        params = {'region': 'us-east-1'}
        self.s3_handler = S3Handler(self.session, params,
                                    runtime_config=runtime_config(
                                        max_concurrent_requests=1))
        self.s3_handler_multi = S3Handler(
            self.session, params,
            runtime_config=runtime_config(multipart_threshold=10,
                                          multipart_chunksize=5,
                                          max_concurrent_requests=1))
        self.bucket = 'mybucket'
        self.s3_files = [self.bucket + '/text1.txt',
                         self.bucket + '/another_directory/text2.txt']
        directory1 = self.file_creator.rootdir + os.sep + 'some_directory' \
            + os.sep
        filename1 = directory1 + "text1.txt"
        directory2 = directory1 + 'another_directory' + os.sep
        filename2 = directory2 + "text2.txt"
        self.loc_files = [filename1, filename2]

    def test_download(self):
        # Create file info objects to perform download.
        tasks = []
        time = datetime.datetime.now()
        for i in range(len(self.s3_files)):
            tasks.append(FileInfo(
                src=self.s3_files[i], src_type='s3',
                dest=self.loc_files[i], dest_type='local',
                last_update=time, operation_name='download',
                size=0, client=self.client))
        self.parsed_responses = [
            {'ETag': '"120ea8a25e5d487bf68b5f7096440019"',
             'Body': six.BytesIO(b'This is a test.')},
            {'ETag': '"120ea8a25e5d487bf68b5f7096440019"',
             'Body': six.BytesIO(b'This is a test.')},
        ]
        ref_calls = [
            ('GetObject', {'Bucket': self.bucket, 'Key': 'text1.txt'}),
            ('GetObject',
             {'Bucket': self.bucket, 'Key': 'another_directory/text2.txt'}),
        ]
        # Perform the download.
        self.assert_operations_for_s3_handler(self.s3_handler, tasks,
                                              ref_calls)
        # Confirm that the files now exist.
        for filename in self.loc_files:
            self.assertTrue(os.path.exists(filename))
        # Ensure the contents are as expected.
        with open(self.loc_files[0], 'rb') as filename:
            self.assertEqual(filename.read(), b'This is a test.')
        with open(self.loc_files[1], 'rb') as filename:
            self.assertEqual(filename.read(), b'This is a test.')

    def test_multi_download(self):
        tasks = []
        time = datetime.datetime.now()
        for i in range(len(self.s3_files)):
            tasks.append(FileInfo(
                src=self.s3_files[i], src_type='s3',
                dest=self.loc_files[i], dest_type='local',
                last_update=time, operation_name='download',
                size=15, client=self.client))
        mock_stream = mock.Mock()
        mock_stream.read.side_effect = [
            b'This ', b'', b'is a ', b'', b'test.', b'',
            b'This ', b'', b'is a ', b'', b'test.', b''
        ]
        self.parsed_responses = [
            {'ETag': '"120ea8a25e5d487bf68b5f7096440019"',
             'Body': mock_stream},
            {'ETag': '"120ea8a25e5d487bf68b5f7096440019"',
             'Body': mock_stream},
            {'ETag': '"120ea8a25e5d487bf68b5f7096440019"',
             'Body': mock_stream},
            {'ETag': '"120ea8a25e5d487bf68b5f7096440019"',
             'Body': mock_stream},
            {'ETag': '"120ea8a25e5d487bf68b5f7096440019"',
             'Body': mock_stream},
            {'ETag': '"120ea8a25e5d487bf68b5f7096440019"',
             'Body': mock_stream}
        ]
        ref_calls = [
            ('GetObject',
             {'Bucket': self.bucket, 'Key': 'text1.txt',
              'Range': 'bytes=0-4'}),
            ('GetObject',
             {'Bucket': self.bucket, 'Key': 'text1.txt',
              'Range': 'bytes=5-9'}),
            ('GetObject',
             {'Bucket': self.bucket, 'Key': 'text1.txt',
              'Range': 'bytes=10-'}),
            ('GetObject',
             {'Bucket': self.bucket, 'Key': 'another_directory/text2.txt',
              'Range': 'bytes=0-4'}),
            ('GetObject',
             {'Bucket': self.bucket, 'Key': 'another_directory/text2.txt',
              'Range': 'bytes=5-9'}),
            ('GetObject',
             {'Bucket': self.bucket, 'Key': 'another_directory/text2.txt',
              'Range': 'bytes=10-'}),
        ]
        # Perform the multipart  download.
        self.assert_operations_for_s3_handler(self.s3_handler_multi, tasks,
                                              ref_calls)
        # Confirm that the files now exist.
        for filename in self.loc_files:
            self.assertTrue(os.path.exists(filename))
        # Ensure the contents are as expected.
        with open(self.loc_files[0], 'rb') as filename:
            self.assertEqual(filename.read(), b'This is a test.')
        with open(self.loc_files[1], 'rb') as filename:
            self.assertEqual(filename.read(), b'This is a test.')

    def test_multi_download_fail(self):
        """
        This test ensures that a multipart download can handle a
        standard error exception stemming from an operation
        being performed on a nonexistant bucket.  The existing file
        should be downloaded properly but the other will not.
        """
        tasks = []
        wrong_s3_files = [self.bucket + '/text1.txt',
                          self.bucket[:-1] + '/another_directory/text2.txt']
        time = datetime.datetime.now()
        for i in range(len(self.s3_files)):
            tasks.append(FileInfo(
                src=wrong_s3_files[i], src_type='s3',
                dest=self.loc_files[i], dest_type='local',
                last_update=time, operation_name='download',
                size=15, client=self.client))
        mock_stream = mock.Mock()
        mock_stream.read.side_effect = [
            b'This ', b'', b'is a ', b'', b'test.', b''
        ]
        self.parsed_responses = [
            {'ETag': '"120ea8a25e5d487bf68b5f7096440019"',
             'Body': mock_stream},
            {'ETag': '"120ea8a25e5d487bf68b5f7096440019"',
             'Body': mock_stream},
            {'ETag': '"120ea8a25e5d487bf68b5f7096440019"',
             'Body': mock_stream},
            # Response with no body will throw an error for the second
            # multipart download.
            {},
            {},
            {}
        ]
        # Perform the multipart  download.
        stdout, stderr, rc = self.run_s3_handler(self.s3_handler_multi, tasks)
        # Confirm that the files now exist.
        self.assertTrue(os.path.exists(self.loc_files[0]))
        # The second file should not exist.
        self.assertFalse(os.path.exists(self.loc_files[1]))
        # Ensure that contents are as expected.
        with open(self.loc_files[0], 'rb') as filename:
            self.assertEqual(filename.read(), b'This is a test.')


class S3HandlerTestBucket(S3HandlerBaseTest):
    """
    Test the ability to make a bucket then remove it.
    """
    def setUp(self):
        super(S3HandlerTestBucket, self).setUp()
        self.params = {'region': 'us-east-1'}
        self.bucket = 'mybucket'

    def test_remove_bucket(self):
        file_info = FileInfo(
            src=self.bucket,
            operation_name='remove_bucket',
            size=0, client=self.client)
        s3_handler = S3Handler(self.session, self.params)
        ref_calls = [
            ('DeleteBucket', {'Bucket': self.bucket})
        ]
        self.assert_operations_for_s3_handler(s3_handler, [file_info],
                                              ref_calls)


class TestS3HandlerInitialization(unittest.TestCase):
    def setUp(self):
        self.arbitrary_params = {'region': 'us-west-2'}

    def test_num_threads_is_plumbed_through(self):
        num_threads_override = 20

        config = runtime_config(max_concurrent_requests=num_threads_override)
        handler = S3Handler(session=None, params=self.arbitrary_params,
                            runtime_config=config)

        self.assertEqual(handler.executor.num_threads, num_threads_override)

    def test_queue_size_is_plumbed_through(self):
        max_queue_size_override = 10000

        config = runtime_config(max_queue_size=max_queue_size_override)
        handler = S3Handler(session=None, params=self.arbitrary_params,
                            runtime_config=config)

        self.assertEqual(handler.executor.queue.maxsize,
                         max_queue_size_override)

    def test_runtime_config_from_attrs(self):
        # These are attrs that are set directly on S3Handler,
        # not on some dependent object
        config = runtime_config(
            multipart_chunksize=1000,
            multipart_threshold=10000)
        handler = S3Handler(session=None, params=self.arbitrary_params,
                            runtime_config=config)

        self.assertEqual(handler.chunksize, 1000)
        self.assertEqual(handler.multi_threshold, 10000)


class TestS3TransferHandlerFactory(unittest.TestCase):
    def setUp(self):
        self.cli_params = {}
        self.runtime_config = runtime_config()
        self.client = mock.Mock()
        self.result_queue = queue.Queue()

    def test_call(self):
        factory = S3TransferHandlerFactory(
            self.cli_params, self.runtime_config)
        self.assertIsInstance(
            factory(self.client, self.result_queue), S3TransferHandler)


class TestS3TransferHandler(unittest.TestCase):
    def setUp(self):
        self.result_queue = queue.Queue()
        self.result_recorder = ResultRecorder()
        self.processed_results = []
        self.result_processor = ResultProcessor(
            self.result_queue,
            [self.result_recorder, self.processed_results.append]
        )
        self.command_result_recorder = CommandResultRecorder(
            self.result_queue, self.result_recorder, self.result_processor)

        self.transfer_manager = mock.Mock(spec=TransferManager)
        self.transfer_manager.__enter__ = mock.Mock()
        self.transfer_manager.__exit__ = mock.Mock()
        self.parameters = {}
        self.s3_transfer_handler = S3TransferHandler(
            self.transfer_manager, self.parameters,
            self.command_result_recorder
        )

    def test_call_return_command_result(self):
        num_failures = 5
        num_warnings = 3
        self.result_recorder.files_failed = num_failures
        self.result_recorder.files_warned = num_warnings
        command_result = self.s3_transfer_handler.call([])
        self.assertEqual(command_result, (num_failures, num_warnings))

    def test_enqueue_uploads(self):
        fileinfos = []
        num_transfers = 5
        for _ in range(num_transfers):
            fileinfos.append(
                FileInfo(src='filename', dest='bucket/key',
                         operation_name='upload'))

        self.s3_transfer_handler.call(fileinfos)
        self.assertEqual(
            self.transfer_manager.upload.call_count, num_transfers)

    def test_enqueue_downloads(self):
        fileinfos = []
        num_transfers = 5
        for _ in range(num_transfers):
            fileinfos.append(
                FileInfo(src='bucket/key', dest='filename',
                         operation_name='download'))

        self.s3_transfer_handler.call(fileinfos)
        self.assertEqual(
            self.transfer_manager.download.call_count, num_transfers)

    def test_enqueue_copies(self):
        fileinfos = []
        num_transfers = 5
        for _ in range(num_transfers):
            fileinfos.append(
                FileInfo(src='sourcebucket/sourcekey', dest='bucket/key',
                         operation_name='copy'))

        self.s3_transfer_handler.call(fileinfos)
        self.assertEqual(
            self.transfer_manager.copy.call_count, num_transfers)

    def test_exception_when_enqueuing(self):
        fileinfos = [
            FileInfo(src='filename', dest='bucket/key',
                     operation_name='upload')
        ]
        self.transfer_manager.__exit__.side_effect = Exception(
            'some exception')
        command_result = self.s3_transfer_handler.call(fileinfos)
        # Exception should have been raised casing the command result to
        # have failed results of one.
        self.assertEqual(command_result, (1, 0))

    def test_enqueue_upload_stream(self):
        self.parameters['is_stream'] = True
        self.s3_transfer_handler.call(
            [FileInfo(src='-', dest='bucket/key', operation_name='upload')])
        self.assertEqual(
            self.transfer_manager.upload.call_count, 1)
        upload_call_kwargs = self.transfer_manager.upload.call_args[1]
        self.assertIsInstance(
            upload_call_kwargs['fileobj'], NonSeekableStream)

    def test_enqueue_dowload_stream(self):
        self.parameters['is_stream'] = True
        self.s3_transfer_handler.call(
            [FileInfo(src='bucket/key', dest='-', operation_name='download')])
        self.assertEqual(
            self.transfer_manager.download.call_count, 1)
        download_call_kwargs = self.transfer_manager.download.call_args[1]
        self.assertIsInstance(
            download_call_kwargs['fileobj'], StdoutBytesWriter)

    def test_enqueue_deletes(self):
        fileinfos = []
        num_transfers = 5
        for _ in range(num_transfers):
            fileinfos.append(
                FileInfo(src='bucket/key', dest=None, operation_name='delete'))

        self.s3_transfer_handler.call(fileinfos)
        self.assertEqual(
            self.transfer_manager.delete.call_count, num_transfers)

    def test_notifies_total_submissions(self):
        fileinfos = []
        num_transfers = 5
        for _ in range(num_transfers):
            fileinfos.append(
                FileInfo(src='bucket/key', dest='filename',
                         operation_name='download'))

        self.s3_transfer_handler.call(fileinfos)
        self.assertEqual(
            self.result_recorder.final_expected_files_transferred,
            num_transfers
        )

    def test_notifies_total_submissions_accounts_for_skips(self):
        fileinfos = []
        num_transfers = 5
        for _ in range(num_transfers):
            fileinfos.append(
                FileInfo(src='bucket/key', dest='filename',
                         operation_name='download'))

        # Add a fileinfo that should get skipped. To skip, we do a glacier
        # download.
        fileinfos.append(FileInfo(
            src='bucket/key', dest='filename', operation_name='download',
            associated_response_data={'StorageClass': 'GLACIER'}))
        self.s3_transfer_handler.call(fileinfos)
        # Since the last glacier download was skipped the final expected
        # total should be equal to the number of transfers provided in the
        # for loop.
        self.assertEqual(
            self.result_recorder.final_expected_files_transferred,
            num_transfers
        )


class BaseTransferRequestSubmitterTest(unittest.TestCase):
    def setUp(self):
        self.transfer_manager = mock.Mock(spec=TransferManager)
        self.result_queue = queue.Queue()
        self.cli_params = {}
        self.filename = 'myfile'
        self.bucket = 'mybucket'
        self.key = 'mykey'


class TestUploadRequestSubmitter(BaseTransferRequestSubmitterTest):
    def setUp(self):
        super(TestUploadRequestSubmitter, self).setUp()
        self.transfer_request_submitter = UploadRequestSubmitter(
            self.transfer_manager, self.result_queue, self.cli_params)

    def test_can_submit(self):
        fileinfo = FileInfo(
            src=self.filename, dest=self.bucket+'/'+self.key,
            operation_name='upload')
        self.assertTrue(
            self.transfer_request_submitter.can_submit(fileinfo))
        fileinfo.operation_name = 'foo'
        self.assertFalse(
            self.transfer_request_submitter.can_submit(fileinfo))

    def test_submit(self):
        fileinfo = FileInfo(
            src=self.filename, dest=self.bucket+'/'+self.key)
        self.cli_params['guess_mime_type'] = True  # Default settings
        future = self.transfer_request_submitter.submit(fileinfo)

        self.assertIs(self.transfer_manager.upload.return_value, future)
        upload_call_kwargs = self.transfer_manager.upload.call_args[1]
        self.assertEqual(upload_call_kwargs['fileobj'], self.filename)
        self.assertEqual(upload_call_kwargs['bucket'], self.bucket)
        self.assertEqual(upload_call_kwargs['key'], self.key)
        self.assertEqual(upload_call_kwargs['extra_args'], {})

        # Make sure the subscriber applied are of the correct type and order
        ref_subscribers = [
            ProvideSizeSubscriber,
            ProvideUploadContentTypeSubscriber,
            UploadResultSubscriber
        ]
        actual_subscribers = upload_call_kwargs['subscribers']
        self.assertEqual(len(ref_subscribers), len(actual_subscribers))
        for i, actual_subscriber in enumerate(actual_subscribers):
            self.assertIsInstance(actual_subscriber, ref_subscribers[i])

    def test_submit_with_extra_args(self):
        fileinfo = FileInfo(
            src=self.filename, dest=self.bucket+'/'+self.key)
        # Set some extra argument like storage_class to make sure cli
        # params get mapped to request parameters.
        self.cli_params['storage_class'] = 'STANDARD_IA'
        self.transfer_request_submitter.submit(fileinfo)

        upload_call_kwargs = self.transfer_manager.upload.call_args[1]
        self.assertEqual(
            upload_call_kwargs['extra_args'], {'StorageClass': 'STANDARD_IA'})

    def test_submit_when_content_type_specified(self):
        fileinfo = FileInfo(
            src=self.filename, dest=self.bucket+'/'+self.key)
        self.cli_params['content_type'] = 'text/plain'
        self.transfer_request_submitter.submit(fileinfo)

        upload_call_kwargs = self.transfer_manager.upload.call_args[1]
        self.assertEqual(
            upload_call_kwargs['extra_args'], {'ContentType': 'text/plain'})
        ref_subscribers = [
            ProvideSizeSubscriber,
            UploadResultSubscriber
        ]
        actual_subscribers = upload_call_kwargs['subscribers']
        self.assertEqual(len(ref_subscribers), len(actual_subscribers))
        for i, actual_subscriber in enumerate(actual_subscribers):
            self.assertIsInstance(actual_subscriber, ref_subscribers[i])

    def test_submit_when_no_guess_content_mime_type(self):
        fileinfo = FileInfo(
            src=self.filename, dest=self.bucket+'/'+self.key)
        self.cli_params['guess_mime_type'] = False
        self.transfer_request_submitter.submit(fileinfo)

        upload_call_kwargs = self.transfer_manager.upload.call_args[1]
        ref_subscribers = [
            ProvideSizeSubscriber,
            UploadResultSubscriber
        ]
        actual_subscribers = upload_call_kwargs['subscribers']
        self.assertEqual(len(ref_subscribers), len(actual_subscribers))
        for i, actual_subscriber in enumerate(actual_subscribers):
            self.assertIsInstance(actual_subscriber, ref_subscribers[i])

    def test_warn_on_too_large_transfer(self):
        fileinfo = FileInfo(
            src=self.filename, dest=self.bucket+'/'+self.key,
            size=MAX_UPLOAD_SIZE+1)
        future = self.transfer_request_submitter.submit(fileinfo)

        # A warning should have been submitted because it is too large.
        warning_result = self.result_queue.get()
        self.assertIsInstance(warning_result, WarningResult)
        self.assertIn('exceeds s3 upload limit', warning_result.message)

        # Make sure that the transfer was still attempted
        self.assertIs(self.transfer_manager.upload.return_value, future)
        self.assertEqual(len(self.transfer_manager.upload.call_args_list), 1)


class TestDownloadRequestSubmitter(BaseTransferRequestSubmitterTest):
    def setUp(self):
        super(TestDownloadRequestSubmitter, self).setUp()
        self.transfer_request_submitter = DownloadRequestSubmitter(
            self.transfer_manager, self.result_queue, self.cli_params)

    def test_can_submit(self):
        fileinfo = FileInfo(
            src=self.bucket+'/'+self.key, dest=self.filename,
            operation_name='download')
        self.assertTrue(
            self.transfer_request_submitter.can_submit(fileinfo))
        fileinfo.operation_name = 'foo'
        self.assertFalse(
            self.transfer_request_submitter.can_submit(fileinfo))

    def test_submit(self):
        fileinfo = FileInfo(
            src=self.bucket+'/'+self.key, dest=self.filename)
        future = self.transfer_request_submitter.submit(fileinfo)

        self.assertIs(self.transfer_manager.download.return_value, future)
        download_call_kwargs = self.transfer_manager.download.call_args[1]
        self.assertEqual(download_call_kwargs['fileobj'], self.filename)
        self.assertEqual(download_call_kwargs['bucket'], self.bucket)
        self.assertEqual(download_call_kwargs['key'], self.key)
        self.assertEqual(download_call_kwargs['extra_args'], {})

        # Make sure the subscriber applied are of the correct type and order
        ref_subscribers = [
            ProvideSizeSubscriber,
            DirectoryCreatorSubscriber,
            ProvideLastModifiedTimeSubscriber,
            DownloadResultSubscriber
        ]
        actual_subscribers = download_call_kwargs['subscribers']
        self.assertEqual(len(ref_subscribers), len(actual_subscribers))
        for i, actual_subscriber in enumerate(actual_subscribers):
            self.assertIsInstance(actual_subscriber, ref_subscribers[i])

    def test_submit_with_extra_args(self):
        fileinfo = FileInfo(
            src=self.bucket+'/'+self.key, dest=self.filename)
        self.cli_params['sse_c'] = 'AES256'
        self.cli_params['sse_c_key'] = 'mykey'
        self.transfer_request_submitter.submit(fileinfo)

        # Set some extra argument like sse_c to make sure cli
        # params get mapped to request parameters.
        download_call_kwargs = self.transfer_manager.download.call_args[1]
        self.assertEqual(
            download_call_kwargs['extra_args'],
            {'SSECustomerAlgorithm': 'AES256', 'SSECustomerKey': 'mykey'}
        )

    def test_warn_glacier_for_incompatible(self):
        fileinfo = FileInfo(
            src=self.bucket+'/'+self.key, dest=self.filename,
            operation_name='download',
            associated_response_data={
                'StorageClass': 'GLACIER',
            }
        )
        future = self.transfer_request_submitter.submit(fileinfo)

        # A warning should have been submitted because it is a non-restored
        # glacier object.
        warning_result = self.result_queue.get()
        self.assertIsInstance(warning_result, WarningResult)
        self.assertIn(
            'Unable to perform download operations on GLACIER objects',
            warning_result.message)

        # The transfer should have been skipped.
        self.assertIsNone(future)
        self.assertEqual(len(self.transfer_manager.download.call_args_list), 0)

    def test_not_warn_glacier_for_compatible(self):
        fileinfo = FileInfo(
            src=self.bucket+'/'+self.key, dest=self.filename,
            operation_name='download',
            associated_response_data={
                'StorageClass': 'GLACIER',
                'Restore': 'ongoing-request="false"'
            }
        )
        future = self.transfer_request_submitter.submit(fileinfo)

        # A warning should have not been submitted because it is a restored
        # glacier object.
        self.assertTrue(self.result_queue.empty())

        # And the transfer should not have been skipped.
        self.assertIs(self.transfer_manager.download.return_value, future)
        self.assertEqual(len(self.transfer_manager.download.call_args_list), 1)

    def test_warn_glacier_force_glacier(self):
        self.cli_params['force_glacier_transfer'] = True
        fileinfo = FileInfo(
            src=self.bucket+'/'+self.key, dest=self.filename,
            operation_name='download',
            associated_response_data={
                'StorageClass': 'GLACIER',
            }
        )
        future = self.transfer_request_submitter.submit(fileinfo)

        # A warning should have not been submitted because it is glacier
        # transfers were forced.
        self.assertTrue(self.result_queue.empty())
        self.assertIs(self.transfer_manager.download.return_value, future)
        self.assertEqual(len(self.transfer_manager.download.call_args_list), 1)

    def test_warn_glacier_ignore_glacier_warnings(self):
        self.cli_params['ignore_glacier_warnings'] = True
        fileinfo = FileInfo(
            src=self.bucket+'/'+self.key, dest=self.filename,
            operation_name='download',
            associated_response_data={
                'StorageClass': 'GLACIER',
            }
        )
        future = self.transfer_request_submitter.submit(fileinfo)

        # A warning should have not been submitted because it was specified
        # to ignore glacier warnings.
        self.assertTrue(self.result_queue.empty())
        # But the transfer still should have been skipped.
        self.assertIsNone(future)
        self.assertEqual(len(self.transfer_manager.download.call_args_list), 0)


class TestCopyRequestSubmitter(BaseTransferRequestSubmitterTest):
    def setUp(self):
        super(TestCopyRequestSubmitter, self).setUp()
        self.source_bucket = 'mysourcebucket'
        self.source_key = 'mysourcekey'
        self.transfer_request_submitter = CopyRequestSubmitter(
            self.transfer_manager, self.result_queue, self.cli_params)

    def test_can_submit(self):
        fileinfo = FileInfo(
            src=self.source_bucket+'/'+self.source_key,
            dest=self.bucket+'/'+self.key, operation_name='copy')
        self.assertTrue(
            self.transfer_request_submitter.can_submit(fileinfo))
        fileinfo.operation_name = 'foo'
        self.assertFalse(
            self.transfer_request_submitter.can_submit(fileinfo))

    def test_submit(self):
        fileinfo = FileInfo(
            src=self.source_bucket+'/'+self.source_key,
            dest=self.bucket+'/'+self.key)
        self.cli_params['guess_mime_type'] = True  # Default settings
        future = self.transfer_request_submitter.submit(fileinfo)
        self.assertIs(self.transfer_manager.copy.return_value, future)
        copy_call_kwargs = self.transfer_manager.copy.call_args[1]
        self.assertEqual(
            copy_call_kwargs['copy_source'],
            {'Bucket': self.source_bucket, 'Key': self.source_key})
        self.assertEqual(copy_call_kwargs['bucket'], self.bucket)
        self.assertEqual(copy_call_kwargs['key'], self.key)
        self.assertEqual(copy_call_kwargs['extra_args'], {})

        # Make sure the subscriber applied are of the correct type and order
        ref_subscribers = [
            ProvideSizeSubscriber,
            ProvideCopyContentTypeSubscriber,
            CopyResultSubscriber
        ]
        actual_subscribers = copy_call_kwargs['subscribers']
        self.assertEqual(len(ref_subscribers), len(actual_subscribers))
        for i, actual_subscriber in enumerate(actual_subscribers):
            self.assertIsInstance(actual_subscriber, ref_subscribers[i])

    def test_submit_with_extra_args(self):
        fileinfo = FileInfo(
            src=self.source_bucket+'/'+self.source_key,
            dest=self.bucket+'/'+self.key)
        # Set some extra argument like storage_class to make sure cli
        # params get mapped to request parameters.
        self.cli_params['storage_class'] = 'STANDARD_IA'
        self.transfer_request_submitter.submit(fileinfo)

        copy_call_kwargs = self.transfer_manager.copy.call_args[1]
        self.assertEqual(
            copy_call_kwargs['extra_args'], {'StorageClass': 'STANDARD_IA'})

    def test_submit_when_content_type_specified(self):
        fileinfo = FileInfo(
            src=self.source_bucket+'/'+self.source_key,
            dest=self.bucket+'/'+self.key)
        self.cli_params['content_type'] = 'text/plain'
        self.transfer_request_submitter.submit(fileinfo)

        copy_call_kwargs = self.transfer_manager.copy.call_args[1]
        self.assertEqual(
            copy_call_kwargs['extra_args'], {'ContentType': 'text/plain'})
        ref_subscribers = [
            ProvideSizeSubscriber,
            CopyResultSubscriber
        ]
        actual_subscribers = copy_call_kwargs['subscribers']
        self.assertEqual(len(ref_subscribers), len(actual_subscribers))
        for i, actual_subscriber in enumerate(actual_subscribers):
            self.assertIsInstance(actual_subscriber, ref_subscribers[i])

    def test_submit_when_no_guess_content_mime_type(self):
        fileinfo = FileInfo(
            src=self.source_bucket+'/'+self.source_key,
            dest=self.bucket+'/'+self.key)
        self.cli_params['guess_mime_type'] = False
        self.transfer_request_submitter.submit(fileinfo)

        copy_call_kwargs = self.transfer_manager.copy.call_args[1]
        ref_subscribers = [
            ProvideSizeSubscriber,
            CopyResultSubscriber
        ]
        actual_subscribers = copy_call_kwargs['subscribers']
        self.assertEqual(len(ref_subscribers), len(actual_subscribers))
        for i, actual_subscriber in enumerate(actual_subscribers):
            self.assertIsInstance(actual_subscriber, ref_subscribers[i])

    def test_warn_glacier_for_incompatible(self):
        fileinfo = FileInfo(
            src=self.source_bucket+'/'+self.source_key,
            dest=self.bucket+'/'+self.key,
            operation_name='copy',
            associated_response_data={
                'StorageClass': 'GLACIER',
            }
        )
        future = self.transfer_request_submitter.submit(fileinfo)

        # A warning should have been submitted because it is a non-restored
        # glacier object.
        warning_result = self.result_queue.get()
        self.assertIsInstance(warning_result, WarningResult)
        self.assertIn(
            'Unable to perform copy operations on GLACIER objects',
            warning_result.message)

        # The transfer request should have never been sent therefore return
        # no future.
        self.assertIsNone(future)
        # The transfer should have been skipped.
        self.assertEqual(len(self.transfer_manager.copy.call_args_list), 0)

    def test_not_warn_glacier_for_compatible(self):
        fileinfo = FileInfo(
            src=self.source_bucket+'/'+self.source_key,
            dest=self.bucket+'/'+self.key,
            operation_name='copy',
            associated_response_data={
                'StorageClass': 'GLACIER',
                'Restore': 'ongoing-request="false"'
            }
        )
        future = self.transfer_request_submitter.submit(fileinfo)
        self.assertIs(self.transfer_manager.copy.return_value, future)

        # A warning should have not been submitted because it is a restored
        # glacier object.
        self.assertTrue(self.result_queue.empty())

        # And the transfer should not have been skipped.
        self.assertEqual(len(self.transfer_manager.copy.call_args_list), 1)

    def test_warn_glacier_force_glacier(self):
        self.cli_params['force_glacier_transfer'] = True
        fileinfo = FileInfo(
            src=self.source_bucket+'/'+self.source_key,
            dest=self.bucket+'/'+self.key,
            operation_name='copy',
            associated_response_data={
                'StorageClass': 'GLACIER',
            }
        )
        future = self.transfer_request_submitter.submit(fileinfo)
        self.assertIs(self.transfer_manager.copy.return_value, future)

        # A warning should have not been submitted because it is glacier
        # transfers were forced.
        self.assertTrue(self.result_queue.empty())
        self.assertEqual(len(self.transfer_manager.copy.call_args_list), 1)

    def test_warn_glacier_ignore_glacier_warnings(self):
        self.cli_params['ignore_glacier_warnings'] = True
        fileinfo = FileInfo(
            src=self.source_bucket+'/'+self.source_key,
            dest=self.bucket+'/'+self.key,
            operation_name='copy',
            associated_response_data={
                'StorageClass': 'GLACIER',
            }
        )
        future = self.transfer_request_submitter.submit(fileinfo)

        # The transfer request should have never been sent therefore return
        # no future.
        self.assertIsNone(future)
        # A warning should have not been submitted because it was specified
        # to ignore glacier warnings.
        self.assertTrue(self.result_queue.empty())
        # But the transfer still should have been skipped.
        self.assertEqual(len(self.transfer_manager.copy.call_args_list), 0)


class TestUploadStreamRequestSubmitter(BaseTransferRequestSubmitterTest):
    def setUp(self):
        super(TestUploadStreamRequestSubmitter, self).setUp()
        self.filename = '-'
        self.cli_params['is_stream'] = True
        self.transfer_request_submitter = UploadStreamRequestSubmitter(
            self.transfer_manager, self.result_queue, self.cli_params)

    def test_can_submit(self):
        fileinfo = FileInfo(
            src=self.filename, dest=self.bucket+'/'+self.key,
            operation_name='upload')
        self.assertTrue(
            self.transfer_request_submitter.can_submit(fileinfo))
        self.cli_params['is_stream'] = False
        self.assertFalse(
            self.transfer_request_submitter.can_submit(fileinfo))

    def test_submit(self):
        fileinfo = FileInfo(
            src=self.filename, dest=self.bucket+'/'+self.key)
        future = self.transfer_request_submitter.submit(fileinfo)
        self.assertIs(self.transfer_manager.upload.return_value, future)

        upload_call_kwargs = self.transfer_manager.upload.call_args[1]
        self.assertIsInstance(
            upload_call_kwargs['fileobj'], NonSeekableStream)
        self.assertEqual(upload_call_kwargs['bucket'], self.bucket)
        self.assertEqual(upload_call_kwargs['key'], self.key)
        self.assertEqual(upload_call_kwargs['extra_args'], {})

        ref_subscribers = [
            UploadStreamResultSubscriber
        ]
        actual_subscribers = upload_call_kwargs['subscribers']
        self.assertEqual(len(ref_subscribers), len(actual_subscribers))
        for i, actual_subscriber in enumerate(actual_subscribers):
            self.assertIsInstance(actual_subscriber, ref_subscribers[i])

    def test_submit_with_expected_size_provided(self):
        provided_size = 100
        self.cli_params['expected_size'] = provided_size
        fileinfo = FileInfo(
            src=self.filename, dest=self.bucket+'/'+self.key)
        self.transfer_request_submitter.submit(fileinfo)
        upload_call_kwargs = self.transfer_manager.upload.call_args[1]

        ref_subscribers = [
            ProvideSizeSubscriber,
            UploadStreamResultSubscriber
        ]
        actual_subscribers = upload_call_kwargs['subscribers']
        self.assertEqual(len(ref_subscribers), len(actual_subscribers))
        for i, actual_subscriber in enumerate(actual_subscribers):
            self.assertIsInstance(actual_subscriber, ref_subscribers[i])
        # The ProvideSizeSubscriber should be providing the correct size
        self.assertEqual(actual_subscribers[0].size, provided_size)


class TestDownloadStreamRequestSubmitter(BaseTransferRequestSubmitterTest):
    def setUp(self):
        super(TestDownloadStreamRequestSubmitter, self).setUp()
        self.filename = '-'
        self.cli_params['is_stream'] = True
        self.transfer_request_submitter = DownloadStreamRequestSubmitter(
            self.transfer_manager, self.result_queue, self.cli_params)

    def test_can_submit(self):
        fileinfo = FileInfo(
            src=self.bucket+'/'+self.key, dest=self.filename,
            operation_name='download')
        self.assertTrue(
            self.transfer_request_submitter.can_submit(fileinfo))
        self.cli_params['is_stream'] = False
        self.assertFalse(
            self.transfer_request_submitter.can_submit(fileinfo))

    def test_submit(self):
        fileinfo = FileInfo(
            src=self.bucket+'/'+self.key, dest=self.filename)
        future = self.transfer_request_submitter.submit(fileinfo)
        self.assertIs(self.transfer_manager.download.return_value, future)

        download_call_kwargs = self.transfer_manager.download.call_args[1]
        self.assertIsInstance(
            download_call_kwargs['fileobj'], StdoutBytesWriter)
        self.assertEqual(download_call_kwargs['bucket'], self.bucket)
        self.assertEqual(download_call_kwargs['key'], self.key)
        self.assertEqual(download_call_kwargs['extra_args'], {})

        ref_subscribers = [
            DownloadStreamResultSubscriber
        ]
        actual_subscribers = download_call_kwargs['subscribers']
        self.assertEqual(len(ref_subscribers), len(actual_subscribers))
        for i, actual_subscriber in enumerate(actual_subscribers):
            self.assertIsInstance(actual_subscriber, ref_subscribers[i])


class TestDeleteRequestSubmitter(BaseTransferRequestSubmitterTest):
    def setUp(self):
        super(TestDeleteRequestSubmitter, self).setUp()
        self.transfer_request_submitter = DeleteRequestSubmitter(
            self.transfer_manager, self.result_queue, self.cli_params)

    def test_can_submit(self):
        fileinfo = FileInfo(
            src=self.bucket+'/'+self.key, dest=None, operation_name='delete')
        self.assertTrue(
            self.transfer_request_submitter.can_submit(fileinfo))
        fileinfo.operation_name = 'foo'
        self.assertFalse(
            self.transfer_request_submitter.can_submit(fileinfo))

    def test_submit(self):
        fileinfo = FileInfo(
            src=self.bucket+'/'+self.key, dest=None, operation_name='delete')
        future = self.transfer_request_submitter.submit(fileinfo)
        self.assertIs(self.transfer_manager.delete.return_value, future)

        delete_call_kwargs = self.transfer_manager.delete.call_args[1]
        self.assertEqual(delete_call_kwargs['bucket'], self.bucket)
        self.assertEqual(delete_call_kwargs['key'], self.key)
        self.assertEqual(delete_call_kwargs['extra_args'], {})

        ref_subscribers = [
            DeleteResultSubscriber
        ]
        actual_subscribers = delete_call_kwargs['subscribers']
        self.assertEqual(len(ref_subscribers), len(actual_subscribers))
        for i, actual_subscriber in enumerate(actual_subscribers):
            self.assertIsInstance(actual_subscriber, ref_subscribers[i])


if __name__ == "__main__":
    unittest.main()
