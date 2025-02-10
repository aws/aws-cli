# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from botocore.exceptions import ClientError

from awscli.customizations.codedeploy.push import Push
from awscli.testutils import mock, unittest
from awscli.compat import StringIO, ZIP_COMPRESSION_MODE


class TestPush(unittest.TestCase):
    def setUp(self):
        self.application_name = 'MyApp'
        self.description = 'MyApp revision'
        self.source = '/tmp'
        self.appspec = 'appspec.yml'
        self.appspec_path = '{0}/{1}'.format(self.source, self.appspec)
        self.bucket = 'foo'
        self.key = 'bar/baz.zip'
        self.s3_location = 's3://' + self.bucket + '/' + self.key
        self.eTag = '"1a2b3cd45e"'
        self.version_id = '12341234-1234-1234-1234-123412341234'
        self.upload_id = 'upload_id'
        self.region = 'us-east-1'
        self.endpoint_url = 'https://codedeploy.aws.amazon.com'

        self.args = Namespace()
        self.args.application_name = self.application_name
        self.args.s3_location = self.s3_location
        self.args.ignore_hidden_files = False
        self.args.no_ignore_hidden_files = False
        self.args.description = self.description
        self.args.source = self.source

        self.globals = Namespace()
        self.globals.region = self.region
        self.globals.endpoint_url = self.endpoint_url
        self.globals.verify_ssl = False

        self.upload_response = {
            'ETag': self.eTag,
            'VersionId': self.version_id
        }
        self.revision = {
            'revisionType': 'S3',
            's3Location': {
                'bucket': self.bucket,
                'key': self.key,
                'bundleType': 'zip',
                'eTag': self.eTag,
                'version': self.version_id
            }
        }

        self.bundle_mock = mock.MagicMock()
        self.bundle_mock.tell.return_value = (5 << 20)
        self.bundle_mock.read.return_value = b'a' * (5 << 20)
        self.bundle_mock.__enter__.return_value = self.bundle_mock
        self.bundle_mock.__exit__.return_value = None

        self.zipfile_mock = mock.MagicMock()
        self.zipfile_mock.write.return_value = None
        self.zipfile_mock.close.return_value = None
        self.zipfile_mock.__enter__.return_value = self.zipfile_mock
        self.zipfile_mock.__exit__.return_value = None

        self.session = mock.MagicMock()

        self.push = Push(self.session)
        self.push.s3 = mock.MagicMock()
        self.push.s3.put_object.return_value = self.upload_response
        self.push.s3.create_multipart_upload.return_value = {
            'UploadId': self.upload_id
        }
        self.push.s3.upload_part.return_value = {
            'ETag': self.eTag
        }
        self.push.s3.complete_multipart_upload\
            .return_value = self.upload_response
        self.push.codedeploy = mock.MagicMock()

    def test_run_main_throws_on_invalid_args(self):
        self.push._validate_args = mock.MagicMock()
        self.push._validate_args.side_effect = RuntimeError()
        with self.assertRaises(RuntimeError):
            self.push._run_main(self.args, self.globals)

    def test_run_main_creates_clients(self):
        self.push._validate_args = mock.MagicMock()
        self.push._push = mock.MagicMock()
        self.push._run_main(self.args, self.globals)
        self.session.create_client.assert_has_calls([
            mock.call(
                'codedeploy',
                region_name=self.region,
                endpoint_url=self.endpoint_url,
                verify=self.globals.verify_ssl
            ),
            mock.call('s3', region_name=self.region)
        ])

    def test_run_main_calls_push(self):
        self.push._validate_args = mock.MagicMock()
        self.push._push = mock.MagicMock()
        self.push._run_main(self.args, self.globals)
        self.push._push.assert_called_with(self.args)

    @mock.patch.object(
        awscli.customizations.codedeploy.push,
        'validate_s3_location'
    )
    def test_validate_args_throws_on_invalid_s3_url(
            self, validate_s3_location
    ):
        self.args.s3_location = 's3:/foo/bar/baz'
        validate_s3_location.side_effect = RuntimeError()
        with self.assertRaises(RuntimeError):
            self.push._validate_args(self.args)

    def test_validate_args_throws_on_ignore_and_no_ignore_hidden_files(self):
        self.args.ignore_hidden_files = True
        self.args.no_ignore_hidden_files = True
        with self.assertRaises(RuntimeError):
            self.push._validate_args(self.args)

    def test_validate_args_default_description(self):
        self.args.description = None
        self.push._validate_args(self.args)
        self.assertRegex(
            self.args.description,
            'Uploaded by AWS CLI .* UTC'
        )

    def test_push_throws_on_upload_to_s3_error(self):
        self.args.bucket = self.bucket
        self.args.key = self.key
        self.push._compress = mock.MagicMock(return_value=self.bundle_mock)
        self.push._upload_to_s3 = mock.MagicMock()
        self.push._upload_to_s3.side_effect = RuntimeError()
        with self.assertRaises(RuntimeError):
            self.push._push(self.args)

    def test_push_strips_quotes_from_etag(self):
        self.args.bucket = self.bucket
        self.args.key = self.key
        self.push._compress = mock.MagicMock(return_value=self.bundle_mock)
        self.push._upload_to_s3 = mock.MagicMock(return_value=self.upload_response)
        self.push._register_revision = mock.MagicMock()
        self.push._push(self.args)
        self.push._register_revision.assert_called_with(self.args)
        self.assertEqual(str(self.args.eTag), self.upload_response['ETag'].replace('"',""))

    @mock.patch('sys.stdout', new_callable=StringIO)
    def test_push_output_message(self, stdout_mock):
        self.args.bucket = self.bucket
        self.args.key = self.key
        self.push._compress = mock.MagicMock(return_value=self.bundle_mock)
        self.push._upload_to_s3 = mock.MagicMock(return_value=self.upload_response)
        self.push._register_revision = mock.MagicMock()
        self.push._push(self.args)
        output = stdout_mock.getvalue().strip()
        expected_revision_output = (
            '--s3-location bucket={0},key={1},'
            'bundleType=zip,eTag={2},version={3}'.format(
                self.bucket,
                self.key,
                self.eTag.replace('"',""),
                self.version_id)
        )
        expected_output = (
            'To deploy with this revision, run:\n'
            'aws deploy create-deployment '
            '--application-name {0} {1} '
            '--deployment-group-name <deployment-group-name> '
            '--deployment-config-name <deployment-config-name> '
            '--description <description>'.format(
                self.application_name,
                expected_revision_output
            )
        )
        self.assertEqual(expected_output, output)

    @mock.patch('zipfile.ZipFile')
    @mock.patch('tempfile.TemporaryFile')
    @mock.patch('os.path')
    @mock.patch('os.walk')
    def test_compress_throws_when_no_appspec(self, walk, path, tf, zf):
        walk.return_value = [(self.source, [], ['noappspec.yml'])]
        noappsec_path = self.source + '/noappspec.yml'
        path.join.return_value = noappsec_path
        path.sep = '/'
        path.abspath.side_effect = [self.source, noappsec_path]
        tf.return_value = self.bundle_mock
        zf.return_value = self.zipfile_mock
        with self.assertRaises(RuntimeError):
            with self.push._compress(
                    self.args.source,
                    self.args.ignore_hidden_files):
                pass

    @mock.patch('zipfile.ZipFile')
    @mock.patch('tempfile.TemporaryFile')
    @mock.patch('os.path')
    @mock.patch('os.walk')
    def test_compress_writes_to_zip_file(self, walk, path, tf, zf):
        walk.return_value = [(self.source, [], [self.appspec])]
        path.join.return_value = self.appspec_path
        path.sep = '/'
        path.abspath.side_effect = [self.source, self.appspec_path]
        tf.return_value = self.bundle_mock
        zf.return_value = self.zipfile_mock
        with self.push._compress(
                self.args.source,
                self.args.ignore_hidden_files):
            zf.assert_called_with(mock.ANY, 'w', allowZip64=True)
            zf().write.assert_called_with(
                '/tmp/appspec.yml',
                self.appspec,
                ZIP_COMPRESSION_MODE
            )

    def test_upload_to_s3_with_put_object(self):
        self.args.bucket = self.bucket
        self.args.key = self.key
        response = self.push._upload_to_s3(self.args, self.bundle_mock)
        self.assertDictEqual(self.upload_response, response)
        self.push.s3.put_object.assert_called_with(
            Bucket=self.bucket,
            Key=self.key,
            Body=self.bundle_mock
        )
        self.assertFalse(self.push.s3.create_multipart_upload.called)
        self.assertFalse(self.push.s3.upload_part.called)
        self.assertFalse(self.push.s3.complete_multipart_upload.called)
        self.assertFalse(self.push.s3.abort_multipart_upload.called)

    def test_upload_to_s3_with_multipart_upload(self):
        self.args.bucket = self.bucket
        self.args.key = self.key
        self.bundle_mock.tell.return_value = (6 << 20)
        self.bundle_mock.read.return_value = b'a' * (6 << 20)
        response = self.push._upload_to_s3(self.args, self.bundle_mock)
        self.assertDictEqual(self.upload_response, response)
        self.assertFalse(self.push.s3.put_object.called)
        self.push.s3.create_multipart_upload.assert_called_with(
            Bucket=self.bucket,
            Key=self.key
        )
        self.push.s3.upload_part.assert_called_with(
            Bucket=self.bucket,
            Key=self.key,
            UploadId=self.upload_id,
            PartNumber=1,
            Body=mock.ANY
        )
        self.push.s3.complete_multipart_upload.assert_called_with(
            Bucket=self.bucket,
            Key=self.key,
            UploadId=self.upload_id,
            MultipartUpload={'Parts': [{'PartNumber': 1, 'ETag': self.eTag}]}
        )
        self.assertFalse(self.push.s3.abort_multipart_upload.called)

    def test_upload_to_s3_with_multipart_upload_aborted_on_error(self):
        self.args.bucket = self.bucket
        self.args.key = self.key
        self.bundle_mock.tell.return_value = (6 << 20)
        self.bundle_mock.read.return_value = b'a' * (6 << 20)
        self.push.s3.upload_part.side_effect = ClientError(
            {'Error': {'Code': 'Error', 'Message': 'Error'}},
            'UploadPart'
        )
        with self.assertRaises(ClientError):
            self.push._upload_to_s3(self.args, self.bundle_mock)
        self.assertFalse(self.push.s3.put_object.called)
        self.push.s3.create_multipart_upload.assert_called_with(
            Bucket=self.bucket,
            Key=self.key
        )
        self.assertTrue(self.push.s3.upload_part.called)
        self.assertFalse(self.push.s3.complete_multipart_upload.called)
        self.push.s3.abort_multipart_upload.assert_called_with(
            Bucket=self.bucket,
            Key=self.key,
            UploadId=self.upload_id
        )

    def test_register_revision(self):
        self.args.bucket = self.bucket
        self.args.key = self.key
        self.args.eTag = self.eTag
        self.args.version = self.version_id
        self.push._register_revision(self.args)
        self.push.codedeploy.register_application_revision.assert_called_with(
            applicationName=self.application_name,
            description=self.description,
            revision=self.revision
        )


if __name__ == "__main__":
    unittest.main()
