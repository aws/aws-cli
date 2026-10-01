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
from awscli.customizations.lambdaweb import (
    inject_commands,
    register_lambda_web_commands,
)
from awscli.customizations.lambdaweb.deploy import LambdaWebDeploy
from awscli.testutils import mock


def test_register_lambda_web_commands_subscribes_to_command_table_event():
    handlers = mock.Mock()
    register_lambda_web_commands(handlers)
    handlers.register.assert_called_once_with(
        'building-command-table.lambda-web', inject_commands
    )


def test_inject_commands_registers_deploy():
    """The hook registers ``deploy`` alongside auto-generated modeled
    operations."""

    command_table = {'create-web-function': mock.sentinel.modeled}
    inject_commands(command_table, session=mock.sentinel.session)
    assert isinstance(command_table['deploy'], LambdaWebDeploy)
    assert 'create' not in command_table
    assert command_table['create-web-function'] is mock.sentinel.modeled
