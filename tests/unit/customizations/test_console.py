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
from argparse import Namespace

from botocore.compat import json
from botocore.credentials import ReadOnlyCredentials

from awscli.customizations.console import ConsoleCommand
from awscli.customizations.exceptions import ParamValidationError
from awscli.testutils import mock, unittest


class FakeResponse:
    def __init__(self, status_code=200, text=''):
        self.status_code = status_code
        self.text = text


class TestConsoleCommand(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock()
        # Temporary credentials by default (SSO / assume-role style).
        creds = mock.Mock()
        creds.get_frozen_credentials.return_value = ReadOnlyCredentials(
            'AKID', 'SKID', 'TOKEN'
        )
        self.session.get_credentials.return_value = creds
        self.session.get_config_variable.return_value = None

        # Partition resolution -> aws.
        resolver = mock.Mock()
        resolver.get_partition_for_region.return_value = 'aws'
        self.session._get_internal_component.return_value = resolver

        # Endpoints data used for global-service detection.
        self.session.get_data.return_value = {
            'partitions': [
                {
                    'partition': 'aws',
                    'services': {
                        's3': {'isRegionalized': False},
                        'ec2': {'isRegionalized': True},
                    },
                }
            ]
        }

        # STS client for multi-session account id.
        sts = mock.Mock()
        sts.get_caller_identity.return_value = {'Account': '123456789012'}
        self.session.create_client.return_value = sts

        self.http = mock.Mock()
        self.http.send.return_value = FakeResponse(
            200, json.dumps({'SigninToken': 'THE-TOKEN'})
        )
        self.opened = []
        self.printed = []
        self.command = ConsoleCommand(
            self.session, http=self.http, opener=self.opened.append
        )
        self.command._stdout = self.printed.append

    def _args(self, **overrides):
        defaults = dict(
            service=None,
            print_url=False,
            browser=None,
            region='eu-west-1',
            destination=None,
        )
        defaults.update(overrides)
        return Namespace(**defaults)

    def _globals(self, region=None, verify_ssl=True):
        return Namespace(region=region, verify_ssl=verify_ssl)

    def _last_login_url(self):
        # opener receives the login URL
        return self.opened[-1]

    def _destination_of(self, url):
        from urllib.parse import parse_qs, unquote

        from botocore.compat import urlsplit

        qs = parse_qs(urlsplit(url).query)
        return unquote(qs['Destination'][0])

    # -- happy paths --------------------------------------------------------

    def test_console_home_default(self):
        rc = self.command._run_main(self._args(), self._globals())
        self.assertEqual(rc, 0)
        url = self._last_login_url()
        self.assertTrue(
            url.startswith('https://signin.aws.amazon.com/federation?')
        )
        self.assertIn('Action=login', url)
        self.assertIn('SigninToken=THE-TOKEN', url)
        self.assertEqual(
            self._destination_of(url),
            'https://eu-west-1.console.aws.amazon.com/console/home'
            '?region=eu-west-1&account=123456789012',
        )

    def test_service_deep_link(self):
        self.command._run_main(self._args(service='ec2'), self._globals())
        self.assertEqual(
            self._destination_of(self._last_login_url()),
            'https://eu-west-1.console.aws.amazon.com/go/view'
            '?service=ec2&region=eu-west-1&account=123456789012',
        )

    def test_service_uses_go_view_for_any_service(self):
        # The console resolves the actual path server-side (e.g. global
        # services or slug differences), so the CLI passes the name as-is.
        self.command._run_main(self._args(service='s3'), self._globals())
        self.assertEqual(
            self._destination_of(self._last_login_url()),
            'https://eu-west-1.console.aws.amazon.com/go/view'
            '?service=s3&region=eu-west-1&account=123456789012',
        )

    def test_account_scoping_always_applied(self):
        self.command._run_main(self._args(service='ec2'), self._globals())
        self.assertIn('account%3D123456789012', self._last_login_url())

    def test_print_url_does_not_open_browser(self):
        self.command._run_main(self._args(print_url=True), self._globals())
        self.assertEqual(self.opened, [])
        self.assertEqual(len(self.printed), 1)
        self.assertIn('Action=login', self.printed[0])

    def test_custom_destination_overrides(self):
        dest = 'https://eu-west-1.console.aws.amazon.com/ec2/home#Instances:'
        self.command._run_main(self._args(destination=dest), self._globals())
        self.assertEqual(self._destination_of(self._last_login_url()), dest)

    # -- partitions ---------------------------------------------------------

    def test_eusc_partition_hosts(self):
        resolver = self.session._get_internal_component.return_value
        resolver.get_partition_for_region.return_value = 'aws-eusc'
        self.command._run_main(
            self._args(service='ec2', region='eusc-de-east-1'),
            self._globals(),
        )
        url = self._last_login_url()
        self.assertTrue(
            url.startswith(
                'https://eusc-de-east-1.signin.amazonaws-eusc.eu/federation?'
            )
        )
        self.assertEqual(
            self._destination_of(url),
            'https://eusc-de-east-1.console.amazonaws-eusc.eu/go/view'
            '?service=ec2&region=eusc-de-east-1&account=123456789012',
        )

    def test_unsupported_partition_errors(self):
        resolver = self.session._get_internal_component.return_value
        resolver.get_partition_for_region.return_value = 'aws-iso'
        with self.assertRaises(ParamValidationError):
            self.command._run_main(
                self._args(region='us-iso-east-1'), self._globals()
            )

    # -- credential guards --------------------------------------------------

    def test_missing_credentials_errors(self):
        self.session.get_credentials.return_value = None
        with self.assertRaises(ParamValidationError):
            self.command._run_main(self._args(), self._globals())

    def test_long_term_credentials_rejected(self):
        creds = mock.Mock()
        creds.get_frozen_credentials.return_value = ReadOnlyCredentials(
            'AKID', 'SKID', None
        )
        self.session.get_credentials.return_value = creds
        with self.assertRaises(ParamValidationError):
            self.command._run_main(self._args(), self._globals())

    def test_federation_http_error_raises(self):
        self.http.send.return_value = FakeResponse(500, 'boom')
        with self.assertRaises(RuntimeError):
            self.command._run_main(self._args(), self._globals())

    # -- argument parsing (guards the real parser, not just Namespace) ------

    def test_service_positional_is_optional(self):
        # Regression: the positional `service` must be optional so that
        # `aws console --print-url` (no service) does not error.
        from awscli.argparser import ArgTableArgParser

        parser = ArgTableArgParser(self.command._build_arg_table())
        parsed, _ = parser.parse_known_args(['--print-url'])
        self.assertIsNone(parsed.service)
        self.assertTrue(parsed.print_url)

    def test_service_positional_is_parsed(self):
        from awscli.argparser import ArgTableArgParser

        parser = ArgTableArgParser(self.command._build_arg_table())
        parsed, _ = parser.parse_known_args(['ec2', '--print-url'])
        self.assertEqual(parsed.service, 'ec2')


if __name__ == '__main__':
    unittest.main()
