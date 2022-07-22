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
import errno
import os
import re
import time
from collections import namedtuple, deque

from dateutil.parser import parse
from dateutil.tz import tzlocal, tzutc
from s3transfer.subscribers import BaseSubscriber

from awscli.compat import bytes_print
from awscli.compat import queue

LOGGER = logging.getLogger(__name__)
HUMANIZE_SUFFIXES = ('KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB')
EPOCH_TIME = datetime(1970, 1, 1, tzinfo=tzutc())
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
_S3_ACCESSPOINT_TO_BUCKET_KEY_REGEX = re.compile(
    r'^(?P<bucket>arn:(aws).*:s3:[a-z\-0-9]*:[0-9]{12}:accesspoint[:/][^/]+)/?'
    r'(?P<key>.*)$'
)
_S3_OUTPOST_TO_BUCKET_KEY_REGEX = re.compile(
    r'^(?P<bucket>arn:(aws).*:s3-outposts:[a-z\-0-9]+:[0-9]{12}:outpost[/:]'
    r'[a-zA-Z0-9\-]{1,63}[/:]accesspoint[/:][a-zA-Z0-9\-]{1,63})[/:]?(?P<key>.*)$'
)

_S3_OUTPOST_BUCKET_ARN_TO_BUCKET_KEY_REGEX = re.compile(
    r'^(?P<bucket>arn:(aws).*:s3-outposts:[a-z\-0-9]+:[0-9]{12}:outpost[/:]'
    r'[a-zA-Z0-9\-]{1,63}[/:]bucket[/:]'
    r'[a-zA-Z0-9\-]{1,63})[/:]?(?P<key>.*)$'
)

_S3_OBJECT_LAMBDA_TO_BUCKET_KEY_REGEX = re.compile(
    r'^(?P<bucket>arn:(aws).*:s3-object-lambda:[a-z\-0-9]+:[0-9]{12}:'
    r'accesspoint[/:][a-zA-Z0-9\-]{1,63})[/:]?(?P<key>.*)$'
)


def human_readable_size(value):
    """Convert a size in bytes into a human readable format.

    For example::

        >>> human_readable_size(1)
        '1 Byte'
        >>> human_readable_size(10)
        '10 Bytes'
        >>> human_readable_size(1024)
        '1.0 KiB'
        >>> human_readable_size(1024 * 1024)
        '1.0 MiB'

    :param value: The size in bytes.
    :return: The size in a human readable format based on base-2 units.

    """
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
    appear later in the command line take preference over rulers that
    appear earlier.
    """
    def __call__(self, parser, namespace, values, option_string=None):
        filter_list = getattr(namespace, self.dest)
        if filter_list:
            filter_list.append([option_string, values[0]])
        else:
            filter_list = [[option_string, values[0]]]
        setattr(namespace, self.dest, filter_list)


class CreateDirectoryError(Exception):
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


def block_unsupported_resources(s3_path):
    # AWS CLI s3 commands don't support object lambdas only direct API calls
    # are available for such resources
    if _S3_OBJECT_LAMBDA_TO_BUCKET_KEY_REGEX.match(s3_path):
        # In AWS CLI v2 we should use
        # awscli.customizations.exceptions.ParamValidationError
        # instead of ValueError
        raise ValueError(
            's3 commands do not support S3 Object Lambda resources. '
            'Use s3api commands instead.'
        )
    # AWS S3 API and AWS CLI s3 commands don't support Outpost bucket ARNs
    # only s3control API supports them so far
    if _S3_OUTPOST_BUCKET_ARN_TO_BUCKET_KEY_REGEX.match(s3_path):
        raise ValueError(
            's3 commands do not support Outpost Bucket ARNs. '
            'Use s3control commands instead.'
        )


def find_bucket_key(s3_path):
    """
    This is a helper function that given an s3 path such that the path is of
    the form: bucket/key
    It will return the bucket and the key represented by the s3 path
    """
    block_unsupported_resources(s3_path)
    match = _S3_ACCESSPOINT_TO_BUCKET_KEY_REGEX.match(s3_path)
    if match:
        return match.group('bucket'), match.group('key')
    match = _S3_OUTPOST_TO_BUCKET_KEY_REGEX.match(s3_path)
    if match:
        return match.group('bucket'), match.group('key')
    s3_components = s3_path.split('/', 1)
    bucket = s3_components[0]
    s3_key = ''
    if len(s3_components) > 1:
        s3_key = s3_components[1]
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
    except (ValueError, OSError, OverflowError):
        # Python's fromtimestamp raises value errors when the timestamp is out
        # of range of the platform's C localtime() function. This can cause
        # issues when syncing from systems with a wide range of valid
        # timestamps to systems with a lower range. Some systems support
        # 64-bit timestamps, for instance, while others only support 32-bit.
        # We don't want to fail in these cases, so instead we pass along none.
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
    warning_message = WarningResult(message=print_string, error=False,
                                    warning=True)
    return warning_message


class StdoutBytesWriter(object):
    """
    This class acts as a file-like object that performs the bytes_print
    function on write.
    """
    def __init__(self, stdout=None):
        self._stdout = stdout

    def write(self, b):
        """
        Writes data to stdout as bytes.

        :param b: data to write
        """
        bytes_print(b, self._stdout)


def guess_content_type(filename):
    """Given a filename, guess it's content type.

    If the type cannot be guessed, a value of None is returned.
    """
    try:
        return mimetypes.guess_type(filename)[0]
    # This catches a bug in the mimetype library where some MIME types
    # specifically on windows machines cause a UnicodeDecodeError
    # because the MIME type in the Windows registry has an encoding
    # that cannot be properly encoded using the default system encoding.
    # https://bugs.python.org/issue9291
    #
    # So instead of hard failing, just log the issue and fall back to the
    # default guessed content type of None.
    except UnicodeDecodeError:
        LOGGER.debug(
            'Unable to guess content type for %s due to '
            'UnicodeDecodeError: ', filename, exc_info=True
        )


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


def _date_parser(date_string):
    return parse(date_string).astimezone(tzlocal())


class BucketLister(object):
    """List keys in a bucket."""
    def __init__(self, client, date_parser=_date_parser):
        self._client = client
        self._date_parser = date_parser

    def list_objects(self, bucket, prefix=None, page_size=None,
                     extra_args=None):
        kwargs = {'Bucket': bucket, 'PaginationConfig': {'PageSize': page_size}}
        if prefix is not None:
            kwargs['Prefix'] = prefix
        if extra_args is not None:
            kwargs.update(extra_args)

        paginator = self._client.get_paginator('list_objects_v2')
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

WarningResult = PrintTask


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

    Note that existing parameters in ``request_params`` will be overridden if
    a parameter in ``cli_params`` maps to the existing parameter.
    """
    @classmethod
    def map_put_object_params(cls, request_params, cli_params):
        """Map CLI params to PutObject request params"""
        cls._set_general_object_params(request_params, cli_params)
        cls._set_metadata_params(request_params, cli_params)
        cls._set_sse_request_params(request_params, cli_params)
        cls._set_sse_c_request_params(request_params, cli_params)
        cls._set_request_payer_param(request_params, cli_params)

    @classmethod
    def map_get_object_params(cls, request_params, cli_params):
        """Map CLI params to GetObject request params"""
        cls._set_sse_c_request_params(request_params, cli_params)
        cls._set_request_payer_param(request_params, cli_params)

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
        cls._set_request_payer_param(request_params, cli_params)

    @classmethod
    def map_head_object_params(cls, request_params, cli_params):
        """Map CLI params to HeadObject request params"""
        cls._set_sse_c_request_params(request_params, cli_params)
        cls._set_request_payer_param(request_params, cli_params)

    @classmethod
    def map_create_multipart_upload_params(cls, request_params, cli_params):
        """Map CLI params to CreateMultipartUpload request params"""
        cls._set_general_object_params(request_params, cli_params)
        cls._set_sse_request_params(request_params, cli_params)
        cls._set_sse_c_request_params(request_params, cli_params)
        cls._set_metadata_params(request_params, cli_params)
        cls._set_request_payer_param(request_params, cli_params)

    @classmethod
    def map_upload_part_params(cls, request_params, cli_params):
        """Map CLI params to UploadPart request params"""
        cls._set_sse_c_request_params(request_params, cli_params)
        cls._set_request_payer_param(request_params, cli_params)

    @classmethod
    def map_upload_part_copy_params(cls, request_params, cli_params):
        """Map CLI params to UploadPartCopy request params"""
        cls._set_sse_c_and_copy_source_request_params(
            request_params, cli_params)
        cls._set_request_payer_param(request_params, cli_params)

    @classmethod
    def map_delete_object_params(cls, request_params, cli_params):
        cls._set_request_payer_param(request_params, cli_params)

    @classmethod
    def map_list_objects_v2_params(cls, request_params, cli_params):
        cls._set_request_payer_param(request_params, cli_params)

    @classmethod
    def _set_request_payer_param(cls, request_params, cli_params):
        if cli_params.get('request_payer'):
            request_params['RequestPayer'] = cli_params['request_payer']

    @classmethod
    def _set_general_object_params(cls, request_params, cli_params):
        # Parameters set in this method should be applicable to the following
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


class ProvideSizeSubscriber(BaseSubscriber):
    """
    A subscriber which provides the transfer size before it's queued.
    """
    def __init__(self, size):
        self.size = size

    def on_queued(self, future, **kwargs):
        future.meta.provide_transfer_size(self.size)


# TODO: Eventually port this down to the BaseSubscriber or a new subscriber
# class in s3transfer. The functionality is very convenient but may need
# some further design decisions to make it a feature in s3transfer.
class OnDoneFilteredSubscriber(BaseSubscriber):
    """Subscriber that differentiates between successes and failures

    It is really a convenience class so developers do not have to have
    to constantly remember to have a general try/except around future.result()
    """
    def on_done(self, future, **kwargs):
        future_exception = None
        try:

            future.result()
        except Exception as e:
            future_exception = e
        # If the result propagates an error, call the on_failure
        # method instead.
        if future_exception:
            self._on_failure(future, future_exception)
        else:
            self._on_success(future)

    def _on_success(self, future):
        pass

    def _on_failure(self, future, e):
        pass


class DeleteSourceSubscriber(OnDoneFilteredSubscriber):
    """A subscriber which deletes the source of the transfer."""
    def _on_success(self, future):
        try:
            self._delete_source(future)
        except Exception as e:
            future.set_exception(e)

    def _delete_source(self, future):
        raise NotImplementedError('_delete_source()')


class DeleteSourceObjectSubscriber(DeleteSourceSubscriber):
    """A subscriber which deletes an object."""
    def __init__(self, client):
        self._client = client

    def _get_bucket(self, call_args):
        return call_args.bucket

    def _get_key(self, call_args):
        return call_args.key

    def _delete_source(self, future):
        call_args = future.meta.call_args
        delete_object_kwargs = {
            'Bucket': self._get_bucket(call_args),
            'Key': self._get_key(call_args)
        }
        if call_args.extra_args.get('RequestPayer'):
            delete_object_kwargs['RequestPayer'] = call_args.extra_args[
                'RequestPayer']
        self._client.delete_object(**delete_object_kwargs)


class DeleteCopySourceObjectSubscriber(DeleteSourceObjectSubscriber):
    """A subscriber which deletes the copy source."""
    def _get_bucket(self, call_args):
        return call_args.copy_source['Bucket']

    def _get_key(self, call_args):
        return call_args.copy_source['Key']


class DeleteSourceFileSubscriber(DeleteSourceSubscriber):
    """A subscriber which deletes a file."""
    def _delete_source(self, future):
        os.remove(future.meta.call_args.fileobj)


class BaseProvideContentTypeSubscriber(BaseSubscriber):
    """A subscriber that provides content type when creating s3 objects"""

    def on_queued(self, future, **kwargs):
        guessed_type = guess_content_type(self._get_filename(future))
        if guessed_type is not None:
            future.meta.call_args.extra_args['ContentType'] = guessed_type

    def _get_filename(self, future):
        raise NotImplementedError('_get_filename()')


class ProvideUploadContentTypeSubscriber(BaseProvideContentTypeSubscriber):
    def _get_filename(self, future):
        return future.meta.call_args.fileobj


class ProvideCopyContentTypeSubscriber(BaseProvideContentTypeSubscriber):
    def _get_filename(self, future):
        return future.meta.call_args.copy_source['Key']


class ProvideLastModifiedTimeSubscriber(OnDoneFilteredSubscriber):
    """Sets utime for a downloaded file"""
    def __init__(self, last_modified_time, result_queue):
        self._last_modified_time = last_modified_time
        self._result_queue = result_queue

    def _on_success(self, future, **kwargs):
        filename = future.meta.call_args.fileobj
        try:
            last_update_tuple = self._last_modified_time.timetuple()
            mod_timestamp = time.mktime(last_update_tuple)
            set_file_utime(filename, int(mod_timestamp))
        except Exception as e:
            warning_message = (
                'Successfully Downloaded %s but was unable to update the '
                'last modified time. %s' % (filename, e))
            self._result_queue.put(create_warning(filename, warning_message))


class DirectoryCreatorSubscriber(BaseSubscriber):
    """Creates a directory to download if it does not exist"""
    def on_queued(self, future, **kwargs):
        d = os.path.dirname(future.meta.call_args.fileobj)
        try:
            if not os.path.exists(d):
                os.makedirs(d)
        except OSError as e:
            if not e.errno == errno.EEXIST:
                raise CreateDirectoryError(
                    "Could not create directory %s: %s" % (d, e))


class NonSeekableStream(object):
    """Wrap a file like object as a non seekable stream.

    This class is used to wrap an existing file like object
    such that it only has a ``.read()`` method.

    There are some file like objects that aren't truly seekable
    but appear to be.  For example, on windows, sys.stdin has
    a ``seek()`` method, and calling ``seek(0)`` even appears
    to work.  However, subsequent ``.read()`` calls will just
    return an empty string.

    Consumers of these file like object have no way of knowing
    if these files are truly seekable or not, so this class
    can be used to force non-seekable behavior when you know
    for certain that a fileobj is non seekable.

    """
    def __init__(self, fileobj):
        self._fileobj = fileobj

    def read(self, amt=None):
        if amt is None:
            return self._fileobj.read()
        else:
            return self._fileobj.read(amt)
