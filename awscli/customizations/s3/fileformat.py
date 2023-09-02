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


class FileFormat(object):
    def format(self, src, dest, parameters):
        """
        This function formats the source and destination
        path to the proper form for a file generator.

        Note that a file is designated as an s3 file if it begins with s3://

        :param src: The path of the source
        :type src: string
        :param dest: The path of the dest
        :type dest: string
        :param parameters: A dictionary that will be formed when the arguments
            of the command line have been parsed.  For this
            function the dictionary should have the key 'dir_op'
            which is a boolean value that is true when
            the operation is being performed on a local directory/
            all objects under a common prefix in s3 or false when
            it is on a single file/object.
            The dictionary should also have the key 'partial_prefix'
            which is a boolean value that is true when the operation is being
            performed on all objects under a prefix (including partially completed
            prefixes) in s3

        :returns: A dictionary that will be passed to a file generator.
            The dictionary contains the keys src, dest, dir_op, partial_prefix and
            use_src_name. src is a dictionary containing the source path
            and whether its located locally or in s3. dest is a dictionary
            containing the destination path and whether its located
            locally or in s3.
        """
        src_type, src_path = self.identify_type(src)
        dest_type, dest_path = self.identify_type(dest)
        # :var dir_op: True when the operation being performed is on a
        #     directory/objects under a common prefix or false when it
        #     is a single file
        dir_op = parameters['dir_op']
        partial_prefix = parameters['partial_prefix']
        if src_type == 'local':
            src_path = self.local_format(src_path, dir_op)
        else:
            src_path = self.s3_format('src', src_path, dir_op, partial_prefix)

        if dest_type == 'local':
            dest_path = self.local_format(dest_path, dir_op)
        else:
            dest_path = self.s3_format('dest', dest_path, dir_op, partial_prefix)
        # :var use_src_name: True when the destination file/object will take on
        #     the name of the source file/object.  False when it
        #     will take on the name the user specified in the
        #     command line.
        use_src_name = self.should_use_src_name(dest_type, dest_path, dir_op)
        files = {'src': {'path': src_path, 'type': src_type},
                 'dest': {'path': dest_path, 'type': dest_type},
                 'dir_op': dir_op, 'use_src_name': use_src_name,
                 'partial_prefix': partial_prefix}
        return files

    def local_format(self, path, dir_op):
        """
        Formats the path of local files
        """
        full_path = os.path.abspath(path)
        if dir_op or path.endswith(os.sep) or (os.path.exists(full_path) and os.path.isdir(full_path)):
            full_path += os.sep
            return full_path
        return full_path

    def s3_format(self, src_or_dest, path, dir_op, partial_prefix):
        """
        Formats s3 paths.
        """
        # If partial prefix match, do not modify the source path
        if partial_prefix and src_or_dest == 'src':
            return path

        # If a directory or prefix operation, ensure the destination path ends with a '/'
        if (dir_op or partial_prefix) and not path.endswith('/'):
            path += '/'
        return path

    def should_use_src_name(self, path_type, dest, dir_op):
        """
        Determines whether the destination file will use the
        name of the source file or the name of the destination.

        :returns: true if the destination file will use the name of the source,
            false if the destination file will use the name provided in the commandline
        """
        # If it's a directory operation, use the source name
        if dir_op:
            return True

        # If destination path is a s3 common prefix, use the source name
        if path_type == 's3' and dest.endswith('/'):
            return True

        # If the destination is a local directory, use the source name
        if path_type == 'local':
            full_path = os.path.abspath(dest)
            if (os.path.exists(full_path) and os.path.isdir(full_path)) or dest.endswith(os.sep):
                return True

        return False


    def identify_type(self, path):
        """
        It identifies whether the path is from local or s3.  Returns the
        adjusted pathname and a string stating whether the file is from local
        or s3.  If from s3 it strips off the s3:// from the beginning of the
        path
        """
        if path.startswith('s3://'):
            return 's3', path[5:]
        else:
            return 'local', path
