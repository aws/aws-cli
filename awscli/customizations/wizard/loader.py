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
"""Load wizards included in the AWS CLI.

Data Layout
===========

Within this directory, there's a ``wizards`` directory.  Each directory
maps to an existing CLI command name.

For each command directory, the filename corresponds to the name of
a wizard (with the .yml prefix stripped).  Any file that starts with
an underscore character is not listed as a wizard in the ``help`` command
output.

This means that wizards (at least these built-in ones) are only supported
from a top level CLI command.  For example::

    $ aws ec2 wizard <wizard-name>

You can also add a special file, `_main.yml` in a directory to indicate
the main wizard used when no wizard name is given.  For example::

    $ aws dynamodb wizard

will check if there's a ``dynamodb/_main.yml`` file.  If no file
exists, then a usage error will be printed.


"""
import os
import ruamel.yaml as yaml


WIZARD_SPEC_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'wizards',
)


class WizardNotExistError(Exception):
    pass


class WizardLoader(object):
    def __init__(self, spec_dir=None):
        if spec_dir is None:
            spec_dir = WIZARD_SPEC_DIR
        self._spec_dir = spec_dir

    def list_commands_with_wizards(self):
        """Returns a list of commands with at least one wizard.
        """
        return os.listdir(self._spec_dir)

    def list_available_wizards(self, command_name):
        """List the names of wizards available for a service.

        If no wizards are avaiable, then an empty list is returned.
        """
        files = os.listdir(os.path.join(self._spec_dir, command_name))
        return [os.path.splitext(f)[0] for f in files]

    def load_wizard(self, command_name, wizard_name):
        """Load a specific wizard.

        Given a command and wizard name (i.e something from the
        output of ``list_available_wizards``), return the loaded file.
        This will open the file and return the parsed yaml contents
        of the file.

        """
        filename = os.path.join(self._spec_dir, command_name,
                                wizard_name + '.yml')
        try:
            with open(filename) as f:
                return self._load_yaml(f.read())
        except (OSError, IOError):
            raise WizardNotExistError("Wizard does not exist for command "
                                      "'%s', name: '%s'" % (command_name,
                                                            wizard_name))

    def _load_yaml(self, contents):
        data = yaml.load(contents, Loader=yaml.RoundTripLoader)
        return data

    def wizard_exists(self, command_name, wizard_name):
        filename = os.path.join(self._spec_dir, command_name,
                                wizard_name + '.yml')
        return os.path.isfile(filename)
