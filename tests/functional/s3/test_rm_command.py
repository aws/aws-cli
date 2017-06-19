# Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.testutils import BaseAWSCommandParamsTest, FileCreator


class TestRmCommand(BaseAWSCommandParamsTest):

    prefix = 's3 rm'

    def setUp(self):
        super(TestRmCommand, self).setUp()
        self.files = FileCreator()

    def tearDown(self):
        super(TestRmCommand, self).tearDown()
        self.files.remove_all()

    def test_operations_used_in_upload(self):
        cmdline = '%s s3://bucket/key.txt' % self.prefix
        self.run_cmd(cmdline, expected_rc=0)
        # The only operation we should have called is DeleteObject.
        self.assertEqual(
            len(self.operations_called), 1, self.operations_called)
        self.assertEqual(self.operations_called[0][0].name, 'DeleteObject')
