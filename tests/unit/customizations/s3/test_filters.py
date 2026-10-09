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
import platform

from awscli.customizations.s3.filegenerator import FileStat
from awscli.customizations.s3.filters import (
    Filter,
    _literal_prefix,
    _pattern_can_match_under,
    _pattern_matches_all_under,
    create_filter,
)
from awscli.testutils import mock, unittest


def platform_path(filepath):
    # Convert posix platforms to windows platforms.
    if platform.system().lower() == 'windows':
        filepath = filepath.replace('/', os.sep)
        filepath = 'C:' + filepath
    return filepath


class FiltersTest(unittest.TestCase):
    def setUp(self):
        self.local_files = [
            self.file_stat('test.txt'),
            self.file_stat('test.jpg'),
            self.file_stat(os.path.join('directory', 'test.jpg')),
        ]
        self.s3_files = [
            self.file_stat('bucket/test.txt', src_type='s3'),
            self.file_stat('bucket/test.jpg', src_type='s3'),
            self.file_stat('bucket/key/test.jpg', src_type='s3'),
        ]

    def file_stat(self, filename, src_type='local'):
        if src_type == 'local':
            filename = os.path.abspath(filename)
            dest_type = 's3'
        else:
            dest_type = 'local'
        return FileStat(
            src=filename,
            dest='',
            compare_key='',
            size=10,
            last_update=0,
            src_type=src_type,
            dest_type=dest_type,
            operation_name='',
        )

    def create_filter(
        self, filters=None, root=None, dst_root=None, parameters=None
    ):
        if root is None:
            root = os.getcwd()
        if filters is None:
            filters = {}
        if dst_root is None:
            dst_root = 'bucket'
        if parameters is not None:
            return create_filter(parameters)
        return Filter(filters, root, dst_root)

    def test_no_filter(self):
        exc_inc_filter = self.create_filter()
        matched_files = list(exc_inc_filter.call(self.local_files))
        self.assertEqual(matched_files, self.local_files)

        matched_files2 = list(exc_inc_filter.call(self.s3_files))
        self.assertEqual(matched_files2, self.s3_files)

    def test_include(self):
        patterns = [['include', '*.txt']]
        include_filter = self.create_filter([['include', '*.txt']])
        matched_files = list(include_filter.call(self.local_files))
        self.assertEqual(matched_files, self.local_files)

        matched_files2 = list(include_filter.call(self.s3_files))
        self.assertEqual(matched_files2, self.s3_files)

    def test_exclude(self):
        exclude_filter = self.create_filter([['exclude', '*']])
        matched_files = list(exclude_filter.call(self.local_files))
        self.assertEqual(matched_files, [])

        matched_files = list(exclude_filter.call(self.s3_files))
        self.assertEqual(matched_files, [])

    def test_exclude_with_dst_root(self):
        exclude_filter = self.create_filter(
            [['exclude', '*.txt']], dst_root='bucket'
        )
        matched_files = list(exclude_filter.call(self.local_files))
        b = os.path.basename
        self.assertNotIn('test.txt', [b(f.src) for f in matched_files])
        # Same filter should match the dst files.
        matched_files = list(exclude_filter.call(self.s3_files))
        self.assertNotIn('test.txt', [b(f.src) for f in matched_files])

    def test_exclude_include(self):
        patterns = [['exclude', '*'], ['include', '*.txt']]
        exclude_include_filter = self.create_filter(patterns)
        matched_files = list(exclude_include_filter.call(self.local_files))
        self.assertEqual(matched_files, [self.local_files[0]])

        matched_files = list(exclude_include_filter.call(self.s3_files))
        self.assertEqual(matched_files, [self.s3_files[0]])

    def test_include_exclude(self):
        patterns = [['include', '*.txt'], ['exclude', '*']]
        exclude_all_filter = self.create_filter(patterns)
        matched_files = list(exclude_all_filter.call(self.local_files))
        self.assertEqual(matched_files, [])

        matched_files = list(exclude_all_filter.call(self.s3_files))
        self.assertEqual(matched_files, [])

    def test_prefix_filtering_consistent(self):
        # The same filter should work for both local and remote files.
        # So if I have a directory with 2 files:
        local_files = [
            self.file_stat('test1.txt'),
            self.file_stat('nottest1.txt'),
        ]
        # And the same 2 files remote (note that the way FileStat objects
        # are constructed, we'll have the bucket name but no leading '/'
        # character):
        remote_files = [
            self.file_stat('bucket/test1.txt', src_type='s3'),
            self.file_stat('bucket/nottest1.txt', src_type='s3'),
        ]
        # If I apply the filter to the local to the local files.
        exclude_filter = self.create_filter([['exclude', 't*']])
        filtered_files = list(exclude_filter.call(local_files))
        self.assertEqual(len(filtered_files), 1)
        self.assertEqual(
            os.path.basename(filtered_files[0].src), 'nottest1.txt'
        )

        # I should get the same result if I apply the same filter to s3
        # objects.
        exclude_filter = self.create_filter([['exclude', 't*']], root='bucket')
        same_filtered_files = list(exclude_filter.call(remote_files))
        self.assertEqual(len(same_filtered_files), 1)
        self.assertEqual(
            os.path.basename(same_filtered_files[0].src), 'nottest1.txt'
        )

    def test_bucket_exclude_with_prefix(self):
        s3_files = [
            self.file_stat('bucket/dir1/key1.txt', src_type='s3'),
            self.file_stat('bucket/dir1/key2.txt', src_type='s3'),
            self.file_stat('bucket/dir1/notkey3.txt', src_type='s3'),
        ]
        filtered_files = list(
            self.create_filter([['exclude', 'dir1/*']], root='bucket').call(
                s3_files
            )
        )
        self.assertEqual(filtered_files, [])

        key_files = list(
            self.create_filter([['exclude', 'dir1/key*']], root='bucket').call(
                s3_files
            )
        )
        self.assertEqual(len(key_files), 1)
        self.assertEqual(key_files[0].src, 'bucket/dir1/notkey3.txt')

    def test_root_dir(self):
        p = platform_path
        local_files = [self.file_stat(p('/foo/bar/baz.txt'), src_type='local')]
        local_filter = self.create_filter(
            [['exclude', 'baz.txt']], root=p('/foo/bar/')
        )
        filtered = list(local_filter.call(local_files))
        self.assertEqual(filtered, [])

        # However, if we're at the root of /foo', then this filter won't match.
        local_filter = self.create_filter(
            [['exclude', 'baz.txt']], root=p('/foo/')
        )
        filtered = list(local_filter.call(local_files))
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].src, p('/foo/bar/baz.txt'))

    def test_create_root_s3_with_prefix(self):
        parameters = {
            'filters': [['--exclude', 'test.txt']],
            'dir_op': True,
            'src': 's3://bucket/prefix/',
            'dest': 'prefix',
        }
        s3_filter = self.create_filter(parameters=parameters)
        s3_files = [
            self.file_stat('bucket/prefix/test.txt', src_type='s3'),
            self.file_stat('bucket/prefix/test2.txt', src_type='s3'),
        ]
        filtered = list(s3_filter.call(s3_files))
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].src, 'bucket/prefix/test2.txt')

    def test_create_root_s3_no_dir_op(self):
        parameters = {
            'filters': [['--exclude', 'test.txt']],
            'dir_op': False,
            'src': 's3://bucket/test.txt',
            'dest': 'temp',
        }
        s3_filter = self.create_filter(parameters=parameters)
        s3_files = [
            self.file_stat('bucket/test.txt', src_type='s3'),
        ]
        filtered = list(s3_filter.call(s3_files))
        self.assertEqual(len(filtered), 0)

    def test_create_filter_s3_to_s3(self):
        source = 'bucket/'
        destination = 'bucket-2/'
        pattern = '*'
        parameters = {
            'filters': [['--exclude', pattern], ['--include', '*.jpg']],
            'dir_op': True,
            'src': 's3://' + source,
            'dest': 's3://' + destination,
        }
        s3_filter = self.create_filter(parameters=parameters)

        source_pattern = s3_filter.patterns[0][1]
        destination_pattern = s3_filter.dst_patterns[0][1]
        self.assertEqual(source_pattern, source + pattern)
        self.assertEqual(destination_pattern, destination + pattern)

        filtered = list(s3_filter.call(self.s3_files))
        self.assertEqual(len(filtered), 2)
        for filtered_file in filtered:
            self.assertFalse('.txt' in filtered_file.src)


class LiteralPrefixTest(unittest.TestCase):
    def test_no_metacharacters_returns_full_pattern(self):
        self.assertEqual(_literal_prefix('foo/bar.txt'), 'foo/bar.txt')

    def test_stops_at_star(self):
        self.assertEqual(_literal_prefix('foo/*'), 'foo/')

    def test_stops_at_question_mark(self):
        self.assertEqual(_literal_prefix('foo/?bar'), 'foo/')

    def test_stops_at_bracket(self):
        self.assertEqual(_literal_prefix('foo/[abc]'), 'foo/')

    def test_starts_with_metacharacter(self):
        self.assertEqual(_literal_prefix('*.py'), '')


class PatternCanMatchUnderTest(unittest.TestCase):
    def test_glob_metachar_pattern_can_match_anywhere(self):
        self.assertTrue(_pattern_can_match_under('*.py', 'root/foo/'))

    def test_pattern_with_target_as_prefix_can_match(self):
        self.assertTrue(
            _pattern_can_match_under('root/excluded/*', 'root/excluded/')
        )

    def test_pattern_more_specific_than_target_still_matches(self):
        self.assertTrue(
            _pattern_can_match_under(
                'root/excluded/included/*', 'root/excluded/'
            )
        )

    def test_diverging_literals_cannot_match(self):
        self.assertFalse(
            _pattern_can_match_under('root/excluded/*', 'root/other/')
        )

    def test_literal_only_pattern_shorter_than_target_cannot_match(self):
        self.assertFalse(
            _pattern_can_match_under('root/excluded', 'root/excluded/')
        )

    def test_literal_only_pattern_under_target_can_match(self):
        self.assertTrue(_pattern_can_match_under('root/foo', 'root/'))


class PatternMatchesAllUnderTest(unittest.TestCase):
    def test_star_only_matches_everything(self):
        self.assertTrue(_pattern_matches_all_under('*', 'anything/'))

    def test_target_star_matches_all_descendants(self):
        self.assertTrue(
            _pattern_matches_all_under('root/excluded/*', 'root/excluded/')
        )

    def test_double_star_treated_as_star(self):
        self.assertTrue(
            _pattern_matches_all_under('root/excluded/**', 'root/excluded/')
        )

    def test_higher_pattern_with_wildcard_covers_descendants(self):
        self.assertTrue(_pattern_matches_all_under('root/*', 'root/foo/'))

    def test_partial_pattern_does_not_cover(self):
        self.assertFalse(_pattern_matches_all_under('root/*.tmp', 'root/foo/'))

    def test_literal_only_pattern_does_not_cover(self):
        self.assertFalse(_pattern_matches_all_under('root/foo', 'root/foo/'))

    def test_diverging_literal_does_not_cover(self):
        self.assertFalse(
            _pattern_matches_all_under('root/excluded/*', 'root/other/')
        )


class CanSkipDirectoryTest(unittest.TestCase):
    """Verifies the §2.5 case table from the design proposal."""

    def _make_filter(self, raw_filters, rootdir=None):
        if rootdir is None:
            rootdir = platform_path('/root')
        normalized = [(action.lstrip('-'), pat) for action, pat in raw_filters]
        return Filter(normalized, rootdir, rootdir)

    def _path_under(self, *parts, rootdir=None):
        if rootdir is None:
            rootdir = platform_path('/root')
        return os.path.join(rootdir, *parts)

    def test_no_filters_never_skips(self):
        f = Filter({}, None, None)
        self.assertFalse(f.can_skip_directory(self._path_under('anything')))

    def test_simple_exclude_skips_matching_directory(self):
        f = self._make_filter([('--exclude', 'src/*')])
        self.assertTrue(f.can_skip_directory(self._path_under('src')))

    def test_exclude_star_skips_all_descendants(self):
        f = self._make_filter([('--exclude', '*')])
        self.assertTrue(f.can_skip_directory(self._path_under('foo', 'bar')))

    def test_kyleknap_regression_does_not_skip(self):
        """The case that killed PR aws/aws-cli#5425 must not regress."""
        f = self._make_filter(
            [('--exclude', '*'), ('--include', '*.py')]
        )
        self.assertFalse(f.can_skip_directory(self._path_under('foo')))
        self.assertFalse(
            f.can_skip_directory(self._path_under('foo', 'bar'))
        )

    def test_include_under_excluded_subtree_blocks_skip(self):
        f = self._make_filter(
            [
                ('--exclude', 'sub/*'),
                ('--include', 'sub/included/*'),
            ]
        )
        self.assertFalse(f.can_skip_directory(self._path_under('sub')))

    def test_sibling_subtree_under_exclude_is_skipped(self):
        f = self._make_filter(
            [
                ('--exclude', 'src/*'),
                ('--include', 'src/included/*'),
            ]
        )
        self.assertTrue(
            f.can_skip_directory(self._path_under('src', 'other'))
        )

    def test_included_subtree_traversed(self):
        f = self._make_filter(
            [
                ('--exclude', 'src/*'),
                ('--include', 'src/included/*'),
            ]
        )
        self.assertFalse(
            f.can_skip_directory(self._path_under('src', 'included'))
        )

    def test_partial_pattern_does_not_skip(self):
        f = self._make_filter([('--exclude', '*.tmp')])
        self.assertFalse(f.can_skip_directory(self._path_under('foo')))

    def test_literal_pattern_does_not_skip_descendants(self):
        f = self._make_filter([('--exclude', 'foo')])
        self.assertFalse(f.can_skip_directory(self._path_under('foo')))

    def test_s3_separator_exclude(self):
        rootdir = 'bucket'
        f = Filter([('exclude', 'logs/*')], rootdir, rootdir)
        self.assertTrue(
            f.can_skip_directory('bucket/logs', src_type='s3')
        )
        self.assertFalse(
            f.can_skip_directory('bucket/keep', src_type='s3')
        )

    def test_three_filter_alternating_stack(self):
        f = self._make_filter(
            [
                ('--exclude', 'excluded/*'),
                ('--include', 'excluded/included/*'),
                ('--exclude', 'included/excluded/*'),
            ]
        )
        self.assertFalse(
            f.can_skip_directory(self._path_under('excluded'))
        )
        self.assertTrue(
            f.can_skip_directory(
                self._path_under('included', 'excluded')
            )
        )
        self.assertFalse(
            f.can_skip_directory(self._path_under('included'))
        )

    def test_can_skip_directory_uses_dst_patterns_when_requested(self):
        """The reverse walker (sync s3://b/ ./dst) must be able to prune
        destination subtrees by consulting ``dst_patterns`` instead of
        the source-rooted ``patterns``.
        """
        src_root = platform_path('/src')
        dst_root = platform_path('/dst')
        f = Filter([('exclude', 'excluded/*')], src_root, dst_root)
        self.assertTrue(
            f.can_skip_directory(
                os.path.join(dst_root, 'excluded'),
                'local',
                use_dst_patterns=True,
            )
        )
        self.assertFalse(
            f.can_skip_directory(
                os.path.join(dst_root, 'excluded'),
                'local',
                use_dst_patterns=False,
            )
        )

    def test_can_skip_directory_dst_patterns_empty_returns_false(self):
        f = Filter({}, None, None)
        self.assertFalse(
            f.can_skip_directory(
                self._path_under('anything'),
                'local',
                use_dst_patterns=True,
            )
        )

    @mock.patch('awscli.customizations.s3.filters.os.path.normcase')
    def test_can_skip_directory_is_case_insensitive_on_windows(
        self, mock_normcase
    ):
        """fnmatch.fnmatch is case-insensitive on Windows via normcase.
        can_skip_directory must apply the same normalization or it will
        wrong-prune a case-different subtree that an include pattern
        actually covers.
        """
        mock_normcase.side_effect = (
            lambda p: p.lower().replace('/', os.sep)
        )
        f = self._make_filter(
            [
                ('--exclude', '*'),
                ('--include', 'SRC/important.txt'),
            ]
        )
        self.assertFalse(f.can_skip_directory(self._path_under('src')))


if __name__ == "__main__":
    unittest.main()
