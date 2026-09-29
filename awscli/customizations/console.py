# Copyright 2026 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
"""Open the AWS Management Console in a browser for the current credentials.

``aws console`` turns the credentials already resolved for the current profile
into a Console sign-in URL using the documented AWS federation flow, then opens
it in a browser (or prints it with ``--print-url``).

The command does not read credential caches or handle long-term secrets itself:
it asks the configured credential provider chain (the same one every ``aws``
call uses) for *temporary* credentials and exchanges them for a short-lived
sign-in token. Long-term IAM user keys are therefore not supported (there is no
session token to federate); use an IAM Identity Center (SSO) or assume-role
profile.
"""

import logging
import webbrowser

from botocore.awsrequest import AWSRequest
from botocore.compat import json, urlencode
from botocore.httpsession import URLLib3Session

from awscli.customizations.commands import BasicCommand
from awscli.customizations.exceptions import ParamValidationError

logger = logging.getLogger(__name__)

# Per-partition console + sign-in hosts.
#
#   console_fmt : format string for the console host, given {region}
#   signin_fmt  : format string for the federation host, given {region}
#   region_in_console : whether the console host is region-prefixed
#
# Sources:
#   * aws        : long-standing, in daily use.
#   * aws-eusc   : verified from the AWS European Sovereign Cloud endpoints
#                  reference (docs.aws.eu .../gr/endpoints.html): the console is
#                  ``<region>.console.amazonaws-eusc.eu`` and the sign-in portal
#                  is ``<region>.signin.amazonaws-eusc.eu``.
#   * aws-cn / aws-us-gov : from public documentation; NOT re-verified here.
#     (Flagged in the PR for maintainer confirmation.)
_PARTITION_HOSTS = {
    'aws': {
        'console': 'https://{region}.console.aws.amazon.com',
        'signin': 'https://signin.aws.amazon.com',
    },
    'aws-cn': {
        'console': 'https://{region}.console.amazonaws.cn',
        'signin': 'https://signin.amazonaws.cn',
    },
    'aws-us-gov': {
        'console': 'https://{region}.console.amazonaws-us-gov.com',
        'signin': 'https://signin.amazonaws-us-gov.com',
    },
    'aws-eusc': {
        'console': 'https://{region}.console.amazonaws-eusc.eu',
        'signin': 'https://{region}.signin.amazonaws-eusc.eu',
    },
}


class ConsoleCommand(BasicCommand):
    NAME = 'console'
    DESCRIPTION = (
        'Open the AWS Management Console in your browser, signed in with the '
        'credentials resolved for the current profile. Optionally deep-link to '
        'a specific service.\n\n'
        'This uses the standard AWS federation sign-in flow, which requires '
        'temporary credentials (for example from IAM Identity Center (SSO) or '
        'an assumed role). Long-term IAM user access keys are not supported.'
        '\n\n'
        'The AWS Management Console can keep several identities signed in at '
        'once (multi-session). This is a per-browser opt-in (Turn on '
        'multi-session in the console account menu); when enabled, the console '
        'routes each distinct identity to its own session. Signing in again '
        'with the same identity replaces that session. This command federates '
        "the current profile's identity; it does not change the browser's "
        'multi-session setting.'
    )
    SYNOPSIS = (
        'aws console [service] [--print-url] [--browser <name>] '
        '[--region <region>] [--destination <url>]'
    )
    EXAMPLES = (
        'Open the console home for the current profile::\n\n'
        '    $ aws console\n\n'
        'Open a service console directly::\n\n'
        '    $ aws console ec2\n'
        '    $ aws console s3\n\n'
        'Print the sign-in URL instead of opening a browser::\n\n'
        '    $ aws console --print-url\n\n'
        'Open in a specific browser::\n\n'
        '    $ aws console --browser firefox\n'
    )
    ARG_TABLE = [
        {
            'name': 'service',
            'nargs': '?',
            'default': None,
            'cli_type_name': 'string',
            'positional_arg': True,
            'help_text': (
                'Optional service to deep-link into, for example ``ec2``, '
                '``s3`` or ``lambda``. The console resolves the destination '
                'for the service; an unrecognized service opens the console '
                'home. Use ``--destination`` for an exact URL.'
            ),
        },
        {
            'name': 'print-url',
            'action': 'store_true',
            'default': False,
            'help_text': (
                'Print the sign-in URL to stdout instead of opening a browser.'
            ),
        },
        {
            'name': 'browser',
            'help_text': (
                'Open the URL in a specific browser (a name registered with '
                "Python's webbrowser module, for example ``firefox`` or "
                '``chrome``). Defaults to the system default browser. '
                'Availability of named browsers is platform dependent.'
            ),
        },
        {
            'name': 'region',
            'help_text': (
                'Console landing region. Defaults to the resolved region, or '
                "the first region of the credentials' partition."
            ),
        },
        {
            'name': 'destination',
            'help_text': (
                'A custom destination URL to land on after sign-in. Overrides '
                'the region/service handling.'
            ),
        },
    ]

    def __init__(self, session, http=None, opener=None):
        super().__init__(session)
        self._http = http
        self._opener = opener

    def _run_main(self, args, parsed_globals):
        service = args.service

        region = (
            args.region
            or parsed_globals.region
            or self._session.get_config_variable('region')
            or 'us-east-1'
        )

        partition = self._resolve_partition(region)
        hosts = _PARTITION_HOSTS.get(partition)
        if hosts is None:
            raise ParamValidationError(
                "aws console does not support the '{}' partition "
                '(region {}). Console sign-in URL generation is only '
                'available for: {}.'.format(
                    partition, region, ', '.join(sorted(_PARTITION_HOSTS))
                )
            )

        frozen = self._resolve_temporary_credentials()

        # Scope the destination to the account so that, when the browser has
        # multi-session enabled, distinct identities are routed to their own
        # session subdomain.
        account_id = self._resolve_account_id(parsed_globals)

        destination = args.destination or self._build_destination(
            hosts, region, service, account_id
        )

        signin_token = self._get_signin_token(hosts, region, frozen)
        login_url = self._build_login_url(
            hosts, region, destination, signin_token
        )

        if args.print_url:
            self._stdout(login_url)
        else:
            self._open_browser(args.browser, login_url)
            what = f'AWS {service} console' if service else 'AWS Console'
            acct = f' (account {account_id})' if account_id else ''
            logger.debug('Opened %s%s in region %s', what, acct, region)
        return 0

    # -- credential + identity resolution (delegated to the CLI) -------------

    def _resolve_temporary_credentials(self):
        credentials = self._session.get_credentials()
        if credentials is None:
            raise ParamValidationError(
                'Unable to resolve credentials. Configure a profile or run '
                '"aws sso login" first.'
            )
        frozen = credentials.get_frozen_credentials()
        if frozen.token is None:
            raise ParamValidationError(
                'aws console requires temporary credentials (a session '
                'token). Long-term IAM user keys are not supported; use an '
                'IAM Identity Center (SSO) or assume-role profile.'
            )
        return frozen

    def _resolve_account_id(self, parsed_globals):
        try:
            sts = self._session.create_client(
                'sts',
                region_name=parsed_globals.region,
                verify=parsed_globals.verify_ssl,
            )
            return sts.get_caller_identity()['Account']
        except Exception as e:
            logger.debug('Could not resolve account id: %s', e)
            return None

    def _resolve_partition(self, region):
        resolver = self._session._get_internal_component('endpoint_resolver')
        return resolver.get_partition_for_region(region)

    # -- URL construction ----------------------------------------------------

    def _build_destination(self, hosts, region, service, account_id):
        if service:
            # The console's /go/view endpoint resolves the correct destination
            # for a service server-side (regional vs global, path/slug
            # differences such as stepfunctions -> states, and an unknown
            # service falls back to the console home). This avoids maintaining
            # a service-to-console-path map in the CLI.
            base = '{}/go/view?service={}&region={}'.format(
                hosts['console'].format(region=region),
                service,
                region,
            )
        else:
            base = '{}/console/home?region={}'.format(
                hosts['console'].format(region=region),
                region,
            )
        if account_id:
            sep = '&' if '?' in base else '?'
            base = f'{base}{sep}account={account_id}'
        return base

    def _get_signin_token(self, hosts, region, frozen):
        session_json = json.dumps(
            {
                'sessionId': frozen.access_key,
                'sessionKey': frozen.secret_key,
                'sessionToken': frozen.token,
            }
        )
        # SessionDuration must be omitted for temporary credentials.
        params = urlencode(
            {'Action': 'getSigninToken', 'Session': session_json}
        )
        url = '{}/federation?{}'.format(
            hosts['signin'].format(region=region),
            params,
        )
        response = self._send(url)
        return json.loads(response)['SigninToken']

    def _build_login_url(self, hosts, region, destination, signin_token):
        params = urlencode(
            {
                'Action': 'login',
                'Issuer': 'aws-cli',
                'Destination': destination,
                'SigninToken': signin_token,
            }
        )
        return '{}/federation?{}'.format(
            hosts['signin'].format(region=region),
            params,
        )

    # -- side effects (injectable for tests) --------------------------------

    def _send(self, url):
        http = self._http or URLLib3Session()
        request = AWSRequest(method='GET', url=url)
        response = http.send(request.prepare())
        status = response.status_code
        if status != 200:
            raise RuntimeError(
                f'The AWS federation endpoint returned HTTP {status}.'
            )
        return response.text

    def _open_browser(self, browser, url):
        if self._opener is not None:
            self._opener(url)
            return
        if browser:
            try:
                controller = webbrowser.get(browser)
            except webbrowser.Error:
                raise ParamValidationError(
                    f"Could not find a browser named '{browser}'. Omit --browser to "
                    'use the system default, or set the BROWSER environment '
                    'variable.'
                )
            controller.open(url)
        else:
            webbrowser.open(url)

    def _stdout(self, text):
        import sys

        sys.stdout.write(text + '\n')
