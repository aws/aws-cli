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
import ruamel.yaml as yaml
from awscli.customizations.commands import BasicCommand
from awscli.customizations.wizard import factory


def register_dev_commands(event_handlers):
    event_handlers.register('building-command-table.cli-dev',
                            WizardDev.add_command)


def create_default_wizard_dev_runner(session):
    runner = factory.create_default_wizard_runner(session)
    return WizardDevRunner(
        wizard_loader=WizardLoader(),
        wizard_runner=runner
    )


class WizardLoader(object):
    def load(self, contents):
        data = yaml.load(contents, Loader=yaml.RoundTripLoader)
        return data


class WizardDevRunner(object):
    def __init__(self, wizard_loader, wizard_runner):
        self._wizard_loader = wizard_loader
        self._wizard_runner = wizard_runner

    def run_wizard(self, wizard_contents):
        """Run a single wizard given the contents as a string."""
        loaded = self._wizard_loader.load(wizard_contents)
        self._wizard_runner.run(loaded)


class WizardDev(BasicCommand):
    NAME = 'wizard-dev'
    DESCRIPTION = (
        'Internal command from developing, testing and debugging wizards.\n'
        'This command is not intended for normal end usage. '
        'Do not rely on this command, backwards compatibility '
        'is not guaranteed.  This command may be removed in '
        'future versions.\n'
    )
    ARG_TABLE = [
        {'name': 'run-wizard',
         'help_text': 'Run a wizard given a wizard file.'}
    ]

    def __init__(self, session, dev_runner=None):
        super(WizardDev, self).__init__(session)
        if dev_runner is None:
            dev_runner = create_default_wizard_dev_runner(session)
        self._dev_runner = dev_runner

    def _run_main(self, args, parsed_globals):
        if args.run_wizard is not None:
            return self._run_wizard(args.run_wizard)

    def _run_wizard(self, wizard_contents):
        self._dev_runner.run_wizard(wizard_contents)
        return 0
