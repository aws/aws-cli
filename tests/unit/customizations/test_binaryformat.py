# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.testutils import unittest, mock
from awscli.customizations.binaryformat import Base64DecodeVisitor
from awscli.customizations.binaryformat import add_binary_formatter
from awscli.customizations.binaryformat import base64_decode_input_blobs
from awscli.customizations.binaryformat import identity
from awscli.customizations.binaryformat import InvalidBase64Error

from botocore import model
from botocore.exceptions import ProfileNotFound
from botocore.session import Session


def test_identity_function():
    assert 2 == identity(2)


class TestBase64DecodeVisitor(unittest.TestCase):
    def construct_model(self, members):
        model_builder = model.DenormalizedStructureBuilder()
        return model_builder.with_members(members).build_model()

    def assert_decoded_params(self, members, params, expected_params):
        shape = self.construct_model(members)
        base64_decode_visitor = Base64DecodeVisitor()
        base64_decode_visitor.visit(params, shape)
        self.assertEqual(params, expected_params)

    def test_can_convert_top_level_blob(self):
        members = {'B': {'type': 'blob'}}
        params = {'B': u'Zm9vAGJheg=='}
        expected_params = {'B': b'foo\x00baz'}
        self.assert_decoded_params(members, params, expected_params)

    def test_can_convert_nested_blob(self):
        members = {
            'Nested': {
                'type': 'structure',
                'members': {
                    'B': {'type': 'blob'},
                }
            }
        }
        params = {
            'Nested': {'B': u'Zm9v'}
        }
        expected_params = {
            'Nested': {'B': b'foo'}
        }
        self.assert_decoded_params(members, params, expected_params)

    def test_can_convert_list_of_blob(self):
        members = {
            'BS': {
                'type': 'list',
                'member': {'type': 'blob'},
            }
        }
        params = {
            'BS': [u'Zm9v', u'']
        }
        expected_params = {
            'BS': [b'foo', b'']
        }
        self.assert_decoded_params(members, params, expected_params)

    def test_can_convert_map_to_blob(self):
        members = {
            'StoB': {
                'type': 'map',
                'key': {'type': 'string'},
                'value': {'type': 'blob'},
            }
        }
        params = {
            'StoB': {'a': u'Zm9v', 'b': u''}
        }
        expected_params = {
            'StoB': {'a': b'foo', 'b': b''}
        }
        self.assert_decoded_params(members, params, expected_params)

    def test_converts_base64_exception(self):
        members = {'B': {'type': 'blob'}}
        params = {'B': u'this:is:not:base64'}
        shape = self.construct_model(members)
        base64_decode_visitor = Base64DecodeVisitor()
        with self.assertRaises(InvalidBase64Error):
            base64_decode_visitor.visit(params, shape)


class TestAddBinaryFormatter(unittest.TestCase):
    def setUp(self):
        self.parsed_args = mock.Mock()
        self.mock_factory = mock.Mock()
        self.mock_session = mock.Mock(spec=Session)
        self.mock_session.get_component.return_value = self.mock_factory

    def _assert_legacy_handlers_added(self):
        # Legacy format does not register a handler to transform input
        self.assertEqual(self.mock_session.register.call_count, 0)
        # Legacy format parses blobs with an identity function
        self.mock_factory.set_parser_defaults.assert_called_with(
            blob_parser=identity
        )

    def test_legacy_handlers_added(self):
        self.parsed_args.cli_binary_format = 'raw-in-base64-out'
        add_binary_formatter(self.mock_session, self.parsed_args)
        self._assert_legacy_handlers_added()

    def test_legacy_handlers_added_via_profile(self):
        self.parsed_args.cli_binary_format = None
        self.mock_session.get_config_variable.return_value = 'raw-in-base64-out'
        add_binary_formatter(self.mock_session, self.parsed_args)
        self._assert_legacy_handlers_added()

    def _assert_base64_handlers_added(self):
        self.assertEqual(self.mock_session.register.call_count, 1)
        self.mock_session.register.assert_called_with(
            'provide-client-params', base64_decode_input_blobs,
        )
        # base64 format parses blobs with an identity function
        self.mock_factory.set_parser_defaults.assert_called_with(
            blob_parser=identity
        )

    def test_base64_handlers_added(self):
        self.parsed_args.cli_binary_format = 'base64'
        add_binary_formatter(self.mock_session, self.parsed_args)
        self._assert_base64_handlers_added()

    def test_base64_handlers_added_via_profile(self):
        self.parsed_args.cli_binary_format = None
        self.mock_session.get_config_variable.return_value = 'base64'
        add_binary_formatter(self.mock_session, self.parsed_args)
        self._assert_base64_handlers_added()

    def test_defaults_to_base64_if_unkonwn_profile(self):
        self.parsed_args.cli_binary_format = None
        exception = ProfileNotFound(profile='notaprofile')
        self.mock_session.get_config_variable.side_effect = exception
        add_binary_formatter(self.mock_session, self.parsed_args)
        self._assert_base64_handlers_added()
