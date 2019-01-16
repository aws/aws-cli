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

import json

from awscli.testutils import BaseAWSCommandParamsTest, FileCreator
from awscli.customizations.ecs.deploy import (CodeDeployer,
                                              MAX_WAIT_MIN,
                                              TIMEOUT_BUFFER_MIN)
from awscli.customizations.ecs.filehelpers import (get_app_name,
                                                   get_deploy_group_name)


class TestDeployCommand(BaseAWSCommandParamsTest):

    PREFIX = 'ecs deploy '

    TASK_DEFINITION_JSON = {
        "family": "test",
        "containerDefinitions": [],
        "cpu": "256",
        "memory": '512'
    }

    JSON_APPSPEC = """
    {
        "version": 0.0,
        "resources": [{
            "TestService": {
                "type": "AWS::ECS::Service",
                "properties": {
                    "taskDefinition": "arn:aws:ecs::123:task-definition:1",
                    "loadBalancerInfo": {
                        "containerName": "web",
                        "containerPort": 80
                    }
                }
            }
        }]
    }
    """

    BAD_APPSPEC = """
    version: 0.0
    resources:
      - TestService:
          type: AWS::Lambda::Function
          properties:
            name: myFunction
    """

    YAML_APPSPEC = """
    version: 0.0
    resources:
      - TestService:
          type: AWS::ECS::Service
          properties:
            taskDefinition: arn:aws:ecs::123:task-definition:1
            loadBalancerInfo:
              containerName: web
              containerPort: 80
    """

    APPSPEC_DICT = {
        "version": 0.0,
        "resources": [{
            "TestService": {
                "type": "AWS::ECS::Service",
                "properties": {
                    "taskDefinition": "arn:aws:ecs::123:task-definition:1",
                    "loadBalancerInfo": {
                        "containerName": "web",
                        "containerPort": 80
                    }
                }
            }
        }]
    }

    def setUp(self):
        super(TestDeployCommand, self).setUp()
        # setup required values
        files = FileCreator()
        self.task_def_file = files.create_file(
            'taskDef.json', json.dumps(self.TASK_DEFINITION_JSON), mode='w')
        self.appspec_file = files.create_file(
            'appspec.yaml', self.YAML_APPSPEC, mode='w')
        self.appspec_file_json = files.create_file(
            'appspec.json', self.JSON_APPSPEC, mode='w')
        self.service_name = 'serviceTest'
        self.service_arn = 'arn:aws:ecs:::service/serviceTest'
        # setup default optional values
        self.cluster_name = 'default'
        self.cluster_arn = 'arn:aws:ecs:::cluster/default'
        self.application_name = get_app_name(
            self.service_name, self.cluster_name, None)
        self.deployment_group_name = get_deploy_group_name(
            self.service_name, self.cluster_name, None)
        # setup test response resources
        self.missing_properties_appspec = files.create_file(
            'appspec_bad.yaml', self.BAD_APPSPEC, mode='w')
        self.task_definition_arn = \
            'arn:aws:ecs::1234567890:task-definition\\test:2'
        self.deployment_id = 'd-1234567XX'
        self.mock_deployer = CodeDeployer(None, self.APPSPEC_DICT)
        self.mock_deployer.update_task_def_arn(self.task_definition_arn)
        self.expected_stdout = ("Successfully registered new ECS task "
                                "definition " + self.task_definition_arn + "\n"
                                "Successfully created deployment " +
                                self.deployment_id + "\n"
                                "Waiting for " + self.deployment_id +
                                " to succeed (will wait up to 30 minutes)..."
                                "\nSuccessfully deployed "
                                + self.task_definition_arn + " to service '"
                                + self.service_name + "'\n")

    def tearDown(self):
        super(TestDeployCommand, self).tearDown()

    def test_deploy_with_defaults(self):
        cmdline = self.PREFIX
        cmdline += '--service ' + self.service_name
        cmdline += ' --task-definition ' + self.task_def_file
        cmdline += ' --codedeploy-appspec ' + self.appspec_file

        expected_create_deployment_params = \
            self.mock_deployer._get_create_deploy_request(
                self.application_name, self.deployment_group_name)

        self.parsed_responses = self._get_parsed_responses(
                                    self.cluster_name,
                                    self.application_name,
                                    self.deployment_group_name)

        expected_params = self._get_expected_params(
                                    self.service_name,
                                    self.cluster_name,
                                    self.application_name,
                                    self.deployment_group_name,
                                    expected_create_deployment_params)

        stdout, _, _ = self.assert_params_list_for_cmd(
            cmdline, expected_params, None)

        self.assertEqual(stdout, self.expected_stdout)

    def test_deploy_with_default_arns(self):
        cmdline = self.PREFIX
        cmdline += '--service ' + self.service_arn
        cmdline += ' --cluster ' + self.cluster_arn
        cmdline += ' --task-definition ' + self.task_def_file
        cmdline += ' --codedeploy-appspec ' + self.appspec_file

        expected_create_deployment_params = \
            self.mock_deployer._get_create_deploy_request(
                self.application_name, self.deployment_group_name)

        self.parsed_responses = self._get_parsed_responses(
                                    self.cluster_name,
                                    self.application_name,
                                    self.deployment_group_name)

        expected_params = self._get_expected_params(
                                    self.service_arn,
                                    self.cluster_arn,
                                    self.application_name,
                                    self.deployment_group_name,
                                    expected_create_deployment_params)

        stdout, _, _ = self.assert_params_list_for_cmd(
            cmdline, expected_params, None)

        self.assertEqual(stdout, self.expected_stdout)

    def test_deploy_with_json_appspec(self):
        cmdline = self.PREFIX
        cmdline += '--service ' + self.service_name
        cmdline += ' --task-definition ' + self.task_def_file
        cmdline += ' --codedeploy-appspec ' + self.appspec_file_json

        expected_create_deployment_params = \
            self.mock_deployer._get_create_deploy_request(
                self.application_name, self.deployment_group_name)

        self.parsed_responses = self._get_parsed_responses(
                                    self.cluster_name,
                                    self.application_name,
                                    self.deployment_group_name)

        expected_params = self._get_expected_params(
                                    self.service_name,
                                    self.cluster_name,
                                    self.application_name,
                                    self.deployment_group_name,
                                    expected_create_deployment_params)

        stdout, _, _ = self.assert_params_list_for_cmd(
            cmdline, expected_params, None)

        self.assertEqual(stdout, self.expected_stdout)

    def test_deploy_with_custom_timeout(self):
        cmdline = self.PREFIX
        cmdline += '--service ' + self.service_name
        cmdline += ' --task-definition ' + self.task_def_file
        cmdline += ' --codedeploy-appspec ' + self.appspec_file

        expected_create_deployment_params = \
            self.mock_deployer._get_create_deploy_request(
                self.application_name, self.deployment_group_name)

        custom_deployment_grp_response = {
            'deploymentGroupInfo': {
                'applicationName': self.application_name,
                'deploymentGroupName': self.deployment_group_name,
                'computePlatform': 'ECS',
                'blueGreenDeploymentConfiguration': {
                    'deploymentReadyOption': {
                        'waitTimeInMinutes': 5
                    },
                    'terminateBlueInstancesOnDeploymentSuccess': {
                        'terminationWaitTimeInMinutes': 60
                    }
                },
                'ecsServices': [{
                    'serviceName': self.service_name,
                    'clusterName': self.cluster_name
                }]
            }
        }
        custom_timeout = str(60 + 5 + TIMEOUT_BUFFER_MIN)

        self.parsed_responses = self._get_parsed_responses(
                                    self.cluster_name,
                                    self.application_name,
                                    self.deployment_group_name)

        self.parsed_responses[2] = custom_deployment_grp_response

        expected_params = self._get_expected_params(
                                    self.service_name,
                                    self.cluster_name,
                                    self.application_name,
                                    self.deployment_group_name,
                                    expected_create_deployment_params)

        expected_stdout = ("Successfully registered new ECS task "
                           "definition " + self.task_definition_arn + "\n"
                           "Successfully created deployment " +
                           self.deployment_id + "\n"
                           "Waiting for " + self.deployment_id +
                           " to succeed (will wait up to " + custom_timeout
                           + " minutes)...\nSuccessfully deployed "
                           + self.task_definition_arn + " to service '"
                           + self.service_name + "'\n")

        stdout, _, _ = self.assert_params_list_for_cmd(
            cmdline, expected_params, None)

        self.assertEqual(stdout, expected_stdout)

    def test_deploy_with_max_timeout(self):
        cmdline = self.PREFIX
        cmdline += '--service ' + self.service_name
        cmdline += ' --task-definition ' + self.task_def_file
        cmdline += ' --codedeploy-appspec ' + self.appspec_file

        expected_create_deployment_params = \
            self.mock_deployer._get_create_deploy_request(
                self.application_name, self.deployment_group_name)

        custom_deployment_grp_response = {
            'deploymentGroupInfo': {
                'applicationName': self.application_name,
                'deploymentGroupName': self.deployment_group_name,
                'computePlatform': 'ECS',
                'blueGreenDeploymentConfiguration': {
                    'deploymentReadyOption': {
                        'waitTimeInMinutes': 90
                    },
                    'terminateBlueInstancesOnDeploymentSuccess': {
                        'terminationWaitTimeInMinutes': 300
                    }
                },
                'ecsServices': [{
                    'serviceName': self.service_name,
                    'clusterName': self.cluster_name
                }]
            }
        }
        max_timeout = str(MAX_WAIT_MIN)

        self.parsed_responses = self._get_parsed_responses(
                                    self.cluster_name,
                                    self.application_name,
                                    self.deployment_group_name)

        self.parsed_responses[2] = custom_deployment_grp_response

        expected_params = self._get_expected_params(
                                    self.service_name,
                                    self.cluster_name,
                                    self.application_name,
                                    self.deployment_group_name,
                                    expected_create_deployment_params)

        expected_stdout = ("Successfully registered new ECS task "
                           "definition " + self.task_definition_arn + "\n"
                           "Successfully created deployment " +
                           self.deployment_id + "\n"
                           "Waiting for " + self.deployment_id +
                           " to succeed (will wait up to " + max_timeout
                           + " minutes)...\nSuccessfully deployed "
                           + self.task_definition_arn + " to service '"
                           + self.service_name + "'\n")

        stdout, _, _ = self.assert_params_list_for_cmd(
            cmdline, expected_params, None)

        self.assertEqual(stdout, expected_stdout)

    def test_deploy_with_optional_values(self):
        custom_app = 'myOtherApp'
        custom_dgp = 'myOtherDgp'
        custom_cluster = 'myOtherCluster'

        cmdline = self.PREFIX
        cmdline += '--service ' + self.service_name
        cmdline += ' --task-definition ' + self.task_def_file
        cmdline += ' --codedeploy-appspec ' + self.appspec_file
        cmdline += ' --cluster ' + self.cluster_name
        cmdline += ' --codedeploy-application ' + custom_app
        cmdline += ' --codedeploy-deployment-group ' + custom_dgp
        cmdline += ' --cluster ' + custom_cluster

        expected_create_deployment_params = \
            self.mock_deployer._get_create_deploy_request(
                custom_app, custom_dgp)

        self.parsed_responses = self._get_parsed_responses(
            custom_cluster, custom_app, custom_dgp)

        expected_params = self._get_expected_params(
            self.service_name, custom_cluster, custom_app,
            custom_dgp, expected_create_deployment_params)

        stdout, _, _ = self.assert_params_list_for_cmd(
            cmdline, expected_params, None)

        self.assertEqual(stdout, self.expected_stdout)

    def test_deploy_error_missing_appspec_property(self):
        cmdline = self.PREFIX
        cmdline += '--service ' + self.service_name
        cmdline += ' --task-definition ' + self.task_def_file
        cmdline += ' --codedeploy-appspec ' + self.missing_properties_appspec

        self.parsed_responses = [
            {
                'services': [{
                    'serviceArn': self.service_arn,
                    'serviceName': self.service_name,
                    'clusterArn': 'arn:aws:ecs:::cluster/' + self.cluster_name
                }]
            },
            {
                'application': {
                    'applicationId': '876uyh6-45tdfg',
                    'applicationName': self.application_name,
                    'computePlatform': 'ECS'
                }
            },
            {
                'deploymentGroupInfo': {
                    'applicationName': self.application_name,
                    'deploymentGroupName': self.deployment_group_name,
                    'computePlatform': 'ECS',
                    'blueGreenDeploymentConfiguration': {
                        'deploymentReadyOption': {
                            'waitTimeInMinutes': 5
                        },
                        'terminateBlueInstancesOnDeploymentSuccess': {
                            'terminationWaitTimeInMinutes': 10
                        }
                    },
                    'ecsServices': [{
                        'serviceName': self.service_name,
                        'clusterName': self.cluster_name
                    }]
                }
            },
            {
                'taskDefinition': {
                    'taskDefinitionArn': self.task_definition_arn,
                    'family': 'test',
                    'containerDefinitions': []
                }
            }
        ]

        expected_params = [
            {
                'operation': 'DescribeServices',
                'params': {
                    'cluster': self.cluster_name,
                    'services': [self.service_name]
                }
            },
            {
                'operation': 'GetApplication',
                'params': {'applicationName': self.application_name}
            },
            {
                'operation': 'GetDeploymentGroup',
                'params': {
                    'applicationName': self.application_name,
                    'deploymentGroupName': self.deployment_group_name
                }
            },
            {
                'operation': 'RegisterTaskDefinition',
                'params': self.TASK_DEFINITION_JSON
            }
        ]

        expected_stdout = ("Successfully registered new ECS task "
                           "definition " + self.task_definition_arn + "\n")

        expected_stderr = ("\nError: Resource 'properties' must "
                           "include property 'taskDefinition'\n")

        stdout, stderr, _ = self.assert_params_list_for_cmd(
            cmdline, expected_params, 255)

        self.assertEqual(stdout, expected_stdout)
        self.assertEqual(stderr, expected_stderr)

    def test_deploy_error_invalid_platform(self):
        cmdline = self.PREFIX
        cmdline += '--service ' + self.service_name
        cmdline += ' --task-definition ' + self.task_def_file
        cmdline += ' --codedeploy-appspec ' + self.missing_properties_appspec

        self.parsed_responses = [
            {
                'services': [{
                    'serviceArn': self.service_arn,
                    'serviceName': self.service_name,
                    'clusterArn': 'arn:aws:ecs:::cluster/' + self.cluster_name
                }]
            },
            {
                'application': {
                    'applicationId': '876uyh6-45tdfg',
                    'applicationName': self.application_name,
                    'computePlatform': 'Server'
                }
            },
            {
                'deploymentGroupInfo': {
                    'applicationName': self.application_name,
                    'deploymentGroupName': self.deployment_group_name,
                    'computePlatform': 'ECS',
                    'ecsServices': [{
                        'serviceName': self.service_name,
                        'clusterName': self.cluster_name
                    }]
                }
            }
        ]

        expected_params = [
            {
                'operation': 'DescribeServices',
                'params': {
                    'cluster': self.cluster_name,
                    'services': [self.service_name]
                }
            },
            {
                'operation': 'GetApplication',
                'params': {'applicationName': self.application_name}
            },
            {
                'operation': 'GetDeploymentGroup',
                'params': {
                    'applicationName': self.application_name,
                    'deploymentGroupName': self.deployment_group_name
                }
            }
        ]

        expected_stderr = ("\nError: Application '" + self.application_name +
                           "' must support 'ECS' compute platform\n")

        stdout, stderr, _ = self.assert_params_list_for_cmd(
            cmdline, expected_params, 255)

        self.assertEqual('', stdout)
        self.assertEqual(expected_stderr, stderr)

    def assert_params_list_for_cmd(self, cmd, params, expected_rc=0,
                                   stderr_contains=None):
        stdout, stderr, rc = self.run_cmd(cmd, expected_rc)
        if stderr_contains is not None:
            self.assertIn(stderr_contains, stderr)

        self.assertEqual(len(self.operations_called), len(params))
        for i, param in enumerate(params):
            self.assertEqual(
                self.operations_called[i][0].name, param['operation'])
            self.assertEqual(
                self.operations_called[i][1], param['params'])

        return stdout, stderr, rc

    def _get_expected_params(self, service_name, cluster_name, app_name,
                             dgp_name, create_deployment_params):
        return [
            {
                'operation': 'DescribeServices',
                'params': {
                    'cluster': cluster_name,
                    'services': [service_name]
                }
            },
            {
                'operation': 'GetApplication',
                'params': {'applicationName': app_name}
            },
            {
                'operation': 'GetDeploymentGroup',
                'params': {
                    'applicationName': app_name,
                    'deploymentGroupName': dgp_name
                }
            },
            {
                'operation': 'RegisterTaskDefinition',
                'params': self.TASK_DEFINITION_JSON
            },
            {
                'operation': 'CreateDeployment',
                'params': create_deployment_params
            },
            {
                'operation': 'GetDeployment',
                'params': {
                    'deploymentId': self.deployment_id
                }
            }
        ]

    def _get_parsed_responses(self, cluster_name, app_name, dgp_name):
        return [
            {
                'services': [{
                    'serviceArn': self.service_arn,
                    'serviceName': self.service_name,
                    'clusterArn': 'arn:aws:ecs:::cluster/' + cluster_name
                }]
            },
            {
                'application': {
                    'applicationId': '876uyh6-45tdfg',
                    'applicationName': app_name,
                    'computePlatform': 'ECS'
                }
            },
            {
                'deploymentGroupInfo': {
                    'applicationName': app_name,
                    'deploymentGroupName': dgp_name,
                    'computePlatform': 'ECS',
                    'blueGreenDeploymentConfiguration': {
                        'deploymentReadyOption': {
                            'waitTimeInMinutes': 5
                        },
                        'terminateBlueInstancesOnDeploymentSuccess': {
                            'terminationWaitTimeInMinutes': 10
                        }
                    },
                    'ecsServices': [{
                        'serviceName': self.service_name,
                        'clusterName': cluster_name
                    }]
                }
            },
            {
                'taskDefinition': {
                    'taskDefinitionArn': self.task_definition_arn,
                    'family': 'test',
                    'containerDefinitions': []
                }
            },
            {
                'deploymentId': self.deployment_id
            },
            {
                'deploymentInfo': {
                    'applicationName': app_name,
                    'status': 'Succeeded'
                }
            }
        ]
