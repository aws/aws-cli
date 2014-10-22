# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import datetime

from awscli.customizations.s3.filegenerator import FileStat
from awscli.customizations.s3.syncstrategy.exacttimestamps import \
    ExactTimestampsSync

from awscli.testutils import unittest


class TestExactTimestampsSync(unittest.TestCase):
    def setUp(self):
        self.sync_strategy = ExactTimestampsSync()

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

        should_sync = self.sync_strategy.determine_should_sync(
            src_file, dst_file)
        self.assertTrue(should_sync)

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

        should_sync = self.sync_strategy.determine_should_sync(
            src_file, dst_file)
        self.assertTrue(should_sync)

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

        should_sync = self.sync_strategy.determine_should_sync(
            src_file, dst_file)
        self.assertFalse(should_sync)

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

        should_sync = self.sync_strategy.determine_should_sync(
            src_file, dst_file)
        self.assertTrue(should_sync)

    def test_compare_exact_timestamps_diff_age_not_download(self):
        """
        Confirm that same sized files are synced when the timestamps differ,
        the type of operation is not a download, and ``exact_timestamps``
        is set.
        """
        time_src = datetime.datetime.now()
        time_dst = time_src - datetime.timedelta(days=1)

        src_file = FileStat(src='', dest='',
                            compare_key='test.py', size=10,
                            last_update=time_src, src_type='s3',
                            dest_type='local', operation_name='upload')

        dst_file = FileStat(src='', dest='',
                            compare_key='test.py', size=10,
                            last_update=time_dst, src_type='local',
                            dest_type='s3', operation_name='')

        should_sync = self.sync_strategy.determine_should_sync(
            src_file, dst_file)
        self.assertTrue(should_sync)


if __name__ == "__main__":
    unittest.main()
