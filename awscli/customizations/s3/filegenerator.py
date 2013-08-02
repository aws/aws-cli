from datetime import datetime, timedelta
import glob
import os
import time
import six
import sys

from dateutil.parser import parse
from dateutil.tz import tzlocal

from awscli import EnvironmentVariables


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
    the file in bytes and time of last modification
    """
    stats = os.stat(path)
    update_time = datetime.fromtimestamp(stats.st_mtime, tzlocal())
    return stats.st_size, update_time


class FileInfo(object):
    """
    This class contains important details about a file.  If the object's
    parameters are fully specifed it can be sent to the S3 Handler to preform
    the appropriate operations.

    :param src: the source path
    :type src: string

    :param dest: the destination path
    :type dest: string

    :param compare_key: the name of the file relative to the specified
        directory/prefix.  This variable is used when preforming synching
        or if the destination file is adopting the source file's name.
    :type compare_key: string

    :param size: The size of the file in bytes.
    :type size: integer

    :param last_update: the local time of last modification.
    :type last_update: datetime object

    :param src_type: if the source file is s3 or local.
    :type src_type: string

    :param dest_type: if the destination is s3 or local.
    :param dest_type: string

    :param operation: the operation being preformed.
    :param operation: string

    Note that a local file will always have its absolute path, and a s3 file
    will have its path in the form of bucket/key
    """
    def __init__(self, src, dest=None, compare_key=None, size=None,
                 last_update=None, src_type=None, dest_type=None,
                 operation=None):
        self.src = src
        self.dest = dest
        self.compare_key = compare_key
        self.size = size
        self.last_update = last_update
        self.src_type = src_type
        self.dest_type = dest_type
        self.operation = operation


class FileGenerator(object):
    """
    This is a class the creates a generator to yield files based on information
    returned from the fileformat class.  It is universal in the sense that
    it will handle s3 files, local files, local directories, and s3 objects
    under the same common prefix.  The generator yields corresponding
    fileinfo objects to send to a comparator or S3 Handler.
    """
    def __init__(self, session, operation="", parameters={}):
        self.session = session
        self.service = self.session.get_service('s3')
        region = self.session.get_config()['region']
        if parameters.get('region', ''):
            region = parameters['region']
        self.endpoint = self.service.get_endpoint(region)
        self.operation = operation

    def call(self, files):
        """
        This is the generalized function to yield the fileinfo objects.
        dir_op and use_src_name flags affect which files are used and
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
            yield FileInfo(src=src_path, dest=dest_path,
                           compare_key=compare_key, size=size,
                           last_update=last_update, src_type=src_type,
                           dest_type=dest_type, operation=self.operation)

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
        if not dir_op:
            size, last_update = get_file_stat(path)
            yield path, size, last_update
        else:
            names = sorted(listdir(path))
            for name in names:
                file_path = join(path, name)
                if isdir(file_path):
                    for x in self.list_files(file_path, dir_op):
                        yield x
                else:
                    size, last_update = get_file_stat(file_path)
                    yield file_path, size, last_update

    def list_objects(self, s3_path, dir_op):
        """
        This function yields the appropriate object or objects under a
        common prefix depending if the operation is on objects under a
        common prefix.  It yields the file's source path, size, and last
        update.
        """
        operation = self.service.get_operation('ListObjects')
        bucket, prefix = find_bucket_key(s3_path)
        iterator = operation.paginate(self.endpoint, bucket=bucket,
                                      prefix=prefix)
        for html_response, response_data in iterator:
            contents = response_data['Contents']
            for content in contents:
                src_path = bucket + '/' + content['Key']
                size = content['Size']
                last_update = parse(content['LastModified'])
                last_update = last_update.astimezone(tzlocal())
                if size == 0 and src_path.endswith('/'):
                    if self.operation != 'delete':
                        pass
                    else:
                        yield src_path, size, last_update
                elif not dir_op and s3_path != src_path:
                    pass
                else:
                    yield src_path, size, last_update
