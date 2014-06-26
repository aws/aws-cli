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
from awscli.testutils import BaseAWSCommandParamsTest
from awscli.customizations.cloudsearchdomain import validate_endpoint_url

import mock


class TestSearchCommand(BaseAWSCommandParamsTest):
    prefix = 'cloudsearchdomain search '

    def test_search_with_query(self):
        cmd = self.prefix.split()
        cmd += [
            '--endpoint-url', 'http://example.com/',
            # Note we're also verifying that --query is renamed to
            # --search-query from argrename.py.
            '--search-query', 'George Lucas',
            '--query-options',
            '{"defaultOperator":"and","fields":["directors^10"]}']

        result = {
            'headers': {},
            'uri_params': {
                'query': 'George Lucas',
                'queryOptions':
                    '{"defaultOperator":"and","fields":["directors^10"]}'}}

        self.assert_params_for_cmd(cmd, result, ignore_params=['payload'])
        # We ignore'd the paylod, but we can verify that there should be
        # no payload for this request.
        self.assertIsNone(self.last_params['payload'].getvalue())

    def test_endpoint_is_required(self):
        cmd = self.prefix.split()
        cmd += ['--search-query', 'foo']
        stderr = self.run_cmd(cmd, expected_rc=255)[1]
        self.assertIn('--endpoint-url is required', stderr)


class TestCloudsearchDomainHandler(unittest.TestCase):
    def test_validate_endpoint_url_is_none(self):
        parsed_args = mock.Mock()
        parsed_args.endpoint_url = None
        parsed_args.command = 'cloudsearchdomain'
        with self.assertRaises(ValueError):
            validate_endpoint_url(parsed_args)


if __name__ == "__main__":
    unittest.main()
