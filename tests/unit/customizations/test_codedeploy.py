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

import argparse

from mock import Mock, ANY, patch, MagicMock
from awscli.compat import six
from six import StringIO

from awscli.customizations.codedeploy import S3Client
from awscli.customizations.codedeploy import CodeDeployClient
from awscli.customizations.codedeploy import CodeDeployBase
from awscli.customizations.codedeploy import CodeDeployPush
from tests.unit.test_clidriver import FakeSession
from awscli.testutils import unittest
from awscli.testutils import BaseAWSCommandParamsTest


class GetApplicationRevisionLocationArgumentsTestCase(
        BaseAWSCommandParamsTest):

    prefix = 'deploy get-application-revision --application-name foo '

    def test_s3_location(self):
        cmd = self.prefix + '--s3-location bucket=b,key=k,bundleType=zip'
        result = {
            'applicationName': 'foo',
            'revision': {
                'revisionType': 'S3',
                's3Location': {
                    'bucket': 'b',
                    'key': 'k',
                    'bundleType': 'zip'
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_s3_location_with_etag(self):
        cmd = self.prefix + (
            '--s3-location bucket=b,key=k,'
            'bundleType=zip,eTag=1234')
        result = {
            'applicationName': 'foo',
            'revision': {
                'revisionType': 'S3',
                's3Location': {
                    'bucket': 'b',
                    'key': 'k',
                    'bundleType': 'zip',
                    'eTag': '1234'
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_s3_location_with_version(self):
        cmd = self.prefix + (
            '--s3-location bucket=b,key=k,'
            'bundleType=zip,version=abcd')
        result = {
            'applicationName': 'foo',
            'revision': {
                'revisionType': 'S3',
                's3Location': {
                    'bucket': 'b',
                    'key': 'k',
                    'bundleType': 'zip',
                    'version': 'abcd'
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_s3_location_with_etag_and_version(self):
        cmd = self.prefix + (
            '--s3-location bucket=b,key=k,'
            'bundleType=zip,eTag=1234,version=abcd')
        result = {
            'applicationName': 'foo',
            'revision': {
                'revisionType': 'S3',
                's3Location': {
                    'bucket': 'b',
                    'key': 'k',
                    'bundleType': 'zip',
                    'eTag': '1234',
                    'version': 'abcd'
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_s3_location_json(self):
        cmd = self.prefix + (
            '--s3-location {"bucket":"b","key":"k",'
            '"bundleType":"zip","eTag":"1234","version":"abcd"}')
        result = {
            'applicationName': 'foo',
            'revision': {
                'revisionType': 'S3',
                's3Location': {
                    'bucket': 'b',
                    'key': 'k',
                    'bundleType': 'zip',
                    'eTag': '1234',
                    'version': 'abcd'
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_s3_location_missing_bucket(self):
        cmd = self.prefix + (
            '--s3-location key=k,'
            'bundleType=zip,eTag=1234,version=abcd')
        self.run_cmd(cmd, 255)

    def test_s3_location_missing_key(self):
        cmd = self.prefix + (
            '--s3-location bucket=b,'
            'bundleType=zip,eTag=1234,version=abcd')
        self.run_cmd(cmd, 255)

    def test_github_location_with_etag(self):
        cmd = self.prefix + (
            '--github-location repository=foo/bar,'
            'commitId=1234')
        result = {
            'applicationName': 'foo',
            'revision': {
                'revisionType': 'GitHub',
                'gitHubLocation': {
                    'repository': 'foo/bar',
                    'commitId': '1234',
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_github_location_json(self):
        cmd = self.prefix + (
            '--github-location {"repository":"foo/bar",'
            '"commitId":"1234"}')
        result = {
            'applicationName': 'foo',
            'revision': {
                'revisionType': 'GitHub',
                'gitHubLocation': {
                    'repository': 'foo/bar',
                    'commitId': '1234',
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_github_location_missing_repository(self):
        cmd = self.prefix + (
            '--github-location '
            'commitId=1234')
        self.run_cmd(cmd, 255)

    def test_github_location_missing_repository(self):
        cmd = self.prefix + '--github-location repository=foo/bar'
        self.run_cmd(cmd, 255)


class RegisterApplicationRevisionLocationArgumentsTestCase(
        BaseAWSCommandParamsTest):

    prefix = 'deploy register-application-revision --application-name foo '

    def test_s3_location(self):
        cmd = self.prefix + '--s3-location bucket=b,key=k,bundleType=zip'
        result = {
            'applicationName': 'foo',
            'revision': {
                'revisionType': 'S3',
                's3Location': {
                    'bucket': 'b',
                    'key': 'k',
                    'bundleType': 'zip'
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_s3_location_with_etag(self):
        cmd = self.prefix + (
            '--s3-location bucket=b,key=k,'
            'bundleType=zip,eTag=1234')
        result = {
            'applicationName': 'foo',
            'revision': {
                'revisionType': 'S3',
                's3Location': {
                    'bucket': 'b',
                    'key': 'k',
                    'bundleType': 'zip',
                    'eTag': '1234'
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_s3_location_with_version(self):
        cmd = self.prefix + (
            '--s3-location bucket=b,key=k,'
            'bundleType=zip,version=abcd')
        result = {
            'applicationName': 'foo',
            'revision': {
                'revisionType': 'S3',
                's3Location': {
                    'bucket': 'b',
                    'key': 'k',
                    'bundleType': 'zip',
                    'version': 'abcd'
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_s3_location_with_etag_and_version(self):
        cmd = self.prefix + (
            '--s3-location bucket=b,key=k,'
            'bundleType=zip,eTag=1234,version=abcd')
        result = {
            'applicationName': 'foo',
            'revision': {
                'revisionType': 'S3',
                's3Location': {
                    'bucket': 'b',
                    'key': 'k',
                    'bundleType': 'zip',
                    'eTag': '1234',
                    'version': 'abcd'
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_s3_location_json(self):
        cmd = self.prefix + (
            '--s3-location {"bucket":"b","key":"k",'
            '"bundleType":"zip","eTag":"1234","version":"abcd"}')
        result = {
            'applicationName': 'foo',
            'revision': {
                'revisionType': 'S3',
                's3Location': {
                    'bucket': 'b',
                    'key': 'k',
                    'bundleType': 'zip',
                    'eTag': '1234',
                    'version': 'abcd'
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_s3_location_missing_bucket(self):
        cmd = self.prefix + (
            '--s3-location key=k,'
            'bundleType=zip,eTag=1234,version=abcd')
        self.run_cmd(cmd, 255)

    def test_s3_location_missing_key(self):
        cmd = self.prefix + (
            '--s3-location bucket=b,'
            'bundleType=zip,eTag=1234,version=abcd')
        self.run_cmd(cmd, 255)

    def test_github_location_with_etag(self):
        cmd = self.prefix + (
            '--github-location repository=foo/bar,'
            'commitId=1234')
        result = {
            'applicationName': 'foo',
            'revision': {
                'revisionType': 'GitHub',
                'gitHubLocation': {
                    'repository': 'foo/bar',
                    'commitId': '1234',
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_github_location_json(self):
        cmd = self.prefix + (
            '--github-location {"repository":"foo/bar",'
            '"commitId":"1234"}')
        result = {
            'applicationName': 'foo',
            'revision': {
                'revisionType': 'GitHub',
                'gitHubLocation': {
                    'repository': 'foo/bar',
                    'commitId': '1234',
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_github_location_missing_repository(self):
        cmd = self.prefix + (
            '--github-location '
            'commitId=1234')
        self.run_cmd(cmd, 255)

    def test_github_location_missing_repository(self):
        cmd = self.prefix + '--github-location repository=foo/bar'
        self.run_cmd(cmd, 255)


class CreateDpeloymentLocationArgumentsTestCase(
        BaseAWSCommandParamsTest):

    prefix = (
        'deploy create-deployment --application-name foo '
        '--deployment-group bar ')

    def test_s3_location(self):
        cmd = self.prefix + '--s3-location bucket=b,key=k,bundleType=zip'
        result = {
            'applicationName': 'foo',
            'deploymentGroupName': 'bar',
            'revision': {
                'revisionType': 'S3',
                's3Location': {
                    'bucket': 'b',
                    'key': 'k',
                    'bundleType': 'zip'
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_s3_location_with_etag(self):
        cmd = self.prefix + (
            '--s3-location bucket=b,key=k,'
            'bundleType=zip,eTag=1234')
        result = {
            'applicationName': 'foo',
            'deploymentGroupName': 'bar',
            'revision': {
                'revisionType': 'S3',
                's3Location': {
                    'bucket': 'b',
                    'key': 'k',
                    'bundleType': 'zip',
                    'eTag': '1234'
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_s3_location_with_version(self):
        cmd = self.prefix + (
            '--s3-location bucket=b,key=k,'
            'bundleType=zip,version=abcd')
        result = {
            'applicationName': 'foo',
            'deploymentGroupName': 'bar',
            'revision': {
                'revisionType': 'S3',
                's3Location': {
                    'bucket': 'b',
                    'key': 'k',
                    'bundleType': 'zip',
                    'version': 'abcd'
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_s3_location_with_etag_and_version(self):
        cmd = self.prefix + (
            '--s3-location bucket=b,key=k,'
            'bundleType=zip,eTag=1234,version=abcd')
        result = {
            'applicationName': 'foo',
            'deploymentGroupName': 'bar',
            'revision': {
                'revisionType': 'S3',
                's3Location': {
                    'bucket': 'b',
                    'key': 'k',
                    'bundleType': 'zip',
                    'eTag': '1234',
                    'version': 'abcd'
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_s3_location_json(self):
        cmd = self.prefix + (
            '--s3-location {"bucket":"b","key":"k",'
            '"bundleType":"zip","eTag":"1234","version":"abcd"}')
        result = {
            'applicationName': 'foo',
            'deploymentGroupName': 'bar',
            'revision': {
                'revisionType': 'S3',
                's3Location': {
                    'bucket': 'b',
                    'key': 'k',
                    'bundleType': 'zip',
                    'eTag': '1234',
                    'version': 'abcd'
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_s3_location_missing_bucket(self):
        cmd = self.prefix + (
            '--s3-location key=k,'
            'bundleType=zip,eTag=1234,version=abcd')
        self.run_cmd(cmd, 255)

    def test_s3_location_missing_key(self):
        cmd = self.prefix + (
            '--s3-location bucket=b,'
            'bundleType=zip,eTag=1234,version=abcd')
        self.run_cmd(cmd, 255)

    def test_github_location_with_etag(self):
        cmd = self.prefix + (
            '--github-location repository=foo/bar,'
            'commitId=1234')
        result = {
            'applicationName': 'foo',
            'deploymentGroupName': 'bar',
            'revision': {
                'revisionType': 'GitHub',
                'gitHubLocation': {
                    'repository': 'foo/bar',
                    'commitId': '1234',
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_github_location_json(self):
        cmd = self.prefix + (
            '--github-location {"repository":"foo/bar",'
            '"commitId":"1234"}')
        result = {
            'applicationName': 'foo',
            'deploymentGroupName': 'bar',
            'revision': {
                'revisionType': 'GitHub',
                'gitHubLocation': {
                    'repository': 'foo/bar',
                    'commitId': '1234',
                }
            }
        }
        self.assert_params_for_cmd(cmd, result)

    def test_github_location_missing_repository(self):
        cmd = self.prefix + (
            '--github-location '
            'commitId=1234')
        self.run_cmd(cmd, 255)

    def test_github_location_missing_repository(self):
        cmd = self.prefix + '--github-location repository=foo/bar'
        self.run_cmd(cmd, 255)


class CodeDeployTestCase(unittest.TestCase):
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
        self.endpoint_url = 'https://codedeploy-%s.amazonaws.com' % self.region

        self.args = argparse.Namespace()
        self.args.application_name = self.application_name
        self.args.s3_location = self.s3_location
        self.args.ignore_hidden_files = False
        self.args.no_ignore_hidden_files = False
        self.args.description = self.description
        self.args.source = self.source

        self.globals = argparse.Namespace()
        self.globals.region = self.region
        self.globals.endpoint_url = self.endpoint_url
        self.globals.verify_ssl = None

        self.endpoint_args = {
            'region_name': self.region,
            'endpoint_url': self.endpoint_url,
            'verify': None
        }
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

        self.bundle_mock = MagicMock()
        self.bundle_mock.tell.return_value = (5 << 20)
        self.bundle_mock.read.return_value = b'a' * (5 << 20)
        self.bundle_mock.__enter__.return_value = self.bundle_mock
        self.bundle_mock.__exit__.return_value = None

        self.zipfile_mock = MagicMock()
        self.zipfile_mock.write.return_value = None
        self.zipfile_mock.close.return_value = None
        self.zipfile_mock.__enter__.return_value = self.zipfile_mock
        self.zipfile_mock.__exit__.return_value = None

        self.session = FakeSession({'config_file': 'myconfigfile'})


class TestS3Client(CodeDeployTestCase):
    def setUp(self):
        super(TestS3Client, self).setUp()
        self.s3client = S3Client(
            self.endpoint_args,
            self.session
        )
        self.s3client.s3 = Mock()
        self.s3client.s3.PutObject.return_value = self.upload_response
        self.s3client.s3.CreateMultipartUpload.return_value = {
            'UploadId': self.upload_id
        }
        self.s3client.s3.UploadPart.return_value = {
            'ETag': self.eTag
        }
        self.s3client.s3.CompleteMultipartUpload\
            .return_value = self.upload_response

    def test_upload_to_s3_with_put_object(self):
        self.args.bucket = self.bucket
        self.args.key = self.key
        response = self.s3client.upload_to_s3(self.args, self.bundle_mock)
        self.assertDictEqual(self.upload_response, response)

        self.s3client.s3.PutObject.assert_called_with(
            bucket=self.bucket,
            key=self.key,
            body=self.bundle_mock
        )
        self.assertFalse(self.s3client.s3.CreateMultipartUpload.called)
        self.assertFalse(self.s3client.s3.UploadPart.called)
        self.assertFalse(self.s3client.s3.CompleteMultipartUpload.called)
        self.assertFalse(self.s3client.s3.AbortMultipartUpload.called)

    def test_upload_to_s3_with_multipart_upload(self):
        self.args.bucket = self.bucket
        self.args.key = self.key
        self.bundle_mock.tell.return_value = (6 << 20)
        self.bundle_mock.read.return_value = b'a' * (6 << 20)
        response = self.s3client.upload_to_s3(self.args, self.bundle_mock)
        self.assertDictEqual(self.upload_response, response)

        self.assertFalse(self.s3client.s3.PutObject.called)
        self.s3client.s3.CreateMultipartUpload.assert_called_with(
            bucket=self.bucket,
            key=self.key
        )
        self.s3client.s3.UploadPart.assert_called_with(
            bucket=self.bucket,
            key=self.key,
            upload_id=self.upload_id,
            part_number=1,
            body=ANY
        )
        self.s3client.s3.CompleteMultipartUpload.assert_called_with(
            bucket=self.bucket,
            key=self.key,
            upload_id=self.upload_id,
            multipart_upload={'Parts': [{'PartNumber': 1, 'ETag': self.eTag}]}
        )
        self.assertFalse(self.s3client.s3.AbortMultipartUpload.called)

    def test_upload_to_s3_with_multipart_upload_aborted_on_error(self):
        self.args.bucket = self.bucket
        self.args.key = self.key
        self.bundle_mock.tell.return_value = (6 << 20)
        self.bundle_mock.read.return_value = b'a' * (6 << 20)
        self.s3client.s3.UploadPart.side_effect = RuntimeError('error')

        with self.assertRaises(RuntimeError) as error:
            self.s3client.upload_to_s3(self.args, self.bundle_mock)

        self.assertFalse(self.s3client.s3.PutObject.called)
        self.s3client.s3.CreateMultipartUpload.assert_called_with(
            bucket=self.bucket,
            key=self.key
        )
        self.assertTrue(self.s3client.s3.UploadPart.called)
        self.assertFalse(self.s3client.s3.CompleteMultipartUpload.called)
        self.s3client.s3.AbortMultipartUpload.assert_called_with(
            bucket=self.bucket,
            key=self.key,
            upload_id=self.upload_id
        )


class TestCodeDeployClient(CodeDeployTestCase):
    def setUp(self):
        super(TestCodeDeployClient, self).setUp()
        self.codedeployclient = CodeDeployClient(
            self.endpoint_args,
            self.session
        )
        self.codedeployclient.codedeploy = Mock()

    def test_register_revision(self):
        self.args.bucket = self.bucket
        self.args.key = self.key
        self.args.eTag = self.eTag
        self.args.version = self.version_id
        self.codedeployclient.register_revision(self.args)
        self.codedeployclient.codedeploy\
            .RegisterApplicationRevision.assert_called_with(
                application_name=self.application_name,
                description=self.description,
                revision=self.revision
            )


class TestCodeDeployBase(CodeDeployTestCase):
    def setUp(self):
        super(TestCodeDeployBase, self).setUp()
        self.codedeploybase = CodeDeployBase(self.session)

    @patch('awscli.customizations.codedeploy.S3Client')
    def test_run_main_creates_s3_client(self, s3_client):
        self.codedeploybase._call = Mock(return_value=None)
        self.codedeploybase._run_main(self.args, self.globals)
        s3_client.assert_called_with(
            endpoint_args=self.endpoint_args,
            session=self.session
        )

    @patch('awscli.customizations.codedeploy.CodeDeployClient')
    def test_run_main_creates_codedeploy_client(self, codedeploy_client):
        self.codedeploybase._call = Mock(return_value=None)
        self.codedeploybase._run_main(self.args, self.globals)
        codedeploy_client.assert_called_with(
            endpoint_args=self.endpoint_args,
            session=self.session
        )

    def test_run_main_throws_not_implemented_error(self):
        with self.assertRaises(NotImplementedError) as error:
            self.codedeploybase._run_main(self.args, self.globals)


class TestCodeDeployPush(CodeDeployTestCase):
    def setUp(self):
        super(TestCodeDeployPush, self).setUp()
        self.codedeploypush = CodeDeployPush(self.session)
        self.codedeploypush.s3 = Mock()
        self.codedeploypush.s3.upload_to_s3.return_value = self.upload_response
        self.codedeploypush.codedeploy = Mock()

    def test_flatten_args_throws_on_invalid_s3_url(self):
        self.args.s3_location = 's3:/foo/bar/baz'
        with self.assertRaises(RuntimeError) as error:
            self.codedeploypush._flatten_args(self.args)

    def test_flatten_args_throws_on_ignore_and_no_ignore_hidden_files(self):
        self.args.ignore_hidden_files = True
        self.args.no_ignore_hidden_files = True
        with self.assertRaises(RuntimeError) as error:
            self.codedeploypush._flatten_args(self.args)

    def test_flatten_args_default_description(self):
        self.args.description = None
        self.codedeploypush._flatten_args(self.args)
        self.assertRegexpMatches(
            self.args.description,
            'Uploaded by AWS CLI .* UTC'
        )

    def test_call_throws_on_upload_to_s3_error(self):
        self.args.bucket = self.bucket
        self.args.key = self.key
        self.codedeploypush._compress = Mock(return_value=self.bundle_mock)
        self.codedeploypush.s3.upload_to_s3.side_effect = RuntimeError('error')
        with self.assertRaises(RuntimeError) as error:
            self.codedeploypush._call(self.args, self.globals)

    @patch('sys.stdout', new_callable=StringIO)
    def test_call_output_message(self, stdout_mock):
        self.args.bucket = self.bucket
        self.args.key = self.key
        self.codedeploypush._compress = Mock(return_value=self.bundle_mock)
        self.codedeploypush._call(self.args, self.globals)
        output = stdout_mock.getvalue().strip()
        expected_revision_output = (
            '--s3-location bucket={0},key={1},'
            'bundleType=zip,eTag={2},version={3}'.format(
                self.bucket,
                self.key,
                self.eTag,
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
        self.assertEquals(expected_output, output)

    @patch('zipfile.ZipFile')
    @patch('tempfile.TemporaryFile')
    @patch('os.path')
    @patch('os.walk')
    def test_compress_throws_when_no_appspec(self, walk, path, tf, zf):
        walk.return_value = [(self.source, [], ['noappspec.yml'])]
        noappsec_path = self.source + '/noappspec.yml'
        path.join.return_value = noappsec_path
        path.sep = '/'
        path.abspath.side_effect = [self.source, noappsec_path]
        tf.return_value = self.bundle_mock
        zf.return_value = self.zipfile_mock
        with self.assertRaises(RuntimeError) as error:
            with self.codedeploypush._compress(
                    self.args.source,
                    self.args.ignore_hidden_files
            ) as bundle:
                pass

    @patch('zipfile.ZipFile')
    @patch('tempfile.TemporaryFile')
    @patch('os.path')
    @patch('os.walk')
    def test_compress_writes_to_zip_file(self, walk, path, tf, zf):
        walk.return_value = [(self.source, [], [self.appspec])]
        path.join.return_value = self.appspec_path
        path.sep = '/'
        path.abspath.side_effect = [self.source, self.appspec_path]
        tf.return_value = self.bundle_mock
        zf.return_value = self.zipfile_mock
        with self.codedeploypush._compress(
                self.args.source,
                self.args.ignore_hidden_files
        ) as bundle:
            zf().write.assert_called_with(
                '/tmp/appspec.yml',
                self.appspec
            )


if __name__ == "__main__":
    unittest.main()
