# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.testutils import unittest, mock
from awscli.autocomplete.db import DatabaseConnection


class TestDatabaseConnection(unittest.TestCase):
    @mock.patch('awscli.compat.sqlite3.connect')
    def test_does_try_to_enable_wal(self, mock_connect):
        conn = DatabaseConnection(':memory:')
        mock_connection = mock_connect.return_value
        conn.execute('my SQL query')
        mock_connection.execute.assert_any_call('PRAGMA journal_mode=OFF', {})
