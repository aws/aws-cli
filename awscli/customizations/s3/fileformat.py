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

        :returns: A dictionary that will be passed to a file generator.
            The dictionary contains the keys src, dest, dir_op, and
            use_src_name. src is a dictionary containing the source path
            and whether its located locally or in s3. dest is a dictionary
            containing the destination path and whether its located
            locally or in s3.
        """
        src_type, src_path = self.identify_type(src)
        dest_type, dest_path = self.identify_type(dest)
        format_table = {'s3': self.s3_format, 'local': self.local_format}
        # :var dir_op: True when the operation being performed is on a
        #     directory/objects under a common prefix or false when it
        #     is a single file
        dir_op = parameters['dir_op']
        src_path = format_table[src_type](src_path, dir_op)[0]
        # :var use_src_name: True when the destination file/object will take on
        #     the name of the source file/object.  False when it
        #     will take on the name the user specified in the
        #     command line.
        dest_path, use_src_name = format_table[dest_type](dest_path, dir_op)
        files = {'src': {'path': src_path, 'type': src_type},
                 'dest': {'path': dest_path, 'type': dest_type},
                 'dir_op': dir_op, 'use_src_name': use_src_name}
        return files

    def local_format(self, path, dir_op):
        """
        This function formats the path of local files and returns whether the
        destination will keep its own name or take the source's name along with
        the editted path.
        Formatting Rules:
            1) If a destination file is taking on a source name, it must end
               with the appropriate operating system seperator

        General Options:
            1) If the operation is on a directory, the destination file will
               always use the name of the corresponding source file.
            2) If the path of the destination exists and is a directory it
               will always use the name of the source file.
            3) If the destination path ends with the appropriate operating
               system seperator but is not an existing directory, the
               appropriate directories will be made and the file will use the
               source's name.
            4) If the destination path does not end with the appropriate
               operating system seperator and is not an existing directory, the
               appropriate directories will be created and the file name will
               be of the one provided.
        """
        full_path = os.path.abspath(path)
        if (os.path.exists(full_path) and os.path.isdir(full_path)) or dir_op:
            full_path += os.sep
            return full_path, True
        else:
            if path.endswith(os.sep):
                full_path += os.sep
                return full_path, True
            else:
                return full_path, False

    def s3_format(self, path, dir_op):
        """
        This function formats the path of source files and returns whether the
        destination will keep its own name or take the source's name along
        with the edited path.
        Formatting Rules:
            1) If a destination file is taking on a source name, it must end
               with a forward slash.
        General Options:
            1) If the operation is on objects under a common prefix,
               the destination file will always use the name of the
               corresponding source file.
            2) If the path ends with a forward slash, the appropriate prefixes
               will be formed and will use the name of the source.
            3) If the path does not end with a forward slash, the appropriate
               prefix will be formed but use the the name provided as opposed
               to the source name.
        """
        if dir_op:
            if not path.endswith('/'):
                path += '/'
            return path, True
        else:
            if not path.endswith('/'):
                return path, False
            else:
                return path, True

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
