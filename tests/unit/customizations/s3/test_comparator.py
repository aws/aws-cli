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
import datetime
import unittest

from awscli.customizations.s3.comparator import Comparator
from awscli.customizations.s3.filegenerator import FileStat


class ComparatorTest(unittest.TestCase):
    def setUp(self):
        self.comparator = Comparator({'delete': True})

    def test_compare_key_equal(self):
        """
        Confirms checking compare key works.
        """
        src_files = []
        dest_files = []
        ref_list = []
        result_list = []
        time = datetime.datetime.now()
        src_file = FileStat(src='', dest='',
                            compare_key='comparator_test.py', size=10,
                            last_update=time, src_type='local',
                            dest_type='s3', operation_name='upload')
        dest_file = FileStat(src='', dest='',
                             compare_key='comparator_test.py', size=10,
                             last_update=time, src_type='s3',
                             dest_type='local', operation_name='')
        src_files.append(src_file)
        dest_files.append(dest_file)
        files = self.comparator.call(iter(src_files), iter(dest_files))
        for filename in files:
            result_list.append(filename)
        self.assertEqual(result_list, ref_list)

    def test_compare_size(self):
        """
        Confirms compare size works.
        """
        src_files = []
        dest_files = []
        ref_list = []
        result_list = []
        time = datetime.datetime.now()
        src_file = FileStat(src='', dest='',
                            compare_key='comparator_test.py', size=11,
                            last_update=time, src_type='local',
                            dest_type='s3', operation_name='upload')
        dest_file = FileStat(src='', dest='',
                             compare_key='comparator_test.py', size=10,
                             last_update=time, src_type='s3',
                             dest_type='local', operation_name='')
        src_files.append(src_file)
        dest_files.append(dest_file)
        files = self.comparator.call(iter(src_files), iter(dest_files))
        ref_list.append(src_file)
        for filename in files:
            result_list.append(filename)
        self.assertEqual(result_list, ref_list)

    def test_compare_lastmod_upload(self):
        """
        Confirms compare time works for uploads.
        """
        src_files = []
        dest_files = []
        ref_list = []
        result_list = []
        time = datetime.datetime.now()
        future_time = time + datetime.timedelta(0, 3)
        src_file = FileStat(src='', dest='',
                            compare_key='comparator_test.py', size=10,
                            last_update=future_time, src_type='local',
                            dest_type='s3', operation_name='upload')
        dest_file = FileStat(src='', dest='',
                             compare_key='comparator_test.py', size=10,
                             last_update=time, src_type='s3',
                             dest_type='local', operation_name='')
        src_files.append(src_file)
        dest_files.append(dest_file)
        files = self.comparator.call(iter(src_files), iter(dest_files))
        ref_list.append(src_file)
        for filename in files:
            result_list.append(filename)
        self.assertEqual(result_list, ref_list)

    def test_compare_lastmod_copy(self):
        """
        Confirms compare time works for copies
        """
        src_files = []
        dest_files = []
        ref_list = []
        result_list = []
        time = datetime.datetime.now()
        future_time = time + datetime.timedelta(0, 3)
        src_file = FileStat(src='', dest='',
                            compare_key='comparator_test.py', size=10,
                            last_update=future_time, src_type='s3',
                            dest_type='s3', operation_name='copy')
        dest_file = FileStat(src='', dest='',
                             compare_key='comparator_test.py', size=10,
                             last_update=time, src_type='s3',
                             dest_type='s3', operation_name='')
        src_files.append(src_file)
        dest_files.append(dest_file)
        files = self.comparator.call(iter(src_files), iter(dest_files))
        ref_list.append(src_file)
        for filename in files:
            result_list.append(filename)
        self.assertEqual(result_list, ref_list)

    def test_compare_lastmod_download(self):
        """
        Confirms compare time works for downloads.
        """
        src_files = []
        dest_files = []
        ref_list = []
        result_list = []
        time = datetime.datetime.now()
        future_time = time + datetime.timedelta(0, 3)
        src_file = FileStat(src='', dest='',
                            compare_key='comparator_test.py', size=10,
                            last_update=time, src_type='s3',
                            dest_type='local', operation_name='download')
        dest_file = FileStat(src='', dest='',
                             compare_key='comparator_test.py', size=10,
                             last_update=future_time, src_type='local',
                             dest_type='s3', operation_name='')
        src_files.append(src_file)
        dest_files.append(dest_file)
        files = self.comparator.call(iter(src_files), iter(dest_files))
        ref_list.append(src_file)
        for filename in files:
            result_list.append(filename)
        self.assertEqual(result_list, ref_list)

        # If the source is newer than the destination do not download.
        src_file = FileStat(src='', dest='',
                            compare_key='comparator_test.py', size=10,
                            last_update=future_time, src_type='s3',
                            dest_type='local', operation_name='download')
        dest_file = FileStat(src='', dest='',
                             compare_key='comparator_test.py', size=10,
                             last_update=time, src_type='local',
                             dest_type='s3', operation_name='')
        src_files = []
        dest_files = []
        src_files.append(src_file)
        dest_files.append(dest_file)
        files = self.comparator.call(iter(src_files), iter(dest_files))
        result_list = []
        for filename in files:
            result_list.append(filename)
        self.assertEqual(result_list, [])

    def test_compare_key_less(self):
        """
        Confirm the appropriate action is taken when the soruce compare key
        is less than the destination compare key.
        """
        src_files = []
        dest_files = []
        ref_list = []
        result_list = []
        time = datetime.datetime.now()
        src_file = FileStat(src='', dest='',
                            compare_key='bomparator_test.py', size=10,
                            last_update=time, src_type='local',
                            dest_type='s3', operation_name='upload')
        dest_file = FileStat(src='', dest='',
                             compare_key='comparator_test.py', size=10,
                             last_update=time, src_type='s3',
                             dest_type='local', operation_name='')
        src_files.append(src_file)
        dest_files.append(dest_file)
        dest_file.operation = 'delete'
        ref_list.append(src_file)
        ref_list.append(dest_file)
        files = self.comparator.call(iter(src_files), iter(dest_files))
        for filename in files:
            result_list.append(filename)
        self.assertEqual(result_list, ref_list)

    def test_compare_key_greater(self):
        """
        Confirm the appropriate action is taken when the soruce compare key
        is greater than the destination compare key.
        """
        src_files = []
        dest_files = []
        ref_list = []
        result_list = []
        time = datetime.datetime.now()
        src_file = FileStat(src='', dest='',
                            compare_key='domparator_test.py', size=10,
                            last_update=time, src_type='local',
                            dest_type='s3', operation_name='upload')
        dest_file = FileStat(src='', dest='',
                             compare_key='comparator_test.py', size=10,
                             last_update=time, src_type='s3',
                             dest_type='local', operation_name='')
        src_files.append(src_file)
        dest_files.append(dest_file)
        src_file.operation = 'upload'
        dest_file.operation = 'delete'
        ref_list.append(dest_file)
        ref_list.append(src_file)
        files = self.comparator.call(iter(src_files), iter(dest_files))
        for filename in files:
            result_list.append(filename)
        self.assertEqual(result_list, ref_list)

    def test_empty_src(self):
        """
        Confirm the appropriate action is taken when there are no more source
        files to take.
        """
        src_files = []
        dest_files = []
        ref_list = []
        result_list = []
        time = datetime.datetime.now()
        dest_file = FileStat(src='', dest='',
                             compare_key='comparator_test.py', size=10,
                             last_update=time, src_type='s3',
                             dest_type='local', operation_name='')
        dest_files.append(dest_file)
        dest_file.operation = 'delete'
        ref_list.append(dest_file)
        files = self.comparator.call(iter(src_files), iter(dest_files))
        for filename in files:
            result_list.append(filename)
        self.assertEqual(result_list, ref_list)

    def test_empty_dest(self):
        """
        Confirm the appropriate action is taken when there are no more dest
        files to take.
        """
        src_files = []
        dest_files = []
        ref_list = []
        result_list = []
        time = datetime.datetime.now()
        src_file = FileStat(src='', dest='',
                            compare_key='domparator_test.py', size=10,
                            last_update=time, src_type='local',
                            dest_type='s3', operation_name='upload')
        src_files.append(src_file)
        ref_list.append(src_file)
        files = self.comparator.call(iter(src_files), iter(dest_files))
        for filename in files:
            result_list.append(filename)
        self.assertEqual(result_list, ref_list)

    def test_empty_src_dest(self):
        """
        Confirm the appropriate action is taken when there are no more
        files to take for both source and destination.
        """
        src_files = []
        dest_files = []
        ref_list = []
        result_list = []
        files = self.comparator.call(iter(src_files), iter(dest_files))
        for filename in files:
            result_list.append(filename)
        self.assertEqual(result_list, ref_list)


class ComparatorSizeOnlyTest(unittest.TestCase):
    def setUp(self):
        self.comparator = Comparator({'delete': True, 'size_only': True})

    def test_compare_size_only_dest_older_than_src(self):
        """
        Confirm that files with the same size but different update times are not
        synced when `size_only` is set.
        """
        time_src = datetime.datetime.now()
        time_dst = time_src + datetime.timedelta(days=1)

        src_file = FileStat(src='', dest='',
                            compare_key='test.py', size=10,
                            last_update=time_src, src_type='local',
                            dest_type='s3', operation_name='upload')

        dst_file = FileStat(src='', dest='',
                            compare_key='test.py', size=10,
                            last_update=time_dst, src_type='s3',
                            dest_type='local', operation_name='')

        files = self.comparator.call(iter([src_file]), iter([dst_file]))
        self.assertEqual(sum(1 for _ in files), 0)

    def test_compare_size_only_src_older_than_dest(self):
        """
        Confirm that files with the same size but different update times are not
        synced when `size_only` is set.
        """
        time_dst = datetime.datetime.now()
        time_src = time_dst + datetime.timedelta(days=1)

        src_file = FileStat(src='', dest='',
                            compare_key='test.py', size=10,
                            last_update=time_src, src_type='local',
                            dest_type='s3', operation_name='upload')

        dst_file = FileStat(src='', dest='',
                            compare_key='test.py', size=10,
                            last_update=time_dst, src_type='s3',
                            dest_type='local', operation_name='')

        files = self.comparator.call(iter([src_file]), iter([dst_file]))
        self.assertEqual(sum(1 for _ in files), 0)


class ComparatorExactTimestampsTest(unittest.TestCase):
    def setUp(self):
        self.comparator = Comparator({'exact_timestamps': True})

    def test_compare_exact_timestamps_dest_older(self):
        """
        Confirm that same-sized files are synced when
        the destination is older than the source and
        `exact_timestamps` is set.
        """
        time_src = datetime.datetime.now()
        time_dst = time_src - datetime.timedelta(days=1)

        src_file = FileStat(src='', dest='',
                            compare_key='test.py', size=10,
                            last_update=time_src, src_type='s3',
                            dest_type='local', operation_name='download')

        dst_file = FileStat(src='', dest='',
                            compare_key='test.py', size=10,
                            last_update=time_dst, src_type='local',
                            dest_type='s3', operation_name='')

        files = self.comparator.call(iter([src_file]), iter([dst_file]))
        self.assertEqual(sum(1 for _ in files), 1)

    def test_compare_exact_timestamps_src_older(self):
        """
        Confirm that same-sized files are synced when
        the source is older than the destination and
        `exact_timestamps` is set.
        """
        time_src = datetime.datetime.now() - datetime.timedelta(days=1)
        time_dst = datetime.datetime.now()

        src_file = FileStat(src='', dest='',
                            compare_key='test.py', size=10,
                            last_update=time_src, src_type='s3',
                            dest_type='local', operation_name='download')

        dst_file = FileStat(src='', dest='',
                            compare_key='test.py', size=10,
                            last_update=time_dst, src_type='local',
                            dest_type='s3', operation_name='')

        files = self.comparator.call(iter([src_file]), iter([dst_file]))
        self.assertEqual(sum(1 for _ in files), 1)

    def test_compare_exact_timestamps_same_age_same_size(self):
        """
        Confirm that same-sized files are not synced when
        the source and destination are the same age and
        `exact_timestamps` is set.
        """
        time_both = datetime.datetime.now()

        src_file = FileStat(src='', dest='',
                            compare_key='test.py', size=10,
                            last_update=time_both, src_type='s3',
                            dest_type='local', operation_name='download')

        dst_file = FileStat(src='', dest='',
                            compare_key='test.py', size=10,
                            last_update=time_both, src_type='local',
                            dest_type='s3', operation_name='')

        files = self.comparator.call(iter([src_file]), iter([dst_file]))
        self.assertEqual(sum(1 for _ in files), 0)

    def test_compare_exact_timestamps_same_age_diff_size(self):
        """
        Confirm that files of differing sizes are synced when
        the source and destination are the same age and
        `exact_timestamps` is set.
        """
        time_both = datetime.datetime.now()

        src_file = FileStat(src='', dest='',
                            compare_key='test.py', size=20,
                            last_update=time_both, src_type='s3',
                            dest_type='local', operation_name='download')

        dst_file = FileStat(src='', dest='',
                            compare_key='test.py', size=10,
                            last_update=time_both, src_type='local',
                            dest_type='s3', operation_name='')

        files = self.comparator.call(iter([src_file]), iter([dst_file]))
        self.assertEqual(sum(1 for _ in files), 1)


if __name__ == "__main__":
    unittest.main()
