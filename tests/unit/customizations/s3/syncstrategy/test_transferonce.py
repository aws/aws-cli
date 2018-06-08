# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.customizations.s3.syncstrategy.transferonce import TransferOnceSync

from awscli.testutils import unittest


class TestTransferOnceSync(unittest.TestCase):
    def setUp(self):
        self.sync_strategy = TransferOnceSync()

    def test_same_name_download(self):
        """
        Confirm that files with the same name are not synced.
        """
        time_src = datetime.datetime.now()
        time_dst = time_src + datetime.timedelta(days=1)

        src_file = FileStat(src='', dest='',
                            compare_key='test.py', size=10,
                            last_update=time_src, src_type='local',
                            dest_type='s3', operation_name='upload')

        dst_file = FileStat(src='', dest='',
                            compare_key='test.py', size=11,
                            last_update=time_dst, src_type='s3',
                            dest_type='local', operation_name='')

        should_sync = self.sync_strategy.determine_should_sync(
            src_file, dst_file)
        self.assertFalse(should_sync)

    def test_same_name_upload(self):
        """
        Confirm that files with the same name are not synced.
        """
        time_src = datetime.datetime.now()
        time_dst = time_src + datetime.timedelta(days=1)

        src_file = FileStat(src='', dest='',
                            compare_key='test.py', size=10,
                            last_update=time_src, src_type='s3',
                            dest_type='local', operation_name='download')

        dst_file = FileStat(src='', dest='',
                            compare_key='test.py', size=11,
                            last_update=time_dst, src_type='local',
                            dest_type='s3', operation_name='')

        should_sync = self.sync_strategy.determine_should_sync(
            src_file, dst_file)
        self.assertFalse(should_sync)


if __name__ == "__main__":
    unittest.main()
