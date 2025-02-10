# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import awscli

from argparse import Namespace
from botocore.session import Session
from botocore.credentials import Credentials
from awscli.customizations.codecommit import CodeCommitGetCommand
from awscli.customizations.codecommit import CodeCommitCommand
from awscli.testutils import mock, unittest, StringIOWithFileNo
from awscli.compat import StringIO

from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest


class TestCodeCommitCredentialHelper(unittest.TestCase):

    PROTOCOL_HOST_PATH = ('protocol=https\n'
                          'host=git-codecommit.us-east-1.amazonaws.com\n'
                          'path=/v1/repos/myrepo')

    PROTOCOL_HOST_PATH_TRAILING_NEWLINE = ('protocol=https\n'
                                           'host=git-codecommit.us-east-1.amazonaws.com\n'
                                           'path=/v1/repos/myrepo\n')

    PROTOCOL_HOST_PATH_BLANK_LINE = ('protocol=https\n'
                                     'host=git-codecommit.us-east-1.amazonaws.com\n'
                                     'path=/v1/repos/myrepo\n\n')

    FIPS_PROTOCOL_HOST_PATH = ('protocol=https\n'
                               'host=git-codecommit-fips.us-east-1.amazonaws.com\n'
                               'path=/v1/repos/myrepo')

    VPC_1_PROTOCOL_HOST_PATH = ('protocol=https\n'
                                'host=vpce-0b47ea360adebf88a-jkl88hez.git-codecommit.us-east-1.vpce.amazonaws.com\n'
                                'path=/v1/repos/myrepo')

    VPC_2_PROTOCOL_HOST_PATH = ('protocol=https\n'
                                'host=vpce-0b47ea360adebf88a-jkl88hez-us-east-1a.git-codecommit.us-east-1.vpce.amazonaws.com\n'
                                'path=/v1/repos/myrepo')

    FIPS_VPC_1_PROTOCOL_HOST_PATH = ('protocol=https\n'
                                     'host=vpce-0b47ea360adebf88a-jkl88hez.git-codecommit-fips.us-east-1.vpce.amazonaws.com\n'
                                     'path=/v1/repos/myrepo')

    FIPS_VPC_2_PROTOCOL_HOST_PATH = ('protocol=https\n'
                                     'host=vpce-0b47ea360adebf88a-jkl88hez-us-west-2b.git-codecommit-fips.us-east-1.vpce.amazonaws.com\n'
                                     'path=/v1/repos/myrepo')

    NO_REGION_PROTOCOL_HOST_PATH = ('protocol=https\n'
                                    'host=git-codecommit.amazonaws.com\n'
                                    'path=/v1/repos/myrepo')

    NON_AWS_PROTOCOL_HOST_PATH = ('protocol=https\n'
                                  'host=mydomain.com\n'
                                  'path=/v1/repos/myrepo')

    MOCK_STDOUT_CLASS = StringIOWithFileNo

    def setUp(self):
        self.credentials = Credentials('access', 'secret')
        self.args = Namespace()
        self.args.ignore_host_check = False
        self.globals = Namespace()
        self.globals.region = 'us-east-1'
        self.globals.verify_ssl = False
        self.session = mock.MagicMock()
        self.session.get_config_variable.return_value = 'us-east-1'
        self.session.get_credentials.return_value = self.credentials

    @mock.patch('sys.stdout', new_callable=MOCK_STDOUT_CLASS)
    @mock.patch('sys.stdin', StringIO(PROTOCOL_HOST_PATH))
    def test_generate_credentials(self, stdout_mock):
        self.get_command = CodeCommitGetCommand(self.session)
        self.get_command._run_main(self.args, self.globals)
        output = stdout_mock.getvalue().strip()
        self.assertRegex(
            output, 'username={0}\npassword=.+'.format('access'))

    @mock.patch('sys.stdout', new_callable=MOCK_STDOUT_CLASS)
    @mock.patch('sys.stdin', StringIO(PROTOCOL_HOST_PATH_TRAILING_NEWLINE))
    def test_generate_credentials_trailing_newline(self, stdout_mock):
        self.get_command = CodeCommitGetCommand(self.session)
        self.get_command._run_main(self.args, self.globals)
        output = stdout_mock.getvalue().strip()
        self.assertRegex(
            output, 'username={0}\npassword=.+'.format('access'))

    @mock.patch('sys.stdout', new_callable=MOCK_STDOUT_CLASS)
    @mock.patch('sys.stdin', StringIO(PROTOCOL_HOST_PATH_BLANK_LINE))
    def test_generate_credentials_blank_line(self, stdout_mock):
        self.get_command = CodeCommitGetCommand(self.session)
        self.get_command._run_main(self.args, self.globals)
        output = stdout_mock.getvalue().strip()
        self.assertRegex(
            output, 'username={0}\npassword=.+'.format('access'))

    @mock.patch('sys.stdout', new_callable=MOCK_STDOUT_CLASS)
    @mock.patch('sys.stdin', StringIO(FIPS_PROTOCOL_HOST_PATH))
    def test_generate_credentials_fips_reads_region_from_url(self, stdout_mock):
        self.globals.region = None
        self.session.get_config_variable.return_value = None
        self.get_command = CodeCommitGetCommand(self.session)
        self.get_command._run_main(self.args, self.globals)
        output = stdout_mock.getvalue().strip()
        self.assertRegex(
            output, 'username={0}\npassword=.+'.format('access'))

    @mock.patch('sys.stdout', new_callable=MOCK_STDOUT_CLASS)
    @mock.patch('sys.stdin', StringIO(VPC_1_PROTOCOL_HOST_PATH))
    def test_generate_credentials_vpc_reads_region_from_url(self, stdout_mock):
        self.globals.region = None
        self.session.get_config_variable.return_value = None
        self.get_command = CodeCommitGetCommand(self.session)
        self.get_command._run_main(self.args, self.globals)
        output = stdout_mock.getvalue().strip()
        self.assertRegex(
            output, 'username={0}\npassword=.+'.format('access'))

    @mock.patch('sys.stdout', new_callable=MOCK_STDOUT_CLASS)
    @mock.patch('sys.stdin', StringIO(VPC_2_PROTOCOL_HOST_PATH))
    def test_generate_credentials_vpc_2_reads_region_from_url(self, stdout_mock):
        self.globals.region = None
        self.session.get_config_variable.return_value = None
        self.get_command = CodeCommitGetCommand(self.session)
        self.get_command._run_main(self.args, self.globals)
        output = stdout_mock.getvalue().strip()
        self.assertRegex(
            output, 'username={0}\npassword=.+'.format('access'))

    @mock.patch('sys.stdout', new_callable=MOCK_STDOUT_CLASS)
    @mock.patch('sys.stdin', StringIO(FIPS_VPC_1_PROTOCOL_HOST_PATH))
    def test_generate_credentials_fips_vpc_1_reads_region_from_url(self, stdout_mock):
        self.globals.region = None
        self.session.get_config_variable.return_value = None
        self.get_command = CodeCommitGetCommand(self.session)
        self.get_command._run_main(self.args, self.globals)
        output = stdout_mock.getvalue().strip()
        self.assertRegex(
            output, 'username={0}\npassword=.+'.format('access'))

    @mock.patch('sys.stdout', new_callable=MOCK_STDOUT_CLASS)
    @mock.patch('sys.stdin', StringIO(FIPS_VPC_2_PROTOCOL_HOST_PATH))
    def test_generate_credentials_fips_vpc_2_reads_region_from_url(self, stdout_mock):
        self.globals.region = None
        self.session.get_config_variable.return_value = None
        self.get_command = CodeCommitGetCommand(self.session)
        self.get_command._run_main(self.args, self.globals)
        output = stdout_mock.getvalue().strip()
        self.assertRegex(
            output, 'username={0}\npassword=.+'.format('access'))

    @mock.patch('sys.stdout', new_callable=MOCK_STDOUT_CLASS)
    @mock.patch('sys.stdin', StringIO(NO_REGION_PROTOCOL_HOST_PATH))
    def test_generate_credentials_reads_region_from_session(self, stdout_mock):
        self.get_command = CodeCommitGetCommand(self.session)
        self.get_command._run_main(self.args, self.globals)
        output = stdout_mock.getvalue().strip()
        self.assertRegex(
            output, 'username={0}\npassword=.+'.format('access'))

    @mock.patch('sys.stdout', new_callable=MOCK_STDOUT_CLASS)
    @mock.patch('sys.stdin', StringIO(NON_AWS_PROTOCOL_HOST_PATH))
    def test_does_nothing_for_non_amazon_domain(self, stdout_mock):
        self.get_command = CodeCommitGetCommand(self.session)
        self.get_command._run_main(self.args, self.globals)
        output = stdout_mock.getvalue().strip()
        self.assertEqual('', output)

    def test_raises_value_error_when_not_provided_any_subcommands(self):
        self.get_command = CodeCommitCommand(self.session)
        with self.assertRaises(ValueError):
            self.get_command._run_main(self.args, self.globals)

    @mock.patch('sys.stdout', new_callable=MOCK_STDOUT_CLASS)
    @mock.patch('sys.stdin', StringIO(PROTOCOL_HOST_PATH))
    def test_generate_session_credentials(self, stdout_mock):
        self.credentials = Credentials('access', 'secret', 'token')
        self.session.get_credentials.return_value = self.credentials
        self.get_command = CodeCommitGetCommand(self.session)
        self.get_command._run_main(self.args, self.globals)
        output = stdout_mock.getvalue().strip()
        self.assertRegex(
            output,
            'username={0}%{1}\npassword=.+'.format('access', 'token'))

    @mock.patch('sys.stdout', MOCK_STDOUT_CLASS())
    @mock.patch('sys.stdin', StringIO(PROTOCOL_HOST_PATH))
    @mock.patch('botocore.auth.SigV4Auth.string_to_sign')
    @mock.patch('botocore.auth.SigV4Auth.signature')
    def test_generate_credentials_creates_a_valid_request(self, signature,
                                                          string_to_sign):
        self.credentials = Credentials('access', 'secret')
        self.session.get_credentials.return_value = self.credentials
        self.get_command = CodeCommitGetCommand(self.session)
        self.get_command._run_main(self.args, self.globals)
        aws_request = signature.call_args[0][1]
        self.assertEqual('GIT', aws_request.method)
        self.assertEqual(
            'https://git-codecommit.us-east-1.amazonaws.com//v1/repos/myrepo',
            aws_request.url)
        self.assertEqual(
            ('GIT\n//v1/repos/myrepo\n\n'
             'host:git-codecommit.us-east-1.amazonaws.com\n\n'
             'host\n'),
            string_to_sign.call_args[0][1])

if __name__ == "__main__":
    unittest.main()
