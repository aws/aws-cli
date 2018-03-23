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
import stat

from dateutil.parser import parse
from dateutil.tz import tzlocal
from botocore.exceptions import ClientError

from awscli.customizations.s3.utils import find_bucket_key, get_file_stat
from awscli.customizations.s3.utils import BucketLister, create_warning, \
    find_dest_path_comp_key, EPOCH_TIME
from awscli.compat import six
from awscli.compat import queue

_open = open


def is_special_file(path):
    """
    This function checks to see if a special file.  It checks if the
    file is a character special device, block special device, FIFO, or
    socket.
    """
    mode = os.stat(path).st_mode
    # Character special device.
    if stat.S_ISCHR(mode):
        return True
    # Block special device
    if stat.S_ISBLK(mode):
        return True
    # FIFO.
    if stat.S_ISFIFO(mode):
        return True
    # Socket.
    if stat.S_ISSOCK(mode):
        return True
    return False


def is_readable(path):
    """
    This function checks to see if a file or a directory can be read.
    This is tested by performing an operation that requires read access
    on the file or the directory.
    """
    if os.path.isdir(path):
        try:
            os.listdir(path)
        except (OSError, IOError):
            return False
    else:
        try:
            with _open(path, 'r') as fd:
                pass
        except (OSError, IOError):
            return False
    return True


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
            'There was an error trying to decode the the file %s in '
            'directory "%s". \n%s' % (repr(self.file_name),
                                      self.directory,
                                      self.ADVICE)
        )
        super(FileDecodingError, self).__init__(self.error_message)


class FileStat(object):
    def __init__(self, src, dest=None, compare_key=None, size=None,
                 last_update=None, src_type=None, dest_type=None,
                 operation_name=None, response_data=None):
        self.src = src
        self.dest = dest
        self.compare_key = compare_key
        self.size = size
        self.last_update = last_update
        self.src_type = src_type
        self.dest_type = dest_type
        self.operation_name = operation_name
        self.response_data = response_data


class FileGenerator(object):
    """
    This is a class the creates a generator to yield files based on information
    returned from the ``FileFormat`` class.  It is universal in the sense that
    it will handle s3 files, local files, local directories, and s3 objects
    under the same common prefix.  The generator yields corresponding
    ``FileInfo`` objects to send to a ``Comparator`` or ``S3Handler``.
    """
    def __init__(self, client, operation_name, follow_symlinks=True,
                 page_size=None, result_queue=None, request_parameters=None):
        self._client = client
        self.operation_name = operation_name
        self.follow_symlinks = follow_symlinks
        self.page_size = page_size
        self.result_queue = result_queue
        if not result_queue:
            self.result_queue = queue.Queue()
        self.request_parameters = {}
        if request_parameters is not None:
            self.request_parameters = request_parameters

    def call(self, files):
        """
        This is the generalized function to yield the ``FileInfo`` objects.
        ``dir_op`` and ``use_src_name`` flags affect which files are used and
        ensure the proper destination paths and compare keys are formed.
        """
        function_table = {'s3': self.list_objects, 'local': self.list_files}
        source = files['src']['path']
        src_type = files['src']['type']
        dest_type = files['dest']['type']
        file_iterator = function_table[src_type](source, files['dir_op'])
        for src_path, extra_information in file_iterator:
            dest_path, compare_key = find_dest_path_comp_key(files, src_path)
            file_stat_kwargs = {
                'src': src_path, 'dest': dest_path, 'compare_key': compare_key,
                'src_type': src_type, 'dest_type': dest_type,
                'operation_name': self.operation_name
            }
            self._inject_extra_information(file_stat_kwargs, extra_information)
            yield FileStat(**file_stat_kwargs)

    def _inject_extra_information(self, file_stat_kwargs, extra_information):
        src_type = file_stat_kwargs['src_type']
        file_stat_kwargs['size'] = extra_information['Size']
        file_stat_kwargs['last_update'] = extra_information['LastModified']

        # S3 objects require the response data retrieved from HeadObject
        # and ListObject
        if src_type == 's3':
            file_stat_kwargs['response_data'] = extra_information

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
                stats = self._safely_get_file_stats(path)
                if stats:
                    yield stats
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
                listdir_names = listdir(path)
                names = []
                for name in listdir_names:
                    if not self.should_ignore_file_with_decoding_warnings(
                            path, name):
                        file_path = join(path, name)
                        if isdir(file_path):
                            name = name + os.path.sep
                        names.append(name)
                self.normalize_sort(names, os.sep, '/')
                for name in names:
                    file_path = join(path, name)
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
                        stats = self._safely_get_file_stats(file_path)
                        if stats:
                            yield stats

    def _safely_get_file_stats(self, file_path):
        try:
            size, last_update = get_file_stat(file_path)
        except (OSError, ValueError):
            self.triggers_warning(file_path)
        else:
            last_update = self._validate_update_time(last_update, file_path)
            return file_path, {'Size': size, 'LastModified': last_update}

    def _validate_update_time(self, update_time, path):
        # If the update time is None we know we ran into an invalid tiemstamp.
        if update_time is None:
            warning = create_warning(
                path=path,
                error_message="File has an invalid timestamp. Passing epoch "
                              "time as timestamp.",
                skip_file=False)
            self.result_queue.put(warning)
            return EPOCH_TIME
        return update_time

    def normalize_sort(self, names, os_sep, character):
        """
        The purpose of this function is to ensure that the same path seperator
        is used when sorting.  In windows, the path operator is a backslash as
        opposed to a forward slash which can lead to differences in sorting
        between s3 and a windows machine.
        """
        names.sort(key=lambda item: item.replace(os_sep, character))

    def should_ignore_file_with_decoding_warnings(self, dirname, filename):
        """
        We can get a UnicodeDecodeError if we try to listdir(<unicode>) and
        can't decode the contents with sys.getfilesystemencoding().  In this
        case listdir() returns the bytestring, which means that
        join(<unicode>, <str>) could raise a UnicodeDecodeError.  When this
        happens we warn using a FileDecodingError that provides more
        information into what's going on.
        """
        if not isinstance(filename, six.text_type):
            decoding_error = FileDecodingError(dirname, filename)
            warning = create_warning(repr(filename),
                                     decoding_error.error_message)
            self.result_queue.put(warning)
            return True
        path = os.path.join(dirname, filename)
        return self.should_ignore_file(path)

    def should_ignore_file(self, path):
        """
        This function checks whether a file should be ignored in the
        file generation process.  This includes symlinks that are not to be
        followed and files that generate warnings.
        """
        if not self.follow_symlinks:
            if os.path.isdir(path) and path.endswith(os.sep):
                # Trailing slash must be removed to check if it is a symlink.
                path = path[:-1]
            if os.path.islink(path):
                return True
        warning_triggered = self.triggers_warning(path)
        if warning_triggered:
            return True
        return False

    def triggers_warning(self, path):
        """
        This function checks the specific types and properties of a file.
        If the file would cause trouble, the function adds a
        warning to the result queue to be printed out and returns a boolean
        value notify whether the file caused a warning to be generated.
        Files that generate warnings are skipped.  Currently, this function
        checks for files that do not exist and files that the user does
        not have read access.
        """
        if not os.path.exists(path):
            warning = create_warning(path, "File does not exist.")
            self.result_queue.put(warning)
            return True
        if is_special_file(path):
            warning = create_warning(path,
                                     ("File is character special device, "
                                      "block special device, FIFO, or "
                                      "socket."))
            self.result_queue.put(warning)
            return True
        if not is_readable(path):
            warning = create_warning(path, "File/Directory is not readable.")
            self.result_queue.put(warning)
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
            lister = BucketLister(self._client)
            extra_args = self.request_parameters.get('ListObjects', {})
            for key in lister.list_objects(bucket=bucket, prefix=prefix,
                                           page_size=self.page_size,
                                           extra_args=extra_args):
                source_path, response_data = key
                if response_data['Size'] == 0 and source_path.endswith('/'):
                    if self.operation_name == 'delete':
                        # This is to filter out manually created folders
                        # in S3.  They have a size zero and would be
                        # undesirably downloaded.  Local directories
                        # are automatically created when they do not
                        # exist locally.  But user should be able to
                        # delete them.
                        yield source_path, response_data
                elif not dir_op and s3_path != source_path:
                    pass
                else:
                    yield source_path, response_data

    def _list_single_object(self, s3_path):
        # When we know we're dealing with a single object, we can avoid
        # a ListObjects operation (which causes concern for anyone setting
        # IAM policies with the smallest set of permissions needed) and
        # instead use a HeadObject request.
        if self.operation_name == 'delete':
            # If the operation is just a single remote delete, there is
            # no need to run HeadObject on the S3 object as none of the
            # information gained from HeadObject is required to delete the
            # object.
            return s3_path, {'Size': None, 'LastModified': None}
        bucket, key = find_bucket_key(s3_path)
        try:
            params = {'Bucket': bucket, 'Key': key}
            params.update(self.request_parameters.get('HeadObject', {}))
            response = self._client.head_object(**params)
        except ClientError as e:
            # We want to try to give a more helpful error message.
            # This is what the customer is going to see so we want to
            # give as much detail as we have.
            if not e.response['Error']['Code'] == '404':
                raise
            # The key does not exist so we'll raise a more specific
            # error message here.
            response = e.response.copy()
            response['Error']['Message'] = 'Key "%s" does not exist' % key
            raise ClientError(response, 'HeadObject')
        response['Size'] = int(response.pop('ContentLength'))
        last_update = parse(response['LastModified'])
        response['LastModified'] = last_update.astimezone(tzlocal())
        return s3_path, response
