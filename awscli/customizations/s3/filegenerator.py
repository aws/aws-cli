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

from dateutil.parser import parse
from dateutil.tz import tzlocal

from awscli.customizations.s3.fileinfo import FileInfo
from awscli.customizations.s3.utils import find_bucket_key, get_file_stat


class FileGenerator(object):
    """
    This is a class the creates a generator to yield files based on information
    returned from the ``FileFormat`` class.  It is universal in the sense that
    it will handle s3 files, local files, local directories, and s3 objects
    under the same common prefix.  The generator yields corresponding
    ``FileInfo`` objects to send to a ``Comparator`` or ``S3Handler``.
    """
    def __init__(self, session, operation="", parameters=None):
        self.session = session
        self.service = self.session.get_service('s3')
        region = self.session.get_config()['region']
        if parameters and parameters.get('region', ''):
            region = parameters['region']
        self.endpoint = self.service.get_endpoint(region)
        self.operation = operation

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
