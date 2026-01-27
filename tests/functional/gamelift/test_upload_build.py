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
import os
from awscli.testutils import BaseAWSCommandParamsTest, FileCreator, mock


class TestUploadBuild(BaseAWSCommandParamsTest):

    prefix = 'gamelift upload-build'

    def setUp(self):
        super().setUp()
        self.files = FileCreator()

    def tearDown(self):
        super().tearDown()
        self.files.remove_all()

    def test_upload_build(self):
        self.files.create_file('tmpfile', 'Some contents')
        cmdline = self.prefix
        cmdline += ' --name mybuild --build-version myversion'
        cmdline += f' --build-root {self.files.rootdir}'

        self.parsed_responses = [
            {'Build': {'BuildId': 'myid'}},
            {'StorageLocation': {
                'Bucket': 'mybucket',
                'Key': 'mykey'},
             'UploadCredentials': {
                'AccessKeyId': 'myaccesskey',
                'SecretAccessKey': 'mysecretkey',
                'SessionToken': 'mytoken'}},
            {}
        ]

        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=0)

        # First the build is created.
        self.assertEqual(len(self.operations_called), 3)
        self.assertEqual(self.operations_called[0][0].name, 'CreateBuild')
        self.assertEqual(
            self.operations_called[0][1],
            {'Name': 'mybuild', 'Version': 'myversion'}
        )

        # Second the credentials are requested.
        self.assertEqual(
            self.operations_called[1][0].name, 'RequestUploadCredentials')
        self.assertEqual(
            self.operations_called[1][1], {'BuildId': 'myid'})

        # The build is then uploaded to S3.
        self.assertEqual(self.operations_called[2][0].name, 'PutObject')
        self.assertEqual(
            self.operations_called[2][1],
            {'Body': mock.ANY, 'Bucket': 'mybucket', 'Key': 'mykey'}
        )

        # Check the output of the command.
        self.assertIn(
            f'Successfully uploaded {self.files.rootdir} to AWS GameLift',
            stdout)
        self.assertIn('Build ID: myid', stdout)

    def test_upload_build_with_operating_system_param(self):
        self.files.create_file('tmpfile', 'Some contents')
        cmdline = self.prefix
        cmdline += ' --name mybuild --build-version myversion'
        cmdline += f' --build-root {self.files.rootdir}'
        cmdline += ' --operating-system WINDOWS_2012'

        self.parsed_responses = [
            {'Build': {'BuildId': 'myid'}},
            {'StorageLocation': {
                'Bucket': 'mybucket',
                'Key': 'mykey'},
             'UploadCredentials': {
                'AccessKeyId': 'myaccesskey',
                'SecretAccessKey': 'mysecretkey',
                'SessionToken': 'mytoken'}},
            {}
        ]

        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=0)

        # First the build is created.
        self.assertEqual(len(self.operations_called), 3)
        self.assertEqual(self.operations_called[0][0].name, 'CreateBuild')
        self.assertEqual(
            self.operations_called[0][1],
            {'Name': 'mybuild', 'Version': 'myversion',
             'OperatingSystem': 'WINDOWS_2012'}
        )

        # Second the credentials are requested.
        self.assertEqual(
            self.operations_called[1][0].name, 'RequestUploadCredentials')
        self.assertEqual(
            self.operations_called[1][1], {'BuildId': 'myid'})

        # The build is then uploaded to S3.
        self.assertEqual(self.operations_called[2][0].name, 'PutObject')
        self.assertEqual(
            self.operations_called[2][1],
            {'Body': mock.ANY, 'Bucket': 'mybucket', 'Key': 'mykey'}
        )

        # Check the output of the command.
        self.assertIn(
            f'Successfully uploaded {self.files.rootdir} to AWS GameLift',
            stdout)
        self.assertIn('Build ID: myid', stdout)

    def test_upload_build_with_empty_directory(self):
        cmdline = self.prefix
        cmdline += ' --name mybuild --build-version myversion'
        cmdline += f' --build-root {self.files.rootdir}'

        self.parsed_responses = [
            {'Build': {'BuildId': 'myid'}},
            {'StorageLocation': {
                'Bucket': 'mybucket',
                'Key': 'mykey'},
             'UploadCredentials': {
                'AccessKeyId': 'myaccesskey',
                'SecretAccessKey': 'mysecretkey',
                'SessionToken': 'mytoken'}},
            {}
            ]

        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=255)

        self.assertIn(
            f'Fail to upload {self.files.rootdir}. '
            'The build root directory is empty or does not exist.\n',
            stderr)

    def test_upload_build_with_nonexistent_directory(self):
        dir_not_exist = os.path.join(self.files.rootdir, 'does_not_exist')

        cmdline = self.prefix
        cmdline += ' --name mybuild --build-version myversion'
        cmdline += f' --build-root {dir_not_exist}'

        self.parsed_responses = [
            {'Build': {'BuildId': 'myid'}},
            {'StorageLocation': {
                'Bucket': 'mybucket',
                'Key': 'mykey'},
             'UploadCredentials': {
                'AccessKeyId': 'myaccesskey',
                'SecretAccessKey': 'mysecretkey',
                'SessionToken': 'mytoken'}},
            {}
            ]

        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=255)

        self.assertIn(
            f'Fail to upload {dir_not_exist}. '
            'The build root directory is empty or does not exist.\n',
            stderr)

    def test_upload_build_with_nonprovided_directory(self):
        cmdline = self.prefix
        cmdline += ' --name mybuild --build-version myversion'
        cmdline += ' --build-root {}'.format('""')

        self.parsed_responses = [
            {'Build': {'BuildId': 'myid'}},
            {'StorageLocation': {
                'Bucket': 'mybucket',
                'Key': 'mykey'},
             'UploadCredentials': {
                'AccessKeyId': 'myaccesskey',
                'SecretAccessKey': 'mysecretkey',
                'SessionToken': 'mytoken'}},
            {}
            ]

        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=255)

        self.assertIn(
            'Fail to upload {}. '
            'The build root directory is empty or does not exist.\n'.format('""'),
            stderr)

    def test_upload_build_with_server_sdk_version_param(self):
        self.files.create_file('tmpfile', 'Some contents')
        cmdline = self.prefix
        cmdline += ' --name mybuild --build-version myversion'
        cmdline += f' --build-root {self.files.rootdir}'
        cmdline += ' --server-sdk-version 4.0.2'

        self.parsed_responses = [
            {'Build': {'BuildId': 'myid'}},
            {'StorageLocation': {
                'Bucket': 'mybucket',
                'Key': 'mykey'},
                'UploadCredentials': {
                    'AccessKeyId': 'myaccesskey',
                    'SecretAccessKey': 'mysecretkey',
                    'SessionToken': 'mytoken'}},
            {}
        ]

        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=0)

        # First the build is created.
        self.assertEqual(len(self.operations_called), 3)
        self.assertEqual(self.operations_called[0][0].name, 'CreateBuild')
        self.assertEqual(
            self.operations_called[0][1],
            {'Name': 'mybuild', 'Version': 'myversion',
             'ServerSdkVersion': '4.0.2'}
        )

        # Second the credentials are requested.
        self.assertEqual(
            self.operations_called[1][0].name, 'RequestUploadCredentials')
        self.assertEqual(
            self.operations_called[1][1], {'BuildId': 'myid'})

        # The build is then uploaded to S3.
        self.assertEqual(self.operations_called[2][0].name, 'PutObject')
        self.assertEqual(
            self.operations_called[2][1],
            {'Body': mock.ANY, 'Bucket': 'mybucket', 'Key': 'mykey'}
        )

        # Check the output of the command.
        self.assertIn(
            f'Successfully uploaded {self.files.rootdir} to AWS GameLift',
            stdout)
        self.assertIn('Build ID: myid', stdout)

    def test_upload_build_with_tags_param(self):
        self.files.create_file('tmpfile', 'Some contents')
        
        expected_tags = [
            {'Key': 'Key1', 'Value': 'Value1'},
            {'Key': 'Key2', 'Value': 'Value2'}
        ]
        
        cmdline = self.prefix
        cmdline += ' --name mybuild --build-version myversion'
        cmdline += f' --build-root {self.files.rootdir}'
        cmdline += ' --tags'
        for tag in expected_tags:
            cmdline += ' {}={}'.format(tag['Key'], tag['Value'])

        self.parsed_responses = [
            {'Build': {'BuildId': 'myid'}},
            {'StorageLocation': {
                'Bucket': 'mybucket',
                'Key': 'mykey'},
                'UploadCredentials': {
                    'AccessKeyId': 'myaccesskey',
                    'SecretAccessKey': 'mysecretkey',
                    'SessionToken': 'mytoken'}},
            {}
        ]

        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=0)

        # First the build is created.
        self.assertEqual(len(self.operations_called), 3)
        self.assertEqual(self.operations_called[0][0].name, 'CreateBuild')
        self.assertEqual(
            self.operations_called[0][1],
            {'Name': 'mybuild', 'Version': 'myversion',
             'Tags': expected_tags}
        )

        # Second the credentials are requested.
        self.assertEqual(
            self.operations_called[1][0].name, 'RequestUploadCredentials')
        self.assertEqual(
            self.operations_called[1][1], {'BuildId': 'myid'})

        # The build is then uploaded to S3.
        self.assertEqual(self.operations_called[2][0].name, 'PutObject')
        self.assertEqual(
            self.operations_called[2][1],
            {'Body': mock.ANY, 'Bucket': 'mybucket', 'Key': 'mykey'}
        )

        # Check the output of the command.
        self.assertIn(
            f'Successfully uploaded {self.files.rootdir} to AWS GameLift',
            stdout)
        self.assertIn('Build ID: myid', stdout)
