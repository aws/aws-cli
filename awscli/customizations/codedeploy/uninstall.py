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

import os
import subprocess
from subprocess import CalledProcessError
import sys
import errno

from awscli.customizations.codedeploy.utils import config_path, \
    validate_instance
from awscli.customizations.commands import BasicCommand


class Uninstall(BasicCommand):
    NAME = 'uninstall'

    DESCRIPTION = (
        'The AWS CodeDeploy uninstall command uninstalls the codedeploy-agent '
        'from the on-premises instance.'
    )

    def _run_main(self, parsed_args, parsed_globals):
        validate_instance(parsed_args)
        params = parsed_args

        try:
            self._delete_config_file()
            self._uninstall_agent(params)
        except Exception as e:
            sys.stdout.write(
                'ERROR\n'
                '{0}\n'
                'Please manually uninstall the codedeploy-agent on the '
                'on-premises instance by following the instructions at '
                '{1}\n'.format(
                    e,
                    'https://docs.aws.amazon.com/codedeploy/...'
                )
            )

    @staticmethod
    def _uninstall_agent(params):
        sys.stdout.write('Uninstalling codedeploy-agent... ')
        if sys.platform == 'linux2':
            try:
                subprocess.check_call(
                    'sudo service codedeploy-agent stop',
                    shell=True
                )
            except CalledProcessError:
                pass
            if params.system == 'ubuntu':
                subprocess.check_call(
                    'sudo dpkg -r codedeploy-agent',
                    shell=True
                )
            elif params.system == 'redhat':
                subprocess.check_call(
                    'sudo yum -y erase codedeploy-agent',
                    shell=True
                )
        elif sys.platform == 'win32':
            try:
                subprocess.check_call(
                    r'wmic product where name="CodeDeploy Host Agent" call uninstall /nointeractive',
                    stdout=subprocess.PIPE,
                    shell=True
                )
            except CalledProcessError:
                raise RuntimeError(
                    'Failed to uninstall the CodeDeploy Host Agent.'
                )

        sys.stdout.write('DONE\n')

    @staticmethod
    def _delete_config_file():
        sys.stdout.write('Deleting on-premises config file... ')
        try:
            os.remove(config_path())
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise e
        sys.stdout.write('DONE\n')
