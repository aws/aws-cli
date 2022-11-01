# Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from awscli.testutils import BaseAWSCommandParamsTest
from awscli.customizations.overridesslcommonname import SSL_COMMON_NAMES


class OverrideSSLCommonNameTestCase(BaseAWSCommandParamsTest):
    def _common_name_test_cases(self):

        service_ops = {
            "sqs": "list-queues",
            "emr": "list-clusters",
            "rds": "describe-db-clusters",
            "neptune": "describe-db-clusters",
            "docdb": "describe-db-clusters",
        }
        for service, operation in service_ops.items():
            for region in SSL_COMMON_NAMES[service]:
                yield (service, operation, region)

    def _assert_region_endpoint_used(
        self, expected_region, expected_endpoint_url
    ):
        self.assertEqual(
            expected_region, self.last_request_dict["context"]["client_region"]
        )
        self.assertEqual(
            expected_endpoint_url,
            self.last_request_dict["url"],
        )

    def test_set_endpoint_url_arg(self):
        for service, operation, region in self._common_name_test_cases():
            self.run_cmd(f"{service} {operation} --region {region}".split())
            expected_endpoint_url = (
                f"https://{SSL_COMMON_NAMES[service][region]}/"
            )
            self._assert_region_endpoint_used(region, expected_endpoint_url)

    def test_override_health_endpoint_and_region(self):
        expected_override_region = "us-east-1"
        health_regions = SSL_COMMON_NAMES["health"]
        for region in health_regions:
            if region in ["cn-north-1", "cn-northwest-1", "aws-cn-global"]:
                expected_override_region = "cn-northwest-1"
            expected_endpoint_url = (
                f"https://{SSL_COMMON_NAMES['health'][region]}/"
            )
            self.run_cmd(f"health describe-events --region {region}".split())
            self._assert_region_endpoint_used(
                expected_override_region,
                expected_endpoint_url,
            )
