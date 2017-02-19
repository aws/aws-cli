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
import sys

from awscli.customizations.commands import BasicCommand

from . import ConfigValue


class ConfigureExportCommand(BasicCommand):
    NAME = 'export'
    DESCRIPTION = (
        'List the AWS CLI configuration data.  This command will '
        'print a usable export command to be used with eval command '
    )
    SYNOPSIS = 'aws configure export [--profile profile-name]'
    EXAMPLES = (
        'To show your current configuration values::\n'
        '\n'
        '  $ aws configure export\n'
        '   export AWS_ACCESS_KEY_ID=****************ABCD\n'
        '   export AWS_SECRET_ACCESS_KEY=****************ABCD\n'
        '   export AWS_DEFAULT_REGION=us-west-2\n'
        '\n'
    )

    def __init__(self, session, stream=sys.stdout):
        super(ConfigureExportCommand, self).__init__(session)
        self._stream = stream

    def _run_main(self, args, parsed_globals):
        access_key, secret_key = self._lookup_credentials()
        region = self._lookup_config('region')
        self._stream.write('export AWS_ACCESS_KEY_ID=%s\n' % (access_key.value,))
        self._stream.write('export AWS_SECRET_ACCESS_KEY=%s\n' % (secret_key.value,))
        self._stream.write('export AWS_DEFAULT_REGION=%s\n' % (region.value,))

    def _lookup_credentials(self):
        # First try it with _lookup_config.  It's possible
        # that we don't find credentials this way (for example,
        # if we're using an IAM role).
        access_key = self._lookup_config('access_key')
        if access_key.value is not '':
            secret_key = self._lookup_config('secret_key')
            return access_key, secret_key
        else:
            # Otherwise we can try to use get_credentials().
            # This includes a few more lookup locations
            # (IAM roles, some of the legacy configs, etc.)
            credentials = self._session.get_credentials()
            if credentials is None:
                no_config = ConfigValue('', None, None)
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
            return ConfigValue('', None, None)
