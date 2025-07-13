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
from awscli.customizations.s3.syncstrategy.nooverwrite import NoOverwriteSync
from awscli.testutils import unittest


class TestNoOverwriteSync(unittest.TestCase):
    def setUp(self):
        self.sync_strategy = NoOverwriteSync()

    def test_file_does_not_exist_at_destination(self):
        """
        Confirms that files are synced when not present at destination.
        """
        time_src = datetime.datetime.now()

        src_file = FileStat(
            src='',
            dest='',
            compare_key='test.py',
            size=10,
            last_update=time_src,
            src_type='s3',
            dest_type='local',
            operation_name='download',
        )
        dest_file = None
        should_sync = self.sync_strategy.determine_should_sync(
            src_file, dest_file
        )
        self.assertTrue(should_sync)

    def test_file_exists_at_destination_with_different_key(self):
        """
        Confirms that files are synced when key differs.
        """
        time_src = datetime.datetime.now()

        src_file = FileStat(
            src='',
            dest='',
            compare_key='test.py',
            size=10,
            last_update=time_src,
            src_type='s3',
            dest_type='s3',
            operation_name='copy',
        )
        dest_file = FileStat(
            src='',
            dest='',
            compare_key='test1.py',
            size=100,
            last_update=time_src,
            src_type='s3',
            dest_type='s3',
            operation_name='',
        )
        should_sync = self.sync_strategy.determine_should_sync(
            src_file, dest_file
        )
        self.assertTrue(should_sync)

    def test_file_exists_at_destination_with_same_key(self):
        """
        Confirm that files with the same key are not synced.
        """
        time_src = datetime.datetime.now()

        src_file = FileStat(
            src='',
            dest='',
            compare_key='test.py',
            size=10,
            last_update=time_src,
            src_type='local',
            dest_type='s3',
            operation_name='upload',
        )
        dest_file = FileStat(
            src='',
            dest='',
            compare_key='test.py',
            size=100,
            last_update=time_src,
            src_type='local',
            dest_type='s3',
            operation_name='',
        )
        should_sync = self.sync_strategy.determine_should_sync(
            src_file, dest_file
        )
        self.assertFalse(should_sync)


if __name__ == "__main__":
    unittest.main()
