import unittest
import os
import datetime
import threading
import time
import random
import sys
import botocore.session

from awscli import EnvironmentVariables
from awscli.customizations.s3.s3handler import S3Handler
from awscli.customizations.s3.filegenerator import FileInfo
from tests.integration.customizations.s3.test_filegenerator import \
    make_loc_files, clean_loc_files, make_s3_files, s3_cleanup, create_bucket

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

"""
Note that all of these functions can be found in the unit tests.
The only difference is that these tests use botocore's actual session
variables to communicate with s3 as these are integration tests.  Therefore,
only tests that use sessions are included as integration tests.
"""


def list_contents(bucket):
    """
    This is a helper function used to return the contents of a list
    object operation
    """
    session = botocore.session.get_session(EnvironmentVariables)
    service = session.get_service('s3')
    region = session.get_config()['region']
    endpoint = service.get_endpoint(region)
    operation = service.get_operation('ListObjects')
    http_response, r_data = operation.call(endpoint, bucket=bucket)
    return r_data['Contents']


def list_buckets():
    """
    This is a helper function used to return the contents of a list
    buckets operation
    """
    session = botocore.session.get_session(EnvironmentVariables)
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
        self.session = botocore.session.get_session(EnvironmentVariables)
        self.s3_handler = S3Handler(self.session)
        self.bucket = make_s3_files()
        self.loc_files = make_loc_files()

    def tearDown(self):
        clean_loc_files(self.loc_files)
        s3_cleanup(self.bucket)

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
                                  dest_type='s3', operation='delete',
                                  size=0))
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
        self.assertEqual(len(list_contents(self.bucket)), 3)
        self.s3_handler.call(tasks)
        self.assertEqual(len(list_contents(self.bucket)), 0)

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
        self.session = botocore.session.get_session(EnvironmentVariables)
        self.s3_handler = S3Handler(self.session, {'acl': ['private']})
        self.s3_handler_multi = S3Handler(self.session, multi_threshold=10,
                                          chunksize=2,
                                          params={'acl': ['private']})
        self.bucket = create_bucket()
        self.loc_files = make_loc_files()
        self.s3_files = [self.bucket + '/text1.txt',
                         self.bucket + '/another_directory/text2.txt']

    def tearDown(self):
        clean_loc_files(self.loc_files)
        s3_cleanup(self.bucket)

    def test_upload(self):
        # Confirm there are no objects in the bucket
        self.assertEqual(len(list_contents(self.bucket)), 0)
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
        self.assertEqual(len(list_contents(self.bucket)), 2)

    def test_multi_upload(self):
        files = [self.loc_files[0], self.loc_files[1]]
        tasks = []
        for i in range(len(files)):
            tasks.append(FileInfo(src=self.loc_files[i],
                                  dest=self.s3_files[i], size=15,
                                  operation='upload'))

        # Note nothing is uploaded because the file is too small
        # a print statement will show up if it fails
        self.s3_handler_multi.call(tasks)


class S3HandlerTestMove(unittest.TestCase):
    """
    This class tests the ability to move s3 objects.  The move
    operation uses a copy then delete.  Thus, tests the ability
    to copy objects as well as delete
    """
    def setUp(self):
        self.session = botocore.session.get_session(EnvironmentVariables)
        self.s3_handler = S3Handler(self.session, {'acl': ['private']})
        self.bucket = make_s3_files()
        self.bucket2 = create_bucket()
        self.s3_files = [self.bucket + '/text1.txt',
                         self.bucket + '/another_directory/text2.txt']
        self.s3_files2 = [self.bucket2 + '/text1.txt',
                          self.bucket2 + '/another_directory/text2.txt']

    def tearDown(self):
        s3_cleanup(self.bucket)
        s3_cleanup(self.bucket2)

    def test_move(self):
        # Confirm there are no objects in the bucket
        self.assertEqual(len(list_contents(self.bucket2)), 0)
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
        self.assertEqual(len(list_contents(self.bucket)), 1)
        self.assertEqual(len(list_contents(self.bucket2)), 2)


class S3HandlerTestDownload(unittest.TestCase):
    """
    This class tests the ability to download s3 objects locally as well
    as using multipart downloads
    """
    def setUp(self):
        self.session = botocore.session.get_session(EnvironmentVariables)
        self.s3_handler = S3Handler(self.session)
        self.s3_handler_multi = S3Handler(self.session, multi_threshold=10,
                                          chunksize=2)
        self.bucket = make_s3_files()
        self.s3_files = [self.bucket + '/text1.txt',
                         self.bucket + '/another_directory/text2.txt']
        directory1 = os.path.abspath('.') + os.sep + 'some_directory' + os.sep
        filename1 = directory1 + "text1.txt"
        directory2 = directory1 + 'another_directory' + os.sep
        filename2 = directory2 + "text2.txt"
        self.loc_files = [filename1, filename2]

    def tearDown(self):
        clean_loc_files(self.loc_files)
        s3_cleanup(self.bucket)

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


class S3HandlerTestBucket(unittest.TestCase):
    """
    Test the ability to make a bucket then remove it.
    """
    def setUp(self):
        self.session = botocore.session.get_session(EnvironmentVariables)
        self.s3_handler = S3Handler(self.session)
        self.bucket = None

    def tearDown(self):
        s3_cleanup(self.bucket)

    def test_bucket(self):
        rand1 = random.randrange(5000)
        rand2 = random.randrange(5000)
        self.bucket = str(rand1) + 'mybucket' + str(rand2) + '/'
        orig_number_buckets = len(list_buckets())

        file_info = FileInfo(src=self.bucket, operation='make_bucket', size=0)
        self.s3_handler.call([file_info])
        print("made it past")
        number_buckets = len(list_buckets())
        self.assertEqual(orig_number_buckets + 1, number_buckets)

        file_info = FileInfo(src=self.bucket, operation='remove_bucket',
                             size=0)
        s3_handler = S3Handler(self.session)
        self.s3_handler.call([file_info])
        number_buckets = len(list_buckets())
        self.assertEqual(orig_number_buckets, number_buckets)


if __name__ == "__main__":
    unittest.main()
