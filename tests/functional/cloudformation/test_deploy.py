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
