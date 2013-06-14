#!/usr/bin/env python
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
from tests.unit import BaseAWSCommandParamsTest
import awscli.clidriver


class TestDescribeInstances(BaseAWSCommandParamsTest):

    prefix = 'cloudformation create-stack'

    def test_basic_create_stack(self):
        cmdline = self.prefix
        cmdline += ' --stack-name test-stack --template-url http://foo'
        result = {'StackName': 'test-stack', 'TemplateURL': 'http://foo'}
        self.assert_params_for_cmd(cmdline, result)

    def test_create_stack_string_params(self):
        cmdline = self.prefix
        cmdline += ' --stack-name test-stack --template-url http://foo'
        cmdline += ' --parameters parameter_key=foo,parameter_value=bar'
        cmdline += ' parameter_key=foo2,parameter_value=bar2'
        result = {'StackName': 'test-stack', 'TemplateURL': 'http://foo',
                  'Parameters.member.1.ParameterKey': 'foo',
                  'Parameters.member.1.ParameterValue': 'bar',
                  'Parameters.member.2.ParameterKey': 'foo2',
                  'Parameters.member.2.ParameterValue': 'bar2'}
        self.assert_params_for_cmd(cmdline, result)

    def test_create_stack_for_csv_params_escaping(self):
        # If a template is specified as a comma delimited list,
        # we need to be able to quote the value or escape the comma.
        cmdline = self.prefix
        cmdline += ' --stack-name test-stack --template-url http://foo'
        cmdline += ' --parameters parameter_key=foo,parameter_value=one\,two'
        result = {'StackName': 'test-stack', 'TemplateURL': 'http://foo',
                  'Parameters.member.1.ParameterKey': 'foo',
                  'Parameters.member.1.ParameterValue': 'one,two',
                  }
        self.assert_params_for_cmd(cmdline, result)

    def test_create_stack_for_csv_with_quoting(self):
        cmdline = self.prefix
        cmdline += ' --stack-name test-stack --template-url http://foo'
        # Note how we're quoting the value of parameter_value.
        cmdline += ' --parameters parameter_key=foo,parameter_value="one,two"'
        result = {'StackName': 'test-stack', 'TemplateURL': 'http://foo',
                  'Parameters.member.1.ParameterKey': 'foo',
                  'Parameters.member.1.ParameterValue': 'one,two',
                  }
        self.assert_params_for_cmd(cmdline, result)


if __name__ == "__main__":
    unittest.main()
