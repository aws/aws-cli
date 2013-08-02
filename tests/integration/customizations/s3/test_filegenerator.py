import unittest
import os
import random

import botocore.session
from awscli import EnvironmentVariables
from awscli.customizations.s3.filegenerator import FileInfo, \
    FileGenerator, get_file_stat

"""
Note that all of these functions can be found in the unit tests.
The only difference is that these tests use botocore's actual session
variables to communicate with s3 as these are integration tests.  Therefore,
only tests that use sessions are included as integration tests.
"""


def make_loc_files():
    """
    This sets up the test by making a directory named some_directory.  It
    has the file text1.txt and the directory another_directory inside.  Inside
    of another_directory it creates the file text2.txt
    """
    directory1 = os.path.abspath('.') + os.sep + 'some_directory' + os.sep
    if not os.path.exists(directory1):
        os.mkdir(directory1)

    string1 = b"This is a test."
    filename1 = directory1 + "text1.txt"
    with open(filename1, 'wb') as file1:
        file1.write(string1)

    directory2 = directory1 + 'another_directory' + os.sep
    if not os.path.exists(directory2):
        os.mkdir(directory2)

    string2 = b"This is another test."
    filename2 = directory2 + "text2.txt"
    with open(filename2, 'wb') as file2:
        file2.write(string2)

    return [filename1, filename2, directory2,  directory1]


def clean_loc_files(files):
    """
    Removes all of the local files made
    """
    for filename in files:
        if os.path.exists(filename):
            if os.path.isfile(filename):
                os.remove(filename)
            else:
                os.rmdir(filename)


def make_s3_files():
    """
    Creates a randomly generated bucket in s3 with the files text1.txt and
    another_directory/text2.txt inside.  The directory is manually created
    as it tests the ability to handle directories when generating s3 files.
    """
    session = botocore.session.get_session(EnvironmentVariables)
    service = session.get_service('s3')
    region = session.get_config()['region']
    endpoint = service.get_endpoint(region)
    bucket = create_bucket()

    operation = service.get_operation('PutObject')
    string1 = "This is a test."
    string2 = "This is another test."
    http_response, response_data = operation.call(endpoint,
                                                  bucket=bucket,
                                                  key='text1.txt',
                                                  body=string1)
    http_response, response_data = operation.call(endpoint,
                                                  bucket=bucket,
                                                  key='another_directory/')
    http_response, r_data = operation.call(endpoint,
                                           bucket=bucket,
                                           key='another_directory/text2.txt',
                                           body=string2)
    return bucket


def create_bucket():
    """
    Creates a bucket
    :retruns: the name of the bucket created
    """
    session = botocore.session.get_session(EnvironmentVariables)
    service = session.get_service('s3')
    region = session.get_config()['region']
    endpoint = service.get_endpoint(region)
    rand1 = random.randrange(5000)
    rand2 = random.randrange(5000)
    bucket_name = str(rand1) + 'mybucket' + str(rand2)
    params = {'endpoint': endpoint, 'bucket': bucket_name}
    if region != 'us-east-1':
        bucket_config = {'location_constraint': region}
        params['create_bucket_configuration'] = bucket_config
    operation = service.get_operation('CreateBucket')
    http_response, response_data = operation.call(**params)
    return bucket_name


def s3_cleanup(bucket):
    """
    Function to cleanup generated s3 bucket and filles
    """
    session = botocore.session.get_session(EnvironmentVariables)
    service = session.get_service('s3')
    region = session.get_config()['region']
    endpoint = service.get_endpoint(region)
    operation = service.get_operation('DeleteObject')
    http_response, r_data = operation.call(endpoint,
                                           bucket=bucket,
                                           key='text1.txt')
    http_response, r_data = operation.call(endpoint,
                                           bucket=bucket,
                                           key='another_directory/')
    http_response, r_data = operation.call(endpoint,
                                           bucket=bucket,
                                           key='another_directory/text2.txt')
    operation = service.get_operation('DeleteBucket')
    http_response, r_data = operation.call(endpoint, bucket=bucket)


def compare_files(self, result_file, ref_file):
    """
    Ensures that the FileInfo's properties are what they
    are suppose to be
    """
    self.assertEqual(result_file.src, ref_file.src)
    self.assertEqual(result_file.dest, ref_file.dest)
    self.assertEqual(result_file.compare_key, ref_file.compare_key)
    self.assertEqual(result_file.size, ref_file.size)
    self.assertEqual(result_file.last_update, ref_file.last_update)
    self.assertEqual(result_file.src_type, ref_file.src_type)
    self.assertEqual(result_file.dest_type, ref_file.dest_type)
    self.assertEqual(result_file.operation, ref_file.operation)


class S3FileGeneratorTest(unittest.TestCase):
    def setUp(self):
        self.bucket = make_s3_files()
        self.file1 = self.bucket+'/'+'text1.txt'
        self.file2 = self.bucket+'/'+'another_directory/text2.txt'
        self.session = botocore.session.get_session(EnvironmentVariables)

    def tearDown(self):
        s3_cleanup(self.bucket)

    def test_nonexist_s3_file(self):
        """
        This tests to make sure that files are not misproperly yielded by
        ensuring the file prefix is the exact same as what was inputted.
        """
        input_s3_file = {'src': {'path': self.file1[:-1], 'type': 's3'},
                         'dest': {'path': 'text1.txt', 'type': 'local'},
                         'dir_op': False, 'use_src_name': False}
        files = FileGenerator(self.session).call(input_s3_file)
        result_list = []
        for filename in files:
            result_list.append(filename)
        self.assertEqual(len(result_list), 0)

    def test_s3_file(self):
        """
        Generate a single s3 file
        Note: Size and last update are not tested because s3 generates them.
        """
        input_s3_file = {'src': {'path': self.file1, 'type': 's3'},
                         'dest': {'path': 'text1.txt', 'type': 'local'},
                         'dir_op': False, 'use_src_name': False}
        files = FileGenerator(self.session).call(input_s3_file)
        result_list = []
        for filename in files:
            result_list.append(filename)
        file_info = FileInfo(src=self.file1, dest='text1.txt',
                             compare_key='text1.txt',
                             size=result_list[0].size,
                             last_update=result_list[0].last_update,
                             src_type='s3',
                             dest_type='local', operation='')

        ref_list = [file_info]
        self.assertEqual(len(result_list), len(ref_list))
        for i in range(len(result_list)):
            compare_files(self, result_list[i], ref_list[i])

    def test_s3_directory(self):
        """
        Generates s3 files under a common prefix. Also it ensures that
        zero size files are ignored.
        Note: Size and last update are not tested because s3 generates them.
        """
        input_s3_file = {'src': {'path': self.bucket+'/', 'type': 's3'},
                         'dest': {'path': '', 'type': 'local'},
                         'dir_op': True, 'use_src_name': True}
        files = FileGenerator(self.session).call(input_s3_file)
        result_list = []
        for filename in files:
            result_list.append(filename)
        file_info = FileInfo(src=self.file2,
                             dest='another_directory' + os.sep + 'text2.txt',
                             compare_key='another_directory/text2.txt',
                             size=result_list[0].size,
                             last_update=result_list[0].last_update,
                             src_type='s3',
                             dest_type='local', operation='')
        file_info2 = FileInfo(src=self.file1,
                              dest='text1.txt',
                              compare_key='text1.txt',
                              size=result_list[1].size,
                              last_update=result_list[1].last_update,
                              src_type='s3',
                              dest_type='local', operation='')

        ref_list = [file_info, file_info2]
        self.assertEqual(len(result_list), len(ref_list))
        for i in range(len(result_list)):
            compare_files(self, result_list[i], ref_list[i])

    def test_s3_delete_directory(self):
        """
        Generates s3 files under a common prefix. Also it ensures that
        the directory itself is included because it is a delete command
        Note: Size and last update are not tested because s3 generates them.
        """
        input_s3_file = {'src': {'path': self.bucket+'/', 'type': 's3'},
                         'dest': {'path': '', 'type': 'local'},
                         'dir_op': True, 'use_src_name': True}
        files = FileGenerator(self.session, 'delete').call(input_s3_file)
        result_list = []
        for filename in files:
            result_list.append(filename)

        file_info1 = FileInfo(src=self.bucket + '/another_directory/',
                              dest='another_directory\\',
                              compare_key='another_directory/',
                              size=result_list[0].size,
                              last_update=result_list[0].last_update,
                              src_type='s3',
                              dest_type='local', operation='delete')
        file_info2 = FileInfo(src=self.file2,
                              dest='another_directory' + os.sep + 'text2.txt',
                              compare_key='another_directory/text2.txt',
                              size=result_list[1].size,
                              last_update=result_list[1].last_update,
                              src_type='s3',
                              dest_type='local', operation='delete')
        file_info3 = FileInfo(src=self.file1,
                              dest='text1.txt',
                              compare_key='text1.txt',
                              size=result_list[2].size,
                              last_update=result_list[2].last_update,
                              src_type='s3',
                              dest_type='local', operation='delete')

        ref_list = [file_info1, file_info2, file_info3]
        self.assertEqual(len(result_list), len(ref_list))
        for i in range(len(result_list)):
            compare_files(self, result_list[i], ref_list[i])

if __name__ == "__main__":
    unittest.main()
