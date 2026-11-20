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
import pytest

from awscli.customizations.ec2.addcount import CountArgument
from awscli.customizations.exceptions import ParamValidationError


class TestCountArgument:
    def setup_method(self):
        self.arg = CountArgument('count')

    def test_single_count(self):
        params = {}
        self.arg.add_to_params(params, '3')
        assert params == {'MinCount': 3, 'MaxCount': 3}

    def test_count_range(self):
        params = {}
        self.arg.add_to_params(params, '1:10')
        assert params == {'MinCount': 1, 'MaxCount': 10}

    @pytest.mark.parametrize('value', ['abc', '1:abc', '1:2:3'])
    def test_invalid_count_raises_param_validation_error(self, value):
        with pytest.raises(ParamValidationError):
            self.arg.add_to_params({}, value)
