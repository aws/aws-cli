# Copyright 2026 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


class TestOTelAlias(BaseAWSCommandParamsTest):
    def test_get_otel_enrichment_alias(self):
        self.run_cmd('cloudwatch get-otel-enrichment', expected_rc=0)
        self.run_cmd('cloudwatch get-o-tel-enrichment', expected_rc=0)

    def test_start_otel_enrichment_alias(self):
        self.run_cmd('cloudwatch start-otel-enrichment', expected_rc=0)
        self.run_cmd('cloudwatch start-o-tel-enrichment', expected_rc=0)

    def test_stop_otel_enrichment_alias(self):
        self.run_cmd('cloudwatch stop-otel-enrichment', expected_rc=0)
        self.run_cmd('cloudwatch stop-o-tel-enrichment', expected_rc=0)
