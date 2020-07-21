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
import os
import re

from awscli.testutils import aws, unittest, FileCreator


class TestShow(unittest.TestCase):
    def setUp(self):
        self.files = FileCreator()
        self.environ = os.environ.copy()
        self.environ['AWS_CONFIG_FILE'] = self.files.create_file(
            'config', (
                '[default]\n'
                'cli_history = enabled'
            )
        )
        self.environ['AWS_DEFAULT_PROFILE'] = 'default'
        self.environ['AWS_DEFAULT_REGION'] = 'us-west-2'
        self.environ['AWS_CLI_HISTORY_FILE'] = os.path.join(
            self.files.rootdir, 'history.db')

    def tearDown(self):
        self.files.remove_all()

    def remove_color(self, output):
        return re.compile(r'\x1b[^m]*m').sub('', output)

    def assert_contains_in_order(self, lines, contents):
        current_pos = 0
        prev_line = None
        for line in lines:
            self.assertIn(line, contents)
            new_pos = contents.find(line)
            if new_pos < current_pos:
                self.fail('Line: "%s" should have came after line: "%s"' % (
                    line, prev_line))
            prev_line = line
            current_pos = new_pos

    def test_show(self):
        # Make a call that does not require credentials just in case the
        # user was using the config file to provide credentials.
        cmd = 'sts assume-role-with-saml '
        cmd += '--role-arn  arn:aws:iam::...:invalid '
        cmd += '--principal-arn  arn:aws:iam::...:invalid  '
        cmd += '--saml-assertion fake-assertion'
        aws(cmd, env_vars=self.environ)
        # Now run the show command and make sure the general output is all
        # there.
        result = aws('history show', env_vars=self.environ)
        uncolored_content = self.remove_color(result.stdout)

        self.assert_contains_in_order(
            [
                'AWS CLI command entered',
                'with AWS CLI version: aws-cli/',
                "with arguments: ['sts', 'assume-role-with-saml',",
                '[0] API call made',
                'to service: sts',
                'using operation: AssumeRoleWithSAML',
                'with parameters: {',
                '    "PrincipalArn": "arn:aws:iam::...:invalid",',
                '    "RoleArn": "arn:aws:iam::...:invalid",',
                '    "SAMLAssertion": "fake-assertion"',
                '[0] HTTP request sent',
                'to URL: https://sts.amazonaws.com/',
                'with method: POST',
                'with body: Action=AssumeRoleWithSAML&Version=2011-06-15',
                '[0] HTTP response received',
                'with status code: 400',
                'with body: <?xml version="1.0" ?>',
                '[0] HTTP response parsed',
                'parsed to: {',
                '    "Error": {',
                'AWS CLI command exited',
                'with return code: 255'
            ],
            uncolored_content
        )
