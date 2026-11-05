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
import re

from awscli.testutils import unittest
from awscli.customizations.cloudfront import unique_string


class TestUniqueString(unittest.TestCase):

    UUID_RE = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
    )

    def test_default_prefix(self):
        result = unique_string()
        self.assertTrue(result.startswith('cli-'), result)

    def test_custom_prefix(self):
        result = unique_string(prefix='myprefix')
        self.assertTrue(result.startswith('myprefix-'), result)

    def test_suffix_is_uuid4(self):
        result = unique_string()
        suffix = result[len('cli-'):]
        self.assertRegex(suffix, self.UUID_RE)

    def test_values_are_unique(self):
        results = {unique_string() for _ in range(1000)}
        self.assertEqual(len(results), 1000)
