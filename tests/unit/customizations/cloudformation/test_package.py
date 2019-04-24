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
import json
import os
import sys
import tempfile

from io import StringIO
from mock import patch, Mock, MagicMock
from awscli.testutils import unittest, BaseAWSCommandParamsTest
from awscli.customizations.cloudformation.package import PackageCommand
from awscli.customizations.cloudformation.yamlhelper import yaml_dump


class FakeTemplate(object):
    def __init__(self, obj):
        self.__dict__.update(obj)

    def export(self, use_json=False):
        return self.__dict__


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
        self.session = Mock()
        self.session.get_scoped_config.return_value = {}
        self.parsed_args = FakeArgs(template_file='./foo',
                                    s3_bucket="s3bucket",
                                    s3_prefix="s3prefix",
                                    kms_key_id="kmskeyid",
                                    output_template_file="./oputput",
                                    use_json=False,
                                    force_upload=False,
                                    metadata=None)
        self.parsed_globals = FakeArgs(region="us-east-1", endpoint_url=None,
                                       verify_ssl=None)
        self.package_command = PackageCommand(self.session)

    @patch("awscli.customizations.cloudformation.package.Template")
    def test_main(self, mock_template):
        self.package_command.write_output = Mock()
        # use a simple format so output ordering doesn't matter
        template_dict = {"Resources": {"Resource1": {}}}
        mock_template.return_value = FakeTemplate(template_dict)

        # Create a temporary file and make this my template
        with tempfile.NamedTemporaryFile() as handle:
            for use_json in (False, True):
                filename = handle.name
                self.parsed_args.template_file = filename
                self.parsed_args.use_json = use_json
                if use_json:
                    expected_str = json.dumps(template_dict, indent=4, ensure_ascii=False)
                else:
                    expected_str = yaml_dump(template_dict)

                rc = self.package_command._run_main(self.parsed_args, self.parsed_globals)
                self.assertEquals(rc, 0)
                self.package_command.write_output.assert_called_once_with(
                        self.parsed_args.output_template_file, expected_str)
                self.package_command.write_output.reset_mock()

    def test_main_error(self):
        self.package_command._export = Mock()
        self.package_command._export.side_effect = RuntimeError()

        # Create a temporary file and make this my template
        with tempfile.NamedTemporaryFile() as handle:
            filename = handle.name
            self.parsed_args.template_file = filename

            with self.assertRaises(RuntimeError):
                self.package_command._run_main(self.parsed_args, self.parsed_globals)

    @patch("awscli.customizations.cloudformation.package.sys.stdout")
    def test_write_output_to_stdout(self, stdoutmock):
        data = u"some data"
        filename = None

        self.package_command.write_output(filename, data)
        stdoutmock.write.assert_called_once_with(data)
