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
import mock
import os
import sys
import tempfile

from io import StringIO
from mock import patch, Mock, MagicMock
from awscli.testutils import unittest, BaseAWSCommandParamsTest
from awscli.customizations.cloudformation.package import PackageCommand
from awscli.customizations.cloudformation.artifact_exporter import Template
from awscli.customizations.cloudformation.yamlhelper import yaml_dump
from awscli.customizations.cloudformation.exceptions import PackageFailedRegionMismatchError, PackageEmptyRegionError
from botocore.exceptions import ClientError


class FakeArgs(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __contains__(self, key):
        return key in self.__dict__


def get_example_template():
    return {
        "Parameters": {
            "Key1": "Value1"
        },
        "Resources": {
            "Resource1": {}
        }
    }


class TestPackageCommand(unittest.TestCase):

    def setUp(self):
        self.session = mock.Mock()
        self.session.get_scoped_config.return_value = {}
        self.parsed_args = FakeArgs(template_file='./foo',
                                    s3_bucket="s3bucket",
                                    s3_prefix="s3prefix",
                                    kms_key_id="kmskeyid",
                                    output_template_file="./oputput",
                                    use_json=False,
                                    force_upload=False)
        self.parsed_globals = FakeArgs(region="us-east-1", endpoint_url=None,
                                       verify_ssl=None)
        self.package_command = PackageCommand(self.session)


    @patch("awscli.customizations.cloudformation.package.yaml_dump")
    def test_main(self, mock_yaml_dump):
        exported_template_str = "hello"

        self.package_command.write_output = Mock()
        self.package_command._export = Mock()
        mock_yaml_dump.return_value = exported_template_str

        # Create a temporary file and make this my template
        with tempfile.NamedTemporaryFile() as handle:
            for use_json in (False, True):
                filename = handle.name
                self.parsed_args.template_file = filename
                self.parsed_args.use_json=use_json

                self.package_command._get_bucket_region = MagicMock(return_value="us-east-1")

                rc = self.package_command._run_main(self.parsed_args, self.parsed_globals)
                self.assertEquals(rc, 0)

                self.package_command._export.assert_called_once_with(filename, use_json)
                self.package_command.write_output.assert_called_once_with(
                        self.parsed_args.output_template_file, mock.ANY)

                self.package_command._export.reset_mock()
                self.package_command.write_output.reset_mock()

    @patch("awscli.customizations.cloudformation.package.yaml_dump")
    def test_main_without_bucket(self, mock_yaml_dump):
        exported_template_str = "hello"

        self.package_command.write_output = Mock()
        self.package_command._export = Mock()
        mock_yaml_dump.return_value = exported_template_str

        # Create a temporary file and make this my template
        with tempfile.NamedTemporaryFile() as handle:
            for use_json in (False, True):
                filename = handle.name
                self.parsed_args.template_file = filename
                self.parsed_args.use_json = use_json

                self.package_command._get_bucket_region = MagicMock(
                    return_value="us-east-1")
                self.parsed_args.s3_bucket = None

                rc = self.package_command._run_main(
                    self.parsed_args, self.parsed_globals)
                self.assertEquals(rc, 0)

                self.package_command._export.assert_called_once_with(
                    filename, use_json)
                self.package_command.write_output.assert_called_once_with(
                    self.parsed_args.output_template_file, mock.ANY)

                self.package_command._export.reset_mock()
                self.package_command.write_output.reset_mock()

    @patch("awscli.customizations.cloudformation.package.yaml_dump")
    def test_main_bucket_different_deployment_region(self, mock_yaml_dump):
        exported_template_str = "hello"

        self.package_command.write_output = Mock()
        self.package_command._export = Mock()
        mock_yaml_dump.return_value = exported_template_str

        # Create a temporary file and make this my template
        with tempfile.NamedTemporaryFile() as handle:
            for use_json in (False, True):
                filename = handle.name
                self.parsed_args.template_file = filename
                self.parsed_args.use_json = use_json

                self.package_command._get_bucket_region = MagicMock(
                    return_value="us-east-1")
                self.parsed_args.s3_bucket = "bucket-in-different-region"
                self.parsed_globals.region = "eu-west-1"

                with self.assertRaises(PackageFailedRegionMismatchError):
                    self.package_command._run_main(
                        self.parsed_args, self.parsed_globals)

    def test_main_empty_region_error(self):
        # Create a temporary file and make this my template
        with tempfile.NamedTemporaryFile() as handle:
            for use_json in (False, True):
                filename = handle.name
                self.parsed_args.template_file = filename
                self.parsed_args.use_json = use_json
                # None is what package receives if no --region is defined/passed
                self.parsed_globals.region = None 

            with self.assertRaises(PackageEmptyRegionError):
                self.package_command._run_main(
                    self.parsed_args, self.parsed_globals)

    def test_bucket_already_exist_catch(self):
        sts_client = Mock()
        s3_client = Mock()
        err_response = {'Error': {'Code': '404', 'Message': 'Not Found'}}
        s3_client.head_bucket.side_effect = ClientError(
            error_response=err_response, operation_name='HeadBucket')

        rc = self.package_command._create_sam_bucket(
            s3_client, sts_client, self.parsed_globals)
        # Test whether S3 Bucket Name has a 'sam-' prefix
        self.assertIn("sam-", rc)

    def test_main_error(self):

        self.package_command._export = Mock()
        self.package_command._export.side_effect = RuntimeError()

        # Create a temporary file and make this my template
        with tempfile.NamedTemporaryFile() as handle:
            filename = handle.name
            self.parsed_args.template_file = filename

            self.package_command._get_bucket_region = MagicMock(
                    return_value="us-east-1")

            with self.assertRaises(RuntimeError):
                self.package_command._run_main(self.parsed_args, self.parsed_globals)


    @patch("awscli.customizations.cloudformation.package.sys.stdout")
    def test_write_output_to_stdout(self, stdoutmock):
        data = u"some data"
        filename = None

        self.package_command.write_output(filename, data)
        stdoutmock.write.assert_called_once_with(data)
