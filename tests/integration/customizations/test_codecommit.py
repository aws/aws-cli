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
import os

from datetime import datetime

from awscli.compat import StringIO
from botocore.session import Session
from botocore.credentials import Credentials
from awscli.customizations.codecommit import CodeCommitGetCommand
from awscli.testutils import mock, unittest, StringIOWithFileNo
from botocore.awsrequest import AWSRequest
from awscli.clidriver import create_clidriver


class TestCodeCommitCredentialHelper(unittest.TestCase):

    PROTOCOL_HOST_PATH = ('protocol=https\n'
                          'host=git-codecommit.us-east-1.amazonaws.com\n'
                          'path=/v1/repos/myrepo')

    FIPS_PROTOCOL_HOST_PATH = ('protocol=https\n'
                               'host=git-codecommit-fips.us-east-1.amazonaws.com\n'
                               'path=/v1/repos/myrepo')

    VPC_PROTOCOL_HOST_PATH = ('protocol=https\n'
                              'host=vpce-0b47ea360adebf88a-jkl88hez.git-codecommit.us-east-1.vpce.amazonaws.com\n'
                              'path=/v1/repos/myrepo')

    def setUp(self):
        self.orig_id = os.environ.get('AWS_ACCESS_KEY_ID')
        self.orig_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
        os.environ['AWS_ACCESS_KEY_ID'] = 'foo'
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'bar'

    def tearDown(self):
        if self.orig_id:
            os.environ['AWS_ACCESS_KEY_ID'] = self.orig_id
        else:
            del os.environ['AWS_ACCESS_KEY_ID']
        if self.orig_key:
            os.environ['AWS_SECRET_ACCESS_KEY'] = self.orig_key
        else:
            del os.environ['AWS_SECRET_ACCESS_KEY']

    @mock.patch('sys.stdin', StringIO(PROTOCOL_HOST_PATH))
    @mock.patch('sys.stdout', new_callable=StringIOWithFileNo)
    @mock.patch.object(awscli.customizations.codecommit.datetime, 'datetime')
    def test_integration_using_cli_driver(self, dt_mock, stdout_mock):
        dt_mock.utcnow.return_value = datetime(2010, 10, 8)
        driver = create_clidriver()
        rc = driver.main('codecommit credential-helper get'.split())
        output = stdout_mock.getvalue().strip()
        self.assertEqual(
            ('username=foo\n'
             'password=20101008T000000Z'
             '7dc259e2d505af354a1219b9bcd784bd384dc706efa0d9aefc571f214be4c89c'),
             output)
        self.assertEqual(0, rc)

    @mock.patch('sys.stdin', StringIO(FIPS_PROTOCOL_HOST_PATH))
    @mock.patch('sys.stdout', new_callable=StringIOWithFileNo)
    @mock.patch.object(awscli.customizations.codecommit.datetime, 'datetime')
    def test_integration_fips_using_cli_driver(self, dt_mock, stdout_mock):
        dt_mock.utcnow.return_value = datetime(2010, 10, 8)
        driver = create_clidriver()
        rc = driver.main('codecommit credential-helper get'.split())
        output = stdout_mock.getvalue().strip()
        self.assertEqual(
            ('username=foo\n'
             'password=20101008T000000Z'
             '500037cb3514b3fe01ebcda7c80973f5b4c0d8199a7a6563b85fd6edf272d460'),
             output)
        self.assertEqual(0, rc)

    @mock.patch('sys.stdin', StringIO(VPC_PROTOCOL_HOST_PATH))
    @mock.patch('sys.stdout', new_callable=StringIOWithFileNo)
    @mock.patch.object(awscli.customizations.codecommit.datetime, 'datetime')
    def test_integration_vpc_using_cli_driver(self, dt_mock, stdout_mock):
        dt_mock.utcnow.return_value = datetime(2010, 10, 8)
        driver = create_clidriver()
        rc = driver.main('codecommit credential-helper get'.split())
        output = stdout_mock.getvalue().strip()
        self.assertEqual(
            ('username=foo\n'
             'password=20101008T000000Z'
             '9ed987cc6336c3de2d9f06b9236c7a9fd76b660b080db15983290e636dbfbd6b'),
             output)
        self.assertEqual(0, rc)


if __name__ == "__main__":
    unittest.main()
