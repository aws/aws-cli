# Copyright 2012-2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import re

from botocore.handlers import generate_idempotent_uuid
from tests import mock, unittest


class TestIdempotencyInjection(unittest.TestCase):
    def setUp(self):
        self.mock_model = mock.MagicMock()
        self.mock_model.idempotent_members = ['RequiredKey']
        self.uuid_pattern = re.compile(
            '^[0-9a-f]{8}-([0-9a-f]{4}-){3}[0-9a-f]{12}$', re.I
        )

    def test_injection(self):
        # No parameters are provided, RequiredKey should be autofilled
        params = {}
        generate_idempotent_uuid(params, self.mock_model)
        self.assertIn('RequiredKey', params)
        self.assertIsNotNone(self.uuid_pattern.match(params['RequiredKey']))

    def test_provided(self):
        # RequiredKey is provided, should not be replaced
        params = {'RequiredKey': 'already populated'}
        generate_idempotent_uuid(params, self.mock_model)
        self.assertEqual(params['RequiredKey'], 'already populated')
