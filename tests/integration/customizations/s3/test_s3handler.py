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


# Note that all of these functions can be found in the unit tests.
# The only difference is that these tests use botocore's actual session
# variables to communicate with s3 as these are integration tests.  Therefore,
# only tests that use sessions are included as integration tests.

import os
import datetime
import random
import sys
from awscli.testutils import unittest, FileCreator

from awscli import EnvironmentVariables
from awscli.compat import StringIO
from awscli.customizations.s3.s3handler import S3Handler
from awscli.customizations.s3.fileinfo import FileInfo
from awscli.customizations.s3.transferconfig import RuntimeConfig
import botocore.session
from tests.unit.customizations.s3 import make_loc_files, clean_loc_files
from tests.integration.customizations.s3 import make_s3_files, s3_cleanup, \
    create_bucket


def runtime_config(**kwargs):
    return RuntimeConfig().build_config(**kwargs)


class S3HandlerTestDelete(unittest.TestCase):
    """
    This tests the ability to delete both files locally and in s3
    """
    def setUp(self):
        self.session = botocore.session.get_session(EnvironmentVariables)
        self.client = self.session.create_client('s3', 'us-west-2')
        self.source_client = self.session.create_client('s3', 'us-west-2')
        params = {'region': 'us-west-2'}
        self.s3_handler = S3Handler(self.session, params)
        self.bucket = make_s3_files(self.session)
        self.file_creator = FileCreator()
        self.loc_files = make_loc_files(self.file_creator)

    def tearDown(self):
        clean_loc_files(self.file_creator)
        s3_cleanup(self.bucket, self.session)

    def test_loc_delete(self):
        """
        Test delete local file tasks.  The local files are the same
        generated from filegenerator_test.py
        """
        files = [self.loc_files[0], self.loc_files[1]]
        tasks = []
        for filename in files:
            self.assertTrue(os.path.exists(filename))
            tasks.append(FileInfo(
                src=filename, src_type='local',
                dest_type='s3', operation_name='delete',
                size=0,
                client=self.client))
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
                size=0, client=self.client,
                source_client=self.source_client
            ))
        response = self.client.list_objects(Bucket=self.bucket)
        self.assertEqual(len(response.get('Contents', [])), 3)
        self.s3_handler.call(tasks)
        response = self.client.list_objects(Bucket=self.bucket)
        self.assertEqual(len(response.get('Contents', [])), 0)

    def test_delete_url_encode(self):
        bucket = make_s3_files(self.session, key1='a+b/foo', key2=None)
        self.addCleanup(s3_cleanup, bucket, self.session)
        key = bucket + '/a+b/foo'
        tasks = [FileInfo(
            src=key, src_type='s3',
            dest_type='local', operation_name='delete', size=0,
            client=self.client, source_client=self.source_client
        )]
        response = self.client.list_objects(Bucket=bucket)
        self.assertEqual(len(response.get('Contents', [])), 1)
        self.s3_handler.call(tasks)
        response = self.client.list_objects(Bucket=bucket)
        self.assertEqual(len(response.get('Contents', [])), 0)


class S3HandlerTestUpload(unittest.TestCase):
    """
    This class tests the ability to upload objects into an S3 bucket as
    well as multipart uploads
    """
    def setUp(self):
        self.session = botocore.session.get_session(EnvironmentVariables)
        self.client = self.session.create_client('s3', 'us-west-2')
        params = {'region': 'us-west-2', 'acl': 'private'}
        self.s3_handler = S3Handler(self.session, params)
        self.s3_handler_multi = S3Handler(
            self.session, params=params,
            runtime_config=runtime_config(
                multipart_threshold=10, multipart_chunksize=2))
        self.bucket = create_bucket(self.session)
        self.file_creator = FileCreator()
        self.loc_files = make_loc_files(self.file_creator)
        self.s3_files = [self.bucket + '/text1.txt',
                         self.bucket + '/another_directory/text2.txt']
        self.output = StringIO()
        self.saved_stderr = sys.stderr
        sys.stderr = self.output

    def tearDown(self):
        self.output.close()
        sys.stderr = self.saved_stderr
        clean_loc_files(self.file_creator)
        s3_cleanup(self.bucket, self.session)

    def test_upload(self):
        # Confirm there are no objects in the bucket.
        response = self.client.list_objects(Bucket=self.bucket)
        self.assertEqual(len(response.get('Contents', [])), 0)
        # Create file info objects to perform upload.
        files = [self.loc_files[0], self.loc_files[1]]
        tasks = []
        for i in range(len(files)):
            tasks.append(FileInfo(
                src=self.loc_files[i],
                dest=self.s3_files[i],
                operation_name='upload', size=0,
                client=self.client,
            ))
        # Perform the upload.
        self.s3_handler.call(tasks)
        # Confirm the files were uploaded.
        response = self.client.list_objects(Bucket=self.bucket)
        self.assertEqual(len(response.get('Contents', [])), 2)

    def test_multi_upload(self):
        files = [self.loc_files[0], self.loc_files[1]]
        tasks = []
        for i in range(len(files)):
            tasks.append(FileInfo(
                src=self.loc_files[i],
                dest=self.s3_files[i], size=15,
                operation_name='upload',
                client=self.client,
            ))

        # Note nothing is uploaded because the file is too small
        # a print statement will show up if it fails.
        self.s3_handler_multi.call(tasks)
        print_op = "Your proposed upload is smaller than the minimum"
        self.assertIn(print_op, self.output.getvalue())


class S3HandlerTestUnicodeMove(unittest.TestCase):
    def setUp(self):
        self.session = botocore.session.get_session(EnvironmentVariables)
        self.client = self.session.create_client('s3', 'us-west-2')
        self.source_client = self.session.create_client('s3', 'us-west-2')
        params = {'region': 'us-west-2', 'acl': 'private', 'quiet': True}
        self.s3_handler = S3Handler(self.session, params)
        self.bucket = make_s3_files(self.session, key1=u'\u2713')
        self.bucket2 = create_bucket(self.session)
        self.s3_files = [self.bucket + '/' + u'\u2713']
        self.s3_files2 = [self.bucket2 + '/' + u'\u2713']

    def tearDown(self):
        s3_cleanup(self.bucket, self.session)
        s3_cleanup(self.bucket2, self.session)

    def test_move_unicode(self):
        response = self.client.list_objects(Bucket=self.bucket)
        self.assertEqual(len(response.get('Contents', [])), 3)
        # Create file info objects to perform move.
        tasks = []
        for i in range(len(self.s3_files)):
            tasks.append(FileInfo(
                src=self.s3_files[i], src_type='s3',
                dest=self.s3_files2[i], dest_type='s3',
                operation_name='move', size=0,
                client=self.client, source_client=self.source_client
            ))
        # Perform the move.
        self.s3_handler.call(tasks)
        response = self.client.list_objects(Bucket=self.bucket2)
        self.assertEqual(len(response.get('Contents', [])), 1)


class S3HandlerTestMove(unittest.TestCase):
    """
    This class tests the ability to move s3 objects.  The move
    operation uses a copy then delete.  Thus, tests the ability
    to copy objects as well as delete
    """
    def setUp(self):
        self.session = botocore.session.get_session(EnvironmentVariables)
        self.client = self.session.create_client('s3', 'us-west-2')
        self.source_client = self.session.create_client('s3', 'us-west-2')
        params = {'region': 'us-west-2', 'acl': 'private'}
        self.s3_handler = S3Handler(self.session, params)
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
        response = self.client.list_objects(Bucket=self.bucket)
        self.assertEqual(len(response['Contents']), 3)
        # Create file info objects to perform move.
        tasks = []
        for i in range(len(self.s3_files)):
            tasks.append(FileInfo(
                src=self.s3_files[i], src_type='s3',
                dest=self.s3_files2[i], dest_type='s3',
                operation_name='move', size=0,
                client=self.client,
                source_client=self.client
            ))
        # Perform the move.
        self.s3_handler.call(tasks)
        # Confirm the files were moved.  The origial bucket had three
        # objects. Only two were moved.
        response = self.client.list_objects(Bucket=self.bucket)
        self.assertEqual(len(response['Contents']), 1)
        response = self.client.list_objects(Bucket=self.bucket2)
        self.assertEqual(len(response['Contents']), 2)


class S3HandlerTestDownload(unittest.TestCase):
    """
    This class tests the ability to download s3 objects locally as well
    as using multipart downloads
    """
    def setUp(self):
        self.session = botocore.session.get_session(EnvironmentVariables)
        self.client = self.session.create_client('s3', 'us-west-2')
        params = {'region': 'us-west-2'}
        self.s3_handler = S3Handler(self.session, params)
        self.s3_handler_multi = S3Handler(
            self.session, params,
            runtime_config=runtime_config(multipart_threshold=10,
                                          multipart_chunksize=2))
        self.bucket = make_s3_files(self.session)
        self.s3_files = [self.bucket + '/text1.txt',
                         self.bucket + '/another_directory/text2.txt']
        self.file_creator = FileCreator()
        directory1 = self.file_creator.rootdir + os.sep + 'some_directory' + \
            os.sep
        filename1 = directory1 + "text1.txt"
        directory2 = directory1 + 'another_directory' + os.sep
        filename2 = directory2 + "text2.txt"
        self.loc_files = [filename1, filename2]

    def tearDown(self):
        clean_loc_files(self.file_creator)
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
                size=0, client=self.client
            ))
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
                size=15, client=self.client,
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


class S3HandlerTestBucket(unittest.TestCase):
    """
    Test the ability to make a bucket then remove it.
    """
    def setUp(self):
        self.session = botocore.session.get_session(EnvironmentVariables)
        self.client = self.session.create_client('s3', 'us-west-2')
        self.source_client = self.session.create_client('s3', 'us-west-2')
        self.params = {'region': 'us-west-2'}
        self.s3_handler = S3Handler(self.session, self.params)
        self.bucket = None

    def tearDown(self):
        s3_cleanup(self.bucket, self.session)

    def test_bucket(self):
        rand1 = random.randrange(5000)
        rand2 = random.randrange(5000)
        self.bucket = str(rand1) + 'mybucket' + str(rand2)

        file_info = FileInfo(
            src=self.bucket, operation_name='make_bucket', size=0,
            client=self.client, source_client=self.source_client
        )
        S3Handler(self.session, self.params).call([file_info])
        buckets_list = []
        for bucket in self.client.list_buckets().get('Buckets', []):
            buckets_list.append(bucket['Name'])
        self.assertIn(self.bucket, buckets_list)

        file_info = FileInfo(
            src=self.bucket, operation_name='remove_bucket', size=0,
            client=self.client, source_client=self.source_client)
        S3Handler(self.session, self.params).call([file_info])
        buckets_list = []
        for bucket in self.client.list_buckets().get('Buckets', []):
            buckets_list.append(bucket['Name'])
        self.assertNotIn(self.bucket, buckets_list)


if __name__ == "__main__":
    unittest.main()
