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
import os
from urllib.parse import urlparse

from awscli.customizations.configure.writer import ConfigFileWriter
from awscli.customizations.sso.resolve import (
    is_aws_owned_domain,
    resolve_start_url,
)
from awscli.customizations.sso.utils import (
    LOGIN_ARGS,
    BaseSSOCommand,
    PrintOnlyHandler,
    do_sso_login,
)
from awscli.customizations.utils import uni_print


class LoginCommand(BaseSSOCommand):
    NAME = 'login'
    DESCRIPTION = (
        'Retrieves and caches an AWS IAM Identity Center access token to '
        'exchange for AWS credentials. To login, the requested profile must '
        'have first been setup using ``aws configure sso``. Each time the '
        '``login`` command is called, a new SSO access token will be '
        'retrieved. Please note that only one login session can be active for '
        'a given SSO Session and creating multiple profiles does not allow for'
        ' multiple users to be authenticated against the same SSO Session.'
    )
    ARG_TABLE = LOGIN_ARGS + [
        {
            'name': 'sso-session',
            'help_text': (
                'An explicit SSO session to use to login. By default, this '
                'command will login using the SSO session configured as part '
                'of the requested profile and generally does not require this '
                'argument to be set.'
            ),
        }
    ]

    def _run_main(self, parsed_args, parsed_globals):
        sso_config = self._get_sso_config(sso_session=parsed_args.sso_session)
        start_url = sso_config['sso_start_url']
        configured_region = sso_config.get('sso_region')

        resolved_url, region = resolve_start_url(
            start_url,
            session=self._session,
            configured_region=configured_region,
            timeout=parsed_globals.connect_timeout,
        )

        on_pending_authorization = None
        if parsed_args.no_browser:
            on_pending_authorization = PrintOnlyHandler()
        do_sso_login(
            session=self._session,
            parsed_globals=parsed_globals,
            sso_region=region,
            start_url=start_url,
            resolved_start_url=resolved_url,
            on_pending_authorization=on_pending_authorization,
            force_refresh=True,
            session_name=sso_config.get('session_name'),
            registration_scopes=sso_config.get('registration_scopes'),
            use_device_code=parsed_args.use_device_code,
        )

        # Only rewrite sso_region after successful login.
        hostname = urlparse(start_url).hostname
        if hostname and not is_aws_owned_domain(hostname):
            if configured_region != region:
                self._write_sso_region(sso_config, region)

        success_msg = 'Successfully logged into Start URL: %s\n'
        uni_print(success_msg % start_url)
        return 0

    def _write_sso_region(self, sso_config, new_region):
        session_name = sso_config.get('session_name')
        config_path = os.path.expanduser(
            self._session.get_config_variable('config_file')
        )
        writer = ConfigFileWriter()
        if session_name:
            section = f'sso-session {session_name}'
        else:
            profile = self._session.get_config_variable('profile') or 'default'
            section = f'profile {profile}'
        writer.update_config(
            {'__section__': section, 'sso_region': new_region},
            config_path,
        )
