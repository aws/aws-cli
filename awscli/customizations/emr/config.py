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
from awscli.customizations.emr import configutils
from awscli.customizations.emr import exceptions

LOG = logging.getLogger(__name__)

SUPPORTED_CONFIG_LIST = [
    {'name': 'service_role'},
    {'name': 'log_uri'},
    {'name': 'instance_profile', 'arg_name': 'ec2_attributes',
     'arg_value_key': 'InstanceProfile'},
    {'name': 'key_name', 'arg_name': 'ec2_attributes',
     'arg_value_key': 'KeyName'},
    {'name': 'enable_debugging', 'type': 'boolean'},
    {'name': 'key_pair_file'}
]

TYPES = ['string', 'boolean']


def get_applicable_configurations(command):
    supported_configurations = _create_supported_configurations()
    return [x for x in supported_configurations if x.is_applicable(command)]


def _create_supported_configuration(config):
    config_type = config['type'] if 'type' in config else 'string'

    if (config_type == 'string'):
        config_arg_name = config['arg_name'] \
            if 'arg_name' in config else config['name']
        config_arg_value_key = config['arg_value_key'] \
            if 'arg_value_key' in config else None
        configuration = StringConfiguration(config['name'],
                                            config_arg_name,
                                            config_arg_value_key)
    elif (config_type == 'boolean'):
        configuration = BooleanConfiguration(config['name'])

    return configuration


def _create_supported_configurations():
    return [_create_supported_configuration(config)
            for config in SUPPORTED_CONFIG_LIST]


class Configuration(object):

    def __init__(self, name, arg_name):
        self.name = name
        self.arg_name = arg_name

    def is_applicable(self, command):
        raise NotImplementedError("is_applicable")

    def is_present(self, parsed_args):
        raise NotImplementedError("is_present")

    def add(self, command, parsed_args, value):
        raise NotImplementedError("add")

    def _check_arg(self, parsed_args, arg_name):
        return getattr(parsed_args, arg_name, None)


class StringConfiguration(Configuration):

    def __init__(self, name, arg_name, arg_value_key=None):
        super(StringConfiguration, self).__init__(name, arg_name)
        self.arg_value_key = arg_value_key

    def is_applicable(self, command):
        return command.supports_arg(self.arg_name.replace('_', '-'))

    def is_present(self, parsed_args):
        if (not self.arg_value_key):
            return self._check_arg(parsed_args, self.arg_name)
        else:
            return self._check_arg(parsed_args, self.arg_name) \
                and self.arg_value_key in getattr(parsed_args, self.arg_name)

    def add(self, command, parsed_args, value):
        if (not self.arg_value_key):
            setattr(parsed_args, self.arg_name, value)
        else:
            if (not self._check_arg(parsed_args, self.arg_name)):
                setattr(parsed_args, self.arg_name, {})
            getattr(parsed_args, self.arg_name)[self.arg_value_key] = value


class BooleanConfiguration(Configuration):

    def __init__(self, name):
        super(BooleanConfiguration, self).__init__(name, name)
        self.no_version_arg_name = "no_" + name

    def is_applicable(self, command):
        return command.supports_arg(self.arg_name.replace('_', '-')) and \
            command.supports_arg(self.no_version_arg_name.replace('_', '-'))

    def is_present(self, parsed_args):
        return self._check_arg(parsed_args, self.arg_name) \
            or self._check_arg(parsed_args, self.no_version_arg_name)

    def add(self, command, parsed_args, value):
        if (value.lower() == 'true'):
            setattr(parsed_args, self.arg_name, True)
            setattr(parsed_args, self.no_version_arg_name, False)
        elif (value.lower() == 'false'):
            setattr(parsed_args, self.arg_name, False)
            setattr(parsed_args, self.no_version_arg_name, True)
        else:
            raise exceptions.InvalidBooleanConfigError(
                config_value=value,
                config_key=self.arg_name,
                profile_var_name=configutils.get_current_profile_var_name(
                    command._session))
