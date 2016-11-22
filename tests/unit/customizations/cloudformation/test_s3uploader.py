# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0e
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import os
import mock
import random
import string
import tempfile
import hashlib
import shutil
from mock import patch, Mock

import botocore
import botocore.session
import botocore.exceptions
from botocore.stub import Stubber
from s3transfer import S3Transfer

from awscli.testutils import unittest
from awscli.customizations.cloudformation.s3uploader import S3Uploader
from awscli.customizations.cloudformation import exceptions


class TestS3Uploader(unittest.TestCase):

    def setUp(self):
        self.s3client = botocore.session.get_session().create_client(
                's3', region_name="us-east-1")
        self.s3client_stub = Stubber(self.s3client)
        self.transfer_manager_mock = Mock(spec=S3Transfer)
        self.transfer_manager_mock.upload = Mock()
        self.bucket_name = "bucketname"
        self.prefix = None

        self.s3uploader = S3Uploader(
            self.s3client, self.bucket_name, self.prefix, None, False,
            self.transfer_manager_mock)

    @patch("awscli.customizations.cloudformation.s3uploader.ProgressPercentage")
    def test_upload_successful(self, progress_percentage_mock):
        file_name = "filename"
        remote_path = "remotepath"
        prefix = "SomePrefix"
        remote_path_with_prefix = "{0}/{1}".format(prefix, remote_path)
        s3uploader = S3Uploader(
            self.s3client, self.bucket_name, prefix, None, False,
            self.transfer_manager_mock)
        expected_upload_url = "s3://{0}/{1}/{2}".format(
            self.bucket_name, prefix, remote_path)

        # Setup mock to fake that file does not exist
        s3uploader.file_exists = Mock()
        s3uploader.file_exists.return_value = False

        upload_url = s3uploader.upload(file_name, remote_path)
        self.assertEquals(expected_upload_url, upload_url)

        expected_encryption_args = {
            "ServerSideEncryption": "AES256"
        }
        self.transfer_manager_mock.upload.assert_called_once_with(
                file_name, self.bucket_name, remote_path_with_prefix,
                expected_encryption_args, mock.ANY)
        s3uploader.file_exists.assert_called_once_with(remote_path_with_prefix)

    @patch("awscli.customizations.cloudformation.s3uploader.ProgressPercentage")
    def test_upload_idempotency(self, progress_percentage_mock):
        file_name = "filename"
        remote_path = "remotepath"

        # Setup mock to fake that file was already uploaded
        self.s3uploader.file_exists = Mock()
        self.s3uploader.file_exists.return_value = True

        self.s3uploader.upload(file_name, remote_path)

        self.transfer_manager_mock.upload.assert_not_called()
        self.s3uploader.file_exists.assert_called_once_with(remote_path)

    @patch("awscli.customizations.cloudformation.s3uploader.ProgressPercentage")
    def test_upload_force_upload(self, progress_percentage_mock):
        file_name = "filename"
        remote_path = "remotepath"
        expected_upload_url = "s3://{0}/{1}".format(self.bucket_name,
                                                    remote_path)

        # Set ForceUpload = True
        self.s3uploader = S3Uploader(
            self.s3client, self.bucket_name, self.prefix,
            None, True, self.transfer_manager_mock)

        # Pretend file already exists
        self.s3uploader.file_exists = Mock()
        self.s3uploader.file_exists.return_value = True

        # Because we forced an update, this should reupload even if file exists
        upload_url = self.s3uploader.upload(file_name, remote_path)
        self.assertEquals(expected_upload_url, upload_url)

        expected_encryption_args = {
            "ServerSideEncryption": "AES256"
        }
        self.transfer_manager_mock.upload.assert_called_once_with(
                file_name, self.bucket_name, remote_path,
                expected_encryption_args, mock.ANY)

        # Since ForceUpload=True, we should NEVER do the file-exists check
        self.s3uploader.file_exists.assert_not_called()

    @patch("awscli.customizations.cloudformation.s3uploader.ProgressPercentage")
    def test_upload_successful_custom_kms_key(self, progress_percentage_mock):
        file_name = "filename"
        remote_path = "remotepath"
        kms_key_id = "kms_id"
        expected_upload_url = "s3://{0}/{1}".format(self.bucket_name,
                                                    remote_path)
        # Set KMS Key Id
        self.s3uploader = S3Uploader(
            self.s3client, self.bucket_name, self.prefix,
            kms_key_id, False, self.transfer_manager_mock)

        # Setup mock to fake that file does not exist
        self.s3uploader.file_exists = Mock()
        self.s3uploader.file_exists.return_value = False

        upload_url = self.s3uploader.upload(file_name, remote_path)
        self.assertEquals(expected_upload_url, upload_url)

        expected_encryption_args = {
            "ServerSideEncryption": "aws:kms",
            "SSEKMSKeyId": kms_key_id
        }
        self.transfer_manager_mock.upload.assert_called_once_with(
                file_name, self.bucket_name, remote_path,
                expected_encryption_args, mock.ANY)
        self.s3uploader.file_exists.assert_called_once_with(remote_path)

    @patch("awscli.customizations.cloudformation.s3uploader.ProgressPercentage")
    def test_upload_successful_nobucket(self, progress_percentage_mock):
        file_name = "filename"
        remote_path = "remotepath"

        # Setup mock to fake that file does not exist
        self.s3uploader.file_exists = Mock()
        self.s3uploader.file_exists.return_value = False

        # Setup uploader to return a NOSuchBucket exception
        exception = botocore.exceptions.ClientError(
                {"Error": {"Code": "NoSuchBucket"}}, "OpName")
        self.transfer_manager_mock.upload.side_effect = exception

        with self.assertRaises(exceptions.NoSuchBucketError):
            self.s3uploader.upload(file_name, remote_path)

    @patch("awscli.customizations.cloudformation.s3uploader.ProgressPercentage")
    def test_upload_successful_exceptions(self, progress_percentage_mock):
        file_name = "filename"
        remote_path = "remotepath"

        # Setup mock to fake that file does not exist
        self.s3uploader.file_exists = Mock()
        self.s3uploader.file_exists.return_value = False

        # Raise an unrecognized botocore error
        exception = botocore.exceptions.ClientError(
                {"Error": {"Code": "SomeError"}}, "OpName")
        self.transfer_manager_mock.upload.side_effect = exception

        with self.assertRaises(botocore.exceptions.ClientError):
            self.s3uploader.upload(file_name, remote_path)

        # Some other exception
        self.transfer_manager_mock.upload.side_effect = FloatingPointError()
        with self.assertRaises(FloatingPointError):
            self.s3uploader.upload(file_name, remote_path)

    def test_upload_with_dedup(self):

        checksum = "some md5 checksum"
        filename = "filename"
        extension = "extn"

        self.s3uploader.file_checksum = Mock()
        self.s3uploader.file_checksum.return_value = checksum

        self.s3uploader.upload = Mock()

        self.s3uploader.upload_with_dedup(filename, extension)

        remotepath = "{0}.{1}".format(checksum, extension)
        self.s3uploader.upload.assert_called_once_with(filename, remotepath)

    def test_file_exists(self):
        key = "some/path"
        expected_params = {
            "Bucket": self.bucket_name,
            "Key": key
        }
        response = {
            "AcceptRanges": "bytes",
            "ContentType": "text/html",
            "LastModified": "Thu, 16 Apr 2015 18:19:14 GMT",
            "ContentLength": 77,
            "VersionId": "null",
            "ETag": "\"30a6ec7e1a9ad79c203d05a589c8b400\"",
            "Metadata": {}
        }

        # Let's pretend file exists
        self.s3client_stub.add_response("head_object",
                                        response,
                                        expected_params)

        with self.s3client_stub:
            self.assertTrue(self.s3uploader.file_exists(key))

        # Let's pretend file does not exist
        self.s3client_stub.add_client_error(
            'head_object', "ClientError", "some error")
        with self.s3client_stub:
            self.assertFalse(self.s3uploader.file_exists(key))

        # Let's pretend some other unknown exception happened
        s3mock = Mock()
        uploader = S3Uploader(s3mock, self.bucket_name)
        s3mock.head_object = Mock()
        s3mock.head_object.side_effect = RuntimeError()

        with self.assertRaises(RuntimeError):
            uploader.file_exists(key)

    def test_file_checksum(self):
        num_chars = 4096*5
        data = ''.join(random.choice(string.ascii_uppercase)
                       for _ in range(num_chars)).encode('utf-8')
        md5 = hashlib.md5()
        md5.update(data)
        expected_checksum = md5.hexdigest()

        tempdir = tempfile.mkdtemp()
        try:
            filename = os.path.join(tempdir, 'tempfile')
            with open(filename, 'wb') as f:
                f.write(data)

            actual_checksum = self.s3uploader.file_checksum(filename)
            self.assertEqual(expected_checksum, actual_checksum)
        finally:
            shutil.rmtree(tempdir)

    def test_make_url(self):
        path = "Hello/how/are/you"
        expected = "s3://{0}/{1}".format(self.bucket_name, path)
        self.assertEquals(expected, self.s3uploader.make_url(path))
