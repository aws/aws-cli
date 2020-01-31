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


class TestGenerateProvisioningArtifact(BaseAWSCommandParamsTest):
    prefix = "servicecatalog generate provisioning-artifact "

    def get_expected_result(self):
        expected_url = 'https://s3.amazonaws.com/{0}/{1}'. \
            format(self.bucket_name, get_s3_path(self.template_path))
        return {
            'IdempotencyToken': mock.ANY,
            'Parameters': {
                'Description': self.provisioning_artifact_description,
                'Info': {
                    'LoadTemplateFromURL': expected_url
                },
                'Name': self.provisioning_artifact_name,
                'Type': self.provisioning_artifact_type
            },
            'ProductId': self.product_id
        }

    def init_params(self):
        self.obj_key = 'development-environment.template'
        self.template_path = os.path.join(os.path.dirname(__file__),
                                          self.obj_key)
        self.bucket_name = 'bucket_name'
        self.provisioning_artifact_name = 'prov_art_name'
        self.provisioning_artifact_description = 'prov_art_desc'
        self.provisioning_artifact_type = 'CLOUD_FORMATION_TEMPLATE'
        self.product_id = 'prod-1234567890abc'

    def build_cmd_line(self):
        cmd_line = self.prefix
        if self.template_path:
            cmd_line += ' --file-path %s' % self.template_path
        if self.bucket_name:
            cmd_line += ' --bucket-name %s' % self.bucket_name
        if self.provisioning_artifact_name:
            cmd_line += ' --provisioning-artifact-name %s' \
                        % self.provisioning_artifact_name
        if self.provisioning_artifact_description:
            cmd_line += ' --provisioning-artifact-description %s' \
                        % self.provisioning_artifact_description
        if self.provisioning_artifact_type:
            cmd_line += ' --provisioning-artifact-type %s' \
                        % self.provisioning_artifact_type
        if self.product_id:
            cmd_line += ' --product-id %s' % self.product_id
        return cmd_line

    def setUp(self):
        super(TestGenerateProvisioningArtifact, self).setUp()
        self.init_params()

    def test_generate_provisioning_artifact_success(self):
        self.cmd_line = self.build_cmd_line()
        expected_result = self.get_expected_result()

        self.assert_params_for_cmd(self.cmd_line,
                                   expected_result,
                                   expected_rc=0)

    def test_generate_provisioning_artifact_success_unicode(self):
        self.provisioning_artifact_name = u'\u05d1\u05e8\u05d9\u05e6\u05e7'
        self.provisioning_artifact_description = u'\u00fd\u00a9\u0194\u0292'
        self.cmd_line = self.build_cmd_line()
        expected_result = self.get_expected_result()

        self.assert_params_for_cmd(self.cmd_line,
                                   expected_result,
                                   expected_rc=0)

    def test_generate_provisioning_artifact_invalid_path(self):
        self.template_path = os.path.join('invalid', 'template', 'file')
        self.cmd_line = self.build_cmd_line()
        self.assert_params_for_cmd(
            self.cmd_line,
            expected_rc=255,
            stderr_contains='cannot be found')

    def test_generate_provisioning_artifact_invalid_pa_type(self):
        self.provisioning_artifact_type = 'invalid_provisioning type'
        self.cmd_line = self.build_cmd_line()
        self.assert_params_for_cmd(
            self.cmd_line,
            expected_rc=252,
            stderr_contains='--provisioning-artifact-type: Invalid choice')

    def test_generate_provisioning_artifact_missing_file_path(self):
        self.template_path = None
        self.cmd_line = self.build_cmd_line()
        self.assert_params_for_cmd(
            self.cmd_line,
            expected_rc=252,
            stderr_contains='--file-path')

    def test_generate_provisioning_artifact_missing_bucket_name(self):
        self.bucket_name = None
        self.cmd_line = self.build_cmd_line()
        self.assert_params_for_cmd(
            self.cmd_line,
            expected_rc=252,
            stderr_contains='--bucket-name')

    def test_generate_provisioning_artifact_missing_pa_name(self):
        self.provisioning_artifact_name = None
        self.cmd_line = self.build_cmd_line()
        self.assert_params_for_cmd(
            self.cmd_line,
            expected_rc=252,
            stderr_contains='--provisioning-artifact-name')

    def test_generate_provisioning_artifact_missing_pa_description(self):
        self.provisioning_artifact_description = None
        self.cmd_line = self.build_cmd_line()
        self.assert_params_for_cmd(
            self.cmd_line,
            expected_rc=252,
            stderr_contains='--provisioning-artifact-description')

    def test_generate_provisioning_artifact_missing_pa_type(self):
        self.provisioning_artifact_type = None
        self.cmd_line = self.build_cmd_line()
        self.assert_params_for_cmd(
            self.cmd_line,
            expected_rc=252,
            stderr_contains='--provisioning-artifact-type')
