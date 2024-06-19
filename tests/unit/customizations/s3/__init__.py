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


class FakeTransferFuture(object):
    def __init__(self, result=None, exception=None, meta=None):
        self._result = result
        self._exception = exception
        self.meta = meta

    def result(self):
        if self._exception:
            raise self._exception
        return self._result


class FakeTransferFutureMeta(object):
    def __init__(self, size=None, call_args=None, transfer_id=None):
        self.size = size
        self.call_args = call_args
        self.transfer_id = transfer_id


class FakeTransferFutureCallArgs(object):
    def __init__(self, **kwargs):
        for kwarg, val in kwargs.items():
            setattr(self, kwarg, val)


def make_loc_files(file_creator, size=None):
    """
    This sets up the test by making a directory named some_directory.  It
    has the file text1.txt and the directory another_directory inside.  Inside
    of another_directory it creates the file text2.txt.
    """
    if size:
        body = "*" * size
    else:
        body = 'This is a test.'

    filename1 = file_creator.create_file(
        os.path.join('some_directory', 'text1.txt'), body)

    filename2 = file_creator.create_file(
        os.path.join('some_directory', 'another_directory', 'text2.txt'), body)
    filename1 = str(filename1)
    filename2 = str(filename2)
    return [filename1, filename2, os.path.dirname(filename2),
            os.path.dirname(filename1)]


def clean_loc_files(file_creator):
    """
    Removes all of the local files made.
    """
    file_creator.remove_all()


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
