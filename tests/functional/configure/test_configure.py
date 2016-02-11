# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import mock

from awscli.testutils import BaseAWSCommandParamsTest
from awscli.customizations.configure import ConfigureSetCommand


class TestConfigureSetCommand(BaseAWSCommandParamsTest):
    def test_configure_set_command_with_url(self):
        with mock.patch.object(
                ConfigureSetCommand, '_run_main',
                lambda _self, args, parsed_globals:
                    self.assertEqual(args.value, 'http://www.example.com')):
            self.run_cmd('configure set endpoint http://www.example.com',
                         expected_rc=None)
