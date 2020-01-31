# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0e
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
from mock import Mock

from awscli.testutils import unittest, BaseAWSCommandParamsTest
from awscli.customizations.s3.s3 import awscli_initialize, add_s3


class AWSInitializeTest(unittest.TestCase):
    """
    This test ensures that all events are correctly registered such that
    all of the commands can be run.
    """
    def setUp(self):
        self.cli = Mock()

    def test_initialize(self):
        awscli_initialize(self.cli)
        reference = []
        reference.append("building-command-table.main")
        reference.append("building-command-table.sync")
        for arg in self.cli.register.call_args_list:
            self.assertIn(arg[0][0], reference)


class CreateTablesTest(unittest.TestCase):
    def test_s3(self):
        """
        Ensures that the table for the service was created properly.
        Also ensures the original s3 service is renamed to ``s3api``.
        """
        s3_service = Mock()
        s3_service.name = 's3'
        self.services = {'s3': s3_service}
        add_s3(self.services, True)
        orig_service = self.services.pop('s3api')
        self.assertEqual(orig_service, s3_service)
        for service in self.services.keys():
            self.assertIn(service, ['s3'])


class TestS3(BaseAWSCommandParamsTest):
    def test_too_few_args(self):
        stderr = self.run_cmd('s3', expected_rc=252)[1]
        self.assertIn(("usage: aws [options] s3 "
                       "<subcommand> [parameters]"), stderr)
        self.assertIn('too few arguments', stderr)


if __name__ == "__main__":
    unittest.main()
