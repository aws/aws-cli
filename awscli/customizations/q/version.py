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

import subprocess
from pathlib import Path

from botocore.utils import original_ld_library_path

from awscli.customizations.commands import BasicCommand
from awscli.customizations.q.utils import Q_EXTENSION_PATH


class VersionCommand(BasicCommand):
    NAME = 'version'
    DESCRIPTION = 'Displays the version of the Q CLI extension.'

    def __init__(self, session):
        super().__init__(session)

    def _run_main(self, parsed_args, parsed_globals):
        # version doesn't install the Q extension if needed like
        # chat does, so check Q_EXTENSION_PATH directly
        if not Path.is_file(Q_EXTENSION_PATH):
            raise RuntimeError(
                'The Q CLI extension is not installed. '
                'Run aws q chat or aws q upgrade to install it.'
            )

        with original_ld_library_path():
            subprocess.check_call(f'{Q_EXTENSION_PATH} --version'.split(' '))
