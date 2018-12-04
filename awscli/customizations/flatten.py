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

from awscli.arguments import CustomArgument

LOG = logging.getLogger(__name__)

# Nested argument member separator
SEP = '.'


class FlattenedArgument(CustomArgument):
    """
    A custom argument which has been flattened from an existing structure. When
    added to the call params it is hydrated back into the structure.

    Supports both an object and a list of objects, in which case the flattened
    parameters will hydrate a list with a single object in it.
    """
    def __init__(self, name, container, prop, help_text='', required=None,
                 type=None, hydrate=None, hydrate_value=None):
        self.type = type
        self._container = container
        self._property = prop
        self._hydrate = hydrate
        self._hydrate_value = hydrate_value
        super(FlattenedArgument, self).__init__(name=name, help_text=help_text,
                                                required=required)

    @property
    def cli_type_name(self):
        return self.type

    def add_to_params(self, parameters, value):
        """
        Hydrate the original structure with the value of this flattened
        argument.

        TODO: This does not hydrate nested structures (``XmlName1.XmlName2``)!
              To do this for now you must provide your own ``hydrate`` method.
        """
        container = self._container.argument_model.name
        cli_type = self._container.cli_type_name
        key = self._property

        LOG.debug('Hydrating {0}[{1}]'.format(container, key))

        if value is not None:
            # Convert type if possible
            if self.type == 'boolean':
                value = not value.lower() == 'false'
            elif self.type in ['integer', 'long']:
                value = int(value)
            elif self.type in ['float', 'double']:
                value = float(value)

            if self._hydrate:
                self._hydrate(parameters, container, cli_type, key, value)
            else:
                if container not in parameters:
                    if cli_type == 'list':
                        parameters[container] = [{}]
                    else:
                        parameters[container] = {}

                if self._hydrate_value:
                    value = self._hydrate_value(value)

                if cli_type == 'list':
                    parameters[container][0][key] = value
                else:
                    parameters[container][key] = value


class FlattenArguments(object):
    """
    Flatten arguments for one or more commands for a particular service from
    a given configuration which maps service call parameters to flattened
    names. Takes in a configuration dict of the form::

        {
            "command-cli-name": {
                "argument-cli-name": {
                    "keep": False,
                    "flatten": {
                        "XmlName": {
                            "name": "flattened-cli-name",
                            "type": "Optional custom type",
                            "required": "Optional custom required",
                            "help_text": "Optional custom docs",
                            "hydrate_value": Optional function to hydrate value,
                            "hydrate": Optional function to hydrate
                        },
                        ...
                    }
                },
                ...
            },
            ...
        }

    The ``type``, ``required`` and ``help_text`` arguments are entirely
    optional and by default are pulled from the model. You should only set them
    if you wish to override the default values in the model.

    The ``keep`` argument determines whether the original command is still
    accessible vs. whether it is removed. It defaults to ``False`` if not
    present, which removes the original argument.

    The keys inside of ``flatten`` (e.g. ``XmlName`` above) can include nested
    references to structures via a colon. For example, ``XmlName1:XmlName2``
    for the following structure::

        {
            "XmlName1": {
                "XmlName2": ...
            }
        }

    The ``hydrate_value`` function takes in a value and should return a value.
    It is only called when the value is not ``None``. Example::

        "hydrate_value": lambda (value): value.upper()

    The ``hydrate`` function takes in a list of existing parameters, the name
    of the container, its type, the name of the container key and its set
    value. For the example above, the container would be
    ``'argument-cli-name'``, the key would be ``'XmlName'`` and the value
    whatever the user passed in. Example::

        def my_hydrate(params, container, cli_type, key, value):
            if container not in params:
                params[container] = {'default': 'values'}

            params[container][key] = value

    It's possible for ``cli_type`` to be ``list``, in which case you should
    ensure that a list of one or more objects is hydrated rather than a
    single object.
    """
    def __init__(self, service_name, configs):
        self.configs = configs
        self.service_name = service_name

    def register(self, cli):
        """
        Register with a CLI instance, listening for events that build the
        argument table for operations in the configuration dict.
        """
        # Flatten each configured operation when they are built
        service = self.service_name
        for operation in self.configs:
            cli.register('building-argument-table.{0}.{1}'.format(service,
                                                                  operation),
                         self.flatten_args)

    def flatten_args(self, command, argument_table, **kwargs):
        # For each argument with a bag of parameters
        for name, argument in self.configs[command.name].items():
            argument_from_table = argument_table[name]
            overwritten = False

            LOG.debug('Flattening {0} argument {1} into {2}'.format(
                command.name, name,
                ', '.join([v['name'] for k, v in argument['flatten'].items()])
            ))

            # For each parameter to flatten out
            for sub_argument, new_config in argument['flatten'].items():
                config = new_config.copy()
                config['container'] = argument_from_table
                config['prop'] = sub_argument

                # Handle nested arguments
                _arg = self._find_nested_arg(
                    argument_from_table.argument_model, sub_argument
                )

                # Pull out docs and required attribute
                self._merge_member_config(_arg, sub_argument, config)

                # Create and set the new flattened argument
                new_arg = FlattenedArgument(**config)
                argument_table[new_config['name']] = new_arg

                if name == new_config['name']:
                    overwritten = True

            # Delete the original argument?
            if not overwritten and ('keep' not in argument or
                                    not argument['keep']):
                del argument_table[name]

    def _find_nested_arg(self, argument, name):
        """
        Find and return a nested argument, if it exists. If no nested argument
        is requested then the original argument is returned. If the nested
        argument cannot be found, then a ValueError is raised.
        """
        if SEP in name:
            # Find the actual nested argument to pull out
            LOG.debug('Finding nested argument in {0}'.format(name))
            for piece in name.split(SEP)[:-1]:
                for member_name, member in argument.members.items():
                    if member_name == piece:
                        argument = member
                        break
                else:
                    raise ValueError('Invalid piece {0}'.format(piece))

        return argument

    def _merge_member_config(self, argument, name, config):
        """
        Merges an existing config taken from the configuration dict with an
        existing member of an existing argument object. This pulls in
        attributes like ``required`` and ``help_text`` if they have not been
        overridden in the configuration dict. Modifies the config in-place.
        """
        # Pull out docs and required attribute
        for member_name, member in argument.members.items():
            if member_name == name.split(SEP)[-1]:
                if 'help_text' not in config:
                    config['help_text'] = member.documentation

                if 'required' not in config:
                    config['required'] = member_name in argument.required_members

                if 'type' not in config:
                    config['type'] = member.type_name

                break
