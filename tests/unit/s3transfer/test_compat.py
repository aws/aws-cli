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
import tempfile
import shutil
import signal

from botocore.compat import six

from tests import unittest
from tests import skip_if_windows
from s3transfer.compat import seekable, readable
from s3transfer.compat import BaseManager


class ErrorRaisingSeekWrapper(object):
    """An object wrapper that throws an error when seeked on

    :param fileobj: The fileobj that it wraps
    :param execption: The exception to raise when seeked on.
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
        # Fails becase there is no seekable(), seek(), nor tell()
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
        self.assertTrue(readable(six.BytesIO()))

    def test_non_file_like_obj(self):
        self.assertFalse(readable(object()))


class TestBaseManager(unittest.TestCase):
    def create_pid_manager(self):
        class PIDManager(BaseManager):
            pass

        PIDManager.register('getpid', os.getpid)
        return PIDManager()

    def get_pid(self, pid_manager):
        pid = pid_manager.getpid()
        # A proxy object is returned back. The needed value can be acquired
        # from the repr and converting that to an integer
        return int(str(pid))

    @skip_if_windows('os.kill() with SIGINT not supported on Windows')
    def test_can_provide_signal_handler_initializers_to_start(self):
        manager = self.create_pid_manager()
        manager.start(signal.signal, (signal.SIGINT, signal.SIG_IGN))
        pid = self.get_pid(manager)
        try:
            os.kill(pid, signal.SIGINT)
        except KeyboardInterrupt:
            pass
        # Try using the manager after the os.kill on the parent process. The
        # manager should not have died and should still be usable.
        self.assertEqual(pid, self.get_pid(manager))
