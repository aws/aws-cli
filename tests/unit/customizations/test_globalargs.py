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
from botocore.session import get_session
from botocore.handlers import disable_signing
import os

from awscli.testutils import mock, unittest
from awscli.customizations import globalargs


class FakeParsedArgs(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __getattr__(self, arg):
        return None


class FakeSession(object):

    def __init__(self, session_vars=None, config_file_vars=None):
        if session_vars is None:
            session_vars = {}
        self.session_var_map = session_vars
        if config_file_vars is None:
            config_file_vars = {}
        self.config_file_vars = config_file_vars

    def get_config_variable(self, name, methods=('env', 'config'),
                            default=None):
        value = None
        config_name, envvar_name = self.session_var_map[name]
        if methods is not None:
            if 'env' in methods and value is None:
                value = os.environ.get(envvar_name)
            if 'config' in methods and value is None:
                value = self.config_file_vars.get(config_name)
        else:
            value = default
        return value


class TestGlobalArgsCustomization(unittest.TestCase):

    def test_parse_query(self):
        parsed_args = FakeParsedArgs(query='foo.bar')
        globalargs.resolve_types(parsed_args)
        # Assert that it looks like a jmespath parsed expression.
        self.assertFalse(isinstance(parsed_args.query, str))
        self.assertTrue(hasattr(parsed_args.query, 'search'))

    def test_parse_query_error_message(self):
        # Invalid jmespath expression.
        parsed_args = FakeParsedArgs(query='foo.bar.')
        with self.assertRaises(ValueError):
            globalargs.resolve_types(parsed_args)
            globalargs.resolve_types('query')

    def test_parse_verify_ssl_default_value(self):
        with mock.patch('os.environ', {}):
            parsed_args = FakeParsedArgs(verify_ssl=True, ca_bundle=None)
            session_var_map = {'ca_bundle': ('ca_bundle', 'AWS_CA_BUNDLE')}
            session = FakeSession(session_vars=session_var_map)
            globalargs.resolve_verify_ssl(parsed_args, session)
            # None, so that botocore can apply it's default logic.
            self.assertIsNone(parsed_args.verify_ssl)

    def test_parse_verify_ssl_verify_turned_off(self):
        with mock.patch('os.environ', {}):
            parsed_args = FakeParsedArgs(verify_ssl=False, ca_bundle=None)
            session_var_map = {'ca_bundle': ('ca_bundle', 'AWS_CA_BUNDLE')}
            session = FakeSession(session_vars=session_var_map)
            globalargs.resolve_verify_ssl(parsed_args, session)
            self.assertFalse(parsed_args.verify_ssl)

    def test_cli_overrides_cert_bundle(self):
        environ = {}
        with mock.patch('os.environ', environ):
            parsed_args = FakeParsedArgs(
                verify_ssl=True,
                ca_bundle='/path/to/cli_bundle.pem')
            config_file_vars = {}
            session_var_map = {'ca_bundle': ('ca_bundle', 'AWS_CA_BUNDLE')}
            session = FakeSession(
                session_vars=session_var_map,
                config_file_vars=config_file_vars)
            globalargs.resolve_verify_ssl(parsed_args, session)
            self.assertEqual(parsed_args.verify_ssl, '/path/to/cli_bundle.pem')

    def test_cli_overrides_env_cert_bundle(self):
        environ = {
            'AWS_CA_BUNDLE': '/path/to/env_bundle.pem',
        }
        with mock.patch('os.environ', environ):
            parsed_args = FakeParsedArgs(
                verify_ssl=True,
                ca_bundle='/path/to/cli_bundle.pem')
            config_file_vars = {}
            session_var_map = {'ca_bundle': ('ca_bundle', 'AWS_CA_BUNDLE')}
            session = FakeSession(
                session_vars=session_var_map,
                config_file_vars=config_file_vars)
            globalargs.resolve_verify_ssl(parsed_args, session)
            self.assertEqual(parsed_args.verify_ssl, '/path/to/cli_bundle.pem')

    def test_no_verify_ssl_overrides_cli_cert_bundle(self):
        environ = {
            'AWS_CA_BUNDLE': '/path/to/env_bundle.pem',
        }
        with mock.patch('os.environ', environ):
            parsed_args = FakeParsedArgs(
                verify_ssl=False,
                ca_bundle='/path/to/cli_bundle.pem')
            config_file_vars = {}
            session_var_map = {'ca_bundle': ('ca_bundle', 'AWS_CA_BUNDLE')}
            session = FakeSession(
                session_vars=session_var_map,
                config_file_vars=config_file_vars)
            globalargs.resolve_verify_ssl(parsed_args, session)
            self.assertFalse(parsed_args.verify_ssl)

    def test_no_sign_request_if_option_specified(self):
        args = FakeParsedArgs(sign_request=False)
        session = mock.Mock()

        globalargs.no_sign_request(args, session)
        emitter = session.get_component('event_emitter')
        emitter.register_first.assert_called_with(
            'choose-signer', disable_signing, unique_id='disable-signing')

    def test_request_signed_by_default(self):
        args = FakeParsedArgs(sign_request=True)
        session = mock.Mock()

        globalargs.no_sign_request(args, session)
        self.assertFalse(session.register.called)

    def test_invalid_endpoint_url(self):
        # Invalid jmespath expression.
        parsed_args = FakeParsedArgs(endpoint_url='missing-scheme.com')
        with self.assertRaises(ValueError):
            globalargs.resolve_types(parsed_args)

    def test_valid_endpoint_url(self):
        parsed_args = FakeParsedArgs(endpoint_url='http://custom-endpoint.com')
        globalargs.resolve_types(parsed_args)
        self.assertEqual(parsed_args.endpoint_url,
                         'http://custom-endpoint.com')

    def test_cli_read_timeout(self):
        parsed_args = FakeParsedArgs(read_timeout='60')
        session = get_session()
        globalargs.resolve_cli_read_timeout(parsed_args, session)
        self.assertEqual(parsed_args.read_timeout, 60)
        self.assertEqual(
            session.get_default_client_config().read_timeout, 60)

    def test_cli_connect_timeout(self):
        parsed_args = FakeParsedArgs(connect_timeout='60')
        session = get_session()
        globalargs.resolve_cli_connect_timeout(parsed_args, session)
        self.assertEqual(parsed_args.connect_timeout, 60)
        self.assertEqual(
            session.get_default_client_config().connect_timeout, 60)

    def test_cli_read_timeout_for_blocking(self):
        parsed_args = FakeParsedArgs(read_timeout='0')
        session = get_session()
        globalargs.resolve_cli_read_timeout(parsed_args, session)
        self.assertEqual(parsed_args.read_timeout, None)
        self.assertEqual(
            session.get_default_client_config().read_timeout, None)

    def test_cli_connect_timeout_for_blocking(self):
        parsed_args = FakeParsedArgs(connect_timeout='0')
        session = get_session()
        globalargs.resolve_cli_connect_timeout(parsed_args, session)
        self.assertEqual(parsed_args.connect_timeout, None)
        self.assertEqual(
            session.get_default_client_config().connect_timeout, None)
