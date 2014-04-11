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

import unittest
from awscli.customizations.emr.emrconfig import get_service_principal
from awscli.customizations.emr.exceptions import \
    ResolveServicePrincipalError


class TestEmrConfig(unittest.TestCase):
    ec2_service = "ec2"
    emr_service = "elasticmapreduce"
    us_east1 = "us-east-1"
    cn_north_1 = "cn-north-1"
    eu_west_1 = "eu-west-1"
    endpoint1 = "https://aws.elasticmapreduce.abc"
    endpoint2 = "https://elasticmapreduce.abcd.def.ghi"
    endpoint3 = "https://grabage.nothing.com"
    expected_result1 = "ec2.amazonaws.com"
    expected_result2 = "ec2.amazonaws.com.cn"
    expected_result3 = "elasticmapreduce.amazonaws.com"
    expected_result4 = "elasticmapreduce.abc"
    expected_result5 = "elasticmapreduce.def.ghi"

    def test_get_service_principal(self):
        msg = "Generated Service Principal does not match the expected" + \
            "Service Principal"

        result1 = get_service_principal(self.ec2_service, self.us_east1, None)
        self.assertEqual(result1, self.expected_result1, msg)

        result2 = get_service_principal(self.ec2_service, self.cn_north_1,
                                        None)
        self.assertEqual(result2, self.expected_result2, msg)

        result3 = get_service_principal(self.emr_service, self.eu_west_1, None)
        self.assertEqual(result3, self.expected_result3, msg)

        result4 = get_service_principal(self.emr_service, None, self.endpoint1)
        self.assertEqual(result4, self.expected_result4, msg)

        result5 = get_service_principal(self.emr_service, None, self.endpoint2)
        self.assertEqual(result5, self.expected_result5, msg)

        self.assertRaises(ResolveServicePrincipalError,
                          get_service_principal, self.ec2_service, None,
                          self.endpoint3)


if __name__ == "__main__":
    unittest.main()