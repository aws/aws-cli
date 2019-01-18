# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from awscli.testutils import unittest
from awscli.customizations.ecs.deploy import CodeDeployValidator
from awscli.customizations.ecs.exceptions import (InvalidPlatformError,
                                                  InvalidProperyError)


class TestCodeDeployValidator(unittest.TestCase):
    TEST_RESOURCES = {
        'service': 'test-service',
        'service_arn': 'arn:aws:ecs:::service/test-service',
        'cluster': 'test-cluster',
        'cluster_arn': 'arn:aws:ecs:::cluster/test-cluster',
        'app_name': 'test-application',
        'deployment_group_name': 'test-deployment-group'
    }

    TEST_APP_DETAILS = {
        'application': {
            'applicationId': '876uyh6-45tdfg',
            'applicationName': 'test-application',
            'computePlatform': 'ECS'
        }
    }

    TEST_DEPLOYMENT_GROUP_DETAILS = {
        'deploymentGroupInfo': {
            'applicationName': 'test-application',
            'deploymentGroupName': 'test-deployment-group',
            'computePlatform': 'ECS',
            'ecsServices': [{
                'serviceName': 'test-service',
                'clusterName': 'test-cluster'
            }]
        }
    }

    def setUp(self):
        self.validator = CodeDeployValidator(None, self.TEST_RESOURCES)
        self.validator.app_details = self.TEST_APP_DETAILS
        self.validator.deployment_group_details = \
            self.TEST_DEPLOYMENT_GROUP_DETAILS

    def test_validations(self):
        self.validator.validate_application()
        self.validator.validate_deployment_group()
        self.validator.validate_all()

    def test_validate_application_error_compute_platform(self):
        invalid_app = {
            'application': {
                'applicationName': 'test-application',
                'computePlatform': 'Server'
            }
        }

        bad_validator = CodeDeployValidator(None, self.TEST_RESOURCES)
        bad_validator.app_details = invalid_app

        with self.assertRaises(InvalidPlatformError):
            bad_validator.validate_application()

    def test_validate_deployment_group_error_compute_platform(self):
        invalid_dgp = {
            'deploymentGroupInfo': {
                'computePlatform': 'Lambda'
            }
        }
        bad_validator = CodeDeployValidator(None, self.TEST_RESOURCES)
        bad_validator.deployment_group_details = invalid_dgp

        with self.assertRaises(InvalidPlatformError):
            bad_validator.validate_deployment_group()

    def test_validate_deployment_group_error_service(self):
        invalid_dgp = {
            'deploymentGroupInfo': {
                'computePlatform': 'ECS',
                'ecsServices': [{
                    'serviceName': 'the-wrong-test-service',
                    'clusterName': 'test-cluster'
                }]
            }
        }
        bad_validator = CodeDeployValidator(None, self.TEST_RESOURCES)
        bad_validator.deployment_group_details = invalid_dgp

        with self.assertRaises(InvalidProperyError):
            bad_validator.validate_deployment_group()

    def test_validate_deployment_group_error_cluster(self):
        invalid_dgp = {
            'deploymentGroupInfo': {
                'computePlatform': 'ECS',
                'ecsServices': [{
                    'serviceName': 'test-service',
                    'clusterName': 'the-wrong-test-cluster'
                }]
            }
        }
        bad_validator = CodeDeployValidator(None, self.TEST_RESOURCES)
        bad_validator.deployment_group_details = invalid_dgp

        with self.assertRaises(InvalidProperyError):
            bad_validator.validate_deployment_group()
