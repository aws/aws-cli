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
from argparse import Namespace
import contextlib
import os
import zipfile

from botocore.session import get_session
from botocore.exceptions import ClientError

from awscli.testutils import unittest, mock, FileCreator
from awscli.customizations.gamelift.uploadbuild import UploadBuildCommand
from awscli.customizations.gamelift.uploadbuild import zip_directory
from awscli.customizations.gamelift.uploadbuild import validate_directory
from awscli.compat import StringIO


class TestGetGameSessionLogCommand(unittest.TestCase):
    def setUp(self):
        self.create_client_patch = mock.patch(
            'botocore.session.Session.create_client')
        self.mock_create_client = self.create_client_patch.start()
        self.session = get_session()

        self.gamelift_client = mock.Mock()
        self.s3_client = mock.Mock()
        self.mock_create_client.side_effect = [
            self.gamelift_client, self.s3_client
        ]

        self.file_creator = FileCreator()
        self.upload_file_patch = mock.patch(
            'awscli.customizations.gamelift.uploadbuild.S3Transfer.upload_file'
        )
        self.upload_file_mock = self.upload_file_patch.start()

        self.cmd = UploadBuildCommand(self.session)
        self._setup_input_output()

    def tearDown(self):
        self.create_client_patch.stop()
        self.file_creator.remove_all()
        self.upload_file_patch.stop()

    def _setup_input_output(self):
        # Input values
        self.region = 'us-west-2'
        self.build_name = 'mybuild'
        self.build_version = 'myversion'
        self.build_root = self.file_creator.rootdir

        self.args = [
            '--name', self.build_name, '--build-version', self.build_version,
            '--build-root', self.build_root
        ]

        self.global_args = Namespace()
        self.global_args.region = self.region
        self.global_args.endpoint_url = None
        self.global_args.verify_ssl = None

        # Output values
        self.build_id = 'myid'
        self.bucket = 'mybucket'
        self.key = 'mykey'
        self.access_key = 'myaccesskey'
        self.secret_key = 'mysecretkey'
        self.session_token = 'mytoken'

        self.gamelift_client.create_build.return_value = {
            'Build': {
                'BuildId': self.build_id
            }
        }

        self.gamelift_client.request_upload_credentials.return_value = {
            'StorageLocation': {
                'Bucket': self.bucket,
                'Key': self.key
            },
            'UploadCredentials': {
                'AccessKeyId': self.access_key,
                'SecretAccessKey': self.secret_key,
                'SessionToken': self.session_token
            }
        }

    def test_upload_build(self):
        self.file_creator.create_file('tmpfile', 'Some contents')
        self.cmd(self.args, self.global_args)
        # Ensure the clients were instantiated correctly.
        client_creation_args = self.mock_create_client.call_args_list
        self.assertEqual(
            client_creation_args,
            [mock.call('gamelift', region_name=self.region,
                       endpoint_url=None, verify=None),
             mock.call('s3', aws_access_key_id=self.access_key,
                       aws_secret_access_key=self.secret_key,
                       aws_session_token=self.session_token,
                       region_name=self.region,
                       verify=None)]
        )

        # Ensure the GameLift client was called correctly.
        self.gamelift_client.create_build.assert_called_once_with(
            Name=self.build_name, Version=self.build_version)

        self.gamelift_client.request_upload_credentials.\
            assert_called_once_with(BuildId=self.build_id)

        # Ensure the underlying S3 transfer call was correct.
        self.upload_file_mock.assert_called_once_with(
            mock.ANY, self.bucket, self.key, callback=mock.ANY)

        tempfile_path = self.upload_file_mock.call_args[0][0]
        # Ensure the temporary zipfile is deleted at the end.
        self.assertFalse(os.path.exists(tempfile_path))

    def test_upload_build_when_operating_system_is_provided(self):
        operating_system = 'WINDOWS_2012'
        self.file_creator.create_file('tmpfile', 'Some contents')
        self.args = [
            '--name', self.build_name, '--build-version', self.build_version,
            '--build-root', self.build_root,
            '--operating-system', operating_system
        ]
        self.cmd(self.args, self.global_args)

        # Ensure the GameLift client was called correctly.
        self.gamelift_client.create_build.assert_called_once_with(
            Name=self.build_name, Version=self.build_version,
            OperatingSystem=operating_system)

    def test_error_message_when_directory_is_empty(self):
        with mock.patch('sys.stderr', StringIO()) as mock_stderr:
            self.cmd(self.args, self.global_args)
            self.assertEqual(
                mock_stderr.getvalue(),
                'Fail to upload %s. '
                'The build root directory is empty or does not exist.\n'
                % (self.build_root)
            )

    def test_error_message_when_directory_is_not_provided(self):
        self.args = [
            '--name', self.build_name,
            '--build-version', self.build_version,
            '--build-root', ''
        ]

        with mock.patch('sys.stderr', StringIO()) as mock_stderr:
            self.cmd(self.args, self.global_args)
            self.assertEqual(
                mock_stderr.getvalue(),
                'Fail to upload %s. '
                'The build root directory is empty or does not exist.\n' % ('')
            )

    def test_error_message_when_directory_does_not_exist(self):
        dir_not_exist = os.path.join(self.build_root, 'does_not_exist')

        self.args = [
            '--name', self.build_name,
            '--build-version', self.build_version,
            '--build-root', dir_not_exist
        ]

        with mock.patch('sys.stderr', StringIO()) as mock_stderr:
            self.cmd(self.args, self.global_args)
            self.assertEqual(
                mock_stderr.getvalue(),
                'Fail to upload %s. '
                'The build root directory is empty or does not exist.\n'
                % (dir_not_exist)
            )

    def test_temporary_file_does_exist_when_fails(self):
        self.upload_file_mock.side_effect = ClientError(
            {'Error': {'Code': 403, 'Message': 'No Access'}}, 'PutObject')
        with self.assertRaises(ClientError):
            self.file_creator.create_file('tmpfile', 'Some contents')
            self.cmd(self.args, self.global_args)
            tempfile_path = self.upload_file_mock.call_args[0][0]
            # Make sure the temporary file is removed.
            self.assertFalse(os.path.exists(tempfile_path))

    def test_upload_build_when_server_sdk_version_is_provided(self):
        server_sdk_version = '4.0.2'
        self.file_creator.create_file('tmpfile', 'Some contents')
        self.args = [
            '--name', self.build_name, '--build-version', self.build_version,
            '--build-root', self.build_root,
            '--server-sdk-version', server_sdk_version
        ]
        self.cmd(self.args, self.global_args)

        # Ensure the GameLift client was called correctly.
        self.gamelift_client.create_build.assert_called_once_with(
            Name=self.build_name, Version=self.build_version,
            ServerSdkVersion=server_sdk_version)


class TestZipDirectory(unittest.TestCase):
    def setUp(self):
        self.file_creator = FileCreator()
        self.zip_file = self.file_creator.create_file('build.zip', '')
        self._dir_root = 'mybuild'

    def tearDown(self):
        self.file_creator.remove_all()

    @property
    def dir_root(self):
        return self.file_creator.full_path(self._dir_root)

    def add_to_directory(self, filename):
        self.file_creator.create_file(
            os.path.join(self._dir_root, filename), 'Some contents')

    def assert_contents_of_zip_file(self, filenames):
        zip_file_object = zipfile.ZipFile(
            self.zip_file, 'r', zipfile.ZIP_DEFLATED)
        with contextlib.closing(zip_file_object) as zf:
            ref_zipfiles = []
            zipfile_contents = zf.namelist()
            for ref_zipfile in zipfile_contents:
                if os.sep == '\\':
                    # Internally namelist() represent directories with
                    # forward slashes so we need to account for that if
                    # the separator is a backslash depending on the operating
                    # system.
                    ref_zipfile = ref_zipfile.replace('/', '\\')
                ref_zipfiles.append(ref_zipfile)
            self.assertEqual(sorted(ref_zipfiles), filenames)

    def test_single_file(self):
        self.add_to_directory('foo')
        zip_directory(self.zip_file, self.dir_root)
        self.assert_contents_of_zip_file(['foo'])

    def test_multiple_files(self):
        self.add_to_directory('foo')
        self.add_to_directory('bar')
        zip_directory(self.zip_file, self.dir_root)
        self.assert_contents_of_zip_file(['bar', 'foo'])

    def test_nested_file(self):
        filename = os.path.join('mydir', 'foo')
        self.add_to_directory(filename)
        zip_directory(self.zip_file, self.dir_root)
        self.assert_contents_of_zip_file([filename])


class TestValidateDirectory(unittest.TestCase):
    def setUp(self):
        self.file_creator = FileCreator()
        self.dir_root = self.file_creator.rootdir

    def tearDown(self):
        self.file_creator.remove_all()

    def test_directory_contains_single_file(self):
        self.file_creator.create_file('foo', '')
        self.assertTrue(validate_directory(self.dir_root))

    def test_directory_contains_file_and_empty_directory(self):
        dirname = os.path.join(self.dir_root, 'foo')
        os.makedirs(dirname)
        self.file_creator.create_file('bar', '')
        self.assertTrue(validate_directory(self.dir_root))

    def test_nested_file(self):
        self.file_creator.create_file('mydir/bar', '')
        self.assertTrue(validate_directory(self.dir_root))

    def test_empty_directory(self):
        self.assertFalse(validate_directory(self.dir_root))

    def test_nonexistent_directory(self):
        dir_not_exist = os.path.join(self.dir_root, 'does_not_exist')
        self.assertFalse(validate_directory(dir_not_exist))

    def test_nonprovided_directory(self):
        self.assertFalse(validate_directory(''))

    def test_empty_nested_directory(self):
        dirname = os.path.join(self.dir_root, 'foo')
        os.makedirs(dirname)
        self.assertFalse(validate_directory(self.dir_root))
