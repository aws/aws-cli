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

from mock import Mock

from awscli.customizations.s3.comparator import Comparator
from awscli.customizations.s3.filegenerator import FileStat


class ComparatorTest(unittest.TestCase):
    def setUp(self):
        self.sync_strategy = Mock()
        self.not_at_src_sync_strategy = Mock()
        self.not_at_dest_sync_strategy = Mock()
        self.comparator = Comparator(self.sync_strategy,
                                     self.not_at_dest_sync_strategy,
                                     self.not_at_src_sync_strategy)

    def test_compare_key_equal_should_not_sync(self):
        """
        Confirm the appropriate action is taken when the soruce compare key
        is equal to the destination compare key.
        """
        # Try when the sync strategy says not to sync the file.
        self.sync_strategy.determine_should_sync.return_value = False

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

        # Try when the sync strategy says to sync the file.
        self.sync_strategy.determine_should_sync.return_value = True

        ref_list = []
        result_list = []
        files = self.comparator.call(iter(src_files), iter(dest_files))
        ref_list.append(src_file)
        for filename in files:
            result_list.append(filename)
        self.assertEqual(result_list, ref_list)

    def test_compare_key_less(self):
        """
        Confirm the appropriate action is taken when the soruce compare key
        is less than the destination compare key.
        """
        self.not_at_src_sync_strategy.determine_should_sync.return_value = False

        # Try when the sync strategy says to sync the file.
        self.not_at_dest_sync_strategy.determine_should_sync.return_value = True

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
        ref_list.append(src_file)
        files = self.comparator.call(iter(src_files), iter(dest_files))
        for filename in files:
            result_list.append(filename)
        self.assertEqual(result_list, ref_list)

        # Now try when the sync strategy says not to sync the file.
        self.not_at_dest_sync_strategy.determine_should_sync.return_value = False
        result_list = []
        ref_list = []
        files = self.comparator.call(iter(src_files), iter(dest_files))
        for filename in files:
            result_list.append(filename)
        self.assertEqual(result_list, ref_list)


    def test_compare_key_greater(self):
        """
        Confirm the appropriate action is taken when the soruce compare key
        is greater than the destination compare key.
        """
        self.not_at_dest_sync_strategy.determine_should_sync.return_value = False

        # Try when the sync strategy says to sync the file.
        self.not_at_src_sync_strategy.determine_should_sync.return_value = True
        
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
        ref_list.append(dest_file)
        files = self.comparator.call(iter(src_files), iter(dest_files))
        for filename in files:
            result_list.append(filename)
        self.assertEqual(result_list, ref_list)

        # Now try when the sync strategy says not to sync the file.
        self.not_at_src_sync_strategy.determine_should_sync.return_value = False
        result_list = []
        ref_list = []
        files = self.comparator.call(iter(src_files), iter(dest_files))
        for filename in files:
            result_list.append(filename)
        self.assertEqual(result_list, ref_list)


    def test_empty_src(self):
        """
        Confirm the appropriate action is taken when there are no more source
        files to take.
        """
        # Try when the sync strategy says to sync the file.
        self.not_at_src_sync_strategy.determine_should_sync.return_value = True

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
        ref_list.append(dest_file)
        files = self.comparator.call(iter(src_files), iter(dest_files))
        for filename in files:
            result_list.append(filename)
        self.assertEqual(result_list, ref_list)

        # Now try when the sync strategy says not to sync the file.
        self.not_at_src_sync_strategy.determine_should_sync.return_value = False
        result_list = []
        ref_list = []
        files = self.comparator.call(iter(src_files), iter(dest_files))
        for filename in files:
            result_list.append(filename)
        self.assertEqual(result_list, ref_list)

    def test_empty_dest(self):
        """
        Confirm the appropriate action is taken when there are no more dest
        files to take.
        """
        # Try when the sync strategy says to sync the file.
        self.not_at_dest_sync_strategy.determine_should_sync.return_value = True

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

        # Now try when the sync strategy says not to sync the file.
        self.not_at_dest_sync_strategy.determine_should_sync.return_value = False
        result_list = []
        ref_list = []
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


if __name__ == "__main__":
    unittest.main()
