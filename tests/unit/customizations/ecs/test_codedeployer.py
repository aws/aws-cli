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

import hashlib
import json

from botocore import compat
from awscli.testutils import capture_output, mock, unittest
from awscli.customizations.ecs.deploy import CodeDeployer, MAX_WAIT_MIN
from awscli.customizations.ecs.exceptions import MissingPropertyError


class TestCodeDeployer(unittest.TestCase):
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
        waiter = mock.Mock()
        waiter.wait.return_value = {}
        mock_cd = mock.Mock()
        mock_cd.get_waiter.return_value = waiter

        self.deployer = CodeDeployer(mock_cd, self.TEST_APPSPEC)

    def test_update_task_def_arn(self):
        test_arn = 'arn:aws:ecs::1234567890:task-definition/new-thing:3'
        self.deployer.update_task_def_arn(test_arn)

        appspec_resources = self.deployer._appspec_dict['resources']
        for resource in appspec_resources:
            actual_arn = \
                resource['TestService']['properties']['taskDefinition']
            self.assertEqual(actual_arn, test_arn)

    def test_update_task_def_arn_error_required_key(self):
        invalid_appspec = {
            "version": 0.0,
            "resources": [{
                "TestFunc": {
                    "type": "AWS::Lambda::Function",
                    "properties": {
                        "name": "some-function"
                    }
                }
            }]
        }
        bad_deployer = CodeDeployer(None, invalid_appspec)

        with self.assertRaises(MissingPropertyError):
            bad_deployer.update_task_def_arn('arn:aws:ecs:task-definiton/test')

    def test_get_create_deploy_request(self):
        test_app = 'test-application'
        test_dgp = 'test-deployment-group'
        request = self.deployer._get_create_deploy_request(test_app, test_dgp)

        self.assertEqual(request['applicationName'], test_app)
        self.assertEqual(request['deploymentGroupName'], test_dgp)

        actual_appspec = \
            json.loads(request['revision']['appSpecContent']['content'])
        actual_hash = request['revision']['appSpecContent']['sha256']

        self.assertEqual(actual_appspec, self.deployer._appspec_dict)
        self.assertEqual(actual_hash, self.deployer._get_appspec_hash())

    def test_get_appspec_hash(self):
        appspec_str = json.dumps(self.deployer._appspec_dict)
        encoded_appspec = compat.ensure_bytes(appspec_str)
        expected_hash = hashlib.sha256(encoded_appspec).hexdigest()

        actual_hash = self.deployer._get_appspec_hash()
        self.assertEqual(actual_hash, expected_hash)

    def test_wait_for_deploy_success_default_wait(self):
        mock_id = 'd-1234567XX'
        expected_stdout = self.deployer.MSG_WAITING.format(
            deployment_id=mock_id, wait=30)

        with capture_output() as captured:
            self.deployer.wait_for_deploy_success('d-1234567XX', 0)
            self.assertEqual(expected_stdout, captured.stdout.getvalue())

    def test_wait_for_deploy_success_custom_wait(self):
        mock_id = 'd-1234567XX'
        mock_wait = 40

        expected_stdout = self.deployer.MSG_WAITING.format(
            deployment_id=mock_id, wait=mock_wait)

        with capture_output() as captured:
            self.deployer.wait_for_deploy_success('d-1234567XX', mock_wait)
            self.assertEqual(expected_stdout, captured.stdout.getvalue())

    def test_wait_for_deploy_success_max_wait_exceeded(self):
        mock_id = 'd-1234567XX'
        mock_wait = MAX_WAIT_MIN + 15

        expected_stdout = self.deployer.MSG_WAITING.format(
            deployment_id=mock_id, wait=MAX_WAIT_MIN)

        with capture_output() as captured:
            self.deployer.wait_for_deploy_success('d-1234567XX', mock_wait)
            self.assertEqual(expected_stdout, captured.stdout.getvalue())
