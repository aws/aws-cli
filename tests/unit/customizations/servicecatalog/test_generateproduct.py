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
from awscli.customizations.servicecatalog.generateproduct \
    import GenerateProductCommand
from awscli.testutils import unittest, mock, capture_output
from botocore.compat import json


class TestCreateProductCommand(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock()
        self.servicecatalog_client = mock.Mock()
        self.s3_client = mock.Mock()
        self.session.create_client.side_effect = [self.s3_client,
                                                  self.servicecatalog_client]
        self.session.get_available_regions.return_value = ['us-east-1',
                                                           'eu-west-1']
        self.cmd = GenerateProductCommand(self.session)

        self.args = Namespace()
        self.args.file_path = 'foo'
        self.args.bucket_name = 'bucket-name'
        self.args.product_name = 'created product name'
        self.args.tags = ["Key=key1,Value=value1",
                          "Key=key2,Value=value2",
                          "Key=key3,Value=value3"]
        self.args.product_owner = 'me'
        self.args.product_type = 'CLOUD_FORMATION_TEMPLATE'
        self.args.product_distributor = 'prod_distributor'
        self.args.provisioning_artifact_name = 'pa-name'
        self.args.provisioning_artifact_description = 'pa-desc'
        self.args.provisioning_artifact_type = 'CLOUD_FORMATION_TEMPLATE'
        self.args.idempotency_token = '123456789'
        self.args.product_description = 'Short description'
        self.args.support_url = 'https://wiki.example.com/CLI/support'
        self.args.support_email = 'cli@example.com'
        self.args.support_description = 'support description'

        self.s3_url = 'https://s3.amazonaws.com/bucket-name/foo'

        # set global args
        self.global_args = Namespace()
        self.global_args.region = 'us-east-1'
        self.global_args.endpoint_url = None
        self.global_args.verify_ssl = None

    @patch('os.path.getsize', return_value=1)
    def test_happy_path(self, getsize_patch):
        # Arrange
        actual_product_view_detail = self.get_product_view_detail()
        self.servicecatalog_client.create_product.return_value = \
            actual_product_view_detail
        expected_product_view_detail = self.get_product_view_detail()
        del expected_product_view_detail["ResponseMetadata"]
        expected_response_output = json.dumps(expected_product_view_detail,
                                              indent=2)
        expected_args = self.get_args_dict()

        # Act
        with capture_output() as captured:
            result = self.cmd._run_main(self.args, self.global_args)

        # Assert
        self.session.create_client.assert_called_with(
                             'servicecatalog',
                             region_name=self.global_args.region,
                             endpoint_url=None,
                             verify=None)

        self.servicecatalog_client.create_product.assert_called_once_with(
                                    Name=expected_args['product-name'],
                                    Owner=expected_args['product-owner'],
                                    Description=expected_args
                                    ['product-description'],
                                    Distributor=expected_args
                                    ['product-distributor'],
                                    SupportDescription=expected_args
                                    ['support-description'],
                                    SupportEmail=expected_args
                                    ['support-email'],
                                    ProductType=expected_args['product-type'],
                                    Tags=expected_args['tags'],
                                    ProvisioningArtifactParameters=self.
                                    get_provisioning_artifact_parameters(
                                        self.args.provisioning_artifact_name,
                                        self.
                                        args.
                                        provisioning_artifact_description,
                                        self.args.provisioning_artifact_type
                                    )
                                )
        self.assertEqual(expected_response_output,
                         captured.stdout.getvalue()
                         )
        self.assertEquals(0, result)

    @patch('os.path.getsize', return_value=1)
    def test_happy_path_unicode(self, getsize_patch):
        # Arrange
        self.args.product_name = u'\u05d1\u05e8\u05d9\u05e6\u05e7\u05dc\u05d4'
        self.args.support_description = u'\u00fd\u00a9\u0194\u0292'

        actual_product_view_detail = self.get_product_view_detail()
        self.servicecatalog_client.create_product.return_value = \
            actual_product_view_detail
        expected_product_view_detail = self.get_product_view_detail()
        del expected_product_view_detail["ResponseMetadata"]
        expected_response_output = json.dumps(expected_product_view_detail,
                                              indent=2)
        expected_args = self.get_args_dict()

        # Act
        with capture_output() as captured:
            result = self.cmd._run_main(self.args, self.global_args)

        # Assert
        self.session.create_client.assert_called_with(
                             'servicecatalog',
                             region_name=self.global_args.region,
                             endpoint_url=None,
                             verify=None)

        self.servicecatalog_client.create_product.assert_called_once_with(
                                    Name=expected_args['product-name'],
                                    Owner=expected_args['product-owner'],
                                    Description=expected_args
                                    ['product-description'],
                                    Distributor=expected_args
                                    ['product-distributor'],
                                    SupportDescription=expected_args
                                    ['support-description'],
                                    SupportEmail=expected_args
                                    ['support-email'],
                                    ProductType=expected_args['product-type'],
                                    Tags=expected_args['tags'],
                                    ProvisioningArtifactParameters=self.
                                    get_provisioning_artifact_parameters(
                                        self.args.provisioning_artifact_name,
                                        self.
                                        args.
                                        provisioning_artifact_description,
                                        self.args.provisioning_artifact_type
                                    )
                                )
        self.assertEqual(expected_response_output,
                         captured.stdout.getvalue()
                         )
        self.assertEquals(0, result)

    def test_region_not_supported(self):
        self.global_args.region = 'not-supported-region'
        with self.assertRaisesRegexp(exceptions.InvalidParametersException,
                                     "not supported"):
            self.cmd._run_main(self.args, self.global_args)

    @patch('os.path.getsize', return_value=1)
    def test_happy_path_omitting_optional_parameters(self, getsize_patch):
        # Arrange
        self.args.support_description = None
        self.args.product_description = None
        self.args.support_email = None
        self.args.product_distributor = None

        actual_product_view_detail = self.get_product_view_detail()
        self.servicecatalog_client.create_product.\
            return_value = actual_product_view_detail
        expected_product_view_detail = self.get_product_view_detail()
        del expected_product_view_detail["ResponseMetadata"]
        expected_response_output = json.dumps(expected_product_view_detail,
                                              indent=2)
        expected_args = self.get_args_dict()

        # Act
        with capture_output() as captured:
            result = self.cmd._run_main(self.args, self.global_args)

        # Assert
        self.session.create_client.assert_called_with(
                                    'servicecatalog',
                                    region_name=self.global_args.region,
                                    endpoint_url=None,
                                    verify=None)
        self.servicecatalog_client.create_product.assert_called_once_with(
                                    Name=expected_args['product-name'],
                                    Owner=expected_args['product-owner'],
                                    ProductType=expected_args['product-type'],
                                    Tags=expected_args['tags'],
                                    ProvisioningArtifactParameters=self.
                                    get_provisioning_artifact_parameters(
                                        self.args.provisioning_artifact_name,
                                        self.
                                        args.
                                        provisioning_artifact_description,
                                        self.args.provisioning_artifact_type
                                    )
                                    )

        self.assertEqual(expected_response_output,
                         captured.stdout.getvalue())
        self.assertEquals(0, result)

    def get_product_view_detail(self):
        return {
            'ProductViewDetail': {
                'ProductViewSummary': {
                    'SupportDescription': 'Contact the CLI department '
                                          'for issues '
                                          'deploying or connecting '
                                          'to this product.',
                    'HasDefaultPath': False,
                    'ShortDescription': self.args.product_description,
                    'SupportUrl': self.args.support_url,
                    'Distributor': '',
                    'SupportEmail': self.args.support_email,
                    'Type': self.args.product_type,
                    'Id': 'prodview-ask5ma4y7gwiy',
                    'ProductId': 'prod-inifmhpr47ft2'
                },
                'Status': 'CREATED',
                'ProductARN': 'arn:aws:catalog:us-west-2:'
                              '856570181934:product/prod-inifmhpr47ft2',
                'CreatedTime': 1492728697.0
            },
            "ProvisioningArtifactDetail": {
                "CreatedTime": 1502495200.0,
                "Description": "pa_desc",
                "Type": "CLOUD_FORMATION_TEMPLATE",
                "Id": "pa-6hgqvd3pnwbgc",
                "Name": "pa_name"
            },
            "Tags": self.get_tags_dictionary(),
            "ResponseMetadata": {}
        }

    def get_args_dict(self):
        return {'file-path': self.args.file_path,
                'bucket-name': self.args.bucket_name,
                'product-name': self.args.product_name,
                'tags': self.get_tags_dictionary(),
                'product-owner': self.args.product_owner,
                'product-type': self.args.product_type,
                'product-description': self.args.product_description,
                'product-distributor': self.args.product_distributor,
                'support-description': self.args.support_description,
                'support-email': self.args.support_email
                }

    def get_tags_dictionary(self):
        return [
            {
                "Value": "value1",
                "Key": "key1"
            },
            {
                "Value": "value2",
                "Key": "key2"
            },
            {
                "Value": "value3",
                "Key": "key3"
            }
        ]

    def get_provisioning_artifact_parameters(self, pa_name,
                                             pa_description, pa_type):
        parameters = {
            'Name': pa_name,
            'Description': pa_description,
            'Info': {
                'LoadTemplateFromURL': self.s3_url
            },
            'Type': pa_type
        }

        return parameters
