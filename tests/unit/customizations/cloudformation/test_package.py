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
from awscli.customizations.cloudformation.package import (
    PackageCommand, Template, json)
from awscli.customizations.cloudformation.yamlhelper import yaml_dump
from awscli.customizations.cloudformation.exceptions import (
    PackageFailedRegionMismatchError, PackageEmptyRegionError,
    InvalidTemplatePathError)
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
                                    output_template_file="./output",
                                    use_json=False,
                                    force_upload=False)
        self.parsed_globals = FakeArgs(region="us-east-1", endpoint_url=None,
                                       verify_ssl=None)
        self.package_command = PackageCommand(self.session)

    @patch("awscli.customizations.cloudformation.package.json")
    @patch("awscli.customizations.cloudformation.package.Template")
    @patch("awscli.customizations.cloudformation.package.yaml_dump")
    def test_main(self, mock_yaml_dump, mock_export_template, mock_json_dump):
        exported_template_str = "hello"
        mock_yaml_dump.return_value = exported_template_str
        mock_json_dump.dumps.return_value = "template_json_format"

        # Create a temporary file and make this my template
        with tempfile.NamedTemporaryFile() as handle:
            self.package_command._get_bucket_region = MagicMock(
                return_value="us-east-1")

            for use_json in (False, True):
                filename = handle.name
                self.parsed_args.template_file = filename
                self.parsed_args.use_json = use_json

                rc = self.package_command._run_main(
                    self.parsed_args, self.parsed_globals)
                self.assertEquals(rc, 0)

                self.package_command.write_output(
                    self.parsed_args.output_template_file, "some data")

            # No output file specified
            self.parsed_args.output_template_file = None
            rc_no_output = self.package_command._run_main(
                self.parsed_args, self.parsed_globals)
            self.assertEquals(rc_no_output, 0)

    @patch("os.path.isfile")
    def test_main_without_bucket(self, mock_os_isfile):
        self.package_command.write_output = Mock()
        self.package_command._export = Mock()
        mock_os_isfile.return_value = True

        self.parsed_args.s3_bucket = None
        self.package_command._get_bucket_region = MagicMock(
            return_value="us-east-1")
        rc = self.package_command._run_main(
            self.parsed_args, self.parsed_globals)

        self.assertEquals(rc, 0)

    @patch("os.path.isfile")
    def test_main_bucket_region_mismatch(self, mock_os_isfile):
        mock_os_isfile.return_value = True
        self.parsed_globals.region = "eu-west-1"
        self.parsed_args.s3_bucket = "bucket-in-different-region"

        with self.assertRaises(PackageFailedRegionMismatchError):
            self.package_command._run_main(
                self.parsed_args, self.parsed_globals
            )

    def test_main_empty_region_error(self):
        self.parsed_globals.region = None
        with self.assertRaises(PackageEmptyRegionError):
            self.package_command._run_main(
                self.parsed_args, self.parsed_globals
            )

    def test_main_invalid_template_error(self):
        self.parsed_args.template_file = "invalid-template-file"
        with self.assertRaises(InvalidTemplatePathError):
            self.package_command._run_main(
                self.parsed_args, self.parsed_globals
            )

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
                self.package_command._run_main(
                    self.parsed_args, self.parsed_globals)

    def test_bucket_already_exist_catch(self):
        sts_client = Mock()
        s3_client = Mock()
        err_response = {'Error': {'Code': '404', 'Message': 'Not Found'}}
        s3_client.head_bucket.side_effect = ClientError(
            error_response=err_response, operation_name='HeadBucket')

        rc_default_region = self.package_command._create_sam_bucket(
            s3_client, sts_client, self.parsed_globals)

        self.assertIn("sam-", rc_default_region)

        self.parsed_globals.region = "eu-west-1"
        rc_custom_region = self.package_command._create_sam_bucket(
            s3_client, sts_client, self.parsed_globals)

        self.assertIn("sam-", rc_custom_region)

        # Covers non-404 use case
        err_response['Error']['Code'] = "418"
        err_response['Error']['Message'] = "Easter egg, return bucket"
        rc_custom_region = self.package_command._create_sam_bucket(
            s3_client, sts_client, self.parsed_globals)

        self.assertIn("sam-", rc_custom_region)

    @patch("awscli.customizations.cloudformation.package.sys.stdout")
    def test_write_output_to_stdout(self, stdoutmock):
        data = u"some data"

        for filename in (self.parsed_args.output_template_file, None):
            rc = self.package_command.write_output(filename, data)
