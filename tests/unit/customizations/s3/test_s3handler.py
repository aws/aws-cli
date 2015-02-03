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

from awscli.testutils import unittest
from awscli import EnvironmentVariables
from awscli.customizations.s3.s3handler import S3Handler, S3StreamHandler
from awscli.customizations.s3.fileinfo import FileInfo
from awscli.customizations.s3.tasks import CreateMultipartUploadTask, \
    UploadPartTask, CreateLocalFileTask
from awscli.customizations.s3.utils import MAX_PARTS
from awscli.customizations.s3.transferconfig import RuntimeConfig
from tests.unit.customizations.s3.fake_session import FakeSession
from tests.unit.customizations.s3 import make_loc_files, clean_loc_files, \
    make_s3_files, s3_cleanup, create_bucket, list_contents, list_buckets, \
    S3HandlerBaseTest, MockStdIn


def runtime_config(**kwargs):
    return RuntimeConfig().build_config(**kwargs)


class S3HandlerTestDeleteList(S3HandlerBaseTest):
    """
    This tests the ability to delete both files locally and in s3.
    """
    def setUp(self):
        super(S3HandlerTestDeleteList, self).setUp()
        self.session = FakeSession()
        self.service = self.session.get_service('s3')
        self.endpoint = self.service.get_endpoint('us-east-1')
        params = {'region': 'us-east-1'}
        self.s3_handler = S3Handler(self.session, params)
        self.bucket = make_s3_files(self.session)
        self.loc_files = make_loc_files()

    def tearDown(self):
        super(S3HandlerTestDeleteList, self).tearDown()
        clean_loc_files(self.loc_files)
        s3_cleanup(self.bucket, self.session)

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
                service=self.service, endpoint=self.endpoint))
        self.s3_handler.call(tasks)
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
                service=self.service,
                endpoint=self.endpoint))
        self.assertEqual(len(list_contents(self.bucket, self.session)), 3)
        self.s3_handler.call(tasks)
        self.assertEqual(len(list_contents(self.bucket, self.session)), 0)

    def test_list_objects(self):
        """
        Tests the ability to list objects, common prefixes, and buckets.
        If an error occurs the test fails as this is only a printing
        operation
        """
        prefix_name = self.bucket + '/'
        file_info = FileInfo(
            src=prefix_name, operation_name='list_objects', size=0,
            service=self.service, endpoint=self.endpoint)
        params = {'region': 'us-east-1'}
        s3_handler = S3Handler(self.session, params)
        s3_handler.call([file_info])
        file_info = FileInfo(
            src='', operation_name='list_objects', size=0,
            service=self.service, endpoint=self.endpoint)
        s3_handler = S3Handler(self.session, params)
        s3_handler.call([file_info])


class S3HandlerTestURLEncodeDeletes(S3HandlerBaseTest):
    def setUp(self):
        super(S3HandlerTestURLEncodeDeletes, self).setUp()
        self.session = FakeSession()
        self.service = self.session.get_service('s3')
        self.endpoint = self.service.get_endpoint('us-east-1')
        params = {'region': 'us-east-1'}
        self.s3_handler = S3Handler(self.session, params)
        self.bucket = make_s3_files(self.session, key1='a+b/foo', key2=None)

    def tearDown(self):
        super(S3HandlerTestURLEncodeDeletes, self).tearDown()
        s3_cleanup(self.bucket, self.session)

    def test_s3_delete_url_encode(self):
        """
        Tests S3 deletes. The files used are the same generated from
        filegenerators_test.py.  This includes the create s3 file.
        """
        key = self.bucket + '/a+b/foo'
        tasks = [FileInfo(
            src=key, src_type='s3', dest_type='local',
            operation_name='delete', size=0,
            service=self.service, endpoint=self.endpoint)]
        self.assertEqual(len(list_contents(self.bucket, self.session)), 1)
        self.s3_handler.call(tasks)
        self.assertEqual(len(list_contents(self.bucket, self.session)), 0)


class S3HandlerTestUpload(S3HandlerBaseTest):
    """
    This class tests the ability to upload objects into an S3 bucket as
    well as multipart uploads
    """
    def setUp(self):
        super(S3HandlerTestUpload, self).setUp()
        self.session = FakeSession()
        self.service = self.session.get_service('s3')
        self.endpoint = self.service.get_endpoint('us-east-1')
        params = {'region': 'us-east-1', 'acl': ['private'], 'quiet': True}
        self.s3_handler = S3Handler(self.session, params)
        self.s3_handler_multi = S3Handler(
            self.session, params=params,
            runtime_config=runtime_config(
                multipart_threshold=10, multipart_chunksize=2))
        self.bucket = create_bucket(self.session)
        self.loc_files = make_loc_files()
        self.s3_files = [self.bucket + '/text1.txt',
                         self.bucket + '/another_directory/text2.txt']

    def tearDown(self):
        super(S3HandlerTestUpload, self).tearDown()
        clean_loc_files(self.loc_files)
        s3_cleanup(self.bucket, self.session)

    def test_upload(self):
        # Confirm there are no objects in the bucket.
        self.assertEqual(len(list_contents(self.bucket, self.session)), 0)
        # Create file info objects to perform upload.
        files = [self.loc_files[0], self.loc_files[1]]
        tasks = []
        for i in range(len(files)):
            tasks.append(FileInfo(
                src=self.loc_files[i],
                dest=self.s3_files[i],
                operation_name='upload', size=0,
                service=self.service, endpoint=self.endpoint))
        # Perform the upload.
        self.s3_handler.call(tasks)
        # Confirm the files were uploaded.
        self.assertEqual(len(list_contents(self.bucket, self.session)), 2)
        # Verify the guessed content type.
        self.assertEqual(
            self.session.s3[self.bucket][
                'another_directory/text2.txt']['ContentType'],
            'text/plain')

    def test_upload_fail(self):
        """
        One of the uploads will fail to upload in this test as
        the second s3 destination's bucket does not exist.
        """
        self.assertEqual(len(list_contents(self.bucket, self.session)), 0)
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
                service=self.service,
                endpoint=self.endpoint))
        self.s3_handler.call(tasks)
        # Confirm only one of the files was uploaded.
        self.assertEqual(len(list_contents(self.bucket, self.session)), 1)

    def test_multi_upload(self):
        """
        This test only checks that the multipart upload process works.
        It confirms that the parts are properly formatted but does not
        perform any tests past checking the parts are uploaded correctly.
        """
        files = [self.loc_files[0], self.loc_files[1]]
        tasks = []
        for i in range(len(files)):
            tasks.append(FileInfo(
                src=self.loc_files[i],
                dest=self.s3_files[i], size=15,
                operation_name='upload',
                service=self.service,
                endpoint=self.endpoint))
        self.s3_handler_multi.call(tasks)
        self.assertEqual(
            self.session.s3[self.bucket][
                'another_directory/text2.txt']['ContentType'],
            'text/plain')


class S3HandlerExceptionSingleTaskTest(S3HandlerBaseTest):
    """
    This tests the ability to handle connection and md5 exceptions.
    The command used in this general test is a put command.
    """
    def setUp(self):
        super(S3HandlerExceptionSingleTaskTest, self).setUp()
        self.session = FakeSession(True, True)
        self.service = self.session.get_service('s3')
        self.endpoint = self.service.get_endpoint('us-east-1')
        params = {'region': 'us-east-1'}
        self.s3_handler = S3Handler(self.session, params)
        self.bucket = create_bucket(self.session)
        self.loc_files = make_loc_files()
        self.s3_files = [self.bucket + '/text1.txt',
                         self.bucket + '/another_directory/text2.txt']

    def tearDown(self):
        super(S3HandlerExceptionSingleTaskTest, self).tearDown()
        clean_loc_files(self.loc_files)
        s3_cleanup(self.bucket, self.session)

    def test_upload(self):
        # Confirm there are no objects in the bucket.
        self.assertEqual(len(list_contents(self.bucket, self.session)), 0)
        # Create file info objects to perform upload.
        files = [self.loc_files[0], self.loc_files[1]]
        tasks = []
        for i in range(len(files)):
            tasks.append(FileInfo(src=self.loc_files[i],
                                  dest=self.s3_files[i],
                                  operation_name='upload', size=0,
                                  service=self.service,
                                  endpoint=self.endpoint))
        # Perform the upload.
        self.s3_handler.call(tasks)
        # Confirm despite the exceptions, the files were uploaded.
        self.assertEqual(len(list_contents(self.bucket, self.session)), 2)


class S3HandlerExceptionMultiTaskTest(S3HandlerBaseTest):
    """
    This tests the ability to handle multipart upload exceptions.
    This includes a standard error stemming from an operation on
    a nonexisting bucket, connection error, and md5 error.
    """
    def setUp(self):
        super(S3HandlerExceptionMultiTaskTest, self).setUp()
        self.session = FakeSession(True, True)
        self.service = self.session.get_service('s3')
        self.endpoint = self.service.get_endpoint('us-east-1')
        params = {'region': 'us-east-1', 'quiet': True}
        self.s3_handler_multi = S3Handler(
            self.session, params,
            runtime_config=runtime_config(
                multipart_threshold=10, multipart_chunksize=2))
        self.bucket = create_bucket(self.session)
        self.loc_files = make_loc_files()
        self.s3_files = [self.bucket + '/text1.txt',
                         self.bucket + '/another_directory/text2.txt']

    def tearDown(self):
        super(S3HandlerExceptionMultiTaskTest, self).tearDown()
        clean_loc_files(self.loc_files)
        s3_cleanup(self.bucket, self.session)

    def test_multi_upload(self):
        files = [self.loc_files[0], self.loc_files[1]]
        fail_s3_files = [self.bucket + '/text1.txt',
                         self.bucket[:-1] + '/another_directory/text2.txt']
        tasks = []
        for i in range(len(files)):
            tasks.append(FileInfo(
                src=self.loc_files[i],
                dest=fail_s3_files[i], size=15,
                operation_name='upload',
                service=self.service,
                endpoint=self.endpoint))
        self.s3_handler_multi.call(tasks)


class S3HandlerTestMvLocalS3(S3HandlerBaseTest):
    """
    This class tests the ability to move s3 objects.  The move
    operation uses a upload then delete.
    """
    def setUp(self):
        super(S3HandlerTestMvLocalS3, self).setUp()
        self.session = FakeSession()
        self.service = self.session.get_service('s3')
        self.endpoint = self.service.get_endpoint('us-east-1')
        params = {'region': 'us-east-1', 'acl': ['private'], 'quiet': True}
        self.s3_handler = S3Handler(self.session, params)
        self.bucket = create_bucket(self.session)
        self.loc_files = make_loc_files()
        self.s3_files = [self.bucket + '/text1.txt',
                         self.bucket + '/another_directory/text2.txt']

    def tearDown(self):
        super(S3HandlerTestMvLocalS3, self).tearDown()
        clean_loc_files(self.loc_files)
        s3_cleanup(self.bucket, self.session)

    def test_move_unicode(self):
        self.bucket2 = make_s3_files(self.session, key1=u'\u2713')
        tasks = [FileInfo(
            src=self.bucket2 + '/' + u'\u2713',
            src_type='s3',
            dest=self.bucket + '/' + u'\u2713',
            dest_type='s3', operation_name='move',
            size=0,
            service=self.service,
            endpoint=self.endpoint,
        )]
        self.s3_handler.call(tasks)
        self.assertEqual(len(list_contents(self.bucket, self.session)), 1)

    def test_move(self):
        # Create file info objects to perform move.
        files = [self.loc_files[0], self.loc_files[1]]
        tasks = []
        for i in range(len(files)):
            tasks.append(FileInfo(
                src=self.loc_files[i], src_type='local',
                dest=self.s3_files[i], dest_type='s3',
                operation_name='move', size=0,
                service=self.service,
                endpoint=self.endpoint))
        # Perform the move.
        self.s3_handler.call(tasks)
        # Confirm the files were uploaded.
        self.assertEqual(len(list_contents(self.bucket, self.session)), 2)
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
        self.session = FakeSession()
        self.service = self.session.get_service('s3')
        self.endpoint = self.service.get_endpoint('us-east-1')
        params = {'region': 'us-east-1', 'acl': ['private']}
        self.s3_handler = S3Handler(self.session, params)
        self.bucket = make_s3_files(self.session)
        self.bucket2 = create_bucket(self.session)
        self.s3_files = [self.bucket + '/text1.txt',
                         self.bucket + '/another_directory/text2.txt']
        self.s3_files2 = [self.bucket2 + '/text1.txt',
                          self.bucket2 + '/another_directory/text2.txt']

    def tearDown(self):
        super(S3HandlerTestMvS3S3, self).tearDown()
        s3_cleanup(self.bucket, self.session)
        s3_cleanup(self.bucket2, self.session)

    def test_move(self):
        # Confirm there are no objects in the bucket.
        self.assertEqual(len(list_contents(self.bucket2, self.session)), 0)
        # Create file info objects to perform move.
        tasks = []
        for i in range(len(self.s3_files)):
            tasks.append(FileInfo(
                src=self.s3_files[i], src_type='s3',
                dest=self.s3_files2[i], dest_type='s3',
                operation_name='move', size=0,
                service=self.service,
                endpoint=self.endpoint))
        # Perform the move.
        self.s3_handler.call(tasks)
        # Confirm the files were moved.  The origial bucket had three
        # objects. Only two were moved.
        self.assertEqual(len(list_contents(self.bucket, self.session)), 1)
        self.assertEqual(len(list_contents(self.bucket2, self.session)), 2)


class S3HandlerTestMvS3Local(S3HandlerBaseTest):
    """
    This class tests the ability to move s3 objects.  The move
    operation uses a download then delete.
    """
    def setUp(self):
        super(S3HandlerTestMvS3Local, self).setUp()
        self.session = FakeSession()
        self.service = self.session.get_service('s3')
        self.endpoint = self.service.get_endpoint('us-east-1')
        params = {'region': 'us-east-1'}
        self.s3_handler = S3Handler(self.session, params)
        self.bucket = make_s3_files(self.session)
        self.s3_files = [self.bucket + '/text1.txt',
                         self.bucket + '/another_directory/text2.txt']
        directory1 = os.path.abspath('.') + os.sep + 'some_directory' + os.sep
        filename1 = directory1 + "text1.txt"
        directory2 = directory1 + 'another_directory' + os.sep
        filename2 = directory2 + "text2.txt"
        self.loc_files = [filename1, filename2]

    def tearDown(self):
        super(S3HandlerTestMvS3Local, self).tearDown()
        clean_loc_files(self.loc_files)
        s3_cleanup(self.bucket, self.session)

    def test_move(self):
        # Create file info objects to perform move.
        tasks = []
        time = datetime.datetime.now()
        for i in range(len(self.s3_files)):
            tasks.append(FileInfo(
                src=self.s3_files[i], src_type='s3',
                dest=self.loc_files[i], dest_type='local',
                last_update=time, operation_name='move',
                size=0,
                service=self.service,
                endpoint=self.endpoint))
        # Perform the move.
        self.s3_handler.call(tasks)
        # Confirm that the files now exist.
        for filename in self.loc_files:
            self.assertTrue(os.path.exists(filename))
        # Ensure the contents are as expected.
        with open(self.loc_files[0], 'rb') as filename:
            self.assertEqual(filename.read(), b'This is a test.')
        with open(self.loc_files[1], 'rb') as filename:
            self.assertEqual(filename.read(), b'This is another test.')
        # Ensure the objects are no longer in the bucket.
        self.assertEqual(len(list_contents(self.bucket, self.session)), 1)


class S3HandlerTestDownload(S3HandlerBaseTest):
    """
    This class tests the ability to download s3 objects locally as well
    as using multipart downloads
    """
    def setUp(self):
        super(S3HandlerTestDownload, self).setUp()
        self.session = FakeSession()
        self.service = self.session.get_service('s3')
        self.endpoint = self.service.get_endpoint('us-east-1')
        params = {'region': 'us-east-1'}
        self.s3_handler = S3Handler(self.session, params)
        self.s3_handler_multi = S3Handler(
            self.session, params,
            runtime_config=runtime_config(multipart_threshold=10,
                                          multipart_chunksize=2))
        self.bucket = make_s3_files(self.session)
        self.s3_files = [self.bucket + '/text1.txt',
                         self.bucket + '/another_directory/text2.txt']
        directory1 = os.path.abspath('.') + os.sep + 'some_directory' + os.sep
        filename1 = directory1 + "text1.txt"
        directory2 = directory1 + 'another_directory' + os.sep
        filename2 = directory2 + "text2.txt"
        self.loc_files = [filename1, filename2]

        self.fail_session = FakeSession(connection_error=True)
        self.fail_session.s3 = self.session.s3
        self.s3_handler_multi_except = S3Handler(
            self.fail_session, params,
            runtime_config=runtime_config(
                multipart_threshold=10,
                multipart_chunksize=2))

    def tearDown(self):
        super(S3HandlerTestDownload, self).tearDown()
        clean_loc_files(self.loc_files)
        s3_cleanup(self.bucket, self.session)

    def test_download(self):
        # Confirm that the files do not exist.
        for filename in self.loc_files:
            self.assertFalse(os.path.exists(filename))
        # Create file info objects to perform download.
        tasks = []
        time = datetime.datetime.now()
        for i in range(len(self.s3_files)):
            tasks.append(FileInfo(
                src=self.s3_files[i], src_type='s3',
                dest=self.loc_files[i], dest_type='local',
                last_update=time, operation_name='download',
                size=0,
                service=self.service,
                endpoint=self.endpoint))
        # Perform the download.
        self.s3_handler.call(tasks)
        # Confirm that the files now exist.
        for filename in self.loc_files:
            self.assertTrue(os.path.exists(filename))
        # Ensure the contents are as expected.
        with open(self.loc_files[0], 'rb') as filename:
            self.assertEqual(filename.read(), b'This is a test.')
        with open(self.loc_files[1], 'rb') as filename:
            self.assertEqual(filename.read(), b'This is another test.')

    def test_multi_download(self):
        tasks = []
        time = datetime.datetime.now()
        for i in range(len(self.s3_files)):
            tasks.append(FileInfo(
                src=self.s3_files[i], src_type='s3',
                dest=self.loc_files[i], dest_type='local',
                last_update=time, operation_name='download',
                size=15,
                service=self.service,
                endpoint=self.endpoint,
            ))
        # Perform the multipart  download.
        self.s3_handler_multi.call(tasks)
        # Confirm that the files now exist.
        for filename in self.loc_files:
            self.assertTrue(os.path.exists(filename))
        # Ensure the contents are as expected.
        with open(self.loc_files[0], 'rb') as filename:
            self.assertEqual(filename.read(), b'This is a test.')
        with open(self.loc_files[1], 'rb') as filename:
            self.assertEqual(filename.read(), b'This is another test.')

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
                size=15,
                service=self.service,
                endpoint=self.endpoint
            ))
        # Perform the multipart  download.
        self.s3_handler_multi.call(tasks)
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
        self.session = FakeSession()
        self.service = self.session.get_service('s3')
        self.endpoint = self.service.get_endpoint('us-east-1')
        self.params = {'region': 'us-east-1'}
        self.bucket = None

    def tearDown(self):
        super(S3HandlerTestBucket, self).tearDown()
        s3_cleanup(self.bucket, self.session)

    def test_bucket(self):
        rand1 = random.randrange(5000)
        rand2 = random.randrange(5000)
        self.bucket = str(rand1) + 'mybucket' + str(rand2) + '/'
        orig_number_buckets = len(list_buckets(self.session))

        file_info = FileInfo(
            src=self.bucket,
            operation_name='make_bucket',
            size=0,
            service=self.service,
            endpoint=self.endpoint)
        S3Handler(self.session, self.params).call([file_info])
        number_buckets = len(list_buckets(self.session))
        self.assertEqual(orig_number_buckets + 1, number_buckets)

        file_info = FileInfo(
            src=self.bucket,
            operation_name='remove_bucket',
            size=0,
            service=self.service,
            endpoint=self.endpoint)
        S3Handler(self.session, self.params).call([file_info])
        number_buckets = len(list_buckets(self.session))
        self.assertEqual(orig_number_buckets, number_buckets)


class TestStreams(S3HandlerBaseTest):
    def setUp(self):
        super(TestStreams, self).setUp()
        self.session = FakeSession()
        self.service = self.session.get_service('s3')
        self.endpoint = self.service.get_endpoint('us-east-1')
        self.params = {'is_stream': True, 'region': 'us-east-1'}

    def test_pull_from_stream(self):
        s3handler = S3StreamHandler(
            self.session, self.params,
            runtime_config=runtime_config(multipart_chunksize=2))
        input_to_stdin = b'This is a test'
        size = len(input_to_stdin)
        # Retrieve the entire string.
        with MockStdIn(input_to_stdin):
            payload, is_amount_requested = s3handler._pull_from_stream(size)
            data = payload.read()
            self.assertTrue(is_amount_requested)
            self.assertEqual(data, input_to_stdin)
        # Ensure the function exits when there is nothing to read.
        with MockStdIn():
            payload, is_amount_requested = s3handler._pull_from_stream(size)
            data = payload.read()
            self.assertFalse(is_amount_requested)
            self.assertEqual(data, b'')
        # Ensure the function does not grab too much out of stdin.
        with MockStdIn(input_to_stdin):
            payload, is_amount_requested = s3handler._pull_from_stream(size-2)
            data = payload.read()
            self.assertTrue(is_amount_requested)
            self.assertEqual(data, input_to_stdin[:-2])
            # Retrieve the rest of standard in.
            payload, is_amount_requested = s3handler._pull_from_stream(size)
            data = payload.read()
            self.assertFalse(is_amount_requested)
            self.assertEqual(data, input_to_stdin[-2:])

    def test_upload_stream_not_multipart_task(self):
        s3handler = S3StreamHandler(self.session, self.params)
        s3handler.executor = mock.Mock()
        fileinfos = [FileInfo('filename', operation_name='upload',
                              is_stream=True, size=0)]
        with MockStdIn(b'bar'):
            s3handler._enqueue_tasks(fileinfos)
        submitted_tasks = s3handler.executor.submit.call_args_list
        # No multipart upload should have been submitted.
        self.assertEqual(len(submitted_tasks), 1)
        self.assertEqual(submitted_tasks[0][0][0].payload.read(),
                         b'bar')

    def test_upload_stream_is_multipart_task(self):
        s3handler = S3StreamHandler(
            self.session, self.params,
            runtime_config=runtime_config(multipart_threshold=1))
        s3handler.executor = mock.Mock()
        fileinfos = [FileInfo('filename', operation_name='upload',
                              is_stream=True, size=0)]
        with MockStdIn(b'bar'):
            s3handler._enqueue_tasks(fileinfos)
        submitted_tasks = s3handler.executor.submit.call_args_list
        # This should be a multipart upload so multiple tasks
        # should have been submitted.
        self.assertEqual(len(submitted_tasks), 4)
        self.assertEqual(submitted_tasks[1][0][0]._payload.read(),
                         b'b')
        self.assertEqual(submitted_tasks[2][0][0]._payload.read(),
                         b'ar')

    def test_upload_stream_with_expected_size(self):
        self.params['expected_size'] = 100000
        # With this large of expected size, the chunksize of 2 will have
        # to change.
        s3handler = S3StreamHandler(
            self.session, self.params,
            runtime_config=runtime_config(multipart_chunksize=2))
        s3handler.executor = mock.Mock()
        fileinfo = FileInfo('filename', operation_name='upload',
                            is_stream=True)
        with MockStdIn(b'bar'):
            s3handler._enqueue_multipart_upload_tasks(fileinfo, b'')
        submitted_tasks = s3handler.executor.submit.call_args_list
        # Determine what the chunksize was changed to from one of the
        # UploadPartTasks.
        changed_chunk_size = submitted_tasks[1][0][0]._chunk_size
        # New chunksize should have a total parts under 1000.
        self.assertTrue(100000 / float(changed_chunk_size) <= MAX_PARTS)

    def test_upload_stream_enqueue_upload_task(self):
        s3handler = S3StreamHandler(self.session, self.params)
        s3handler.executor = mock.Mock()
        fileinfo = FileInfo('filename', operation_name='upload',
                            is_stream=True)
        stdin_input = b'This is a test'
        with MockStdIn(stdin_input):
            num_parts = s3handler._enqueue_upload_tasks(None, 2, mock.Mock(),
                                                        fileinfo,
                                                        UploadPartTask)
        submitted_tasks = s3handler.executor.submit.call_args_list
        # Ensure the returned number of parts is correct.
        self.assertEqual(num_parts, len(submitted_tasks) + 1)
        # Ensure the number of tasks uploaded are as expected
        self.assertEqual(len(submitted_tasks), 8)
        index = 0
        for i in range(len(submitted_tasks)-1):
            self.assertEqual(submitted_tasks[i][0][0]._payload.read(),
                             stdin_input[index:index+2])
            index += 2
        # Ensure that the last part is an empty string as expected.
        self.assertEqual(submitted_tasks[7][0][0]._payload.read(), b'')

    def test_enqueue_upload_single_part_task_stream(self):
        """
        This test ensures that a payload gets attached to a task when
        it is submitted to the executor.
        """
        s3handler = S3StreamHandler(self.session, self.params)
        s3handler.executor = mock.Mock()
        mock_task_class = mock.Mock()
        s3handler._enqueue_upload_single_part_task(
            part_number=1, chunk_size=2, upload_context=None,
            filename=None, task_class=mock_task_class,
            payload=b'This is a test'
        )
        args, kwargs = mock_task_class.call_args
        self.assertIn('payload', kwargs.keys())
        self.assertEqual(kwargs['payload'], b'This is a test')

    def test_enqueue_multipart_download_stream(self):
        """
        This test ensures the right calls are made in ``_enqueue_tasks()``
        if the file should be a multipart download.
        """
        s3handler = S3StreamHandler(
            self.session, self.params,
            runtime_config=runtime_config(multipart_threshold=5))
        s3handler.executor = mock.Mock()
        fileinfo = FileInfo('filename', operation_name='download',
                            is_stream=True)
        with mock.patch('awscli.customizations.s3.s3handler'
                        '.S3StreamHandler._enqueue_range_download_tasks') as \
                mock_enqueue_range_tasks:
            with mock.patch('awscli.customizations.s3.fileinfo.FileInfo'
                            '.set_size_from_s3') as mock_set_size_from_s3:
                # Set the file size to something larger than the multipart
                # threshold.
                fileinfo.size = 100
                # Run the main enqueue function.
                s3handler._enqueue_tasks([fileinfo])
                # Assert that the size of the ``FileInfo`` object was set
                # if we are downloading a stream.
                self.assertTrue(mock_set_size_from_s3.called)
                # Ensure that this download would have been a multipart
                # download.
                self.assertTrue(mock_enqueue_range_tasks.called)

    def test_enqueue_range_download_tasks_stream(self):
        s3handler = S3StreamHandler(
            self.session, self.params,
            runtime_config=runtime_config(multipart_chunksize=100))
        s3handler.executor = mock.Mock()
        fileinfo = FileInfo('filename', operation_name='download',
                            is_stream=True, size=100)
        s3handler._enqueue_range_download_tasks(fileinfo)
        # Ensure that no request was sent to make a file locally.
        submitted_tasks = s3handler.executor.submit.call_args_list
        self.assertNotEqual(type(submitted_tasks[0][0][0]),
                            CreateLocalFileTask)


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


if __name__ == "__main__":
    unittest.main()
