# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import zipfile
from contextlib import closing

from awscli.testutils import BaseAWSCommandParamsTest
from awscli.testutils import FileCreator


class BaseLambdaTests(BaseAWSCommandParamsTest):

    def setUp(self):
        super(BaseLambdaTests, self).setUp()
        self.files = FileCreator()
        self.temp_file = self.files.create_file(
            'foo', 'mycontents')
        self.zip_file = os.path.join(self.files.rootdir, 'foo.zip')
        with closing(zipfile.ZipFile(self.zip_file, 'w')) as f:
            f.write(self.temp_file)
        with open(self.zip_file, 'rb') as f:
            self.zip_file_contents = f.read()

    def tearDown(self):
        super(BaseLambdaTests, self).tearDown()
        self.files.remove_all()


class TestCreateFunction(BaseLambdaTests):

    prefix = 'lambda create-function'

    def test_create_function_with_file(self):
        cmdline = self.prefix
        cmdline += ' --function-name myfunction --runtime myruntime'
        cmdline += ' --role myrole --handler myhandler'
        cmdline += ' --zip-file fileb://%s' % self.zip_file
        result = {
            'FunctionName': 'myfunction',
            'Runtime': 'myruntime',
            'Role': 'myrole',
            'Handler': 'myhandler',
            'Code': {'ZipFile': self.zip_file_contents}
        }
        self.assert_params_for_cmd(cmdline, result)

    def test_create_function_with_code_argument(self):
        cmdline = self.prefix
        cmdline += ' --function-name myfunction --runtime myruntime'
        cmdline += ' --role myrole --handler myhandler'
        cmdline += ' --code S3Bucket=mybucket,S3Key=mykey,S3ObjectVersion=vs'
        result = {
            'FunctionName': 'myfunction',
            'Runtime': 'myruntime',
            'Role': 'myrole',
            'Handler': 'myhandler',
            'Code': {'S3Bucket': 'mybucket',
                     'S3Key': 'mykey',
                     'S3ObjectVersion': 'vs'}
        }
        self.assert_params_for_cmd(cmdline, result)

    def test_create_function_with_code_and_zipfile_argument(self):
        cmdline = self.prefix
        cmdline += ' --function-name myfunction --runtime myruntime'
        cmdline += ' --role myrole --handler myhandler'
        cmdline += ' --code S3Bucket=mybucket,S3Key=mykey,S3ObjectVersion=vs'
        cmdline += ' --zip-file fileb://%s' % self.zip_file
        result = {
            'FunctionName': 'myfunction',
            'Runtime': 'myruntime',
            'Role': 'myrole',
            'Handler': 'myhandler',
            'Code': {'S3Bucket': 'mybucket',
                     'S3Key': 'mykey',
                     'S3ObjectVersion': 'vs',
                     'ZipFile': self.zip_file_contents}
        }
        self.assert_params_for_cmd(cmdline, result)

    def test_create_function_with_zip_file_in_code_argument(self):
        cmdline = self.prefix
        cmdline += ' --function-name myfunction --runtime myruntime'
        cmdline += ' --role myrole --handler myhandler'
        cmdline += ' --code S3Bucket=mybucket,S3Key=mykey,S3ObjectVersion=vs,'
        cmdline += 'ZipFile=foo'
        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=252)
        self.assertIn('ZipFile cannot be provided as part of the --code',
                      stderr)

    def test_create_function_with_invalid_file_contents(self):
        cmdline = self.prefix
        cmdline += ' --function-name myfunction --runtime myruntime'
        cmdline += ' --role myrole --handler myhandler'
        cmdline += ' --zip-file filename_instead_of_contents.zip'
        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=252)
        self.assertIn('must be a zip file with the fileb:// prefix', stderr)
        # Should also give a pointer to fileb:// for them.
        self.assertIn('fileb://', stderr)

    def test_not_using_fileb_prefix(self):
        cmdline = self.prefix
        cmdline += ' --function-name myfunction --runtime myruntime'
        cmdline += ' --role myrole --handler myhandler'
        # Note file:// instead of fileb://
        cmdline += ' --zip-file file://%s' % self.zip_file
        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=252)
        # Ensure we mention fileb:// to give the user an idea of
        # where to go next.
        self.assertIn('fileb://', stderr)


class TestPublishLayerVersion(BaseLambdaTests):

    prefix = 'lambda publish-layer-version'

    def test_publish_layer_version_with_file(self):
        cmdline = self.prefix
        cmdline += ' --layer-name mylayer'
        cmdline += ' --zip-file fileb://%s' % self.zip_file
        result = {
            'LayerName': 'mylayer',
            'Content': {'ZipFile': self.zip_file_contents}
        }
        self.assert_params_for_cmd(cmdline, result)

    def test_publish_layer_version_with_content_argument(self):
        cmdline = self.prefix
        cmdline += ' --layer-name mylayer'
        cmdline += ' --content'
        cmdline += ' S3Bucket=mybucket,S3Key=mykey,S3ObjectVersion=vs'
        result = {
            'LayerName': 'mylayer',
            'Content': {'S3Bucket': 'mybucket',
                        'S3Key': 'mykey',
                        'S3ObjectVersion': 'vs'}
        }
        self.assert_params_for_cmd(cmdline, result)

    def test_publish_layer_version_with_content_and_zipfile_argument(self):
        cmdline = self.prefix
        cmdline += ' --layer-name mylayer'
        cmdline += ' --content'
        cmdline += ' S3Bucket=mybucket,S3Key=mykey,S3ObjectVersion=vs'
        cmdline += ' --zip-file fileb://%s' % self.zip_file
        result = {
            'LayerName': 'mylayer',
            'Content': {'S3Bucket': 'mybucket',
                        'S3Key': 'mykey',
                        'S3ObjectVersion': 'vs',
                        'ZipFile': self.zip_file_contents}
        }
        self.assert_params_for_cmd(cmdline, result)

    def test_publish_layer_version_with_zip_file_in_content_argument(self):
        cmdline = self.prefix
        cmdline += ' --layer-name mylayer'
        cmdline += ' --content'
        cmdline += ' S3Bucket=mybucket,S3Key=mykey,S3ObjectVersion=vs,'
        cmdline += 'ZipFile=foo'
        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=252)
        self.assertIn('ZipFile cannot be provided as part of the --content',
                      stderr)

    def test_publish_layer_version_with_invalid_file_contents(self):
        cmdline = self.prefix
        cmdline += ' --layer-name mylayer'
        cmdline += ' --zip-file filename_instead_of_contents.zip'
        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=252)
        self.assertIn('must be a zip file with the fileb:// prefix', stderr)
        # Should also give a pointer to fileb:// for them.
        self.assertIn('fileb://', stderr)

    def test_not_using_fileb_prefix(self):
        cmdline = self.prefix
        cmdline += ' --layer-name mylayer'
        # Note file:// instead of fileb://
        cmdline += ' --zip-file file://%s' % self.zip_file
        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=252)
        # Ensure we mention fileb:// to give the user an idea of
        # where to go next.
        self.assertIn('fileb://', stderr)


class TestUpdateFunctionCode(BaseLambdaTests):

    prefix = 'lambda update-function-code'

    def test_not_using_fileb_prefix(self):
        cmdline = self.prefix + ' --function-name foo'
        cmdline += ' --zip-file filename_instead_of_contents.zip'
        stdout, stderr, rc = self.run_cmd(cmdline, expected_rc=252)
        self.assertIn('must be a zip file with the fileb:// prefix', stderr)
        # Should also give a pointer to fileb:// for them.
        self.assertIn('fileb://', stderr)

    def test_using_fileb_prefix_succeeds(self):
        cmdline = self.prefix
        cmdline += ' --function-name myfunction'
        cmdline += ' --zip-file fileb://%s' % self.zip_file
        result = {
            'FunctionName': 'myfunction',
            'ZipFile': self.zip_file_contents,
        }
        self.assert_params_for_cmd(cmdline, result)
