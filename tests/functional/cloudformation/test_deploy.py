# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import json

from awscli.testutils import BaseAWSCommandParamsTest
from awscli.testutils import FileCreator


class TestDeployCommand(BaseAWSCommandParamsTest):
    def setUp(self):
        super(TestDeployCommand, self).setUp()
        self.files = FileCreator()
        self.parsed_responses = [
            # First it checks to see if a stack with that name exists. So
            # we fake a response indicating that the stack exists and is in
            # an OK state.
            {'Stacks': {'StackName': 'Stack',
                        'StackStatus': 'UPDATE_COMPLETE'}},
            # Now it creates a changeset, so we fake a response with an ID.
            {'Id': 'FakeChangeSetId'},
            # This fakes a failed response from the waiter because the
            # changeset was empty.
            {
                'StackName': 'Stack',
                'Status': 'FAILED',
                'StatusReason': (
                    'The submitted information didn\'t contain changes. '
                    'Submit different information to create a change set.'
                ),
                'ExecutionStatus': 'UNAVAILABLE'
            },
        ]
        # The template is inspected before we make any of the calls so it
        # needs to have valid JSON content.
        path = self.files.create_file('template.json', '{}')
        self.command = (
            'cloudformation deploy --template-file %s '
            '--stack-name Stack'
        ) % path

    def tearDown(self):
        self.files.remove_all()
        super(TestDeployCommand, self).tearDown()

    def test_does_return_zero_exit_code_on_empty_changeset_by_default(self):
        self.run_cmd(self.command, expected_rc=0)

    def test_does_return_zero_exit_code_on_empty_changeset(self):
        self.command += ' --no-fail-on-empty-changeset'
        self.run_cmd(self.command, expected_rc=0)

    def test_does_return_non_zero_exit_code_on_empty_changeset(self):
        self.command += ' --fail-on-empty-changeset'
        self.run_cmd(self.command, expected_rc=255)


class TestDeployCommandParameterOverrides(TestDeployCommand):
    def setUp(self):
        super(TestDeployCommandParameterOverrides, self).setUp()
        template = '''{
          "AWSTemplateFormatVersion": "2010-09-09",
          "Parameters": {
            "Key1": {
              "Type": "String"
            },
            "Key2": {
              "Type": "String"
            }
          }
        }'''
        path = self.files.create_file('template.json', template)
        self.command = (
            'cloudformation deploy --template-file %s '
            '--stack-name Stack '
        ) % path

    def _assert_parameters_parsed(self):
        self.assertEqual(
            self.operations_called[1][1]['Parameters'],
            [
                {'ParameterKey': 'Key1', 'ParameterValue': 'Value1'},
                {'ParameterKey': 'Key2', 'ParameterValue': 'Value2'}
            ]
        )

    def create_json_file(self, filename, data):
        return self.files.create_file(filename, json.dumps(data))

    def test_parameter_overrides_shorthand(self):
        self.command += ' --parameter-overrides Key1=Value1 Key2=Value2'
        self.run_cmd(self.command)
        self._assert_parameters_parsed()

    def test_parameter_overrides_from_inline_original_json(self):
        original_like_json = ['Key1=Value1', 'Key2=Value2']
        path = self.create_json_file('param.json', original_like_json)
        self.command += ' --parameter-overrides file://%s' % path
        self.run_cmd(self.command)
        self._assert_parameters_parsed()

    def test_parameter_overrides_from_inline_cf_like_json(self):
        cf_like_json = ('[{"ParameterKey":"Key1",'
                        '"ParameterValue":"Value1"},'
                        '{"ParameterKey":"Key2",'
                        '"ParameterValue":"Value2"}]')
        self.command += ' --parameter-overrides %s' % cf_like_json
        self.run_cmd(self.command)
        self._assert_parameters_parsed()

    def test_parameter_overrides_from_cf_like_json_file(self):
        cf_like_json = [
            {'ParameterKey': 'Key1', 'ParameterValue': 'Value1'},
            {'ParameterKey': 'Key2', 'ParameterValue': 'Value2'}
        ]
        path = self.create_json_file('param.json', cf_like_json)
        self.command += ' --parameter-overrides file://%s' % path
        self.run_cmd(self.command)
        self._assert_parameters_parsed()

    def test_parameter_overrides_from_inline_codepipeline_like_json(self):
        codepipeline_like_json = ('{"Parameters":{"Key1":"Value1",'
                                  '"Key2":"Value2"}}')
        self.command += ' --parameter-overrides %s' % codepipeline_like_json
        self.run_cmd(self.command)
        self._assert_parameters_parsed()

    def test_parameter_overrides_from_codepipeline_like_json_file(self):
        codepipeline_like_json = {
            'Parameters': {
                'Key1': 'Value1',
                'Key2': 'Value2'
            }
        }
        path = self.create_json_file('param.json', codepipeline_like_json)
        self.command += ' --parameter-overrides file://%s' % path
        self.run_cmd(self.command)
        self._assert_parameters_parsed()

    def test_parameter_overrides_from_original_json_file(self):
        original_like_json = ['Key1=Value1', 'Key2=Value2']
        path = self.create_json_file('param.json', original_like_json)
        self.command += ' --parameter-overrides file://%s' % path
        self.run_cmd(self.command, expected_rc=0)
        self._assert_parameters_parsed()

    def test_parameter_overrides_from_invalid_cf_like_json_file(self):
        invalid_cf_like_json = [
            {
                'ParameterKey': 'Key1',
                'ParameterValue': 'Value1',
                'RedundantKey': 'RedundantValue'
            },
            {
                'ParameterKey': 'Key2',
                'ParameterValue': 'Value2'
            }
        ]
        path = self.create_json_file('param.json', invalid_cf_like_json)
        self.command += ' --parameter-overrides file://%s' % path
        _, err, _ = self.run_cmd(self.command, expected_rc=252)
        self.assertTrue('JSON passed to --parameter-overrides must be'
                        in err)

    def test_parameter_overrides_from_invalid_json(self):
        cf_like_json = {'SomeKey': [{'RedundantKey': 'RedundantValue'}]}
        path = self.create_json_file('param.json', cf_like_json)
        self.command += ' --parameter-overrides file://%s' % path
        _, err, _ = self.run_cmd(self.command, expected_rc=252)
        self.assertTrue('JSON passed to --parameter-overrides must be'
                        in err)
