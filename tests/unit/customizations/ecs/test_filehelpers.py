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
from awscli.customizations.ecs.exceptions import MissingPropertyError
from awscli.customizations.ecs.filehelpers import (APP_PREFIX,
                                                   DGP_PREFIX,
                                                   find_required_key,
                                                   get_app_name,
                                                   get_cluster_name_from_arn,
                                                   get_deploy_group_name,
                                                   MAX_CHAR_LENGTH,
                                                   parse_appspec)


class TestFilehelpers(unittest.TestCase):

    YAML_APPSPEC = """
    version: 0.0
    resources:
      - TestService:
          type: AWS::ECS::Service
          properties:
            taskDefinition: arn:aws:ecs:::task-definition/test:1
            loadBalancerInfo:
              containerName: web
              containerPort: 80
    """

    PARSED_APPSPEC = {
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

    MIXED_CASE_APPSPEC = {
        "version": 0.0,
        "Resources": [{
            "TestService": {
                "TYPE": "AWS::ECS::Service",
                "PROperties": {
                    "TaskDefinition": "arn:aws:ecs:::task-definition/test:1",
                    "loadbalancerInfo": {
                        "containerName": "web",
                        "containerPort": 80
                    }
                }
            }
        }]
    }

    def test_find_required_key(self):
        test_properties_dict = {
            "TaskDefinition": "arn:aws:ecs:::task-definition/test:1",
            "loadbalancerInfo": {
                    "containerName": "web",
                    "containerPort": 80
                } 
        }
        test_key = 'taskDefinition'
        expected_result = 'TaskDefinition'

        result = find_required_key(
            'task definition', test_properties_dict, test_key)
        self.assertEqual(result, expected_result)

    def test_find_required_key_error_missing_key(self):
        invalid_properties_dict = {
            'name': 'some-lambda-function'
        }
        test_key = 'taskDefinition'

        with self.assertRaises(MissingPropertyError):
            find_required_key('task definition', invalid_properties_dict, test_key)

    def test_find_required_key_error_empty_object(self):
        test_key = 'taskDefinition'

        with self.assertRaises(MissingPropertyError):
            find_required_key('task definition', dict(), test_key)

    def test_get_app_name_long(self):
        cluster = 'ClusterClusterClusterClusterClusterClusterClusterCluster'
        service = 'ServiceServiceServiceServiceServiceServiceServiceService'

        expected = APP_PREFIX + cluster[:MAX_CHAR_LENGTH] + '-' + service[:MAX_CHAR_LENGTH]
        response = get_app_name(service, cluster, None)

        self.assertEqual(expected, response)

    def test_get_app_name_no_cluster(self):
        service = 'test-service'
        expected_name = 'AppECS-default-test-service'

        response = get_app_name(service, None, None)
        self.assertEqual(expected_name, response)

    def test_get_app_name_provided(self):
        cluster = 'test-cluster'
        service = 'test-service'
        app_name = 'test-app'

        response = get_app_name(service, cluster, app_name)
        self.assertEqual(app_name, response)

    def test_get_cluster_name_from_arn(self):
        name = "default"
        arn = 'arn:aws:ecs:::cluster/default'

        response = get_cluster_name_from_arn(arn)
        self.assertEqual(name, response)

    def test_get_deploy_group_name_long(self):
        cluster = 'ClusterClusterClusterClusterClusterClusterClusterCluster'
        service = 'ServiceServiceServiceServiceServiceServiceServiceService'

        expected = DGP_PREFIX + cluster[:MAX_CHAR_LENGTH] + '-' + service[:MAX_CHAR_LENGTH]
        response = get_deploy_group_name(service, cluster, None)

        self.assertEqual(expected, response)

    def test_get_deploy_group_name_no_cluster(self):
        service = 'test-service'
        expected_name = 'DgpECS-default-test-service'

        response = get_deploy_group_name(service, None, None)
        self.assertEqual(expected_name, response)

    def test_get_deploy_group_name_provided(self):
        cluster = 'test-cluster'
        service = 'test-service'
        dgp_name = 'test-deployment-group'

        response = get_deploy_group_name(service, cluster, dgp_name)
        self.assertEqual(dgp_name, response)

    """ def test_get_ecs_suffix_no_cluster(self):
        service = 'myService'
        expected_suffix = 'default-myService'

        output = get_ecs_suffix(service, None)
        self.assertEqual(output, expected_suffix)

    def test_get_ecs_suffix_cluster_provided(self):
        service = 'myService'
        cluster = 'myCluster'
        expected_suffix = 'myCluster-myService'

        output = get_ecs_suffix(service, cluster)
        self.assertEqual(output, expected_suffix) """

    def test_parse_appsec(self):
        output = parse_appspec(self.YAML_APPSPEC)
        self.assertEqual(output, self.PARSED_APPSPEC)

    def test_parse_appsec_json(self):
        output = parse_appspec(str(self.PARSED_APPSPEC))
        self.assertEqual(output, self.PARSED_APPSPEC)