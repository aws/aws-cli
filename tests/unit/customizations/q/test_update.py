# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from unittest.mock import patch

from awscli.customizations.q.update import UpdateCommand
from awscli.testutils import mock


class TestUpdateCommand:
    def setup_method(self):
        self.session = mock.Mock()
        self.update_command = UpdateCommand(self.session)

    def test_update(self):
        # TODO - implement tests once update is implemented
        self.update_command._run_main([], None)
