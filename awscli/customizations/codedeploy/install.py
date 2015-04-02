# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

import errno
import os
import shutil
import sys

from awscli.customizations.commands import BasicCommand
from awscli.customizations.codedeploy.utils import \
    validate_region, validate_s3_location, validate_instance


class Install(BasicCommand):
    NAME = 'install'

    DESCRIPTION = (
        'Configures and installs the AWS CodeDeploy Agent on the on-premises '
        'instance.'
    )

    ARG_TABLE = [
        {
            'name': 'config-file',
            'synopsis': '--config-file <path>',
            'required': True,
            'help_text': (
                'Required. The path to the on-premises instance configuration '
                'file.'
            )
        },
        {
            'name': 'override-config',
            'action': 'store_true',
            'default': False,
            'help_text': (
                'Optional. Overrides the on-premises instance configuration '
                'file.'
            )
        },
        {
            'name': 'agent-installer',
            'synopsis': '--agent-installer <s3-location>',
            'required': False,
            'help_text': (
                'Optional. The AWS CodeDeploy Agent installer file.'
            )
        }
    ]

    def _run_main(self, parsed_args, parsed_globals):
        params = parsed_args
        params.session = self._session
        validate_region(params, parsed_globals)
        validate_instance(params)
        params.system.validate_administrator()
        self._validate_override_config(params)
        self._validate_agent_installer(params)

        try:
            self._create_config(params)
            self._install_agent(params)
        except Exception as e:
            sys.stdout.flush()
            sys.stderr.write(
                'ERROR\n'
                '{0}\n'
                'Install the AWS CodeDeploy Agent on the on-premises instance '
                'by following the instructions in "Configure Existing '
                'On-Premises Instances by Using AWS CodeDeploy" in the AWS '
                'CodeDeploy User Guide.\n'.format(e)
            )

    def _validate_override_config(self, params):
        if os.path.isfile(params.system.CONFIG_PATH) and \
                not params.override_config:
            raise RuntimeError(
                'The on-premises instance configuration file already exists. '
                'Specify --override-config to update the existing on-premises '
                'instance configuration file.'
            )

    def _validate_agent_installer(self, params):
        validate_s3_location(params, 'agent_installer')
        if 'bucket' not in params:
            params.bucket = 'aws-codedeploy-{0}'.format(params.region)
        if 'key' not in params:
            params.key = 'latest/{0}'.format(params.system.INSTALLER)
            params.installer = params.system.INSTALLER
        else:
            start = params.key.rfind('/') + 1
            params.installer = params.key[start:]

    def _create_config(self, params):
        sys.stdout.write(
            'Creating the on-premises instance configuration file... '
        )
        try:
            os.makedirs(params.system.CONFIG_DIR)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise e
        if params.config_file != params.system.CONFIG_PATH:
            shutil.copyfile(params.config_file, params.system.CONFIG_PATH)
        sys.stdout.write('DONE\n')

    def _install_agent(self, params):
        sys.stdout.write('Installing the AWS CodeDeploy Agent... ')
        params.system.install(params)
        sys.stdout.write('DONE\n')
