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
from datetime import datetime
import mimetypes
import hashlib
import math
import os
import sys
from functools import partial

from six import PY3
from six.moves import queue as Queue
from dateutil.tz import tzlocal

from awscli.customizations.s3.constants import QUEUE_TIMEOUT_WAIT, \
    MAX_PARTS, MAX_SINGLE_UPLOAD_SIZE


class MD5Error(Exception):
    """
    Exception for md5's that do not match.
    """
    pass


class NoBlockQueue(Queue.Queue):
    """
    This queue ensures that joining does not block interrupt signals.
    It also contains a threading event ``interrupt`` that breaks the
    while loop if signaled.  The ``interrupt`` signal is optional.
    If left out, this should act like a normal queue.
    """
    def __init__(self, interrupt=None, maxsize=0):
        Queue.Queue.__init__(self, maxsize=maxsize)
        self.interrupt = interrupt

    def join(self):
        self.all_tasks_done.acquire()
        try:
            while self.unfinished_tasks:
                if self.interrupt and self.interrupt.isSet():
                    break
                self.all_tasks_done.wait(QUEUE_TIMEOUT_WAIT)
        finally:
            self.all_tasks_done.release()


def find_bucket_key(s3_path):
    """
    This is a helper function that given an s3 path such that the path is of
    the form: bucket/key
    It will return the bucket and the key represented by the s3 path
    """
    s3_components = s3_path.split('/')
    bucket = s3_components[0]
    s3_key = ""
    if len(s3_components) > 1:
        s3_key = '/'.join(s3_components[1:])
    return bucket, s3_key


def get_file_stat(path):
    """
    This is a helper function that given a local path return the size of
    the file in bytes and time of last modification.
    """
    stats = os.stat(path)
    update_time = datetime.fromtimestamp(stats.st_mtime, tzlocal())
    return stats.st_size, update_time


def check_etag(etag, fileobj):
    """
    This fucntion checks the etag and the md5 checksum to ensure no
    data was corrupted upon transfer.
    """
    get_chunk = partial(fileobj.read, 1024 * 1024)
    m = hashlib.md5()
    for chunk in iter(get_chunk, b''):
        m.update(chunk)
    if '-' not in etag:
        if etag != m.hexdigest():
            raise MD5Error


def check_error(response_data):
    """
    A helper function that prints out the error message recieved in the
    response_data and raises an error when there is an error.
    """
    if response_data:
        if 'Errors' in response_data:
            errors = response_data['Errors']
            for error in errors:
                raise Exception("Error: %s\n" % error['Message'])


def operate(service, cmd, kwargs):
    """
    A helper function that universally calls any command by taking in the
    service, name of the command, and any additional parameters required in
    the call.
    """
    operation = service.get_operation(cmd)
    http_response, response_data = operation.call(**kwargs)
    check_error(response_data)
    return response_data, http_response


def find_chunksize(size, current_chunksize):
    """
    The purpose of this function is determine a chunksize so that
    the number of parts in a multipart upload is not greater than
    the ``MAX_PARTS``.  If the ``chunksize`` is greater than
    ``MAX_SINGLE_UPLOAD_SIZE`` it returns ``MAX_SINGLE_UPLOAD_SIZE``.
    """
    chunksize = current_chunksize
    num_parts = int(math.ceil(size / float(chunksize)))
    while num_parts > MAX_PARTS:
        chunksize *= 2
        num_parts = int(math.ceil(size / float(chunksize)))
    if chunksize > MAX_SINGLE_UPLOAD_SIZE:
        return MAX_SINGLE_UPLOAD_SIZE
    else:
        return chunksize


class MultiCounter(object):
    """
    This class is used as a way to keep track of how many multipart
    operations are in progress.  It also is used to track how many
    part operations are occuring.
    """
    def __init__(self):
        self.count = 0


def uni_print(statement):
    """
    This function is used to properly write unicode to stdout.  It
    ensures that the proper encoding is used if the statement is
    not in a version type of string.  The initial check is to
    allow if ``sys.stdout`` does not use an encoding
    """
    encoding = getattr(sys.stdout, 'encoding', None)
    if encoding is not None and not PY3:
        sys.stdout.write(statement.encode(sys.stdout.encoding))
    else:
        try:
            sys.stdout.write(statement)
        except UnicodeEncodeError:
            # Some file like objects like cStringIO will
            # try to decode as ascii.  Interestingly enough
            # this works with a normal StringIO.
            sys.stdout.write(statement.encode('utf-8'))


def guess_content_type(filename):
    """Given a filename, guess it's content type.

    If the type cannot be guessed, a value of None is returned.
    """
    return mimetypes.guess_type(filename)[0]


def relative_path(filename, start=os.path.curdir):
    """Cross platform relative path of a filename.

    If no relative path can be calculated (i.e different
    drives on Windows), then instead of raising a ValueError,
    the absolute path is returned.

    """
    try:
        dirname, basename = os.path.split(filename)
        relative_dir = os.path.relpath(dirname, start)
        return os.path.join(relative_dir, basename)
    except ValueError:
        return os.path.abspath(filename)


class ReadFileChunk(object):
    def __init__(self, filename, start_byte, size):
        self._filename = filename
        self._start_byte = start_byte
        self._fileobj = open(self._filename, 'rb')
        self._size = self._calculate_file_size(self._fileobj, requested_size=size,
                                               start_byte=start_byte)
        self._fileobj.seek(self._start_byte)
        self._amount_read = 0

    def _calculate_file_size(self, fileobj, requested_size, start_byte):
        actual_file_size = os.fstat(fileobj.fileno()).st_size
        max_chunk_size = actual_file_size - start_byte
        return min(max_chunk_size, requested_size)

    def read(self, amount=None):
        if amount is None:
            remaining = self._size - self._amount_read
            data = self._fileobj.read(remaining)
            self._amount_read += remaining
            return data
        else:
            actual_amount = min(self._size - self._amount_read, amount)
            data = self._fileobj.read(actual_amount)
            self._amount_read += actual_amount
            return data

    def seek(self, where):
        self._fileobj.seek(self._start_byte + where)
        self._amount_read = where

    def close(self):
        self._fileobj.close()

    def __len__(self):
        # __len__ is defined because requests will try to determine the length
        # of the stream to set a content length.  In the normal case
        # of the file it will just stat the file, but we need to change that
        # behavior.  By providing a __len__, requests will use that instead
        # of stat'ing the file.
        return self._size

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self._fileobj.close()

    def __iter__(self):
        # This is a workaround for http://bugs.python.org/issue17575
        # Basically httplib will try to iterate over the contents, even
        # if its a file like object.  This wasn't noticed because we've
        # already exhausted the stream so iterating over the file immediately
        # steps, which is what we're simulating here.
        return iter([])
