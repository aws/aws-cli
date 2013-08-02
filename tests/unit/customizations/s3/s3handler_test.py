import datetime
import os
import random
import sys
import threading
import time
if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

from awscli import EnvironmentVariables
from tests.unit.customizations.s3.fake_session import FakeSession
from tests.unit.customizations.s3.filegenerator_test import \
    make_loc_files, clean_loc_files, make_s3_files, s3_cleanup, create_bucket
from awscli.customizations.s3.s3handler import S3Handler
from awscli.customizations.s3.filegenerator import FileInfo


def list_contents(bucket, session):
    """
    This is a helper function used to return the contents of a list
    object operation
    """
    session = session
    service = session.get_service('s3')
    region = session.get_config()['region']
    endpoint = service.get_endpoint(region)
    operation = service.get_operation('ListObjects')
    http_response, r_data = operation.call(endpoint, bucket=bucket)
    return r_data['Contents']


def list_buckets(session):
    """
    This is a helper function used to return the contents of a list
    buckets operation
    """
    session = session
    service = session.get_service('s3')
    region = session.get_config()['region']
    endpoint = service.get_endpoint(region)
    operation = service.get_operation('ListBuckets')
    html_response, response_data = operation.call(endpoint)
    contents = response_data['Buckets']
    return contents


class S3HandlerTestDeleteList(unittest.TestCase):
    """
    This tests the ability to delete both files locally and in s3
    """
    def setUp(self):
        self.session = FakeSession()
        self.s3_handler = S3Handler(self.session)
        self.bucket = make_s3_files(self.session)
        self.loc_files = make_loc_files()

    def tearDown(self):
        clean_loc_files(self.loc_files)
        s3_cleanup(self.bucket, self.session)

    def test_loc_delete(self):
        """
        Test delete local file tasks.  The local files are the same
        generated from filegenerator_test.py
        """
        files = [self.loc_files[0], self.loc_files[1]]
        tasks = []
        for filename in files:
            self.assertEqual(os.path.exists(filename), True)
            tasks.append(FileInfo(src=filename, src_type='local',
                                  dest_type='s3', operation='delete', size=0))
        self.s3_handler.call(tasks)
        for filename in files:
            self.assertEqual(os.path.exists(filename), False)

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
            tasks.append(FileInfo(src=key, src_type='s3',
                                  dest_type='local', operation='delete',
                                  size=0))
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
        file_info = FileInfo(src=prefix_name, operation='list_objects', size=0)
        s3_handler = S3Handler(self.session)
        s3_handler.call([file_info])
        file_info = FileInfo(src='', operation='list_objects', size=0)
        s3_handler = S3Handler(self.session)
        s3_handler.call([file_info])


class S3HandlerTestUpload(unittest.TestCase):
    """
    This class tests the ability to upload objects into an S3 bucket as
    well as multipart uploads
    """
    def setUp(self):
        self.session = FakeSession()
        self.s3_handler = S3Handler(self.session, {'acl': ['private']})
        self.s3_handler_multi = S3Handler(self.session, multi_threshold=10,
                                          chunksize=2,
                                          params={'acl': ['private']})
        self.bucket = create_bucket(self.session)
        self.loc_files = make_loc_files()
        self.s3_files = [self.bucket + '/text1.txt',
                         self.bucket + '/another_directory/text2.txt']

    def tearDown(self):
        clean_loc_files(self.loc_files)
        s3_cleanup(self.bucket, self.session)

    def test_upload(self):
        """
        Test the abiltiy to upload a file without the use of threads.
        """
        # Confirm there are no objects in the bucket
        self.assertEqual(len(list_contents(self.bucket, self.session)), 0)
        # Create file info objects to perform upload
        files = [self.loc_files[0], self.loc_files[1]]
        tasks = []
        for i in range(len(files)):
            tasks.append(FileInfo(src=self.loc_files[i],
                                  dest=self.s3_files[i],
                                  operation='upload', size=0))
        # Perform the upload
        self.s3_handler.call(tasks)
        # Confirm the files were uploaded
        self.assertEqual(len(list_contents(self.bucket, self.session)), 2)

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
            tasks.append(FileInfo(src=self.loc_files[i],
                                  dest=fail_s3_files[i],
                                  operation='upload', size=0))
        self.s3_handler.call(tasks)
        # Confirm only one of the files was uploaded
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
            tasks.append(FileInfo(src=self.loc_files[i],
                                  dest=self.s3_files[i], size=15,
                                  operation='upload'))
        self.s3_handler_multi.call(tasks)


class S3HandlerExceptionSingleTaskTest(unittest.TestCase):
    """
    This tests the ability to handle connection and md5 exceptions.
    The command used in this general test is a put command.
    """
    def setUp(self):
        self.session = FakeSession(True, True)
        self.s3_handler = S3Handler(self.session)
        self.bucket = create_bucket(self.session)
        self.loc_files = make_loc_files()
        self.s3_files = [self.bucket + '/text1.txt',
                         self.bucket + '/another_directory/text2.txt']

    def tearDown(self):
        clean_loc_files(self.loc_files)
        s3_cleanup(self.bucket, self.session)

    def test_upload(self):
        # Confirm there are no objects in the bucket
        self.assertEqual(len(list_contents(self.bucket, self.session)), 0)
        # Create file info objects to perform upload
        files = [self.loc_files[0], self.loc_files[1]]
        tasks = []
        for i in range(len(files)):
            tasks.append(FileInfo(src=self.loc_files[i],
                                  dest=self.s3_files[i],
                                  operation='upload', size=0))
        # Perform the upload
        self.s3_handler.call(tasks)
        # Confirm despite the exceptions, the files were uploaded
        self.assertEqual(len(list_contents(self.bucket, self.session)), 2)


class S3HandlerExceptionMultiTaskTest(unittest.TestCase):
    """
    This tests the ability to handle multipart upload exceptions.
    This includes a standard error stemming from an operation on
    a nonexisting bucket, connection error, and md5 error.
    """
    def setUp(self):
        self.session = FakeSession(True, True)
        self.s3_handler_multi = S3Handler(self.session, multi_threshold=10,
                                          chunksize=2)
        self.bucket = create_bucket(self.session)
        self.loc_files = make_loc_files()
        self.s3_files = [self.bucket + '/text1.txt',
                         self.bucket + '/another_directory/text2.txt']

    def tearDown(self):
        clean_loc_files(self.loc_files)
        s3_cleanup(self.bucket, self.session)

    def test_multi_upload(self):
        files = [self.loc_files[0], self.loc_files[1]]
        fail_s3_files = [self.bucket + '/text1.txt',
                         self.bucket[:-1] + '/another_directory/text2.txt']
        tasks = []
        for i in range(len(files)):
            tasks.append(FileInfo(src=self.loc_files[i],
                                  dest=fail_s3_files[i], size=15,
                                  operation='upload'))
        self.s3_handler_multi.call(tasks)


class S3HandlerTestMove(unittest.TestCase):
    """
    This class tests the ability to move s3 objects.  The move
    operation uses a copy then delete.  Thus, tests the ability
    to copy objects as well as delete
    """
    def setUp(self):
        self.session = FakeSession()
        self.s3_handler = S3Handler(self.session, {'acl': ['private']})
        self.bucket = make_s3_files(self.session)
        self.bucket2 = create_bucket(self.session)
        self.s3_files = [self.bucket + '/text1.txt',
                         self.bucket + '/another_directory/text2.txt']
        self.s3_files2 = [self.bucket2 + '/text1.txt',
                          self.bucket2 + '/another_directory/text2.txt']

    def tearDown(self):
        s3_cleanup(self.bucket, self.session)
        s3_cleanup(self.bucket2, self.session)

    def test_move(self):
        # Confirm there are no objects in the bucket
        self.assertEqual(len(list_contents(self.bucket2, self.session)), 0)
        # Create file info objects to perform move
        tasks = []
        for i in range(len(self.s3_files)):
            tasks.append(FileInfo(src=self.s3_files[i], src_type='s3',
                                  dest=self.s3_files2[i], dest_type='s3',
                                  operation='move', size=0))
        # Perform the move
        self.s3_handler.call(tasks)
        # Confirm the files were moved.  The origial bucket had three
        # objects. Only two were moved
        self.assertEqual(len(list_contents(self.bucket, self.session)), 1)
        self.assertEqual(len(list_contents(self.bucket2, self.session)), 2)


class S3HandlerTestDownload(unittest.TestCase):
    """
    This class tests the ability to download s3 objects locally as well
    as using multipart downloads
    """
    def setUp(self):
        self.session = FakeSession()
        self.s3_handler = S3Handler(self.session)
        self.s3_handler_multi = S3Handler(self.session, multi_threshold=10,
                                          chunksize=2)
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
        self.s3_handler_multi_except = S3Handler(self.fail_session,
                                                 multi_threshold=10,
                                                 chunksize=2)

    def tearDown(self):
        clean_loc_files(self.loc_files)
        s3_cleanup(self.bucket, self.session)

    def test_download(self):
        # Confirm that the files do not exist
        for filename in self.loc_files:
            self.assertEqual(os.path.exists(filename), False)
        # Create file info objects to perform download
        tasks = []
        time = datetime.datetime.now()
        for i in range(len(self.s3_files)):
            tasks.append(FileInfo(src=self.s3_files[i], src_type='s3',
                                  dest=self.loc_files[i], dest_type='local',
                                  last_update=time, operation='download',
                                  size=0))
        # Perform the download
        self.s3_handler.call(tasks)
        # Confirm that the files now exist
        for filename in self.loc_files:
            self.assertEqual(os.path.exists(filename), True)
        # Ensure the contents are as expected
        with open(self.loc_files[0], 'rb') as filename:
            self.assertEqual(filename.read(), b'This is a test.')
        with open(self.loc_files[1], 'rb') as filename:
            self.assertEqual(filename.read(), b'This is another test.')

    def test_multi_download(self):
        tasks = []
        time = datetime.datetime.now()
        for i in range(len(self.s3_files)):
            tasks.append(FileInfo(src=self.s3_files[i], src_type='s3',
                                  dest=self.loc_files[i], dest_type='local',
                                  last_update=time, operation='download',
                                  size=15))
        # Perform the multipart  download
        self.s3_handler_multi.call(tasks)
        # Confirm that the files now exist
        for filename in self.loc_files:
            self.assertEqual(os.path.exists(filename), True)
        # Ensure the contents are as expected
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
            tasks.append(FileInfo(src=wrong_s3_files[i], src_type='s3',
                                  dest=self.loc_files[i], dest_type='local',
                                  last_update=time, operation='download',
                                  size=15))
        # Perform the multipart  download
        self.s3_handler_multi.call(tasks)
        # Confirm that the files now exist
        for filename in self.loc_files:
            self.assertEqual(os.path.exists(filename), True)
        # Ensure that contents are as expected
        with open(self.loc_files[0], 'rb') as filename:
            self.assertEqual(filename.read(), b'This is a test.')
        with open(self.loc_files[1], 'rb') as filename:
            self.assertNotEqual(filename.read(), b'This is a test.')

    def test_multi_download_exceptions(self):
        """
        Ensure multipart downloads can handle connection errors properly
        and correctly download the file.
        """
        tasks = []
        time = datetime.datetime.now()
        for i in range(len(self.s3_files)):
            tasks.append(FileInfo(src=self.s3_files[i], src_type='s3',
                                  dest=self.loc_files[i], dest_type='local',
                                  last_update=time, operation='download',
                                  size=15))
        self.s3_handler_multi_except.call(tasks)
        for filename in self.loc_files:
            self.assertEqual(os.path.exists(filename), True)
        with open(self.loc_files[0], 'rb') as filename:
            self.assertEqual(filename.read(), b'This is a test.')
        with open(self.loc_files[1], 'rb') as filename:
            self.assertEqual(filename.read(), b'This is another test.')


class S3HandlerTestBucket(unittest.TestCase):
    """
    Test the ability to make a bucket then remove it.
    """
    def setUp(self):
        self.session = FakeSession()
        self.s3_handler = S3Handler(self.session)
        self.bucket = None

    def tearDown(self):
        s3_cleanup(self.bucket, self.session)

    def test_bucket(self):
        rand1 = random.randrange(5000)
        rand2 = random.randrange(5000)
        self.bucket = str(rand1) + 'mybucket' + str(rand2) + '/'
        orig_number_buckets = len(list_buckets(self.session))

        file_info = FileInfo(src=self.bucket, operation='make_bucket', size=0)
        self.s3_handler.call([file_info])
        number_buckets = len(list_buckets(self.session))
        self.assertEqual(orig_number_buckets + 1, number_buckets)

        file_info = FileInfo(src=self.bucket, operation='remove_bucket',
                             size=0)
        self.s3_handler.call([file_info])
        number_buckets = len(list_buckets(self.session))
        self.assertEqual(orig_number_buckets, number_buckets)


if __name__ == "__main__":
    unittest.main()
