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
from awscli.compat import ensure_text_type

from tests.functional.history import BaseHistoryCommandParamsTest


class TestListCommand(BaseHistoryCommandParamsTest):
    def test_show_nothing_when_no_history(self):
        out, err, rc = self.run_cmd('history list', expected_rc=255)
        error_message = (
            'No commands were found in your history. Make sure you have '
            'enabled history mode by adding "cli_history = enabled" '
            'to the config file.'
        )
        self.assertEqual('', ensure_text_type(out))
        self.assertEqual('\n%s\n' % error_message, ensure_text_type(err))
