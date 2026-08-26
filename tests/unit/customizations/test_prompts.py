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

from awscli.customizations.prompts import yes_no_choice


def test_enter_accepts_yes_default():
    with patch(
        'awscli.customizations.prompts.compat_input', return_value=''
    ) as input_mock:
        assert yes_no_choice('Continue? [Y/n]: ', default=True)

    input_mock.assert_called_once_with('Continue? [Y/n]: ')
