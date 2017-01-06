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
from awscli.testutils import unittest
import mock

from awscli.customizations import scalarparse


class TestScalarParse(unittest.TestCase):
    def setUp(self):
        self.formatter_dict_ident = dict(blob_parser=scalarparse.identity,
                                        timestamp_parser=scalarparse.identity)
        self.formatter_dict_iso = dict(blob_parser=scalarparse.identity,
                                       timestamp_parser=scalarparse.iso_format)

    def test_register_scalar_parser(self):
        event_handers = mock.Mock()
        scalarparse.register_scalar_parser(event_handers)
        event_handers.register_first.assert_called_with(
            'session-initialized', scalarparse.add_scalar_parsers)

    def test_identity(self):
        self.assertEqual(scalarparse.identity('foo'), 'foo')
        self.assertEqual(scalarparse.identity(10), 10)

    def test_scalar_parsers_set(self):
        session = mock.Mock()
        session.get_scoped_config.return_value.get.return_value = 'none'
        scalarparse.add_scalar_parsers(session)
        session.get_component.assert_called_with('response_parser_factory')
        factory = session.get_component.return_value
        factory.set_parser_defaults.assert_called_with(
            blob_parser=scalarparse.identity,
            timestamp_parser=scalarparse.identity)

    def test_choose_default_formatters(self):
        self.assertEqual(self.formatter_dict_ident,
                         scalarparse.choose_default_parsers('none'))
        self.assertEqual(self.formatter_dict_iso,
                         scalarparse.choose_default_parsers('iso8601'))

    def test_choose_default_formatters_invalid_parser(self):
        with self.assertRaises(ValueError):
            scalarparse.choose_default_parsers('foobar')
