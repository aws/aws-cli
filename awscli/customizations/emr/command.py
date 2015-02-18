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

import logging
from awscli.customizations.commands import BasicCommand
from awscli.customizations.emr import config
from awscli.customizations.emr import configutils

LOG = logging.getLogger(__name__)


class Command(BasicCommand):

    def __init__(self, session):
        super(Command, self).__init__(session)

        session.register('before-building-arg-table-parser.%s' % self.NAME,
                         self.override_args_required_option)

    def supports_arg(self, name):
        return any((x['name'] == name for x in self.ARG_TABLE))

    def _run_main(self, parsed_args, parsed_globals):
        self._apply_configs(parsed_args,
                            configutils.get_configs(self._session))
        return self._run_main_command(parsed_args, parsed_globals)

    def _apply_configs(self, parsed_args, parsed_configs):
        parsed_configs = configutils.get_configs(self._session)

        applicable_configurations = \
            self._get_applicable_configurations(parsed_args, parsed_configs)

        configs_added = {}
        for configuration in applicable_configurations:
            configuration.add(self, parsed_args,
                              parsed_configs[configuration.name])
            configs_added[configuration.name] = \
                parsed_configs[configuration.name]

        if configs_added:
            LOG.debug("Updated arguments with configs: %s" % configs_added)
        else:
            LOG.debug("No configs applied")
        LOG.debug("Running command with args: %s" % parsed_args)

    def _get_applicable_configurations(self, parsed_args, parsed_configs):
        # We need to find the applicable configurations by applying
        # following filters:
        # 1. Configurations that are applicable to this command
        # 3. Configurations that are present in parsed_configs
        # 2. Configurations that are not present in parsed_args

        configurations = \
            config.get_applicable_configurations(self)

        configurations = [x for x in configurations
                          if x.name in parsed_configs
                          and not x.is_present(parsed_args)]

        configurations = self._filter_configurations_in_special_cases \
            (configurations, parsed_args, parsed_configs)

        return configurations

    def _filter_configurations_in_special_cases(self, configurations,
                                                parsed_args, parsed_configs):
        # Subclasses can override this method to filter the applicable
        # configurations further based upon some custom logic
        # Default behavior is to return the configurations list as is
        return configurations

    def _run_main_command(self, parsed_args, parsed_globals):
        # Subclasses should implement this method.
        # parsed_globals are the parsed global args (things like region,
        # profile, output, etc.)
        # parsed_args are any arguments you've defined in your ARG_TABLE
        # that are parsed.
        # parsed_args are updated to include any emr specific configuration
        # from the config file if the corresponding argument is not
        # explicitly specified on the CLI
        raise NotImplementedError("_run_main_command")

    def override_args_required_option(self, arg_table, **kwargs):
        # This function overrides the 'required' property of an argument
        # if a value corresponding to that argument is present in the config
        # file
        parsed_configs = configutils.get_configs(self._session)
        for arg_name in arg_table.keys():
            if arg_name.replace('-', '_') in parsed_configs:
                arg_table[arg_name].required = False
