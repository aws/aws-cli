# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import os
import shutil
import tempfile
from io import BytesIO

from s3transfer.compat import readable, seekable
from tests import unittest


class ErrorRaisingSeekWrapper:
    """An object wrapper that throws an error when seeked on

    :param fileobj: The fileobj that it wraps
    :param exception: The exception to raise when seeked on.
    """

    def __init__(self, fileobj, exception):
        self._fileobj = fileobj
        self._exception = exception

    def seek(self, offset, whence=0):
        raise self._exception

    def tell(self):
        return self._fileobj.tell()


class TestSeekable(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.filename = os.path.join(self.tempdir, 'foo')

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_seekable_fileobj(self):
        with open(self.filename, 'w') as f:
            self.assertTrue(seekable(f))

    def test_non_file_like_obj(self):
        # Fails because there is no seekable(), seek(), nor tell()
        self.assertFalse(seekable(object()))

    def test_non_seekable_ioerror(self):
        # Should return False if IOError is thrown.
        with open(self.filename, 'w') as f:
            self.assertFalse(seekable(ErrorRaisingSeekWrapper(f, IOError())))

    def test_non_seekable_oserror(self):
        # Should return False if OSError is thrown.
        with open(self.filename, 'w') as f:
            self.assertFalse(seekable(ErrorRaisingSeekWrapper(f, OSError())))


class TestReadable(unittest.TestCase):
    def test_readable_fileobj(self):
        with tempfile.TemporaryFile() as f:
            self.assertTrue(readable(f))

    def test_readable_file_like_obj(self):
        self.assertTrue(readable(BytesIO()))

    def test_non_file_like_obj(self):
        self.assertFalse(readable(object()))
