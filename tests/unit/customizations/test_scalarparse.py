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
from awscli.compat import six
import mock

from awscli.customizations import scalarparse


class TestScalarParse(unittest.TestCase):

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
        scalarparse.add_scalar_parsers(session)
        session.get_component.assert_called_with('response_parser_factory')
        factory = session.get_component.return_value
        factory.set_parser_defaults.assert_called_with(
            blob_parser=scalarparse.identity,
            timestamp_parser=scalarparse.identity)
