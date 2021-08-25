# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.testutils import FileCreator, BaseAWSCommandParamsTest, \
    create_clidriver


class TestSignin(BaseAWSCommandParamsTest):
    prefix = 'signin'

    def setUp(self):
        super(TestSignin, self).setUp()
        self.environ['AWS_CONFIG_FILE'] = FileCreator().create_file(
            'config',
            '[default]\ncli_follow_urlparam = false\n')
        self.environ['AWS_ACCESS_KEY_ID'] = 'ASIAAAAAAAAAAAAAAAAAA'
        self.environ['AWS_SECRET_ACCESS_KEY'] = 'SECRET_ACCESS_TEST_VALUE'
        self.environ['AWS_SESSION_TOKEN'] = 'SESSION_TOKEN_TEST_VALUE'
        self.driver = create_clidriver()

    def tearDown(self):
        super(TestSignin, self).tearDown()

    def test_signin(self):
        args = (' --partition AWS --destination-url'
                ' https://console.aws.amazon.com/cloudformation/home'
                ' --issuer-url http://sso.mycompany.com')
        cmdline = self.prefix + args

        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=0)

        self.assertIn(
            'https://signin.aws.amazon.com/federation',
            stdout,
            msg='Signin URL does not contain the proper domain and path'
        )

        self.assertIn(
            'Action=login',
            stdout,
            msg='Signin URL does not contain the proper action parameter'
        )

        self.assertIn(
            'Issuer=http%3A%2F%2Fsso.mycompany.com',
            stdout,
            msg='Signin URL does not contain the proper issuer parameter'
        )

        self.assertIn(
            ('Destination=https%3A%2F%2Fconsole.aws.amazon.com%2Fcloudformatio'
             'n%2Fhome'),
            stdout,
            msg='Signin URL does not contain the proper destination parameter'
        )

        self.assertIn(
            ('SigninToken='),
            stdout,
            msg='Signin URL does not contain a signin token'
        )

        self.assertEqual(rc, 0, msg='Signin does not return a 0 exit code')
