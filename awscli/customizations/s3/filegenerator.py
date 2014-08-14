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
import sys

import six
from dateutil.parser import parse
from dateutil.tz import tzlocal

from awscli.customizations.s3.utils import find_bucket_key, get_file_stat
from awscli.customizations.s3.utils import BucketLister
from awscli.errorhandler import ClientError


# This class is provided primarily to provide a detailed error message.

class FileDecodingError(Exception):
    """Raised when there was an issue decoding the file."""

    ADVICE = (
        "Please check your locale settings.  The filename was decoded as: %s\n"
        "On posix platforms, check the LC_CTYPE environment variable."
        % (sys.getfilesystemencoding())
    )

    def __init__(self, directory, filename):
        self.directory = directory
        self.file_name = filename
        self.error_message = (
            'There was an error trying to decode the the file "%s" in '
            'directory "%s". \n%s' % (self.file_name,
                                      self.directory.encode('utf-8'),
                                      self.ADVICE)
        )
        super(FileDecodingError, self).__init__(self.error_message)


class FileStat(object):
    def __init__(self, src, dest=None, compare_key=None, size=None,
                 last_update=None, src_type=None, dest_type=None,
                 operation_name=None):
        self.src = src
        self.dest = dest
        self.compare_key = compare_key
        self.size = size
        self.last_update = last_update
        self.src_type = src_type
        self.dest_type = dest_type
        self.operation_name = operation_name


class FileGenerator(object):
    """
    This is a class the creates a generator to yield files based on information
    returned from the ``FileFormat`` class.  It is universal in the sense that
    it will handle s3 files, local files, local directories, and s3 objects
    under the same common prefix.  The generator yields corresponding
    ``FileInfo`` objects to send to a ``Comparator`` or ``S3Handler``.
    """
    def __init__(self, service, endpoint, operation_name,
                 follow_symlinks=True):
        self._service = service
        self._endpoint = endpoint
        self.operation_name = operation_name
        self.follow_symlinks = follow_symlinks

    def call(self, files):
        """
        This is the generalized function to yield the ``FileInfo`` objects.
        ``dir_op`` and ``use_src_name`` flags affect which files are used and
        ensure the proper destination paths and compare keys are formed.
        """
        src = files['src']
        dest = files['dest']
        src_type = src['type']
        dest_type = dest['type']
        function_table = {'s3': self.list_objects, 'local': self.list_files}
        sep_table = {'s3': '/', 'local': os.sep}
        source = src['path']
        file_list = function_table[src_type](source, files['dir_op'])
        for src_path, size, last_update in file_list:
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
            yield FileStat(src=src_path, dest=dest_path,
                           compare_key=compare_key, size=size,
                           last_update=last_update, src_type=src_type,
                           dest_type=dest_type,
                           operation_name=self.operation_name)

    def list_files(self, path, dir_op):
        """
        This function yields the appropriate local file or local files
        under a directory depending on if the operation is on a directory.
        For directories a depth first search is implemented in order to
        follow the same sorted pattern as a s3 list objects operation
        outputs.  It yields the file's source path, size, and last
        update
        """
        join, isdir, isfile = os.path.join, os.path.isdir, os.path.isfile
        error, listdir = os.error, os.listdir
        if not self.should_ignore_file(path):
            if not dir_op:
                size, last_update = get_file_stat(path)
                yield path, size, last_update
            else:
                # We need to list files in byte order based on the full
                # expanded path of the key: 'test/1/2/3.txt'  However,
                # listdir() will only give us contents a single directory
                # at a time, so we'll get 'test'.  At the same time we don't
                # want to load the entire list of files into memory.  This
                # is handled by first going through the current directory
                # contents and adding the directory separator to any
                # directories.  We can then sort the contents,
                # and ensure byte order.
                names = listdir(path)
                self._check_paths_decoded(path, names)
                for i, name in enumerate(names):
                    file_path = join(path, name)
                    if isdir(file_path):
                        names[i] = name + os.path.sep
                self.normalize_sort(names, os.sep, '/')
                for name in names:
                    file_path = join(path, name)
                    if not self.should_ignore_file(file_path):
                        if isdir(file_path):
                            # Anything in a directory will have a prefix of
                            # this current directory and will come before the
                            # remaining contents in this directory.  This
                            # means we need to recurse into this sub directory
                            # before yielding the rest of this directory's
                            # contents.
                            for x in self.list_files(file_path, dir_op):
                                yield x
                        else:
                            size, last_update = get_file_stat(file_path)
                            yield file_path, size, last_update

    def normalize_sort(self, names, os_sep, character):
        """
        The purpose of this function is to ensure that the same path seperator
        is used when sorting.  In windows, the path operator is a backslash as
        opposed to a forward slash which can lead to differences in sorting
        between s3 and a windows machine.
        """
        names.sort(key=lambda item: item.replace(os_sep, character))

    def _check_paths_decoded(self, path, names):
        # We can get a UnicodeDecodeError if we try to listdir(<unicode>) and
        # can't decode the contents with sys.getfilesystemencoding().  In this
        # case listdir() returns the bytestring, which means that
        # join(<unicode>, <str>) could raise a UnicodeDecodeError.  When this
        # happens we raise a FileDecodingError that provides more information
        # into what's going on.
        for name in names:
            if not isinstance(name, six.text_type):
                raise FileDecodingError(path, name)

    def should_ignore_file(self, path):
        """
        This function checks whether a file should be ignored in the
        file generation process.  This includes symlinks that are not to be
        followed.
        """
        if not self.follow_symlinks:
            if os.path.isdir(path) and path.endswith(os.sep):
                # Trailing slash must be removed to check if it is a symlink.
                path = path[:-1]
            if os.path.islink(path):
                return True
        return False

    def list_objects(self, s3_path, dir_op):
        """
        This function yields the appropriate object or objects under a
        common prefix depending if the operation is on objects under a
        common prefix.  It yields the file's source path, size, and last
        update.
        """
        # Short circuit path: if we are not recursing into the s3
        # bucket and a specific path was given, we can just yield
        # that path and not have to call any operation in s3.
        bucket, prefix = find_bucket_key(s3_path)
        if not dir_op and prefix:
            yield self._list_single_object(s3_path)
        else:
            operation = self._service.get_operation('ListObjects')
            lister = BucketLister(operation, self._endpoint)
            for key in lister.list_objects(bucket=bucket, prefix=prefix):
                source_path, size, last_update = key
                if size == 0 and source_path.endswith('/'):
                    if self.operation_name == 'delete':
                        # This is to filter out manually created folders
                        # in S3.  They have a size zero and would be
                        # undesirably downloaded.  Local directories
                        # are automatically created when they do not
                        # exist locally.  But user should be able to
                        # delete them.
                        yield source_path, size, last_update
                elif not dir_op and s3_path != source_path:
                    pass
                else:
                    yield source_path, size, last_update

    def _list_single_object(self, s3_path):
        # When we know we're dealing with a single object, we can avoid
        # a ListObjects operation (which causes concern for anyone setting
        # IAM policies with the smallest set of permissions needed) and
        # instead use a HeadObject request.
        bucket, key = find_bucket_key(s3_path)
        operation = self._service.get_operation('HeadObject')
        try:
            response = operation.call(
                self._endpoint, bucket=bucket, key=key)[1]
        except ClientError as e:
            # We want to try to give a more helpful error message.
            # This is what the customer is going to see so we want to
            # give as much detail as we have.
            copy_fields = e.__dict__.copy()
            if not e.error_message == 'Unknown':
                raise
            if e.http_status_code == 404:
                # The key does not exist so we'll raise a more specific
                # error message here.
                copy_fields['error_code'] = 'NoSuchKey'
                copy_fields['error_message'] = 'Key "%s" does not exist' % key
            else:
                reason = six.moves.http_client.responses[
                    e.http_status_code]
                copy_fields['error_code'] = reason
                copy_fields['error_message'] = reason
            raise ClientError(**copy_fields)
        file_size = int(response['ContentLength'])
        last_update = parse(response['LastModified'])
        last_update = last_update.astimezone(tzlocal())
        return s3_path, file_size, last_update
