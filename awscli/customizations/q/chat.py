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

from botocore.utils import original_ld_library_path

from awscli.customizations.commands import BasicCommand
from awscli.customizations.q.utils import _get_executable_path_or_download


class ChatCommand(BasicCommand):
    NAME = 'chat'
    DESCRIPTION = (
        'Launch Amazon Q Developer, which can translate natural language '
        'to AWS CLI commands.'
    )

    def __init__(self, session):
        super().__init__(session)

    def _run_main(self, parsed_args, parsed_globals):
        path = _get_executable_path_or_download()
        if not path:
            raise RuntimeError('Amazon Q extension is not found.')

        # TODO pass through credentials and region
        with original_ld_library_path():
            subprocess.check_call(path)
