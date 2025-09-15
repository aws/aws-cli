# Copyright 2025 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import unittest
import json
from unittest.mock import Mock, MagicMock, patch
from io import StringIO

from awscli.customizations.supplychain.sbom import GenerateSBOMCommand


class TestGenerateSBOMCommand(unittest.TestCase):
    """Test the GenerateSBOMCommand class"""

    def setUp(self):
        self.session = Mock()
        self.command = GenerateSBOMCommand(self.session)

    def test_command_name(self):
        """Test command has correct name"""
        self.assertEqual(self.command.NAME, 'generate-sbom')

    def test_command_arg_table(self):
        """Test command has expected arguments"""
        arg_names = [arg['name'] for arg in self.command.ARG_TABLE]

        expected_args = [
            'resource-arn', 'image-uri', 'format',
            'output', 'upload', 's3-bucket', 'scan-depth'
        ]

        for expected in expected_args:
            self.assertIn(expected, arg_names)

    def test_requires_resource_or_image(self):
        """Test that either resource-arn or image-uri is required"""
        parsed_args = Mock()
        parsed_args.resource_arn = None
        parsed_args.image_uri = None
        parsed_globals = Mock()

        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            result = self.command._run_main(parsed_args, parsed_globals)

        self.assertEqual(result, 1)
        self.assertIn('Either --resource-arn or --image-uri must be specified',
                      mock_stderr.getvalue())

    @patch('awscli.customizations.supplychain.sbom.get_ecr_client')
    @patch('awscli.customizations.supplychain.sbom.format_sbom_output')
    def test_generate_sbom_for_image(self, mock_format, mock_get_ecr):
        """Test SBOM generation for container image"""
        # Setup mocks
        parsed_args = Mock()
        parsed_args.image_uri = '123456789012.dkr.ecr.us-east-1.amazonaws.com/app:latest'
        parsed_args.resource_arn = None
        parsed_args.format = 'spdx-json'
        parsed_args.output = None
        parsed_args.upload = False
        parsed_globals = Mock()

        mock_ecr = Mock()
        mock_get_ecr.return_value = mock_ecr
        mock_ecr.batch_get_image.return_value = {
            'images': [{'imageId': {'imageTag': 'latest'}}]
        }
        mock_ecr.describe_image_scan_findings.side_effect = Exception('No scan')

        mock_format.return_value = '{"spdxVersion": "SPDX-2.3"}'

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            result = self.command._run_main(parsed_args, parsed_globals)

        self.assertEqual(result, 0)
        self.assertIn('spdxVersion', mock_stdout.getvalue())

    @patch('awscli.customizations.supplychain.sbom.get_lambda_client')
    @patch('awscli.customizations.supplychain.sbom.format_sbom_output')
    def test_generate_sbom_for_lambda(self, mock_format, mock_get_lambda):
        """Test SBOM generation for Lambda function"""
        # Setup mocks
        parsed_args = Mock()
        parsed_args.resource_arn = 'arn:aws:lambda:us-east-1:123456789012:function:my-func'
        parsed_args.image_uri = None
        parsed_args.format = 'spdx-json'
        parsed_args.output = None
        parsed_args.upload = False
        parsed_globals = Mock()

        mock_lambda = Mock()
        mock_get_lambda.return_value = mock_lambda
        mock_lambda.get_function.return_value = {
            'Configuration': {
                'FunctionName': 'my-func',
                'Runtime': 'python3.9',
                'Version': '$LATEST'
            }
        }

        mock_format.return_value = '{"spdxVersion": "SPDX-2.3"}'

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            result = self.command._run_main(parsed_args, parsed_globals)

        self.assertEqual(result, 0)
        self.assertIn('spdxVersion', mock_stdout.getvalue())

    def test_output_to_file(self):
        """Test writing SBOM to file"""
        parsed_args = Mock()
        parsed_args.image_uri = '123456789012.dkr.ecr.us-east-1.amazonaws.com/app:latest'
        parsed_args.resource_arn = None
        parsed_args.format = 'spdx-json'
        parsed_args.output = '/tmp/sbom.json'
        parsed_args.upload = False
        parsed_globals = Mock()

        with patch('awscli.customizations.supplychain.sbom.get_ecr_client') as mock_get_ecr:
            with patch('awscli.customizations.supplychain.sbom.format_sbom_output') as mock_format:
                with patch('builtins.open', unittest.mock.mock_open()) as mock_file:
                    mock_ecr = Mock()
                    mock_get_ecr.return_value = mock_ecr
                    mock_ecr.batch_get_image.return_value = {
                        'images': [{'imageId': {'imageTag': 'latest'}}]
                    }
                    mock_format.return_value = '{"test": "data"}'

                    result = self.command._run_main(parsed_args, parsed_globals)

                    mock_file.assert_called_with('/tmp/sbom.json', 'w')
                    mock_file().write.assert_called_with('{"test": "data"}')