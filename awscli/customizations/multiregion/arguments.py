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

from awscli.arguments import CustomArgument
from awscli.customizations.multiregion.caller import (
    MultiRegionOperationCaller,
)
from awscli.customizations.multiregion.validation import (
    parse_multi_regions,
    validate_options,
)

MULTI_REGIONS_NAME = 'multi-regions'
MULTI_REGIONS_DEST = 'multi_regions'

MULTI_REGIONS_HELP = (
    '<p>Runs the operation in several regions and merges the results. '
    'Takes a comma-separated list of regions in one partition (for example '
    '<code>us-east-1,eu-west-1</code>), or <code>all</code> for every '
    'enabled region that offers the service. Each returned object has a '
    '<code>_CliScope</code> member naming its region. If any region '
    'fails, the command stops and reports the error. Cannot be used '
    'with <code>--region</code> or <code>--endpoint-url</code>.</p>'
)


class MultiRegionsArgument(CustomArgument):
    """The ``--multi-regions`` option of a single command.

    Its value is resolved once the operation's arguments are parsed.  The
    command's operation caller is then replaced by one that runs the
    operation in every region, so the fan-out happens where the
    single-region call would have been made.
    """

    def __init__(self, session, command):
        super().__init__(
            name=MULTI_REGIONS_NAME,
            help_text=MULTI_REGIONS_HELP,
            dest=MULTI_REGIONS_DEST,
        )
        self._session = session
        self._command = command
        self._single_region_caller = command._operation_caller
        # The handler acts only for this command, because the argument
        # holds this command's operation, and other commands' argument
        # tables can be built in the same session (by --cli-auto-prompt,
        # for example).
        command_id = f'{command._parent_name}.{command.name}'
        session.register(f'operation-args-parsed.{command_id}', self.resolve)

    def resolve(self, parsed_args, parsed_globals, **kwargs):
        # Reset first, so that a run without the option is not affected
        # by an earlier run of the same command object.
        self._command._operation_caller = self._single_region_caller
        value = getattr(parsed_args, MULTI_REGIONS_DEST, None)
        if value is None:
            return
        spec = parse_multi_regions(value)
        validate_options(spec, parsed_globals, self._session)
        parsed_globals.multi_regions = spec
        # A new caller for every run, since it holds that run's results.
        self._command._operation_caller = MultiRegionOperationCaller(
            self._session, self._single_region_caller, spec
        )
