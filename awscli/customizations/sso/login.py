# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
from awscli.customizations.commands import BasicCommand
from awscli.customizations.sso.utils import do_sso_login
from awscli.customizations.utils import uni_print
from awscli.customizations.exceptions import ConfigurationError


class InvalidSSOConfigError(ConfigurationError):
    pass


class LoginCommand(BasicCommand):
    NAME = 'login'
    DESCRIPTION = (
        'Retrieves and caches an AWS SSO access token to exchange for AWS '
        'credentials. To login, the requested profile must have first been '
        'setup using ``aws configure sso``. Each time the ``login`` command '
        'is called, a new SSO access token will be retrieved.'
    )
    ARG_TABLE = []
    _REQUIRED_SSO_CONFIG_VARS = [
        'sso_start_url',
        'sso_region',
        'sso_role_name',
        'sso_account_id',
    ]

    def _run_main(self, parsed_args, parsed_globals):
        sso_config = self._get_sso_config()
        do_sso_login(
            session=self._session,
            sso_region=sso_config['sso_region'],
            start_url=sso_config['sso_start_url'],
            force_refresh=True
        )
        success_msg = 'Successully logged into Start URL: %s\n'
        uni_print(success_msg % sso_config['sso_start_url'])
        return 0

    def _get_sso_config(self):
        scoped_config = self._session.get_scoped_config()
        sso_config = {}
        missing_vars = []
        for config_var in self._REQUIRED_SSO_CONFIG_VARS:
            if config_var not in scoped_config:
                missing_vars.append(config_var)
            else:
                sso_config[config_var] = scoped_config[config_var]
        if missing_vars:
            raise InvalidSSOConfigError(
                'Missing the following required SSO configuration values: %s. '
                'To make sure this profile is properly configured to use SSO, '
                'please run: aws configure sso' % ', '.join(missing_vars)
            )
        return sso_config
