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
import sys
import shutil
import subprocess
from subprocess import CalledProcessError

from awscli.customizations.commands import BasicCommand
from awscli.customizations.codedeploy.utils import \
    validate_region, validate_s3_location, config_path, create_config_file, \
    validate_iam_user_arn, validate_instance, REGION_ARG, IAM_USER_ARN_ARG


class Install(BasicCommand):
    NAME = 'install'

    DESCRIPTION = (
        'The AWS CodeDeploy install command configures and installs the '
        'codedeploy-agent on the on-premises instance.'
    )

    ARG_TABLE = [
        {
            'name': 'override-config',
            'action': 'store_true',
            'default': False,
            'help_text': (
                'Optional. Specify --override-config flag to override the '
                'on-premises config file.'
            )
        },
        {
            'name': 'config-file',
            'synopsis': '--config-file <path>',
            'required': False,
            'help_text': (
                'Optional. The path to the on-premises config file.'
            )
        },
        IAM_USER_ARN_ARG,
        REGION_ARG,
        {
            'name': 'agent-installer',
            'synopsis': '--agent-installer <s3-location>',
            'required': False,
            'help_text': (
                'Optional. The codedeploy-agent installer file.'
            )
        }
    ]

    def _run_main(self, parsed_args, parsed_globals):
        parsed_args.region = validate_region(parsed_globals, self._session)
        validate_instance(parsed_args)
        self._validate_config(parsed_args)
        validate_iam_user_arn(parsed_args)
        self._validate_agent_installer(parsed_args)
        params = parsed_args

        try:
            self._create_config(params)
            self._install_agent(params)
        except Exception as e:
            sys.stdout.write(
                'ERROR\n'
                '{0}\n'
                'Please manually install the codedeploy-agent on the '
                'on-premises instance by following the instructions at '
                '{1}\n'.format(
                    e,
                    'https://docs.aws.amazon.com/codedeploy/...'
                )
            )

    @staticmethod
    def _validate_config(parsed_args):
        if parsed_args.config_file and parsed_args.iam_user_arn:
            raise RuntimeError(
                'You cannot specify both --config-file and --iam-user-arn'
            )

    @staticmethod
    def _validate_agent_installer(parsed_args):
        validate_s3_location(parsed_args, 'agent_installer')
        if 'bucket' not in parsed_args:
            parsed_args.bucket = 'aws-codedeploy-{0}'.format(
                parsed_args.region
            )
        if 'key' not in parsed_args:
            if sys.platform == 'linux2':
                parsed_args.installer = 'install'
            elif sys.platform == 'win32':
                parsed_args.installer = 'codedeploy-agent.msi'
            parsed_args.key = 'latest/{0}'.format(parsed_args.installer)
        else:
            start = parsed_args.key.rfind('/') + 1
            parsed_args.installer = parsed_args.key[start:]

    @staticmethod
    def _create_config(params):
        sys.stdout.write('Creating on-premises config file... ')
        if os.path.isfile(config_path()) and not params.override_config:
            raise RuntimeError(
                'On-premises config file already exists. Please specify '
                '--override-config to update the existing config file.'
            )

        try:
            os.makedirs(os.path.dirname(config_path()))
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise e

        if params.config_file and params.config_file != config_path():
            shutil.copyfile(params.config_file, config_path())
        else:
            sys.stdout.write('\n')
            if not params.iam_user_arn:
                params.iam_user_arn = raw_input('Enter IAM User ARN: ')
            params.access_key_id = raw_input('Enter Access Key ID: ')
            params.secret_access_key = raw_input('Enter Secret Access Key: ')
            sys.stdout.write('... ')
            create_config_file(config_path(), params)
        sys.stdout.write('DONE\n')

    @staticmethod
    def _install_agent(params):
        sys.stdout.write('Installing codedeploy-agent... ')
        if sys.platform == 'linux2':
            if params.system == 'ubuntu':
                subprocess.check_call(
                    'sudo apt-get -y update',
                    shell=True
                )
                subprocess.check_call(
                    'sudo apt-get -y install ruby2.0',
                    shell=True
                )
            elif params.system == 'redhat':
                subprocess.check_call(
                    'sudo yum -y update',
                    shell=True
                )
            try:
                subprocess.check_call(
                    'sudo service codedeploy-agent stop',
                    shell=True
                )
            except CalledProcessError:
                pass
            subprocess.check_call(
                'aws s3 cp s3://{0}/{1} ./{2} --region {3}'.format(
                    params.bucket,
                    params.key,
                    params.installer,
                    params.region
                ),
                shell=True
            )
            subprocess.check_call(
                'sudo chmod +x ./{0}'.format(params.installer),
                shell=True
            )
            subprocess.check_call(
                'sudo ./{0} auto'.format(params.installer),
                shell=True
            )
        elif sys.platform == 'win32':
            try:
                subprocess.check_call(
                    'powershell.exe -Command Stop-Service'
                    ' -Name codedeployagent',
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True
                )
            except CalledProcessError:
                pass
            subprocess.check_call(
                r'powershell.exe -Command New-Item'
                r' -Path "c:\temp"'
                r' -ItemType Directory'
                r' -Force',
                shell=True
            )
            subprocess.check_call(
                r'powershell.exe -Command Read-S3Object'
                r' -BucketName {0} -Key {1}'
                r' -File c:\temp\{2}'.format(
                    params.bucket,
                    params.key,
                    params.installer
                ),
                shell=True
            )
            subprocess.check_call(
                r'c:\temp\{0}'
                r' /quiet'
                r' /l c:\temp\codedeploy-agent-install-log.txt'.format(
                    params.installer
                ),
                shell=True
            )
            subprocess.check_call(
                'powershell.exe -Command Restart-Service'
                ' -Name codedeployagent',
                shell=True
            )
        sys.stdout.write('... DONE\n')
