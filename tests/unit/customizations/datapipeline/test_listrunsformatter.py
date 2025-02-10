# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import difflib

from awscli.testutils import mock, unittest
from awscli.customizations.datapipeline.listrunsformatter \
    import ListRunsFormatter
from awscli.compat import StringIO


class TestListRunsFormatter(unittest.TestCase):
    def setUp(self):
        self.formatter = ListRunsFormatter(mock.Mock(query=None))
        self.stream = StringIO()

    def assert_data_renders_to(self, data, table):
        self.formatter('list-runs', data, stream=self.stream)
        rendered = self.stream.getvalue()

        differ = difflib.Differ()
        diff = differ.compare(table.splitlines(1), rendered.splitlines(1))

        self.assertEqual(table, rendered, msg='\n' + '\n'.join(diff))

    def test_empty(self):
        self.assert_data_renders_to(
            [],
            "       Name                                                Scheduled Start      Status                 \n"  # noqa
            "       ID                                                  Started              Ended              \n"  # noqa
            "---------------------------------------------------------------------------------------------------\n")  # noqa

    def test_single_row(self):
        self.assert_data_renders_to(
            [{
                 '@componentParent': 'parent',
                 '@id': 'id',
                 '@scheduledStartTime': 'now',
                 '@status': 'status',
                 '@actualStartTime': 'actualStartTime',
                 '@actualEndTime': 'actualEndTime',
             }],
            "       Name                                                Scheduled Start      Status                 \n"  # noqa
            "       ID                                                  Started              Ended              \n"  # noqa
            "---------------------------------------------------------------------------------------------------\n"  # noqa
            "   1.  parent                                              now                  status                 \n"  # noqa
            "       id                                                  actualStartTime      actualEndTime      \n"  # noqa
            "\n"
        )
