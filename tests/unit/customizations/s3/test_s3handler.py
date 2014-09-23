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
from awscli.testutils import unittest

from awscli import EnvironmentVariables
from awscli.customizations.s3.s3handler import S3Handler
from awscli.customizations.s3.fileinfo import FileInfo
from tests.unit.customizations.s3.fake_session import FakeSession
from tests.unit.customizations.s3 import make_loc_files, clean_loc_files, \
    make_s3_files, s3_cleanup, create_bucket, list_contents, list_buckets, \
    S3HandlerBaseTest


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
        self.s3_handler_multi = S3Handler(self.session, multi_threshold=10,
                                          chunksize=2,
                                          params=params)
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
        self.s3_handler_multi = S3Handler(self.session, params,
                                          multi_threshold=10, chunksize=2)
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
        self.s3_handler_multi = S3Handler(self.session, params,
                                          multi_threshold=10, chunksize=2)
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
        self.s3_handler_multi_except = S3Handler(self.fail_session, params,
                                                 multi_threshold=10,
                                                 chunksize=2)

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


if __name__ == "__main__":
    unittest.main()
