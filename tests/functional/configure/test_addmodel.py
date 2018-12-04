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
import json
import os

from awscli.testutils import BaseAWSCommandParamsTest, FileCreator


class TestAddModel(BaseAWSCommandParamsTest):
    prefix = 'configure add-model'

    def setUp(self):
        super(TestAddModel, self).setUp()
        self.files = FileCreator()
        self.customer_data_root = self.files.rootdir
        self.data_loader = self.driver.session.get_component('data_loader')
        self.data_loader.CUSTOMER_DATA_PATH = self.customer_data_root
        self.service_definition = {
            "version": "2.0",
            "metadata": {
                "apiVersion": '2015-12-02',
                "endpointPrefix": 'myservice',
            },
            "operations": {},
            "shapes": {}
        }
        self.service_unicode_definition = {
            "version": "2.0",
            "metadata": {
                "apiVersion": '2015-12-02',
                "endpointPrefix": 'myservice',
                "keyWithUnicode": u'\u2713'
            },
            "operations": {},
            "shapes": {}
        }

    def tearDown(self):
        super(TestAddModel, self).tearDown()
        self.files.remove_all()

    def test_add_model(self):
        cmdline = self.prefix + ' --service-model %s' % json.dumps(
            self.service_definition, separators=(',', ':'))
        self.run_cmd(cmdline)

        # Ensure that the model exists in the correct location.
        self.assertTrue(
            os.path.exists(os.path.join(
                self.customer_data_root, 'myservice', '2015-12-02',
                'service-2.json')))

    def test_add_model_with_unicode(self):
        cmdline = self.prefix + ' --service-model %s' % json.dumps(
            self.service_unicode_definition, separators=(',', ':'))
        self.run_cmd(cmdline)

        # Ensure that the model exists in the correct location.
        self.assertTrue(
            os.path.exists(os.path.join(
                self.customer_data_root, 'myservice', '2015-12-02',
                'service-2.json')))

    def test_add_model_with_service_name(self):
        cmdline = self.prefix + ' --service-model %s' % json.dumps(
            self.service_definition, separators=(',', ':'))
        cmdline += ' --service-name override-name'
        self.run_cmd(cmdline)

        # Ensure that the model exists in the correct location.
        self.assertTrue(
            os.path.exists(os.path.join(
                self.customer_data_root, 'override-name', '2015-12-02',
                'service-2.json')))
