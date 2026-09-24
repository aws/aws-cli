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
import os

from botocore import UNSIGNED
from botocore.session import get_session

from awscli.customizations import globalargs
from awscli.customizations.exceptions import ParamValidationError
from awscli.testutils import mock, unittest


class FakeParsedArgs:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __getattr__(self, arg):
        return None


class FakeSession:
    def __init__(self, session_vars=None, config_file_vars=None):
        if session_vars is None:
            session_vars = {}
        self.session_var_map = session_vars
        if config_file_vars is None:
            config_file_vars = {}
        self.config_file_vars = config_file_vars

    def get_config_variable(
        self, name, methods=('env', 'config'), default=None
    ):
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
        with self.assertRaises(ParamValidationError):
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
                verify_ssl=True, ca_bundle='/path/to/cli_bundle.pem'
            )
            config_file_vars = {}
            session_var_map = {'ca_bundle': ('ca_bundle', 'AWS_CA_BUNDLE')}
            session = FakeSession(
                session_vars=session_var_map, config_file_vars=config_file_vars
            )
            globalargs.resolve_verify_ssl(parsed_args, session)
            self.assertEqual(parsed_args.verify_ssl, '/path/to/cli_bundle.pem')

    def test_cli_overrides_env_cert_bundle(self):
        environ = {
            'AWS_CA_BUNDLE': '/path/to/env_bundle.pem',
        }
        with mock.patch('os.environ', environ):
            parsed_args = FakeParsedArgs(
                verify_ssl=True, ca_bundle='/path/to/cli_bundle.pem'
            )
            config_file_vars = {}
            session_var_map = {'ca_bundle': ('ca_bundle', 'AWS_CA_BUNDLE')}
            session = FakeSession(
                session_vars=session_var_map, config_file_vars=config_file_vars
            )
            globalargs.resolve_verify_ssl(parsed_args, session)
            self.assertEqual(parsed_args.verify_ssl, '/path/to/cli_bundle.pem')

    def test_no_verify_ssl_overrides_cli_cert_bundle(self):
        environ = {
            'AWS_CA_BUNDLE': '/path/to/env_bundle.pem',
        }
        with mock.patch('os.environ', environ):
            parsed_args = FakeParsedArgs(
                verify_ssl=False, ca_bundle='/path/to/cli_bundle.pem'
            )
            config_file_vars = {}
            session_var_map = {'ca_bundle': ('ca_bundle', 'AWS_CA_BUNDLE')}
            session = FakeSession(
                session_vars=session_var_map, config_file_vars=config_file_vars
            )
            globalargs.resolve_verify_ssl(parsed_args, session)
            self.assertFalse(parsed_args.verify_ssl)

    def test_no_sign_request_if_option_specified(self):
        args = FakeParsedArgs(sign_request=False)
        session = mock.Mock()
        with mock.patch(
            'awscli.customizations.globalargs._update_default_client_config'
        ) as mock_update:
            globalargs.no_sign_request(args, session)
            mock_update.assert_called_once_with(
                session, 'signature_version', UNSIGNED
            )

    def test_request_signed_by_default(self):
        args = FakeParsedArgs(sign_request=True)
        session = mock.Mock()

        globalargs.no_sign_request(args, session)
        self.assertFalse(session.register.called)

    def test_invalid_endpoint_url(self):
        # Invalid endpoint URL
        parsed_args = FakeParsedArgs(endpoint_url='missing-scheme.com')
        with self.assertRaises(ParamValidationError):
            globalargs.resolve_types(parsed_args)

    def test_valid_endpoint_url(self):
        parsed_args = FakeParsedArgs(endpoint_url='http://custom-endpoint.com')
        globalargs.resolve_types(parsed_args)
        self.assertEqual(
            parsed_args.endpoint_url, 'http://custom-endpoint.com'
        )

    def test_cli_read_timeout(self):
        parsed_args = FakeParsedArgs(read_timeout='60')
        session = get_session()
        globalargs.resolve_cli_read_timeout(parsed_args, session)
        self.assertEqual(parsed_args.read_timeout, 60)
        self.assertEqual(session.get_default_client_config().read_timeout, 60)

    def test_cli_connect_timeout(self):
        parsed_args = FakeParsedArgs(connect_timeout='60')
        session = get_session()
        globalargs.resolve_cli_connect_timeout(parsed_args, session)
        self.assertEqual(parsed_args.connect_timeout, 60)
        self.assertEqual(
            session.get_default_client_config().connect_timeout, 60
        )

    def test_cli_read_timeout_for_blocking(self):
        parsed_args = FakeParsedArgs(read_timeout='0')
        session = get_session()
        globalargs.resolve_cli_read_timeout(parsed_args, session)
        self.assertEqual(parsed_args.read_timeout, None)
        self.assertEqual(
            session.get_default_client_config().read_timeout, None
        )

    def test_cli_connect_timeout_for_blocking(self):
        parsed_args = FakeParsedArgs(connect_timeout='0')
        session = get_session()
        globalargs.resolve_cli_connect_timeout(parsed_args, session)
        self.assertEqual(parsed_args.connect_timeout, None)
        self.assertEqual(
            session.get_default_client_config().connect_timeout, None
        )


class TestResolveApnId(unittest.TestCase):
    def _make_session(self, config_value=None, user_agent_extra=''):
        session = mock.Mock()
        session.user_agent_extra = user_agent_extra
        if config_value is not None:
            session.get_scoped_config.return_value = {'apn_id': config_value}
        else:
            session.get_scoped_config.return_value = {}
        return session

    def test_no_apn_id_leaves_user_agent_unchanged(self):
        session = self._make_session(user_agent_extra='botocore/1.0')
        parsed_args = FakeParsedArgs()
        with mock.patch.dict(os.environ, {}, clear=True):
            globalargs.resolve_apn_id(parsed_args, session)
        self.assertEqual(session.user_agent_extra, 'botocore/1.0')

    def test_cli_flag_appends_apn_marker(self):
        session = self._make_session(user_agent_extra='botocore/1.0')
        parsed_args = FakeParsedArgs(apn_id='pc_abc123')
        globalargs.resolve_apn_id(parsed_args, session)
        self.assertEqual(
            session.user_agent_extra, 'botocore/1.0 APN_1.1/pc_abc123$'
        )

    def test_env_var_used_when_flag_missing(self):
        session = self._make_session(user_agent_extra='botocore/1.0')
        parsed_args = FakeParsedArgs()
        with mock.patch.dict(os.environ, {'AWS_APN_ID': 'pc_env123'}):
            globalargs.resolve_apn_id(parsed_args, session)
        self.assertEqual(
            session.user_agent_extra, 'botocore/1.0 APN_1.1/pc_env123$'
        )

    def test_config_file_used_when_flag_and_env_missing(self):
        session = self._make_session(
            config_value='pc_cfg123', user_agent_extra='botocore/1.0'
        )
        parsed_args = FakeParsedArgs()
        with mock.patch.dict(os.environ, {}, clear=True):
            globalargs.resolve_apn_id(parsed_args, session)
        self.assertEqual(
            session.user_agent_extra, 'botocore/1.0 APN_1.1/pc_cfg123$'
        )

    def test_cli_flag_overrides_env_and_config(self):
        session = self._make_session(
            config_value='pc_from-config', user_agent_extra='botocore/1.0'
        )
        parsed_args = FakeParsedArgs(apn_id='pc_from-flag')
        with mock.patch.dict(os.environ, {'AWS_APN_ID': 'pc_from-env'}):
            globalargs.resolve_apn_id(parsed_args, session)
        self.assertEqual(
            session.user_agent_extra,
            'botocore/1.0 APN_1.1/pc_from-flag$',
        )

    def test_env_overrides_config(self):
        session = self._make_session(
            config_value='pc_from-config', user_agent_extra='botocore/1.0'
        )
        parsed_args = FakeParsedArgs()
        with mock.patch.dict(os.environ, {'AWS_APN_ID': 'ra_from-env'}):
            globalargs.resolve_apn_id(parsed_args, session)
        self.assertEqual(
            session.user_agent_extra,
            'botocore/1.0 APN_1.1/ra_from-env$',
        )

    def test_appends_when_user_agent_extra_is_empty(self):
        session = self._make_session(user_agent_extra='')
        parsed_args = FakeParsedArgs(apn_id='pc_abc123')
        globalargs.resolve_apn_id(parsed_args, session)
        self.assertEqual(session.user_agent_extra, 'APN_1.1/pc_abc123$')

    def test_appends_when_user_agent_extra_is_none(self):
        session = self._make_session(user_agent_extra=None)
        session.user_agent_extra = None
        parsed_args = FakeParsedArgs(apn_id='pc_abc123')
        globalargs.resolve_apn_id(parsed_args, session)
        self.assertEqual(session.user_agent_extra, 'APN_1.1/pc_abc123$')

    def test_idempotent_when_marker_already_present(self):
        session = self._make_session(
            user_agent_extra='botocore/1.0 APN_1.1/pc_abc123$'
        )
        parsed_args = FakeParsedArgs(apn_id='pc_abc123')
        globalargs.resolve_apn_id(parsed_args, session)
        self.assertEqual(
            session.user_agent_extra, 'botocore/1.0 APN_1.1/pc_abc123$'
        )

    def test_empty_string_treated_as_unset(self):
        session = self._make_session(user_agent_extra='botocore/1.0')
        parsed_args = FakeParsedArgs(apn_id='')
        with mock.patch.dict(os.environ, {}, clear=True):
            globalargs.resolve_apn_id(parsed_args, session)
        self.assertEqual(session.user_agent_extra, 'botocore/1.0')

    def test_rejects_value_with_whitespace(self):
        session = self._make_session(user_agent_extra='botocore/1.0')
        parsed_args = FakeParsedArgs(apn_id='bad value')
        with self.assertRaises(ParamValidationError):
            globalargs.resolve_apn_id(parsed_args, session)

    def test_rejects_value_with_special_chars(self):
        session = self._make_session(user_agent_extra='botocore/1.0')
        parsed_args = FakeParsedArgs(apn_id='bad/value')
        with self.assertRaises(ParamValidationError):
            globalargs.resolve_apn_id(parsed_args, session)

    def test_rejects_value_with_dot(self):
        session = self._make_session(user_agent_extra='botocore/1.0')
        parsed_args = FakeParsedArgs(apn_id='1.0')
        with self.assertRaises(ParamValidationError):
            globalargs.resolve_apn_id(parsed_args, session)

    def test_rejects_value_over_255_chars(self):
        session = self._make_session(user_agent_extra='botocore/1.0')
        parsed_args = FakeParsedArgs(apn_id='a' * 256)
        with self.assertRaises(ParamValidationError):
            globalargs.resolve_apn_id(parsed_args, session)

    def test_accepts_max_length_value(self):
        session = self._make_session(user_agent_extra='botocore/1.0')
        long_id = 'a' * 255
        parsed_args = FakeParsedArgs(apn_id=long_id)
        globalargs.resolve_apn_id(parsed_args, session)
        self.assertEqual(
            session.user_agent_extra,
            'botocore/1.0 APN_1.1/%s$' % long_id,
        )

    def test_accepts_dash_and_underscore(self):
        session = self._make_session(user_agent_extra='botocore/1.0')
        parsed_args = FakeParsedArgs(apn_id='pc_Pc-1_test')
        globalargs.resolve_apn_id(parsed_args, session)
        self.assertEqual(
            session.user_agent_extra,
            'botocore/1.0 APN_1.1/pc_Pc-1_test$',
        )

    def test_accepts_ra_prefix(self):
        session = self._make_session(user_agent_extra='botocore/1.0')
        parsed_args = FakeParsedArgs(apn_id='ra_MyPartner123')
        globalargs.resolve_apn_id(parsed_args, session)
        self.assertEqual(
            session.user_agent_extra,
            'botocore/1.0 APN_1.1/ra_MyPartner123$',
        )

    def test_handler_is_registered(self):
        cli = mock.Mock()
        globalargs.register_parse_global_args(cli)
        registered = [
            c.kwargs.get('unique_id') for c in cli.register.call_args_list
        ]
        self.assertIn('resolve-apn-id', registered)
