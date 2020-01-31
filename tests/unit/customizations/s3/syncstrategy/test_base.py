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
from awscli.customizations.s3.syncstrategy.base import BaseSync, \
    SizeAndLastModifiedSync, MissingFileSync, NeverSync
from awscli.testutils import unittest
from awscli.customizations.exceptions import ParamValidationError


class TestBaseSync(unittest.TestCase):
    def setUp(self):
        self.sync_strategy = BaseSync()

    def test_init(self):
        valid_sync_types = ['file_at_src_and_dest', 'file_not_at_dest',
                            'file_not_at_src']
        for sync_type in valid_sync_types:
            strategy = BaseSync(sync_type)
            self.assertEqual(strategy.sync_type, sync_type)

        # Check for invalid ``sync_type`` options.
        with self.assertRaises(ParamValidationError):
            BaseSync('wrong_sync_type')

    def test_register_strategy(self):
        """
        Ensures that the class registers all of the necessary handlers
        """
        session = Mock()
        self.sync_strategy.register_strategy(session)
        register_args = session.register.call_args_list
        self.assertEqual(register_args[0][0][0],
                         'building-arg-table.sync')
        self.assertEqual(register_args[0][0][1],
                         self.sync_strategy.add_sync_argument)
        self.assertEqual(register_args[1][0][0], 'choosing-s3-sync-strategy')
        self.assertEqual(register_args[1][0][1],
                         self.sync_strategy.use_sync_strategy)

    def test_determine_should_sync(self):
        """
        Ensure that this class cannot be directly used as the sync strategy.
        """
        with self.assertRaises(NotImplementedError):
            self.sync_strategy.determine_should_sync(None, None)

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
        self.sync_strategy.add_sync_argument(arg_table)
        self.assertEqual(arg_table,
                         [{'name': 'original_argument'},
                          {'name': 'sync_argument'}])

    def test_no_add_sync_argument_for_no_argument_specified(self):
        """
        Ensures nothing is added to the command's ``arg_table`` if no
        ``ARGUMENT`` table is specified.
        """
        arg_table = [{'name': 'original_argument'}]
        self.sync_strategy.add_sync_argument(arg_table)
        self.assertEqual(arg_table, [{'name': 'original_argument'}])

    def test_no_use_sync_strategy_for_no_argument_specified(self):
        """
        Test if that the sync strategy is not returned if it has no argument.
        """
        params = {'my_sync_strategy': True}
        self.assertEqual(self.sync_strategy.use_sync_strategy(params), None)

    def test_use_sync_strategy_for_name_and_no_dest(self):
        """
        Test if sync strategy argument has ``name`` but no ``dest`` and the
        strategy was called in ``params``.
        """
        self.sync_strategy.ARGUMENT = {'name': 'my-sync-strategy'}
        params = {'my_sync_strategy': True}
        self.assertEqual(self.sync_strategy.use_sync_strategy(params),
                         self.sync_strategy)

    def test_no_use_sync_strategy_for_name_and_no_dest(self):
        """
        Test if sync strategy argument has ``name`` but no ``dest`` but
        the strategy was not called in ``params``.
        """
        self.sync_strategy.ARGUMENT = {'name': 'my-sync-strategy'}
        params = {'my_sync_strategy': False}
        self.assertEqual(self.sync_strategy.use_sync_strategy(params), None)

    def test_no_use_sync_strategy_for_not_in_params(self):
        """
        Test if sync strategy argument has a ``name`` but for whatever reason
        the strategy is not in ``params``.
        """
        self.sync_strategy.ARGUMENT = {'name': 'my-sync-strategy'}
        self.assertEqual(self.sync_strategy.use_sync_strategy({}), None)

    def test_use_sync_strategy_for_name_and_dest(self):
        """
        Test if sync strategy argument has ``name`` and ``dest`` and the
        strategy was called in ``params``.
        """
        self.sync_strategy.ARGUMENT = {'name': 'my-sync-strategy',
                                       'dest': 'my-dest'}
        params = {'my-dest': True}
        self.assertEqual(self.sync_strategy.use_sync_strategy(params),
                         self.sync_strategy)

    def test_no_use_sync_strategy_for_name_and_dest(self):
        """
        Test if sync strategy argument has ``name`` and ``dest`` but the
        the strategy was not called in ``params``.
        """
        self.sync_strategy.ARGUMENT = {'name': 'my-sync-strategy',
                                       'dest': 'my-dest'}
        params = {'my-dest': False}
        self.assertEqual(self.sync_strategy.use_sync_strategy(params), None)

    def test_no_use_sync_strategy_for_dest_but_only_name_in_params(self):
        """
        Test if sync strategy argument has ``name`` and ``dest`` but the
        the strategy was not called in ``params`` even though the ``name`` was
        called in ``params``.
        """
        self.sync_strategy.ARGUMENT = {'name': 'my-sync-strategy',
                                       'dest': 'my-dest'}
        params = {'my-sync-strategy': True}
        self.assertEqual(self.sync_strategy.use_sync_strategy(params), None)


class TestSizeAndLastModifiedSync(unittest.TestCase):
    def setUp(self):
        self.sync_strategy = SizeAndLastModifiedSync()

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
        should_sync = self.sync_strategy.determine_should_sync(
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
        should_sync = self.sync_strategy.determine_should_sync(
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
        should_sync = self.sync_strategy.determine_should_sync(
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

        should_sync = self.sync_strategy.determine_should_sync(
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

        should_sync = self.sync_strategy.determine_should_sync(
            src_file, dest_file)
        self.assertFalse(should_sync)


class TestNeverSync(unittest.TestCase):
    def setUp(self):
        self.sync_strategy = NeverSync()

    def test_constructor(self):
        self.assertEqual(self.sync_strategy.sync_type, 'file_not_at_src')

    def test_determine_should_sync(self):
        time_dst = datetime.datetime.now()

        dst_file = FileStat(src='', dest='',
                            compare_key='test.py', size=10,
                            last_update=time_dst, src_type='s3',
                            dest_type='local', operation_name='')

        should_sync = self.sync_strategy.determine_should_sync(
            None, dst_file)
        self.assertFalse(should_sync)


class TestMissingFileSync(unittest.TestCase):
    def setUp(self):
        self.sync_strategy = MissingFileSync()

    def test_constructor(self):
        self.assertEqual(self.sync_strategy.sync_type, 'file_not_at_dest')

    def test_determine_should_sync(self):
        time_src = datetime.datetime.now()

        src_file = FileStat(src='', dest='',
                            compare_key='test.py', size=10,
                            last_update=time_src, src_type='s3',
                            dest_type='local', operation_name='')

        should_sync = self.sync_strategy.determine_should_sync(
            src_file, None)
        self.assertTrue(should_sync)


if __name__ == "__main__":
    unittest.main()
