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
import logging
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
            real_filters.append((filter_type.lstrip('-'), filter_pattern))
        source_location = parameters['src']
        if source_location.startswith('s3://'):
            # This gives us (bucket, keyname) and we want
            # the bucket to be the root dir.
            src_rootdir = _get_s3_root(source_location, parameters['dir_op'])
        else:
            src_rootdir = _get_local_root(
                parameters['src'], parameters['dir_op']
            )

        destination_location = parameters['dest']
        if destination_location.startswith('s3://'):
            dst_rootdir = _get_s3_root(
                parameters['dest'], parameters['dir_op']
            )
        else:
            dst_rootdir = _get_local_root(
                parameters['dest'], parameters['dir_op']
            )

        return Filter(real_filters, src_rootdir, dst_rootdir)
    else:
        return Filter({}, None, None)


def _get_s3_root(source_location, dir_op):
    # Obtain the bucket and the key.
    bucket, key = split_s3_bucket_key(source_location)
    if not dir_op and not key.endswith('/'):
        # If we are not performing an operation on a directory and the key
        # is of the form: ``prefix/key``. We only want ``prefix`` included in
        # the the s3 root and not ``key``.
        key = '/'.join(key.split('/')[:-1])
    # Rejoin the bucket and key back together.
    s3_path = '/'.join([bucket, key])
    return s3_path


def _get_local_root(source_location, dir_op):
    if dir_op:
        rootdir = os.path.abspath(source_location)
    else:
        rootdir = os.path.abspath(os.path.dirname(source_location))
    return rootdir


def _literal_prefix(pattern):
    for i, ch in enumerate(pattern):
        if ch in '*?[':
            return pattern[:i]
    return pattern


def _pattern_can_match_under(pattern, target_with_sep):
    """Return True if some descendant path under ``target_with_sep``
    could match ``pattern``. False means no descendant can possibly
    match, so the caller may safely skip the directory. False is
    never returned when a match is actually possible.
    """
    lit = _literal_prefix(pattern)
    common = min(len(lit), len(target_with_sep))
    if lit[:common] != target_with_sep[:common]:
        return False
    if len(target_with_sep) <= len(lit):
        return True
    if lit == pattern:
        return False
    return True


def _pattern_matches_all_under(pattern, target_with_sep):
    """Return True only when every descendant path under
    ``target_with_sep`` is guaranteed to match ``pattern``. False
    means we cannot prove this — the caller must not assume a match.
    """
    lit = _literal_prefix(pattern)
    if not target_with_sep.startswith(lit):
        return False
    rest = pattern[len(lit):]
    return bool(rest) and all(c == '*' for c in rest)


class Filter:
    """
    This is a universal exclude/include filter.
    """

    def __init__(self, patterns, rootdir, dst_rootdir):
        """
        :var patterns: A list of patterns. A pattern consists of a list
            whose first member is a string 'exclude' or 'include'.
            The second member is the actual rule.
        :var rootdir: The root directory where the patterns are evaluated.
            This will generally be the directory of the source location.
        :var dst_rootdir: The destination root directory where the patterns are
            evaluated.  This is only useful when the --delete option is
            also specified.

        """
        self._original_patterns = patterns
        self.patterns = self._full_path_patterns(patterns, rootdir)
        self.dst_patterns = self._full_path_patterns(patterns, dst_rootdir)

    def _full_path_patterns(self, original_patterns, rootdir):
        # We need to transform the patterns into patterns that have
        # the root dir prefixed, so things like ``--exclude "*"``
        # will actually be ['exclude', '/path/to/root/*']
        full_patterns = []
        for pattern in original_patterns:
            full_patterns.append(
                (pattern[0], os.path.join(rootdir, pattern[1]))
            )
        return full_patterns

    def call(self, file_infos):
        """
        This function iterates over through the yielded file_info objects.  It
        determines the type of the file and applies pattern matching to
        determine if the rule applies.  While iterating though the patterns the
        file is assigned a boolean flag to determine if a file should be
        yielded on past the filer.  Anything identified by the exclude filter
        has its flag set to false.  Anything identified by the include filter
        has its flag set to True.  All files begin with the flag set to true.
        Rules listed at the end will overwrite flags thrown by rules listed
        before it.
        """
        for file_info in file_infos:
            file_path = file_info.src
            file_status = (file_info, True)
            for pattern, dst_pattern in zip(self.patterns, self.dst_patterns):
                current_file_status = self._match_pattern(pattern, file_info)
                if current_file_status is not None:
                    file_status = current_file_status
                dst_current_file_status = self._match_pattern(
                    dst_pattern, file_info
                )
                if dst_current_file_status is not None:
                    file_status = dst_current_file_status
            LOG.debug(
                "=%s final filtered status, should_include: %s",
                file_path,
                file_status[1],
            )
            if file_status[1]:
                yield file_info

    def _match_pattern(self, pattern, file_info):
        file_status = None
        file_path = file_info.src
        pattern_type = pattern[0]
        if file_info.src_type == 'local':
            path_pattern = pattern[1].replace('/', os.sep)
        else:
            path_pattern = pattern[1].replace(os.sep, '/')
        is_match = fnmatch.fnmatch(file_path, path_pattern)
        if is_match and pattern_type == 'include':
            file_status = (file_info, True)
            LOG.debug("%s matched include filter: %s", file_path, path_pattern)
        elif is_match and pattern_type == 'exclude':
            file_status = (file_info, False)
            LOG.debug("%s matched exclude filter: %s", file_path, path_pattern)
        else:
            LOG.debug(
                "%s did not match %s filter: %s",
                file_path,
                pattern_type,
                path_pattern,
            )
        return file_status

    def can_skip_directory(
        self, dir_path, src_type='local', use_dst_patterns=False
    ):
        """Return True only when the filter chain cannot include any
        descendant of ``dir_path``, so the walker may skip listing it.
        False means the directory must be traversed normally — either
        a descendant could match, or we cannot prove otherwise.

        ``use_dst_patterns``: when True, evaluate against ``dst_patterns``
        (rooted at the destination) instead of ``patterns`` (rooted at the
        source). The reverse-direction file generator used during
        ``s3 sync s3://bucket/ ./local`` walks the local destination, so
        it must consult the destination-rooted patterns to prune correctly.
        """
        patterns = self.dst_patterns if use_dst_patterns else self.patterns
        if not patterns:
            return False
        sep = os.sep if src_type == 'local' else '/'
        target = dir_path.rstrip(sep) + sep
        if src_type == 'local':
            # ``fnmatch.fnmatch`` (used by ``_match_pattern``) normalizes
            # case via ``os.path.normcase`` on Windows, so this prefix
            # comparison must do the same — otherwise a case-different
            # subtree on Windows would be incorrectly pruned. On POSIX
            # ``normcase`` is identity.
            target = os.path.normcase(target)
        normalized = []
        for pattern_type, pat in patterns:
            if src_type == 'local':
                pat = os.path.normcase(pat.replace('/', os.sep))
            else:
                pat = pat.replace(os.sep, '/')
            normalized.append((pattern_type, pat))
        for pattern_type, pat in normalized:
            if pattern_type == 'include' and _pattern_can_match_under(
                pat, target
            ):
                return False
        for pattern_type, pat in normalized:
            if pattern_type == 'exclude' and _pattern_matches_all_under(
                pat, target
            ):
                return True
        return False
