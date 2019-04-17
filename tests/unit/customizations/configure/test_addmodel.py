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

from botocore.session import get_session
from botocore.loaders import Loader

from awscli.customizations.configure.addmodel import get_model_location
from awscli.testutils import unittest, FileCreator


class TestGetModelLocation(unittest.TestCase):
    def setUp(self):
        self.session = get_session()
        self.files = FileCreator()

        # Create our own loader for the unit test and not rely on the
        # customer's actual ~/.aws/models nor the builtin botocore data
        # directory.
        self.customer_data_root = os.path.join(self.files.rootdir, 'customer')
        os.mkdir(self.customer_data_root)

        self.builtin_data_root = os.path.join(self.files.rootdir, 'builtin')
        os.mkdir(self.builtin_data_root)

        self.data_loader = Loader(
            [self.customer_data_root, self.builtin_data_root],
            include_default_search_paths=False
        )
        self.data_loader.CUSTOMER_DATA_PATH = self.customer_data_root
        self.session.register_component('data_loader', self.data_loader)

        # Add some models into the builtin model directory
        # We are going to add two models. One with a matching service name
        # and endpoint and another without.
        self.matching_service = 'matching'
        self.non_matching_service = 'nonmatching'
        self.non_matching_prefix = 'nonmatching-prefix'
        self.default_api_version = '2015-10-01'

        matching_service_path = os.path.join(
            self.builtin_data_root, self.matching_service,
            self.default_api_version, 'service-2.json'
        )
        os.makedirs(os.path.dirname(matching_service_path))

        non_matching_service_path = os.path.join(
            self.builtin_data_root, self.non_matching_service,
            self.default_api_version, 'service-2.json'
        )
        os.makedirs(os.path.dirname(non_matching_service_path))

        # Write the models to the builtin directory
        with open(matching_service_path, 'w') as f:
            json.dump(self._create_service_definition(
                self.matching_service, self.default_api_version), f)

        with open(non_matching_service_path, 'w') as f:
            json.dump(self._create_service_definition(
                self.non_matching_prefix, self.default_api_version), f)

    def tearDown(self):
        self.files.remove_all()

    def _create_service_definition(self, endpoint_prefix, api_version):
        return {
            "version": "2.0",
            "metadata": {
                "apiVersion": api_version,
                "endpointPrefix": endpoint_prefix,
            },
            "operations": {},
            "shapes": {}
        }

    def test_get_model_location_for_matching_prefix_and_name(self):
        model_location = get_model_location(
            self.session, self._create_service_definition(
                self.matching_service, self.default_api_version))
        self.assertEqual(
            os.path.join(
                self.data_loader.CUSTOMER_DATA_PATH,
                self.matching_service, self.default_api_version,
                'service-2.json'), model_location)

    def test_get_model_location_with_nonmatching_prefix_and_name(self):
        model_location = get_model_location(
            self.session, self._create_service_definition(
                self.non_matching_prefix, self.default_api_version))
        self.assertEqual(
            os.path.join(
                self.data_loader.CUSTOMER_DATA_PATH,
                self.non_matching_service, self.default_api_version,
                'service-2.json'), model_location)

    def test_get_model_location_of_nonexistent_service(self):
        model_location = get_model_location(
            self.session, self._create_service_definition(
                'nonexistent', self.default_api_version))
        self.assertEqual(
            os.path.join(
                self.data_loader.CUSTOMER_DATA_PATH,
                'nonexistent', self.default_api_version,
                'service-2.json'), model_location)

    def test_get_model_location_when_service_name_provided(self):
        model_location = get_model_location(
            self.session, self._create_service_definition(
                'nonexistent', self.default_api_version), 'override')
        self.assertEqual(
            os.path.join(
                self.data_loader.CUSTOMER_DATA_PATH,
                'override', self.default_api_version,
                'service-2.json'), model_location)

    def test_get_model_location_with_non_v2(self):
        service_definition = self._create_service_definition(
            'existent', self.default_api_version)
        service_definition['version'] = '3.0'
        model_location = get_model_location(self.session, service_definition)
        self.assertEqual(
            os.path.join(
                self.data_loader.CUSTOMER_DATA_PATH,
                'existent', self.default_api_version,
                'service-3.json'), model_location)

    def test_get_model_location_with_missing_version(self):
        service_definition = self._create_service_definition(
            'existent', self.default_api_version)
        service_definition.pop('version')
        model_location = get_model_location(self.session, service_definition)
        self.assertEqual(
            os.path.join(
                self.data_loader.CUSTOMER_DATA_PATH,
                'existent', self.default_api_version,
                'service-2.json'), model_location)
