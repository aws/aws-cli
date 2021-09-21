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
from awscli.help import PagingHelpRenderer
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

        expected = {
            'query': u'George Lucas',
            'queryOptions': u'{"defaultOperator":"and","fields":["directors^10"]}'
        }
        self.assert_params_for_cmd(cmd, expected)

    def test_endpoint_is_required(self):
        cmd = self.prefix.split()
        cmd += ['--search-query', 'foo']
        stderr = self.run_cmd(cmd, expected_rc=255)[1]
        self.assertIn('--endpoint-url is required', stderr)

    def test_endpoint_not_required_for_help(self):
        cmd = self.prefix + 'help'
        with mock.patch('awscli.help.get_renderer') as get_renderer:
            mock_render = mock.Mock(spec=PagingHelpRenderer)
            get_renderer.return_value = mock_render
            stdout, stderr, rc = self.run_cmd(cmd, expected_rc=None)
            # If we get this far we've succeeded, but we can do
            # a quick sanity check and make sure the service name is
            # in the stdout help text.
            self.assertIn(stdout, 'cloudsearchdomain')


class TestCloudsearchDomainHandler(unittest.TestCase):
    def test_validate_endpoint_url_is_none(self):
        parsed_globals = mock.Mock()
        parsed_globals.endpoint_url = None
        # Method should return instantiated exception.
        self.assertTrue(isinstance(validate_endpoint_url(parsed_globals),
                                   ValueError))


if __name__ == "__main__":
    unittest.main()
