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
import os
import random
from awscli.testutils import unittest
import string

from awscli.compat import six
from mock import patch, Mock


class S3HandlerBaseTest(unittest.TestCase):
    pass


def make_loc_files():
    """
    This sets up the test by making a directory named some_directory.  It
    has the file text1.txt and the directory another_directory inside.  Inside
    of another_directory it creates the file text2.txt.
    """
    directory1 = six.text_type(
        os.path.abspath('.') + os.sep + 'some_directory' + os.sep)
    if not os.path.exists(directory1):
        os.mkdir(directory1)

    string1 = b"This is a test."
    filename1 = directory1 + u"text1.txt"
    with open(filename1, 'wb') as file1:
        file1.write(string1)

    directory2 = directory1 + u'another_directory' + os.sep
    if not os.path.exists(directory2):
        os.mkdir(directory2)

    string2 = b"This is another test."
    filename2 = directory2 + u"text2.txt"
    with open(filename2, 'wb') as file2:
        file2.write(string2)

    return [filename1, filename2, directory2,  directory1]


def clean_loc_files(files):
    """
    Removes all of the local files made.
    """
    for filename in files:
        if os.path.exists(filename):
            if os.path.isfile(filename):
                os.remove(filename)
            else:
                os.rmdir(filename)


def make_s3_files(session, key1='text1.txt', key2='text2.txt'):
    """
    Creates a randomly generated bucket in s3 with the files text1.txt and
    another_directory/text2.txt inside.  The directory is manually created
    as it tests the ability to handle directories when generating s3 files.
    """
    service = session.get_service('s3')
    region = 'us-east-1'
    endpoint = service.get_endpoint(region)
    bucket = create_bucket(session)

    operation = service.get_operation('PutObject')
    string1 = "This is a test."
    string2 = "This is another test."
    http_response, response_data = operation.call(endpoint,
                                                  bucket=bucket,
                                                  key=key1,
                                                  body=string1)
    if key2 is not None:
        http_response, response_data = operation.call(endpoint,
                                                    bucket=bucket,
                                                    key='another_directory/')
        http_response, r_data = operation.call(endpoint,
                                            bucket=bucket,
                                            key='another_directory/%s' % key2,
                                            body=string2)
    return bucket


def create_bucket(session, name=None, region=None):
    """
    Creates a bucket
    :returns: the name of the bucket created
    """
    service = session.get_service('s3')
    if not region:
        region = 'us-west-2'
    endpoint = service.get_endpoint(region)
    if name:
        bucket_name = name
    else:
        rand1 = ''.join(random.sample(string.ascii_lowercase + string.digits,
                                      10))
        bucket_name = 'awscli-s3test-' + str(rand1)
    params = {'endpoint': endpoint, 'bucket': bucket_name}
    if region != 'us-east-1':
        params['create_bucket_configuration'] = {'LocationConstraint': region}
    operation = service.get_operation('CreateBucket')
    http_response, response_data = operation.call(**params)
    return bucket_name


def s3_cleanup(bucket, session, key1='text1.txt', key2='text2.txt'):
    """
    Function to cleanup generated s3 bucket and files.
    """
    service = session.get_service('s3')
    region = 'us-east-1'
    endpoint = service.get_endpoint(region)
    operation = service.get_operation('DeleteObject')
    http_response, r_data = operation.call(endpoint,
                                           bucket=bucket,
                                           key=key1)
    if key2 is not None:
        http_response, r_data = operation.call(endpoint,
                                            bucket=bucket,
                                            key='another_directory/')
        http_response, r_data = operation.call(endpoint,
                                            bucket=bucket,
                                            key='another_directory/%s' % key2)
    operation = service.get_operation('DeleteBucket')
    http_response, r_data = operation.call(endpoint, bucket=bucket)


def compare_files(self, result_file, ref_file):
    """
    Ensures that the FileStat's properties are what they
    are suppose to be.
    """
    self.assertEqual(result_file.src, ref_file.src)
    self.assertEqual(result_file.dest, ref_file.dest)
    self.assertEqual(result_file.compare_key, ref_file.compare_key)
    self.assertEqual(result_file.size, ref_file.size)
    self.assertEqual(result_file.last_update, ref_file.last_update)
    self.assertEqual(result_file.src_type, ref_file.src_type)
    self.assertEqual(result_file.dest_type, ref_file.dest_type)
    self.assertEqual(result_file.operation_name, ref_file.operation_name)


def list_contents(bucket, session):
    """
    This is a helper function used to return the contents of a list
    object operation.
    """
    service = session.get_service('s3')
    region = 'us-east-1'
    endpoint = service.get_endpoint(region)
    operation = service.get_operation('ListObjects')
    http_response, r_data = operation.call(endpoint, bucket=bucket)
    return r_data.get('Contents', [])


def list_buckets(session):
    """
    This is a helper function used to return the contents of a list
    buckets operation.
    """
    service = session.get_service('s3')
    region = 'us-east-1'
    endpoint = service.get_endpoint(region)
    operation = service.get_operation('ListBuckets')
    html_response, response_data = operation.call(endpoint)
    contents = response_data['Buckets']
    return contents


class MockStdIn(object):
    """
    This class patches stdin in order to write a stream of bytes into
    stdin.
    """
    def __init__(self, input_bytes=b''):
        input_data = six.BytesIO(input_bytes)
        if six.PY3:
            mock_object = Mock()
            mock_object.buffer = input_data
        else:
            mock_object = input_data
        self._patch = patch('sys.stdin', mock_object)

    def __enter__(self):
        self._patch.__enter__()

    def __exit__(self, exc_type, exc_value, traceback):
        self._patch.__exit__()
