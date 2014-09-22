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

from mock import Mock, patch

from awscli.customizations.s3.filegenerator import FileStat
from awscli.customizations.s3.syncstrategy import BaseSyncStrategy, \
    DefaultSyncStrategy, SizeOnlySyncStrategy, ExactTimestampsSyncStrategy, \
    register_sync_strategy, register_sync_strategies
from awscli.testutils import unittest


class TestRegisterSyncStrategies(unittest.TestCase):
    def test_register_sync_strategy(self):
        """
        Ensure that registering a single strategy class works as expected
        """
        session = Mock()
        strategy_cls = Mock()
        strategy_object = Mock()
        strategy_cls.return_value = strategy_object
        register_sync_strategy(session, strategy_cls)
        # Ensure sync strategy class is instantiated
        strategy_cls.assert_called_with()
        # Ensure the sync strategy's ``register_strategy`` method is
        # called correctly.
        strategy_object.register_strategy.assert_called_with(session)

    def test_register_sync_strategies(self):
        """
        Ensure that the registering all sync strategy classes works.
        """
        session = Mock()
        reg_cls = 'awscli.customizations.s3.syncstrategy.register_sync_strategy'
        with patch(reg_cls) as mock_register:
            register_sync_strategies([], session)
            # Ensure the ``SizeOnlySyncStrategy`` was registered.
            self.assertEqual(mock_register.call_args_list[0][0][0],
                             session)
            self.assertEqual(mock_register.call_args_list[0][0][1],
                             SizeOnlySyncStrategy)

            # Ensure the ``ExactTimestampsSyncStrategy`` was registered.
            self.assertEqual(mock_register.call_args_list[1][0][0],
                             session)
            self.assertEqual(mock_register.call_args_list[1][0][1],
                             ExactTimestampsSyncStrategy)


class TestBaseSyncStrategy(unittest.TestCase):
    def setUp(self):
        self.sync_strategy = BaseSyncStrategy()

    def test_register_strategy(self):
        """
        Ensures that the class registers all of the necessary handlers
        """
        session = Mock()
        self.sync_strategy.register_strategy(session)
        register_args = session.register.call_args_list
        self.assertEqual(register_args[0][0][0], 'initiate-building-arg-table')
        self.assertEqual(register_args[0][0][1],
                         self.sync_strategy._add_sync_argument)
        self.assertEqual(register_args[1][0][0], 'choosing-s3-sync-strategy')
        self.assertEqual(register_args[1][0][1],
                         self.sync_strategy._use_sync_strategy)

    def test_compare_same_name_files(self):
        """
        Ensure that this class cannot be directly used as the sync strategy.
        """
        with self.assertRaises(NotImplementedError):
            self.sync_strategy.compare_same_name_files(None, None)

    def test_arg_name(self):
        """
        Ensure that the ``arg_name`` property works as expected.
        """
        self.assertEqual(self.sync_strategy.arg_name, None)
        self.sync_strategy.ARGUMENT = {'name': 'my-sync-strategy'}
        self.assertEqual(self.sync_strategy.arg_name, 'my-sync-strategy')

    def test_arg_dest(self):
        """
        Ensure that the ``arg_dest`` property works as expected.
        """
        self.assertEqual(self.sync_strategy.arg_dest, None)
        self.sync_strategy.ARGUMENT = {'dest': 'my-dest'}
        self.assertEqual(self.sync_strategy.arg_dest, 'my-dest')

    def test_add_sync_argument(self):
        """
        Ensures the sync argument is properly added to the
        the command's ``arg_table``.
        """
        arg_table = [{'name': 'original_argument'}]
        self.sync_strategy.ARGUMENT = {'name': 'sync_argument'}
        self.sync_strategy._add_sync_argument(arg_table, None)
        self.assertEqual(arg_table,
                         [{'name': 'original_argument'},
                          {'name': 'sync_argument'}])

    def test_use_sync_strategy(self):
        """
        Ensures how sync strategies are chosen works as expected.
        """
        # Test if the sync strategy has no argument
        self.assertEqual(self.sync_strategy._use_sync_strategy({}), None)

        # Test if sync strategy argument has ``name`` but no ``dest`` and
        # was called.
        self.sync_strategy.ARGUMENT = {'name': 'my-sync-strategy'}
        params = {'my_sync_strategy': True}
        self.assertEqual(self.sync_strategy._use_sync_strategy(params),
                         self.sync_strategy)

        # Test if sync strategy argument has ``name`` but no ``dest`` and
        # was not called.
        self.sync_strategy.ARGUMENT = {'name': 'my-sync-strategy'}
        params = {'my_sync_strategy': False}
        self.assertEqual(self.sync_strategy._use_sync_strategy(params), None)

        # Test if sync strategy argument has ``name`` and
        # for whatever reason is not in ``params``.
        self.sync_strategy.ARGUMENT = {'name': 'my-sync-strategy'}
        self.assertEqual(self.sync_strategy._use_sync_strategy({}), None)

        # Test if sync strategy argument has ``name`` and ``dest`` and
        # was called.
        self.sync_strategy.ARGUMENT = {'name': 'my-sync-strategy',
                                       'dest': 'my-dest'}
        params = {'my-dest': True}
        self.assertEqual(self.sync_strategy._use_sync_strategy(params),
                         self.sync_strategy)

        # Test if sync strategy argument has ``name`` and ``dest`` and
        # was not called.
        self.sync_strategy.ARGUMENT = {'name': 'my-sync-strategy',
                                       'dest': 'my-dest'}
        params = {'my-dest': False}
        self.assertEqual(self.sync_strategy._use_sync_strategy(params), None)


class TestDefaultSyncStrategy(unittest.TestCase):
    def setUp(self):
        self.sync_strategy = DefaultSyncStrategy()

    def test_compare_size(self):
        """
        Confirms compare size works.
        """
        time = datetime.datetime.now()
        src_file = FileStat(src='', dest='',
                            compare_key='comparator_test.py', size=11,
                            last_update=time, src_type='local',
                            dest_type='s3', operation_name='upload')
        dest_file = FileStat(src='', dest='',
                             compare_key='comparator_test.py', size=10,
                             last_update=time, src_type='s3',
                             dest_type='local', operation_name='')
        should_sync = self.sync_strategy.compare_same_name_files(
            src_file, dest_file)
        self.assertTrue(should_sync)

    def test_compare_lastmod_upload(self):
        """
        Confirms compare time works for uploads.
        """
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
        should_sync = self.sync_strategy.compare_same_name_files(
            src_file, dest_file)
        self.assertTrue(should_sync)

    def test_compare_lastmod_copy(self):
        """
        Confirms compare time works for copies.
        """
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
        should_sync = self.sync_strategy.compare_same_name_files(
            src_file, dest_file)
        self.assertTrue(should_sync)

    def test_compare_lastmod_download(self):
        """
        Confirms compare time works for downloads.
        """
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

        should_sync = self.sync_strategy.compare_same_name_files(
            src_file, dest_file)
        self.assertTrue(should_sync)

        # If the source is newer than the destination do not download.
        src_file = FileStat(src='', dest='',
                            compare_key='comparator_test.py', size=10,
                            last_update=future_time, src_type='s3',
                            dest_type='local', operation_name='download')
        dest_file = FileStat(src='', dest='',
                             compare_key='comparator_test.py', size=10,
                             last_update=time, src_type='local',
                             dest_type='s3', operation_name='')

        should_sync = self.sync_strategy.compare_same_name_files(
            src_file, dest_file)
        self.assertFalse(should_sync)


class TestSizeOnlySyncStrategy(unittest.TestCase):
    def setUp(self):
        self.sync_strategy = SizeOnlySyncStrategy()

    def test_compare_size_only(self):
        """
        Confirm that files are synced when size differs.
        """
        time_src = datetime.datetime.now()
        time_dst = time_src + datetime.timedelta(days=1)

        src_file = FileStat(src='', dest='',
                            compare_key='test.py', size=11,
                            last_update=time_src, src_type='local',
                            dest_type='s3', operation_name='upload')

        dst_file = FileStat(src='', dest='',
                            compare_key='test.py', size=10,
                            last_update=time_dst, src_type='s3',
                            dest_type='local', operation_name='')

        should_sync = self.sync_strategy.compare_same_name_files(
            src_file, dst_file)
        self.assertTrue(should_sync)

    def test_compare_size_only_different_update_times(self):
        """
        Confirm that files with the same size but different update times
        are not synced.
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

        should_sync = self.sync_strategy.compare_same_name_files(
            src_file, dst_file)
        self.assertFalse(should_sync)


class TestExactTimestampsSyncStrategy(unittest.TestCase):
    def setUp(self):
        self.sync_strategy = ExactTimestampsSyncStrategy()

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

        should_sync = self.sync_strategy.compare_same_name_files(
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

        should_sync = self.sync_strategy.compare_same_name_files(
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

        should_sync = self.sync_strategy.compare_same_name_files(
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

        should_sync = self.sync_strategy.compare_same_name_files(
            src_file, dst_file)
        self.assertTrue(should_sync)


if __name__ == "__main__":
    unittest.main()
