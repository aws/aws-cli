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
import sys
import errno

from awscli.customizations.codedeploy.utils import validate_instance, \
    validate_region
from awscli.customizations.commands import BasicCommand


class Uninstall(BasicCommand):
    NAME = 'uninstall'

    DESCRIPTION = (
        'Uninstalls the AWS CodeDeploy Agent from the on-premises instance.'
    )

    def _run_main(self, parsed_args, parsed_globals):
        params = parsed_args
        params.session = self._session
        validate_region(params, parsed_globals)
        validate_instance(params)
        params.system.validate_administrator()

        try:
            self._uninstall_agent(params)
            self._delete_config_file(params)
        except Exception as e:
            sys.stdout.flush()
            sys.stderr.write(
                'ERROR\n'
                '{0}\n'
                'Uninstall the AWS CodeDeploy Agent on the on-premises '
                'instance by following the instructions in "Configure '
                'Existing On-Premises Instances by Using AWS CodeDeploy" in '
                'the AWS CodeDeploy User Guide.\n'.format(e)
            )

    def _uninstall_agent(self, params):
        sys.stdout.write('Uninstalling the AWS CodeDeploy Agent... ')
        params.system.uninstall(params)
        sys.stdout.write('DONE\n')

    def _delete_config_file(self, params):
        sys.stdout.write('Deleting the on-premises instance configuration... ')
        try:
            os.remove(params.system.CONFIG_PATH)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise e
        sys.stdout.write('DONE\n')
