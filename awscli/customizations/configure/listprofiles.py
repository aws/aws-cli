# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import sys

from awscli.customizations.commands import BasicCommand
from awscli.customizations.utils import uni_print


class ListProfilesCommand(BasicCommand):
    NAME = 'list-profiles'
    DESCRIPTION = (
        'List the profiles available to the AWS CLI.'
    )
    EXAMPLES = (
        'aws configure list-profiles\n\n'
    )

    def __init__(self, session, out_stream=None):
        super(ListProfilesCommand, self).__init__(session)

        if out_stream is None:
            out_stream = sys.stdout
        self._out_stream = out_stream

    def _run_main(self, parsed_args, parsed_globals):
        for profile in self._session.available_profiles:
            uni_print('%s\n' % profile, out_file=self._out_stream)
        return 0
