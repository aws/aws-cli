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
from awscli.customizations.s3.syncstrategy.delete import DeleteSync

from awscli.testutils import unittest


class TestDeleteSync(unittest.TestCase):
    def setUp(self):
        self.sync_strategy = DeleteSync()

    def test_determine_should_sync(self):
        timenow = datetime.datetime.now()

        dst_file = FileStat(src='', dest='',
                            compare_key='test.py', size=10,
                            last_update=timenow, src_type='local',
                            dest_type='s3', operation_name='')

        should_sync = self.sync_strategy.determine_should_sync(
            None, dst_file)
        self.assertTrue(should_sync)
        self.assertEqual(dst_file.operation_name, 'delete')


if __name__ == "__main__":
    unittest.main()
