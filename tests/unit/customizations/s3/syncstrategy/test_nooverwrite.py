# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import pytest

from awscli.customizations.s3.filegenerator import FileStat
from awscli.customizations.s3.syncstrategy.nooverwrite import NoOverwriteSync


@pytest.fixture
def sync_strategy():
    return NoOverwriteSync('file_at_src_and_dest')


def test_file_exists_at_destination_with_same_key(sync_strategy):
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
    should_sync = sync_strategy.determine_should_sync(src_file, dest_file)
    assert not should_sync
