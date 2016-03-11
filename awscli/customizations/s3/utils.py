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
import argparse
import logging
from datetime import datetime
import mimetypes
import hashlib
import math
import errno
import os
import sys
from collections import namedtuple, deque
from functools import partial

from dateutil.parser import parse
from dateutil.tz import tzlocal, tzutc
from botocore.compat import unquote_str

from awscli.compat import six
from awscli.compat import PY3
from awscli.compat import queue

LOGGER = logging.getLogger(__name__)
HUMANIZE_SUFFIXES = ('KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB')
MAX_PARTS = 10000
EPOCH_TIME = datetime(1970, 1, 1, tzinfo=tzutc())
# The maximum file size you can upload via S3 per request.
# See: http://docs.aws.amazon.com/AmazonS3/latest/dev/UploadingObjects.html
# and: http://docs.aws.amazon.com/AmazonS3/latest/dev/qfacts.html
MAX_SINGLE_UPLOAD_SIZE = 5 * (1024 ** 3)
MIN_UPLOAD_CHUNKSIZE = 5 * (1024 ** 2)
# Maximum object size allowed in S3.
# See: http://docs.aws.amazon.com/AmazonS3/latest/dev/qfacts.html
MAX_UPLOAD_SIZE = 5 * (1024 ** 4)
SIZE_SUFFIX = {
    'kb': 1024,
    'mb': 1024 ** 2,
    'gb': 1024 ** 3,
    'tb': 1024 ** 4,
    'kib': 1024,
    'mib': 1024 ** 2,
    'gib': 1024 ** 3,
    'tib': 1024 ** 4,
}



def human_readable_size(value):
    """Convert an size in bytes into a human readable format.

    For example::

        >>> human_readable_size(1)
        '1 Byte'
        >>> human_readable_size(10)
        '10 Bytes'
        >>> human_readable_size(1024)
        '1.0 KiB'
        >>> human_readable_size(1024 * 1024)
        '1.0 MiB'

    :param value: The size in bytes
    :return: The size in a human readable format based on base-2 units.

    """
    one_decimal_point = '%.1f'
    base = 1024
    bytes_int = float(value)

    if bytes_int == 1:
        return '1 Byte'
    elif bytes_int < base:
        return '%d Bytes' % bytes_int

    for i, suffix in enumerate(HUMANIZE_SUFFIXES):
        unit = base ** (i+2)
        if round((bytes_int / unit) * base) < base:
            return '%.1f %s' % ((base * bytes_int / unit), suffix)


def human_readable_to_bytes(value):
    """Converts a human readable size to bytes.

    :param value: A string such as "10MB".  If a suffix is not included,
        then the value is assumed to be an integer representing the size
        in bytes.
    :returns: The converted value in bytes as an integer

    """
    value = value.lower()
    if value[-2:] == 'ib':
        # Assume IEC suffix.
        suffix = value[-3:].lower()
    else:
        suffix = value[-2:].lower()
    has_size_identifier = (
        len(value) >= 2 and suffix in SIZE_SUFFIX)
    if not has_size_identifier:
        try:
            return int(value)
        except ValueError:
            raise ValueError("Invalid size value: %s" % value)
    else:
        multiplier = SIZE_SUFFIX[suffix]
        return int(value[:-len(suffix)]) * multiplier


class AppendFilter(argparse.Action):
    """
    This class is used as an action when parsing the parameters.
    Specifically it is used for actions corresponding to exclude
    and include filters.  What it does is that it appends a list
    consisting of the name of the parameter and its value onto
    a list containing these [parameter, value] lists.  In this
    case, the name of the parameter will either be --include or
    --exclude and the value will be the rule to apply.  This will
    format all of the rules inputted into the command line
    in a way compatible with the Filter class.  Note that rules that
    appear later in the command line take preferance over rulers that
    appear earlier.
    """
    def __call__(self, parser, namespace, values, option_string=None):
        filter_list = getattr(namespace, self.dest)
        if filter_list:
            filter_list.append([option_string, values[0]])
        else:
            filter_list = [[option_string, values[0]]]
        setattr(namespace, self.dest, filter_list)


class MD5Error(Exception):
    """
    Exception for md5's that do not match.
    """
    pass


class StablePriorityQueue(queue.Queue):
    """Priority queue that maintains FIFO order for same priority items.

    This class was written to handle the tasks created in
    awscli.customizations.s3.tasks, but it's possible to use this
    class outside of that context.  In order for this to be the case,
    the following conditions should be met:

        * Objects that are queued should have a PRIORITY attribute.
          This should be an integer value not to exceed the max_priority
          value passed into the ``__init__``.  Objects with lower
          priority numbers are retrieved before objects with higher
          priority numbers.
        * A relatively small max_priority should be chosen.  ``get()``
          calls are O(max_priority).

    Any object that does not have a ``PRIORITY`` attribute or whose
    priority exceeds ``max_priority`` will be queued at the highest
    (least important) priority available.

    """
    def __init__(self, maxsize=0, max_priority=20):
        queue.Queue.__init__(self, maxsize=maxsize)
        self.priorities = [deque([]) for i in range(max_priority + 1)]
        self.default_priority = max_priority

    def _qsize(self):
        size = 0
        for bucket in self.priorities:
            size += len(bucket)
        return size

    def _put(self, item):
        priority = min(getattr(item, 'PRIORITY', self.default_priority),
                        self.default_priority)
        self.priorities[priority].append(item)

    def _get(self):
        for bucket in self.priorities:
            if not bucket:
                continue
            return bucket.popleft()


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


def split_s3_bucket_key(s3_path):
    """Split s3 path into bucket and key prefix.

    This will also handle the s3:// prefix.

    :return: Tuple of ('bucketname', 'keyname')

    """
    if s3_path.startswith('s3://'):
        s3_path = s3_path[5:]
    return find_bucket_key(s3_path)


def get_file_stat(path):
    """
    This is a helper function that given a local path return the size of
    the file in bytes and time of last modification.
    """
    try:
        stats = os.stat(path)
    except IOError as e:
        raise ValueError('Could not retrieve file stat of "%s": %s' % (
            path, e))

    try:
        update_time = datetime.fromtimestamp(stats.st_mtime, tzlocal())
    except ValueError:
        # Python's fromtimestamp raises value errors when the timestamp is out
        # of range of the platform's C localtime() function. This can cause
        # issues when syncing from systems with a wide range of valid timestamps
        # to systems with a lower range. Some systems support 64-bit timestamps,
        # for instance, while others only support 32-bit. We don't want to fail
        # in these cases, so instead we pass along none.
        update_time = None

    return stats.st_size, update_time


def find_dest_path_comp_key(files, src_path=None):
    """
    This is a helper function that determines the destination path and compare
    key given parameters received from the ``FileFormat`` class.
    """
    src = files['src']
    dest = files['dest']
    src_type = src['type']
    dest_type = dest['type']
    if src_path is None:
        src_path = src['path']

    sep_table = {'s3': '/', 'local': os.sep}

    if files['dir_op']:
        rel_path = src_path[len(src['path']):]
    else:
        rel_path = src_path.split(sep_table[src_type])[-1]
    compare_key = rel_path.replace(sep_table[src_type], '/')
    if files['use_src_name']:
        dest_path = dest['path']
        dest_path += rel_path.replace(sep_table[src_type],
                                      sep_table[dest_type])
    else:
        dest_path = dest['path']
    return dest_path, compare_key


def create_warning(path, error_message, skip_file=True):
    """
    This creates a ``PrintTask`` for whenever a warning is to be thrown.
    """
    print_string = "warning: "
    if skip_file:
        print_string = print_string + "Skipping file " + path + ". "
    print_string = print_string + error_message
    warning_message = PrintTask(message=print_string, error=False,
                                warning=True)
    return warning_message


def find_chunksize(size, current_chunksize):
    """
    The purpose of this function is determine a chunksize so that the number of
    parts in a multipart upload is not greater than the ``MAX_PARTS``, and that
    the chunksize is not less than the minimum chunksize.

    :param size: The size of the file to upload
    :param current_chunksize: The currently configured chunksize
    :return: If the given chunksize is valid, it is returned. Otherwise a valid
        chunksize is calculated and returned.
    :raises: ValueError: if the file size exceeds the max size of 5TB
    """
    if size > MAX_UPLOAD_SIZE:
        raise ValueError("File size exceeds maximum upload size.")
    size = adjust_chunksize_for_max_parts(size, current_chunksize)
    return adjust_chunksize_to_upload_limits(size)


def adjust_chunksize_to_upload_limits(current_chunksize):
    """
    Given a chunksize, verifies that the chunksize is within max and min
    chunksize for uploads. If it is not, a valid chunksize will be returned.

    :param current_chunksize: The current configured chunksize.
    :return: If the given chunksize is valid, it is returned. Otherwise a valid
        chunksize, which is a close to the given as possible, is returned.
    """
    chunksize = current_chunksize
    chunksize_human = human_readable_size(chunksize)
    if chunksize > MAX_SINGLE_UPLOAD_SIZE:
        LOGGER.debug(
            "Chunksize greater than maximum chunksize. Setting to %s from %s."
            % (human_readable_size(MAX_SINGLE_UPLOAD_SIZE), chunksize_human))
        return MAX_SINGLE_UPLOAD_SIZE
    elif chunksize < MIN_UPLOAD_CHUNKSIZE:
        LOGGER.debug(
            "Chunksize less than minimum chunksize. Setting to %s from %s." %
            (human_readable_size(MIN_UPLOAD_CHUNKSIZE), chunksize_human))
        return MIN_UPLOAD_CHUNKSIZE
    else:
        return chunksize


def adjust_chunksize_for_max_parts(size, current_chunksize):
    """
    Given a chunksize and file size, verifies that the upload will not exceed
    the maximum parts for a multipart upload. If it will, a valid chunksize
    is calculated and returned.

    :param size: The size of the file to upload
    :param current_chunksize: The currently configured chunksize
    :return: If the given chunksize is valid, it is returned. Otherwise a valid
        chunksize is calculated and returned.
    """
    chunksize = current_chunksize
    num_parts = int(math.ceil(size / float(chunksize)))

    while num_parts > MAX_PARTS:
        chunksize *= 2
        num_parts = int(math.ceil(size / float(chunksize)))

    if chunksize != current_chunksize:
        chunksize_human = human_readable_size(chunksize)
        LOGGER.debug(
            "Chunksize would result in the number of parts exceeding the "
            "maximum. Setting to %s from %s." %
            (chunksize_human, human_readable_size(current_chunksize)))

    return chunksize


class MultiCounter(object):
    """
    This class is used as a way to keep track of how many multipart
    operations are in progress.  It also is used to track how many
    part operations are occuring.
    """
    def __init__(self):
        self.count = 0


def uni_print(statement, out_file=None):
    """
    This function is used to properly write unicode to a file, usually
    stdout or stdderr.  It ensures that the proper encoding is used if the
    statement is not a string type.
    """
    if out_file is None:
        out_file = sys.stdout
    try:
        # Otherwise we assume that out_file is a
        # text writer type that accepts str/unicode instead
        # of bytes.
        out_file.write(statement)
    except UnicodeEncodeError:
        # Some file like objects like cStringIO will
        # try to decode as ascii on python2.
        #
        # This can also fail if our encoding associated
        # with the text writer cannot encode the unicode
        # ``statement`` we've been given.  This commonly
        # happens on windows where we have some S3 key
        # previously encoded with utf-8 that can't be
        # encoded using whatever codepage the user has
        # configured in their console.
        #
        # At this point we've already failed to do what's
        # been requested.  We now try to make a best effort
        # attempt at printing the statement to the outfile.
        # We're using 'ascii' as the default because if the
        # stream doesn't give us any encoding information
        # we want to pick an encoding that has the highest
        # chance of printing successfully.
        new_encoding = getattr(out_file, 'encoding', 'ascii')
        # When the output of the aws command is being piped,
        # ``sys.stdout.encoding`` is ``None``.
        if new_encoding is None:
            new_encoding = 'ascii'
        new_statement = statement.encode(
            new_encoding, 'replace').decode(new_encoding)
        out_file.write(new_statement)
    out_file.flush()


def bytes_print(statement):
    """
    This function is used to properly write bytes to standard out.
    """
    if PY3:
        if getattr(sys.stdout, 'buffer', None):
            sys.stdout.buffer.write(statement)
        else:
            # If it is not possible to write to the standard out buffer.
            # The next best option is to decode and write to standard out.
            sys.stdout.write(statement.decode('utf-8'))
    else:
        sys.stdout.write(statement)


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


def set_file_utime(filename, desired_time):
    """
    Set the utime of a file, and if it fails, raise a more explicit error.

    :param filename: the file to modify
    :param desired_time: the epoch timestamp to set for atime and mtime.
    :raises: SetFileUtimeError: if you do not have permission (errno 1)
    :raises: OSError: for all errors other than errno 1
    """
    try:
        os.utime(filename, (desired_time, desired_time))
    except OSError as e:
        # Only raise a more explicit exception when it is a permission issue.
        if e.errno != errno.EPERM:
            raise e
        raise SetFileUtimeError(
            ("The file was downloaded, but attempting to modify the "
             "utime of the file failed. Is the file owned by another user?"))


class SetFileUtimeError(Exception):
    pass


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

    def tell(self):
        return self._amount_read

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


def _date_parser(date_string):
    return parse(date_string).astimezone(tzlocal())


class BucketLister(object):
    """List keys in a bucket."""
    def __init__(self, client, date_parser=_date_parser):
        self._client = client
        self._date_parser = date_parser

    def list_objects(self, bucket, prefix=None, page_size=None):
        kwargs = {'Bucket': bucket, 'PaginationConfig': {'PageSize': page_size}}
        if prefix is not None:
            kwargs['Prefix'] = prefix

        paginator = self._client.get_paginator('list_objects')
        pages = paginator.paginate(**kwargs)
        for page in pages:
            contents = page.get('Contents', [])
            for content in contents:
                source_path = bucket + '/' + content['Key']
                content['LastModified'] = self._date_parser(
                    content['LastModified'])
                yield source_path, content


class PrintTask(namedtuple('PrintTask',
                          ['message', 'error', 'total_parts', 'warning'])):
    def __new__(cls, message, error=False, total_parts=None, warning=None):
        """
        :param message: An arbitrary string associated with the entry.   This
            can be used to communicate the result of the task.
        :param error: Boolean indicating a failure.
        :param total_parts: The total number of parts for multipart transfers.
        :param warning: Boolean indicating a warning
        """
        return super(PrintTask, cls).__new__(cls, message, error, total_parts,
                                             warning)


IORequest = namedtuple('IORequest',
                       ['filename', 'offset', 'data', 'is_stream'])
# Used to signal that IO for the filename is finished, and that
# any associated resources may be cleaned up.
_IOCloseRequest = namedtuple('IOCloseRequest', ['filename', 'desired_mtime'])
class IOCloseRequest(_IOCloseRequest):
    def __new__(cls, filename, desired_mtime=None):
        return super(IOCloseRequest, cls).__new__(cls, filename, desired_mtime)


class RequestParamsMapper(object):
    """A utility class that maps CLI params to request params

    Each method in the class maps to a particular operation and will set
    the request parameters depending on the operation and CLI parameters
    provided. For each of the class's methods the parameters are as follows:

    :type request_params: dict
    :param request_params: A dictionary to be filled out with the appropriate
        parameters for the specified client operation using the current CLI
        parameters

    :type cli_params: dict
    :param cli_params: A dictionary of the current CLI params that will be
        used to generate the request parameters for the specified operation

    For example, take the mapping of request parameters for PutObject::

        >>> cli_request_params = {'sse': 'AES256', 'storage_class': 'GLACIER'}
        >>> request_params = {}
        >>> RequestParamsMapper.map_put_object_params(
                request_params, cli_request_params)
        >>> print(request_params)
        {'StorageClass': 'GLACIER', 'ServerSideEncryption': 'AES256'}

    Note that existing parameters in ``request_params`` will be overriden if
    a parameter in ``cli_params`` maps to the existing parameter.
    """
    @classmethod
    def map_put_object_params(cls, request_params, cli_params):
        """Map CLI params to PutObject request params"""
        cls._set_general_object_params(request_params, cli_params)
        cls._set_metadata_params(request_params, cli_params)
        cls._set_sse_request_params(request_params, cli_params)
        cls._set_sse_c_request_params(request_params, cli_params)

    @classmethod
    def map_get_object_params(cls, request_params, cli_params):
        """Map CLI params to GetObject request params"""
        cls._set_sse_c_request_params(request_params, cli_params)

    @classmethod
    def map_copy_object_params(cls, request_params, cli_params):
        """Map CLI params to CopyObject request params"""
        cls._set_general_object_params(request_params, cli_params)
        cls._set_metadata_directive_param(request_params, cli_params)
        cls._set_metadata_params(request_params, cli_params)
        cls._auto_populate_metadata_directive(request_params)
        cls._set_sse_request_params(request_params, cli_params)
        cls._set_sse_c_and_copy_source_request_params(
            request_params, cli_params)

    @classmethod
    def map_head_object_params(cls, request_params, cli_params):
        """Map CLI params to HeadObject request params"""
        cls._set_sse_c_request_params(request_params, cli_params)

    @classmethod
    def map_create_multipart_upload_params(cls, request_params, cli_params):
        """Map CLI params to CreateMultipartUpload request params"""
        cls._set_general_object_params(request_params, cli_params)
        cls._set_sse_request_params(request_params, cli_params)
        cls._set_sse_c_request_params(request_params, cli_params)
        cls._set_metadata_params(request_params, cli_params)

    @classmethod
    def map_upload_part_params(cls, request_params, cli_params):
        """Map CLI params to UploadPart request params"""
        cls._set_sse_c_request_params(request_params, cli_params)

    @classmethod
    def map_upload_part_copy_params(cls, request_params, cli_params):
        """Map CLI params to UploadPartCopy request params"""
        cls._set_sse_c_and_copy_source_request_params(
            request_params, cli_params)

    @classmethod
    def _set_general_object_params(cls, request_params, cli_params):
        # Paramters set in this method should be applicable to the following
        # operations involving objects: PutObject, CopyObject, and
        # CreateMultipartUpload.
        general_param_translation = {
            'acl': 'ACL',
            'storage_class': 'StorageClass',
            'website_redirect': 'WebsiteRedirectLocation',
            'content_type': 'ContentType',
            'cache_control': 'CacheControl',
            'content_disposition': 'ContentDisposition',
            'content_encoding': 'ContentEncoding',
            'content_language': 'ContentLanguage',
            'expires': 'Expires'
        }
        for cli_param_name in general_param_translation:
            if cli_params.get(cli_param_name):
                request_param_name = general_param_translation[cli_param_name]
                request_params[request_param_name] = cli_params[cli_param_name]
        cls._set_grant_params(request_params, cli_params)

    @classmethod
    def _set_grant_params(cls, request_params, cli_params):
        if cli_params.get('grants'):
            for grant in cli_params['grants']:
                try:
                    permission, grantee = grant.split('=', 1)
                except ValueError:
                    raise ValueError('grants should be of the form '
                                     'permission=principal')
                request_params[cls._permission_to_param(permission)] = grantee

    @classmethod
    def _permission_to_param(cls, permission):
        if permission == 'read':
            return 'GrantRead'
        if permission == 'full':
            return 'GrantFullControl'
        if permission == 'readacl':
            return 'GrantReadACP'
        if permission == 'writeacl':
            return 'GrantWriteACP'
        raise ValueError('permission must be one of: '
                         'read|readacl|writeacl|full')

    @classmethod
    def _set_metadata_params(cls, request_params, cli_params):
        if cli_params.get('metadata'):
            request_params['Metadata'] = cli_params['metadata']

    @classmethod
    def _auto_populate_metadata_directive(cls, request_params):
        if request_params.get('Metadata') and \
                not request_params.get('MetadataDirective'):
            request_params['MetadataDirective'] = 'REPLACE'

    @classmethod
    def _set_metadata_directive_param(cls, request_params, cli_params):
        if cli_params.get('metadata_directive'):
            request_params['MetadataDirective'] = cli_params[
                'metadata_directive']

    @classmethod
    def _set_sse_request_params(cls, request_params, cli_params):
        if cli_params.get('sse'):
            request_params['ServerSideEncryption'] = cli_params['sse']
        if  cli_params.get('sse_kms_key_id'):
            request_params['SSEKMSKeyId'] = cli_params['sse_kms_key_id']

    @classmethod
    def _set_sse_c_request_params(cls, request_params, cli_params):
        if cli_params.get('sse_c'):
            request_params['SSECustomerAlgorithm'] = cli_params['sse_c']
            request_params['SSECustomerKey'] = cli_params['sse_c_key']

    @classmethod
    def _set_sse_c_copy_source_request_params(cls, request_params, cli_params):
        if cli_params.get('sse_c_copy_source'):
            request_params['CopySourceSSECustomerAlgorithm'] = cli_params[
                'sse_c_copy_source']
            request_params['CopySourceSSECustomerKey'] = cli_params[
                'sse_c_copy_source_key']

    @classmethod
    def _set_sse_c_and_copy_source_request_params(cls, request_params,
                                                  cli_params):
        cls._set_sse_c_request_params(request_params, cli_params)
        cls._set_sse_c_copy_source_request_params(request_params, cli_params)
