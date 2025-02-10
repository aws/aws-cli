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
from awscli.customizations.emr.createdefaultroles import get_service_principal
from awscli.customizations.emr.exceptions import \
    ResolveServicePrincipalError


class TestEmrConfig(unittest.TestCase):
    ec2_service = "ec2"
    ec2_service_principal = "ec2.amazonaws.com"
    emr_service = "elasticmapreduce"
    endpoint1 = "https://ap-southeast-1.elasticmapreduce.abc/"
    endpoint2 = "https://elasticmapreduce.abcd.def.ghi"
    endpoint3 = "https://garbage.nothing.com"
    expected_result1 = "elasticmapreduce.abc"
    expected_result2 = "elasticmapreduce.def.ghi"

    def test_get_emr_service_principal(self):
        msg = "Generated Service Principal does not match the expected" + \
            "Service Principal"

        result1 = get_service_principal(self.emr_service, self.endpoint1)
        self.assertEqual(result1, self.expected_result1, msg)

        result2 = get_service_principal(self.emr_service, self.endpoint2)
        self.assertEqual(result2, self.expected_result2, msg)

        self.assertRaises(ResolveServicePrincipalError,
                          get_service_principal, self.emr_service,
                          self.endpoint3)

    def test_get_ec2_service_principal(self):
        self.assertEqual(get_service_principal(self.ec2_service, self.endpoint1), self.ec2_service_principal)
        self.assertEqual(get_service_principal(self.ec2_service, self.endpoint2), self.ec2_service_principal)
        self.assertEqual(get_service_principal(self.ec2_service, self.endpoint3), self.ec2_service_principal)


if __name__ == "__main__":
    unittest.main()
