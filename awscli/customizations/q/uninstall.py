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

import shutil
import sys
from pathlib import Path

from awscli.customizations.commands import BasicCommand
from awscli.customizations.q.utils import Q_EXTENSION_DIR, Q_EXTENSION_PATH


class UninstallCommand(BasicCommand):
    NAME = 'uninstall'
    DESCRIPTION = 'Uninstall the Q CLI extension.'

    def __init__(self, session):
        super().__init__(session)

    def _run_main(self, parsed_args, parsed_globals):
        if not Path.is_file(Q_EXTENSION_PATH):
            sys.stdout.write('The Q CLI extension is not installed.\n')
        else:
            shutil.rmtree(Q_EXTENSION_DIR, ignore_errors=True)
            sys.stdout.write(f'Uninstalled {Q_EXTENSION_DIR}\n')
