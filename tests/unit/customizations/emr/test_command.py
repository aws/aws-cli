# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import mock


from tests.unit.customizations.emr import EMRBaseAWSCommandParamsTest as \
    BaseAWSCommandParamsTest
import argparse
from awscli.customizations.emr.command import Command


class FakeCommand(Command):

    def _run_main_command(self, parsed_args, parsed_globals):
        return 0


class TestCommand(BaseAWSCommandParamsTest):

    def test_region(self):
        def mock_region_side_effect(*args, **kwargs):
            if args[0] == 'region':
                return 'eu-central-1'
            else:
                return None

        mock_session = mock.Mock()
        mock_session.get_config_variable.side_effect = mock_region_side_effect
        mock_session.get_scoped_config.return_value = {}
        parsed_globals = argparse.Namespace()
        parsed_globals.region = None
        mocked_parsed_args = mock.Mock()

        cmd = FakeCommand(mock_session)
        cmd._run_main(mocked_parsed_args, parsed_globals)

        self.assertEquals(cmd.region, 'eu-central-1')
