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

import botocore
import mock

from awscli.testutils import unittest, capture_output
from awscli.customizations.ecs.deploy import ECSDeploy


class TestECSDeploy(unittest.TestCase):

    TEST_APPSPEC = {
        "version": 0.0,
        "resources": [{
            "TestService": {
                "type": "AWS::ECS::Service",
                "properties": {
                    "taskDefinition": "arn:aws:ecs:::task-definition/test:1",
                    "loadBalancerInfo": {
                        "containerName": "web",
                        "containerPort": 80
                    }
                }
            }
        }]
    }

    def setUp(self):
        self.session = mock.Mock(spec=botocore.session.Session)
        self.ecs_deployer = ECSDeploy(self.session)
        self.ecs_deployer.task_def_arn = \
            'arn:aws:ecs:::task-definition/test:3'
        self.ecs_deployer.resources = {
            'service': 'testService',
            'service_arn': 'arn:aws:ecs:::service/testService',
            'cluster': 'testCluster',
            'cluster_arn': 'arn:aws:ecs:::custer/testCluster',
            'app_name': 'testApp',
            'deployment_group_name': 'testDeploymentGroup'
        }

    def test_create_and_wait_for_deployment(self):
        cd_client = mock.Mock()
        cd_client.create_deployment.return_value = {
            'deploymentId': 'd-12345ZYX'
        }

        expected_stdout = ("Successfully created deployment " +
                           "d-12345ZYX\nWaiting for d-12345ZYX "
                           "to succeed...\nSuccessfully deployed "
                           "arn:aws:ecs:::task-definition/test:3 to "
                           "service 'testService'\n")

        with capture_output() as captured:
            self.ecs_deployer._create_and_wait_for_deployment(
                cd_client, self.TEST_APPSPEC)

            self.assertEqual(expected_stdout,
                             captured.stdout.getvalue())
