# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from awscli.testutils import unittest
from awscli.customizations.emr.createdefaultroles import assume_role_policy


class TestDefaultRoles(unittest.TestCase):
    service_principal = "ec2.amazonaws.com"
    expected_result = {
        "Version": "2008-10-17",
        "Statement": [
            {
                "Sid": "",
                "Effect": "Allow",
                "Principal": {"Service": "ec2.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }

    def test_assume_role_policy(self):
        result = assume_role_policy(self.service_principal)
        self.assertEqual(result, self.expected_result)


if __name__ == "__main__":
    unittest.main()
