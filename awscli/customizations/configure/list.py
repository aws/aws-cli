# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import profile
import sys

from awscli.customizations.commands import BasicCommand
#from tests.unit.customizations.test_overridesslcommonname import parsed_globals

from . import ConfigValue, NOT_SET

from awscli.formatter import get_formatter

class ConfigureListCommand(BasicCommand):
    NAME = 'list'
    DESCRIPTION = (
        'Lists the profile, access key, secret key, and region configuration '
        'information used for the specified profile. For each configuration '
        'item, it shows the value, where the configuration value '
        'was retrieved, and the configuration variable name.\n'
        '\n'
        'For example, '
        'if you provide the AWS region in an environment variable, this '
        'command shows you the name of the region you\'ve configured, '
        'that this value came from an environment '
        'variable, and the name of the environment '
        'variable.\n'
        '\n'
        'For temporary credential methods such as roles and IAM Identity '
        'Center, this command displays the temporarily cached access key and '
        'secret access key is displayed.\n'
    )
    SYNOPSIS = 'aws configure list [--profile profile-name]'
    EXAMPLES = (
        'To show your current configuration values::\n'
        '\n'
        '  $ aws configure list\n'
        '        Name                    Value             Type    Location\n'
        '        ----                    -----             ----    --------\n'
        '     profile                <not set>             None    None\n'
        '  access_key     ****************ABCD      config_file    ~/.aws/config\n'
        '  secret_key     ****************ABCD      config_file    ~/.aws/config\n'
        '      region                us-west-2              env    AWS_DEFAULT_REGION\n'
        '\n'
    )

    def __init__(self, session, stream=None):
        super(ConfigureListCommand, self).__init__(session)
        if stream is None:
            stream = sys.stdout
        self._stream = stream

    def _run_main(self, args, parsed_globals):
        if parsed_globals and parsed_globals.profile is not None:
            profile = ConfigValue(self._session.profile, 'manual', '--profile')
        else:
            profile = self._lookup_config('profile')

        access_key, secret_key = self._lookup_credentials()
        region = self._lookup_config('region')

        output_format = getattr(parsed_globals, 'output', None)

        if output_format and output_format != 'table':
            config_data = {
            'profile': {
                'value': profile.value,
                'type': profile.config_type,
                'location': profile.config_variable,
            },
            'access_key': {
                'value': access_key.value,
                'type': access_key.config_type,
                'location': access_key.config_variable,
            },
            'secret_key': {
                'value': secret_key.value,
                'type': secret_key.config_type,
                'location': secret_key.config_variable,
            },
            'region': {
                'value': region.value,
                'type': region.config_type,
                'location': region.config_variable,
            },
        }
            formatter = get_formatter(output_format, parsed_globals)
            formatter(self.NAME, config_data, stream=self._stream)
        else:
            self._display_config_value(
            ConfigValue('Value', 'Type', 'Location'), 'Name')
            self._display_config_value(
            ConfigValue('-----', '----', '--------'), '----')
            self._display_config_value(profile, 'profile')
            self._display_config_value(access_key, 'access_key')
            self._display_config_value(secret_key, 'secret_key')
            self._display_config_value(region, 'region')

        return 0

    def _display_config_value(self, config_value, config_name):
        self._stream.write('%10s %24s %16s    %s\n' % (
            config_name, config_value.value, config_value.config_type,
            config_value.config_variable))

    def _lookup_credentials(self):
        # First try it with _lookup_config.  It's possible
        # that we don't find credentials this way (for example,
        # if we're using an IAM role).
        access_key = self._lookup_config('access_key')
        if access_key.value is not NOT_SET:
            secret_key = self._lookup_config('secret_key')
            access_key.mask_value()
            secret_key.mask_value()
            return access_key, secret_key
        else:
            # Otherwise we can try to use get_credentials().
            # This includes a few more lookup locations
            # (IAM roles, some of the legacy configs, etc.)
            credentials = self._session.get_credentials()
            if credentials is None:
                no_config = ConfigValue(NOT_SET, None, None)
                return no_config, no_config
            else:
                # For the ConfigValue, we don't track down the
                # config_variable because that info is not
                # visible from botocore.credentials.  I think
                # the credentials.method is sufficient to show
                # where the credentials are coming from.
                access_key = ConfigValue(credentials.access_key,
                                         credentials.method, '')
                secret_key = ConfigValue(credentials.secret_key,
                                         credentials.method, '')
                access_key.mask_value()
                secret_key.mask_value()
                return access_key, secret_key

    def _lookup_config(self, name):
        # First try to look up the variable in the env.
        value = self._session.get_config_variable(name, methods=('env',))
        if value is not None:
            return ConfigValue(value, 'env', self._session.session_var_map[name][1])
        # Then try to look up the variable in the config file.
        value = self._session.get_config_variable(name, methods=('config',))
        if value is not None:
            return ConfigValue(value, 'config-file',
                               self._session.get_config_variable('config_file'))
        else:
            return ConfigValue(NOT_SET, None, None)
