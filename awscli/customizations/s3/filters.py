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
import logging
import fnmatch
import os

from awscli.customizations.s3.utils import split_s3_bucket_key


LOG = logging.getLogger(__name__)


def create_filter(parameters):
    """Given the CLI parameters dict, create a Filter object."""
    # We need to evaluate all the filters based on the source
    # directory.
    if parameters['filters']:
        cli_filters = parameters['filters']
        real_filters = []
        for filter_type, filter_pattern in cli_filters:
            real_filters.append((filter_type.lstrip('-'),
                                 filter_pattern))
        source_location = parameters['src']
        if source_location.startswith('s3://'):
            # This gives us (bucket, keyname) and we want
            # the bucket to be the root dir.
            rootdir = split_s3_bucket_key(source_location)[0]
        else:
            if parameters.get('dir_op'):
                rootdir = os.path.abspath(parameters['src'])
            else:
                rootdir = os.path.abspath(os.path.dirname(parameters['src']))
        return Filter(real_filters, rootdir)
    else:
        return Filter({}, None)


class Filter(object):
    """
    This is a universal exclude/include filter.
    """
    def __init__(self, patterns, rootdir):
        """
        :var patterns: A list of patterns. A pattern consits of a list
            whose first member is a string 'exclude' or 'include'.
            The second member is the actual rule.
        :var rootdir: The root directory where the patterns are evaluated.
            This will generally be the directory of the source location.

        """
        self.patterns = self._full_path_patterns(patterns, rootdir)

    def _full_path_patterns(self, original_patterns, rootdir):
        # We need to transform the patterns into patterns that have
        # the root dir prefixed, so things like ``--exclude "*"``
        # will actually be ['exclude', '/path/to/root/*']
        full_patterns = []
        for pattern in original_patterns:
            full_patterns.append(
                (pattern[0], os.path.join(rootdir, pattern[1])))
        return full_patterns

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
                else:
                    path_pattern = pattern[1].replace(os.sep, '/')
                is_match = fnmatch.fnmatch(file_path, path_pattern)
                if is_match and pattern_type == 'include':
                    file_status = (file_info, True)
                    LOG.debug("%s matched include filter: %s",
                              file_path, path_pattern)
                elif is_match and pattern_type == 'exclude':
                    file_status = (file_info, False)
                    LOG.debug("%s matched exclude filter: %s",
                              file_path, path_pattern)
                else:
                    LOG.debug("%s did not match %s filter: %s",
                              file_path, pattern_type[2:], path_pattern)
            LOG.debug("=%s final filtered status, should_include: %s",
                      file_path, file_status[1])
            if file_status[1]:
                yield file_info
