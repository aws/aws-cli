# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from awscli.handlers import awscli_initialize


class TestNoDryRunDocCustomization(unittest.TestCase):
    def test_no_dry_run_doc_customizations(self):
        event_emitter = mock.Mock()
        awscli_initialize(event_emitter)
        registered_handlers = event_emitter.register.call_args_list
        # Make sure there is no doc customization for ec2's DryRun
        self.assertNotIn(
            mock.call('doc-option-example.ec2.*.dry-run', mock.ANY),
            registered_handlers
        )
