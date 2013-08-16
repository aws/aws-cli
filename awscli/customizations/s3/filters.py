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
import fnmatch
import os


class Filter(object):
    """
    This is a universal exclude/include filter.
    """
    def __init__(self, parameters=None):
        """
        :var self.patterns: A list of patterns. A pattern consits of a list
            whose first member is a string '--exclude' or '--include'.
            The second member is the actual rule.
        """
        if 'filters' in parameters:
            self.patterns = parameters['filters']
        else:
            self.patterns = []

    def call(self, file_infos):
        """
        This function iterates over through the yielded file_info
        objects.  It determines the type of the file and
        applies pattern matching to determine if the rule applies.
        While iterating though the patterns the file is assigned
        a boolean flag to determine if a file should be yielded on
        past the filer.  Anything identified by the exclude filter
        has its flag set to false.  Anything identified by the include
        filter has its flag set to True.  All files begin with
        the flag set to true. Rules listed at the end will
        overwrite flags thrown by rules listed
        before it.
        """
        for file_info in file_infos:
            file_path = file_info.src
            file_status = (file_info, True)

            for pattern in self.patterns:
                pattern_type = pattern[0]
                if file_info.src_type == 'local':
                    path_pattern = pattern[1].replace('/', os.sep)
                    full_path_pattern = os.path.abspath(path_pattern)

                else:
                    path_pattern = pattern[1].replace(os.sep, '/')
                    full_path_pattern = path_pattern

                is_match = fnmatch.fnmatch(file_path, full_path_pattern)
                if is_match and pattern_type == '--include':
                    file_status = (file_info, True)
                elif is_match and pattern_type == '--exclude':
                    file_status = (file_info, False)

            if file_status[1]:
                yield file_info
