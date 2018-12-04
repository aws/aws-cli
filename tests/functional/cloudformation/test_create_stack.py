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
from awscli.testutils import BaseAWSCommandParamsTest


class TestCreateStack(BaseAWSCommandParamsTest):

    prefix = 'cloudformation create-stack'

    def test_basic_create_stack(self):
        cmdline = self.prefix
        cmdline += ' --stack-name test-stack --template-url http://foo'
        result = {'StackName': 'test-stack', 'TemplateURL': 'http://foo'}
        self.assert_params_for_cmd(cmdline, result)

    def test_create_stack_string_params(self):
        cmdline = self.prefix
        cmdline += ' --stack-name test-stack --template-url http://foo'
        cmdline += ' --parameters ParameterKey=foo,ParameterValue=bar'
        cmdline += ' ParameterKey=foo2,ParameterValue=bar2'
        result = {'StackName': 'test-stack', 'TemplateURL': 'http://foo',
                  'Parameters': [
                      {'ParameterKey': 'foo', 'ParameterValue': 'bar'},
                      {'ParameterKey': 'foo2', 'ParameterValue': 'bar2'},
                  ]}
        self.assert_params_for_cmd(cmdline, result)

    def test_create_stack_for_csv_params_escaping(self):
        # If a template is specified as a comma delimited list,
        # we need to be able to quote the value or escape the comma.
        cmdline = self.prefix
        cmdline += ' --stack-name test-stack --template-url http://foo'
        cmdline += ' --parameters ParameterKey=foo,ParameterValue=one\,two'
        result = {'StackName': 'test-stack', 'TemplateURL': 'http://foo',
                  'Parameters': [{'ParameterKey': 'foo',
                                  'ParameterValue': 'one,two'}]}
        self.assert_params_for_cmd(cmdline, result)

    def test_create_stack_for_csv_with_quoting(self):
        cmdline = self.prefix
        cmdline += ' --stack-name test-stack --template-url http://foo'
        # Note how we're quoting the value of parameter_value.
        cmdline += ' --parameters ParameterKey=foo,ParameterValue="one,two"'
        result = {'StackName': 'test-stack', 'TemplateURL': 'http://foo',
                  'Parameters': [{'ParameterKey': 'foo',
                                  'ParameterValue': 'one,two'}]}
        self.assert_params_for_cmd(cmdline, result)

    def test_can_handle_empty_parameters(self):
        cmdline = self.prefix
        cmdline += ' --stack-name test --parameters --template-url http://foo'
        result = {'StackName': 'test', 'TemplateURL': 'http://foo',
                  'Parameters': []}
        self.assert_params_for_cmd(cmdline, result)
