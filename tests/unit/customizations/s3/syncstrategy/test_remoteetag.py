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
from awscli.customizations.s3.syncstrategy.remoteetag import RemoteEtagSync

from awscli.testutils import unittest


class TestRemoteEtagSync(unittest.TestCase):
    def setUp(self):
        self.sync_strategy = RemoteEtagSync()

    def test_compare_remote_etag_different(self):
        """
        Confirm that files are synced when remote etag differs.
        """
        response_data_src = { u'ETag': '"AnEtag"' }
        response_data_dst = { u'ETag': '"AnotherEtag"' }

        src_file = FileStat(src='', dest='',
                            compare_key='test.py', src_type='s3',
                            dest_type='s3', operation_name='copy',
                            response_data=response_data_src)

        dst_file = FileStat(src='', dest='',
                            compare_key='test.py', src_type='s3',
                            dest_type='s3', operation_name='',
                            response_data=response_data_dst)

        should_sync = self.sync_strategy.determine_should_sync(src_file, dst_file)
        self.assertTrue(should_sync)

    def test_compare_remote_etag_same(self):
        """
        Confirm that files are not synced when remote etags are the same.
        """
        response_data_src = { u'ETag': '"AnEtag"' }
        response_data_dst = { u'ETag': '"AnEtag"' }

        src_file = FileStat(src='', dest='',
                            compare_key='test.py', src_type='s3',
                            dest_type='s3', operation_name='copy',
                            response_data=response_data_src)

        dst_file = FileStat(src='', dest='',
                            compare_key='test.py', src_type='s3',
                            dest_type='s3', operation_name='',
                            response_data=response_data_src)

        should_sync = self.sync_strategy.determine_should_sync(src_file, dst_file)
        self.assertFalse(should_sync)


if __name__ == "__main__":
    unittest.main()
