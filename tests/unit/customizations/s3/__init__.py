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

import mock
from mock import patch, Mock

from awscli.compat import six
from awscli.testutils import unittest, BaseAWSCommandParamsTest


class S3HandlerBaseTest(BaseAWSCommandParamsTest):
    def setUp(self):
        super(S3HandlerBaseTest, self).setUp()
        self.session = self.driver.session
        self.driver.session.register('before-call', self.before_call)
        self.driver.session.register('before-parameter-build',
                                     self.before_parameter_build)
        self.client = self.session.create_client('s3', 'us-east-1')
        self.source_client = self.session.create_client('s3', 'us-east-1')

    def run_s3_handler(self, s3_handler, tasks):
        self.patch_make_request()
        captured_stderr = six.StringIO()
        captured_stdout = six.StringIO()
        with mock.patch('sys.stderr', captured_stderr):
            with mock.patch('sys.stdout', captured_stdout):
                try:
                    rc = s3_handler.call(tasks)
                except SystemExit as e:
                    # We need to catch SystemExit so that we
                    # can get a proper rc and still present the
                    # stdout/stderr to the test runner so we can
                    # figure out what went wrong.
                    rc = e.code
        stderr = captured_stderr.getvalue()
        stdout = captured_stdout.getvalue()
        return stdout, stderr, rc

    def assert_operations_for_s3_handler(self, s3_handler, tasks,
                                         ref_operations):
        """Assert API operations based on tasks given to s3 handler

        :param s3_handler: A S3Handler object
        :param tasks: An iterable of tasks
        :param ref_operations: A list of tuples where the first element is
            the name of the API operation and the second element is the
            parameters passed to it (as it would be passed to botocore).
        """
        stdout, stderr, rc = self.run_s3_handler(s3_handler, tasks)
        self.assertEqual(rc.num_tasks_failed, 0)
        self.assertEqual(len(self.operations_called), len(ref_operations))
        for i, ref_operation in enumerate(ref_operations):
            self.assertEqual(self.operations_called[i][0].name,
                             ref_operation[0])
            self.assertEqual(self.operations_called[i][1], ref_operation[1])


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

    body = b"This is a test."
    filename1 = directory1 + u"text1.txt"
    with open(filename1, 'wb') as file1:
        file1.write(body)

    directory2 = directory1 + u'another_directory' + os.sep
    if not os.path.exists(directory2):
        os.mkdir(directory2)

    filename2 = directory2 + u"text2.txt"
    with open(filename2, 'wb') as file2:
        file2.write(body)

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
