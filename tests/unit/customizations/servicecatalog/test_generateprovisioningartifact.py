# Copyright 2012-2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from mock import patch

from awscli.customizations.servicecatalog import exceptions
from awscli.customizations.servicecatalog.generateprovisioningartifact \
    import GenerateProvisioningArtifactCommand
from awscli.testutils import unittest, mock, capture_output
from botocore.compat import json


class TestCreateProvisioningArtifactCommand(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock()
        self.servicecatalog_client = mock.Mock()
        self.s3_client = mock.Mock()
        self.session.create_client.side_effect = [self.s3_client,
                                                  self.servicecatalog_client]
        self.session.get_available_regions.return_value = ['us-east-1',
                                                           'eu-west-1']
        self.cmd = GenerateProvisioningArtifactCommand(self.session)

        self.args = Namespace()
        self.args.file_path = 'foo-file-path'
        self.args.bucket_name = 'foo-bucket-name'
        self.args.provisioning_artifact_name = 'foo-pa-name'
        self.args.provisioning_artifact_description = 'foo-pa-desc'
        self.args.provisioning_artifact_type = 'CLOUD_FORMATION_TEMPLATE'
        self.args.product_id = 'prod-1234567890abc'

        self.s3_url = "https://s3.amazonaws.com/foo-bucket-name/foo-file-path"

        # set global args
        self.global_args = Namespace()
        self.global_args.region = 'us-east-1'
        self.global_args.endpoint_url = None
        self.global_args.verify_ssl = None

    @patch('os.path.getsize', return_value=1)
    def test_happy_path(self, getsize_patch):
        # Arrange
        self.servicecatalog_client.create_provisioning_artifact\
            .return_value = self.get_create_provisioning_artifact_output()
        expected_pa_detail = self.get_create_provisioning_artifact_output()
        del expected_pa_detail['ResponseMetadata']
        expected_response_output = json.dumps(expected_pa_detail,
                                              indent=2,
                                              ensure_ascii=False)

        # Act
        with capture_output() as captured:
            result = self.cmd._run_main(self.args, self.global_args)

        # Assert
        self.session.create_client.assert_called_with(
                                        'servicecatalog',
                                        region_name=self.global_args.region,
                                        endpoint_url=None,
                                        verify=None)
        self.servicecatalog_client.create_provisioning_artifact.\
            assert_called_once_with(
                            ProductId=self.args.product_id,
                            Parameters=self.
                            get_provisioning_artifact_parameters(
                                self.args.provisioning_artifact_name,
                                self.args.provisioning_artifact_description,
                                self.args.provisioning_artifact_type
                            )
                        )
        self.assertEqual(expected_response_output,
                         captured.stdout.getvalue())
        self.assertEqual(0, result)

    @patch('os.path.getsize', return_value=1)
    def test_happy_path_unicode(self, getsize_patch):
        # Arrange
        self.args.provisioning_artifact_name = u'\u05d1\u05e8\u05d9\u05e6'
        self.args.provisioning_artifact_description = u'\u00fd\u00a9\u0194'
        self.servicecatalog_client.create_provisioning_artifact\
            .return_value = self.get_create_provisioning_artifact_output()
        expected_pa_detail = self.get_create_provisioning_artifact_output()
        del expected_pa_detail['ResponseMetadata']
        expected_response_output = json.dumps(expected_pa_detail,
                                              indent=2,
                                              ensure_ascii=False)

        # Act
        with capture_output() as captured:
            result = self.cmd._run_main(self.args, self.global_args)

        # Assert
        self.session.create_client.assert_called_with(
                                        'servicecatalog',
                                        region_name=self.global_args.region,
                                        endpoint_url=None,
                                        verify=None)
        self.servicecatalog_client.create_provisioning_artifact.\
            assert_called_once_with(
                            ProductId=self.args.product_id,
                            Parameters=self.
                            get_provisioning_artifact_parameters(
                                self.args.provisioning_artifact_name,
                                self.args.provisioning_artifact_description,
                                self.args.provisioning_artifact_type
                            )
                        )
        self.assertEqual(expected_response_output,
                         captured.stdout.getvalue())
        self.assertEqual(0, result)

    def test_region_not_supported(self):
        self.global_args.region = 'not-supported-region'
        with self.assertRaisesRegexp(exceptions.InvalidParametersException,
                                     "not supported"):
            self.cmd._run_main(self.args, self.global_args)

    def get_provisioning_artifact_parameters(self, pa_name,
                                             pa_description, pa_type):
        return {
            'Name': pa_name,
            'Description': pa_description,
            'Info': {
                'LoadTemplateFromURL': self.s3_url
            },
            'Type': pa_type
        }

    def get_create_provisioning_artifact_output(self):
        return {
            'Info': {
                'TemplateUrl': self.s3_url
            },
            'ProvisioningArtifactDetail': {
                'Description': self.args.provisioning_artifact_description,
                'Id': 'pa-inifmhpr47ft2',
                'Name': self.args.provisioning_artifact_name,
                'Type': self.args.provisioning_artifact_type
            },
            'Status': "CREATING",
            'ResponseMetadata': {}
        }
