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
from botocore.handlers import disable_signing

from awscli.testutils import unittest
from awscli.compat import six
import mock

from awscli.customizations import globalargs


class FakeParsedArgs(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __getattr__(self, arg):
        return None


class TestGlobalArgsCustomization(unittest.TestCase):

    def test_parse_query(self):
        parsed_args = FakeParsedArgs(query='foo.bar')
        globalargs.resolve_types(parsed_args)
        # Assert that it looks like a jmespath parsed expression.
        self.assertFalse(isinstance(parsed_args.query, six.string_types))
        self.assertTrue(hasattr(parsed_args.query, 'search'))

    def test_parse_query_error_message(self):
        # Invalid jmespath expression.
        parsed_args = FakeParsedArgs(query='foo.bar.')
        with self.assertRaises(ValueError):
            globalargs.resolve_types(parsed_args)
            globalargs.resolve_types('query')

    def test_parse_verify_ssl_default_value(self):
        with mock.patch('os.environ', {}):
            parsed_args = FakeParsedArgs(verify_ssl=True)
            globalargs.resolve_types(parsed_args)
            # None, so that botocore can apply it's default logic.
            self.assertIsNone(parsed_args.verify_ssl)

    def test_parse_verify_ssl_verify_turned_off(self):
        with mock.patch('os.environ', {}):
            parsed_args = FakeParsedArgs(verify_ssl=False)
            globalargs.resolve_types(parsed_args)
            self.assertFalse(parsed_args.verify_ssl)

    def test_os_environ_overrides_cert_bundle(self):
        environ = {
            'AWS_CA_BUNDLE': '/path/to/bundle.pem',
        }
        with mock.patch('os.environ', environ):
            parsed_args = FakeParsedArgs(verify_ssl=True)
            globalargs.resolve_types(parsed_args)
            self.assertEqual(parsed_args.verify_ssl, '/path/to/bundle.pem')

    def test_no_sign_request_if_option_specified(self):
        args = FakeParsedArgs(sign_request=False)
        session = mock.Mock()

        globalargs.no_sign_request(args, session)
        session.register.assert_called_with('choose-signer', disable_signing)

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
