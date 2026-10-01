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
from awscli.autocomplete.parser import ParsedResult
from awscli.autocomplete.serverside.custom_completers.console.autocomplete import (
    ConsoleServiceCompleter,
)
from awscli.testutils import unittest


class TestConsoleServiceCompleter(unittest.TestCase):
    def setUp(self):
        self.completer = ConsoleServiceCompleter()

    def _parsed(self, command, param, fragment):
        return ParsedResult(
            current_command=command,
            current_param=param,
            current_fragment=fragment,
            lineage=['aws'],
        )

    def _names(self, result):
        return [r.name for r in result]

    def test_completes_service_prefix(self):
        result = self.completer.complete(
            self._parsed('console', 'service', 'ec')
        )
        self.assertEqual(self._names(result), ['ec2', 'ecr', 'ecs'])

    def test_empty_fragment_returns_all(self):
        result = self.completer.complete(
            self._parsed('console', 'service', '')
        )
        self.assertIn('ec2', self._names(result))
        self.assertIn('s3', self._names(result))

    def test_ignores_other_commands(self):
        self.assertIsNone(
            self.completer.complete(self._parsed('ec2', 'service', 'ec'))
        )

    def test_ignores_other_params(self):
        self.assertIsNone(
            self.completer.complete(self._parsed('console', 'region', 'eu'))
        )

    def test_no_match_returns_empty(self):
        result = self.completer.complete(
            self._parsed('console', 'service', 'zzz')
        )
        self.assertEqual(self._names(result), [])


if __name__ == '__main__':
    unittest.main()
