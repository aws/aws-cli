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
from awscli.customizations.sso.utils import (
    do_sso_login, PrintOnlyHandler, LOGIN_ARGS, BaseSSOCommand,
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
            )
        }
    ]

    def _run_main(self, parsed_args, parsed_globals):
        sso_config = self._get_sso_config(sso_session=parsed_args.sso_session)
        on_pending_authorization = None
        if parsed_args.no_browser:
            on_pending_authorization = PrintOnlyHandler()
        do_sso_login(
            session=self._session,
            sso_region=sso_config['sso_region'],
            start_url=sso_config['sso_start_url'],
            on_pending_authorization=on_pending_authorization,
            force_refresh=True,
            session_name=sso_config.get('session_name'),
            registration_scopes=sso_config.get('registration_scopes'),
            use_device_code=parsed_args.use_device_code,
        )
        success_msg = 'Successfully logged into Start URL: %s\n'
        uni_print(success_msg % sso_config['sso_start_url'])
        return 0
