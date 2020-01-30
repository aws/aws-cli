# Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from botocore.exceptions import ProfileNotFound
from botocore.session import Session
from mock import Mock, call

from awscli.customizations import timestampformat
from awscli.customizations.exceptions import ConfigurationError
from awscli.testutils import unittest


class TestScalarParse(unittest.TestCase):
    def test_register_timestamp_format(self):
        event_handers = Mock()
        timestampformat.register_timestamp_format(event_handers)
        event_handers.register_first.assert_called_with(
            'session-initialized', timestampformat.add_timestamp_parser)

    def test_identity(self):
        self.assertEqual(timestampformat.identity('foo'), 'foo')
        self.assertEqual(timestampformat.identity(10), 10)

    def test_scalar_parsers_set(self):
        session = Mock()
        session.get_scoped_config.return_value = {'cli_timestamp_format':
                                                  'wire'}
        timestampformat.add_timestamp_parser(session)
        session.get_component.assert_called_with('response_parser_factory')
        factory = session.get_component.return_value
        expected = [call(timestamp_parser=timestampformat.identity)]
        self.assertEqual(factory.set_parser_defaults.mock_calls, expected)

    def test_choose_none_timestamp_formatter(self):
        session = Mock(spec=Session)
        session.get_scoped_config.return_value = {'cli_timestamp_format':
                                                  'wire'}
        factory = session.get_component.return_value
        timestampformat.add_timestamp_parser(session)
        factory.set_parser_defaults.assert_called_with(
            timestamp_parser=timestampformat.identity)

    def test_choose_iso_timestamp_formatter(self):
        session = Mock(spec=Session)
        session.get_scoped_config.return_value = {'cli_timestamp_format':
                                                  'iso8601'}
        factory = session.get_component.return_value
        timestampformat.add_timestamp_parser(session)
        factory.set_parser_defaults.assert_called_with(
            timestamp_parser=timestampformat.iso_format)

    def test_choose_invalid_timestamp_formatter(self):
        session = Mock(spec=Session)
        session.get_scoped_config.return_value = {'cli_timestamp_format':
                                                  'foobar'}
        session.get_component.return_value
        with self.assertRaises(ConfigurationError):
            timestampformat.add_timestamp_parser(session)

    def test_choose_timestamp_parser_profile_not_found(self):
        session = Mock(spec=Session)
        session.get_scoped_config.side_effect = ProfileNotFound(profile='foo')
        factory = session.get_component.return_value
        timestampformat.add_timestamp_parser(session)
        factory.set_parser_defaults.assert_called_with(
            timestamp_parser=timestampformat.iso_format)
