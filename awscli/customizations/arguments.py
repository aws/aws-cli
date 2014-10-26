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
from awscli.arguments import CustomArgument


class OverrideRequiredArgsArgument(CustomArgument):
    """An argument that if specified makes all other arguments not required

    By not required, it refers to not having an error thrown when the
    parser does not find an argument that is required on the command line.
    To obtain this argument's property of ignoring required arguments,
    subclass from this class and fill out the ``ARG_DATA`` parameter as
    described below. Note this class is really only useful for subclassing.
    """

    # ``ARG_DATA`` follows the same format as a member of ``ARG_TABLE`` in
    # ``BasicCommand`` class as specified in
    # ``awscli/customizations/commands.py``.
    #
    # For example, an ``ARG_DATA`` variable would be filled out as:
    #
    # ARG_DATA =
    # {'name': 'my-argument',
    #  'help_text': 'This is argument ensures the argument is specified'
    #               'no other arguments are required'}
    ARG_DATA = {'name': 'no-required-args'}

    def __init__(self, session):
        self._session = session
        self._register_argument_action()
        super(OverrideRequiredArgsArgument, self).__init__(**self.ARG_DATA)

    def _register_argument_action(self):
        self._session.register('before-building-argument-table-parser',
                               self.override_required_args)

    def override_required_args(self, argument_table, args, **kwargs):
        name_in_cmdline = '--' + self.name
        # Set all ``Argument`` objects in ``argument_table`` to not required
        # if this argument's name is present in the command line.
        if name_in_cmdline in args:
            for arg_name in argument_table.keys():
                argument_table[arg_name].required = False
