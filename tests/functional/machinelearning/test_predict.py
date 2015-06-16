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
from awscli.testutils import BaseAWSCommandParamsTest


class TestPredict(BaseAWSCommandParamsTest):

    prefix = 'machinelearning predict'

    def test_renamed_reboot_arg(self):
        cmdline = self.prefix
        cmdline += ' --ml-model-id ml-foo --record Foo=Bar,Biz=Baz'
        cmdline += ' --predict-endpoint https://myendpoint.amazonaws.com'
        result = {'MLModelId': 'ml-foo',
                  'Record': {'Foo': 'Bar', 'Biz': 'Baz'},
                  'PredictEndpoint': 'https://myendpoint.amazonaws.com'}
        self.assert_params_for_cmd(cmdline, result)
