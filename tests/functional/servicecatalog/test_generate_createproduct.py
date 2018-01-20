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


import os
from mock import mock

from awscli.customizations.servicecatalog.utils \
    import get_s3_path
from awscli.testutils import BaseAWSCommandParamsTest


class TestGenerateProduct(BaseAWSCommandParamsTest):
    prefix = "servicecatalog generate product "

    def get_expected_result(self):
        expected_url = 'https://s3.amazonaws.com/{0}/{1}'.\
                            format(self.bucket_name,
                                   get_s3_path(self.template_path))

        return {'Description': self.product_description,
                'Distributor': self.product_distributor,
                'IdempotencyToken': mock.ANY,
                'Name': self.product_name,
                'Owner': self.product_owner,
                'ProductType': self.product_type,
                'ProvisioningArtifactParameters': {
                    'Description': self.provisioning_artifact_description,
                    'Info': {'LoadTemplateFromURL': expected_url},
                    'Name': self.provisioning_artifact_name,
                    'Type': self.provisioning_artifact_type},
                'SupportDescription': self.support_description,
                'SupportEmail': self.support_email,
                'Tags': [
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
                ]}

    def init_params(self):
        self.obj_key = 'development-environment.template'
        self.template_path = os.path.join(os.path.dirname(__file__),
                                          self.obj_key)
        self.bucket_name = 'bucket_name'
        self.product_name = 'prod_name'
        self.tags = 'Key=key1,Value=value1  Key=key2,Value=value2 \
                    Key=key3,Value=value3'
        self.product_owner = 'prod_owner'
        self.product_type = 'CLOUD_FORMATION_TEMPLATE'
        self.provisioning_artifact_name = 'prov_art_name'
        self.provisioning_artifact_description = 'prov_art_desc'
        self.provisioning_artifact_type = 'CLOUD_FORMATION_TEMPLATE'
        self.product_description = 'prod_desc'
        self.product_distributor = 'prod_dist'
        self.support_description = 'support_desc'
        self.support_email = 'support_email'

    def build_cmd_line(self):
        cmd_line = self.prefix
        if self.template_path:
            cmd_line += ' --file-path %s' % self.template_path
        if self.bucket_name:
            cmd_line += ' --bucket-name %s' % self.bucket_name
        if self.product_name:
            cmd_line += ' --product-name %s' % self.product_name
        cmd_line += ' --tags %s' % self.tags
        if self.product_owner:
            cmd_line += ' --product-owner %s' % self.product_owner
        if self.product_type:
            cmd_line += ' --product-type %s' % self.product_type
        if self.provisioning_artifact_name:
            cmd_line += ' --provisioning-artifact-name %s' \
                        % self.provisioning_artifact_name
        if self.provisioning_artifact_description:
            cmd_line += ' --provisioning-artifact-description %s' \
                        % self.provisioning_artifact_description
        if self.provisioning_artifact_type:
            cmd_line += ' --provisioning-artifact-type %s' \
                        % self.provisioning_artifact_type
        cmd_line += ' --product-description %s' % self.product_description
        cmd_line += ' --product-distributor %s' % self.product_distributor
        cmd_line += ' --support-description %s' % self.support_description
        cmd_line += ' --support-email %s' % self.support_email
        return cmd_line

    def setUp(self):
        super(TestGenerateProduct, self).setUp()
        self.init_params()

    def test_generate_product_success(self):
        self.cmd_line = self.build_cmd_line()
        expected_result = self.get_expected_result()

        self.assert_params_for_cmd(self.cmd_line,
                                   expected_result,
                                   expected_rc=0)

    def test_generate_product_success_unicode(self):
        self.product_name = u'\u05d1\u05e8\u05d9\u05e6\u05e7\u05dc\u05d4'
        self.support_description = u'\u00fd\u00a9\u0194\u0292'

        self.cmd_line = self.build_cmd_line()
        expected_result = self.get_expected_result()

        self.assert_params_for_cmd(self.cmd_line,
                                   expected_result,
                                   expected_rc=0)

    def test_generate_product_invalid_path(self):
        self.template_path = os.path.join('invalid', 'template', 'file')
        self.cmd_line = self.build_cmd_line()
        self.assert_params_for_cmd(
            self.cmd_line,
            expected_rc=255,
            stderr_contains='cannot be found'
        )

    def test_generate_product_missing_file_path(self):
        self.template_path = None
        self.cmd_line = self.build_cmd_line()
        self.assert_params_for_cmd(
            self.cmd_line,
            expected_rc=2,
            stderr_contains='--file-path')

    def test_generate_product_missing_bucket_name(self):
        self.bucket_name = None
        self.cmd_line = self.build_cmd_line()
        self.assert_params_for_cmd(
            self.cmd_line,
            expected_rc=2,
            stderr_contains='--bucket-name')

    def test_generate_product_missing_product_type(self):
        self.product_type = None
        self.cmd_line = self.build_cmd_line()
        self.assert_params_for_cmd(
            self.cmd_line,
            expected_rc=2,
            stderr_contains='--product-type')

    def test_generate_product_missing_product_name(self):
        self.product_name = None
        self.cmd_line = self.build_cmd_line()
        self.assert_params_for_cmd(
            self.cmd_line,
            expected_rc=2,
            stderr_contains='--product-name')

    def test_generate_product_missing_product_owner(self):
        self.product_owner = None
        self.cmd_line = self.build_cmd_line()
        self.assert_params_for_cmd(
            self.cmd_line,
            expected_rc=2,
            stderr_contains='--product-owner')

    def test_generate_product_missing_provisioning_artifact_name(self):
        self.provisioning_artifact_name = None
        self.cmd_line = self.build_cmd_line()
        self.assert_params_for_cmd(
            self.cmd_line,
            expected_rc=2,
            stderr_contains='--provisioning-artifact-name')

    def test_generate_product_missing_provisioning_artifact_description(self):
        self.provisioning_artifact_description = None
        self.cmd_line = self.build_cmd_line()
        self.assert_params_for_cmd(
            self.cmd_line,
            expected_rc=2,
            stderr_contains='--provisioning-artifact-description')

    def test_generate_product_missing_provisioning_artifact_type(self):
        self.provisioning_artifact_type = None
        self.cmd_line = self.build_cmd_line()
        self.assert_params_for_cmd(
            self.cmd_line,
            expected_rc=2,
            stderr_contains='--provisioning-artifact-type')

    def test_invalid_product_type(self):
        self.product_type = 'invalid-product-type'
        self.cmd_line = self.build_cmd_line()

        self.assert_params_for_cmd(
            self.cmd_line,
            expected_rc=2,
            stderr_contains='--product-type: Invalid choice')

    def test_generate_product_invalid_provisioning_artifact_type(self):
        self.provisioning_artifact_type = 'invalid_provisioning type'
        self.cmd_line = self.build_cmd_line()

        self.assert_params_for_cmd(
            self.cmd_line,
            expected_rc=2,
            stderr_contains='--provisioning-artifact-type: Invalid choice')
