# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from awscli.testutils import BaseAWSCommandParamsTest, mock


class TestMonitorMutatingGatewayServiceIntegration(BaseAWSCommandParamsTest):
    def setUp(self):
        super().setUp()
        self.patch_make_request()

    def test_create_gateway_service_with_monitoring(self):
        # Setup mock responses: only valid create response, no describe response
        self.parsed_responses = [
            # CreateExpressGatewayService response
            {
                "service": {
                    "serviceArn": "arn:aws:ecs:us-east-1:123456789:service/test-cluster/test-service",
                    "serviceName": "test-service",
                    "status": "ACTIVE",
                }
            }
            # No DescribeExpressGatewayService response - will cause an error and monitoring to terminate
        ]

        # Execute command with monitoring enabled
        cmdline = 'ecs create-express-gateway-service --service-name test-service --cluster test-cluster --execution-role-arn arn:aws:iam::123456789:role/exec --infrastructure-role-arn arn:aws:iam::123456789:role/infra --primary-container image=nginx --monitor-resources'

        self.run_cmd(cmdline, expected_rc=0)

        # Verify API calls were made (create + monitoring attempted)
        operation_names = [op[0].name for op in self.operations_called]
        assert 'CreateExpressGatewayService' in operation_names
        # Note: DescribeExpressGatewayService calls happen via after-call events
        # which are not supported by the functional test framework

    def test_create_gateway_service_without_monitoring(self):
        # Setup mock response
        self.parsed_responses = [
            {
                "service": {
                    "serviceArn": "arn:aws:ecs:us-east-1:123456789:service/test-cluster/test-service",
                    "serviceName": "test-service",
                    "clusterArn": "arn:aws:ecs:us-east-1:123456789:cluster/test-cluster",
                    "status": "ACTIVE",
                }
            }
        ]

        # Execute command without monitoring flag (default behavior)
        cmdline = 'ecs create-express-gateway-service --service-name test-service --cluster test-cluster --execution-role-arn arn:aws:iam::123456789:role/exec --infrastructure-role-arn arn:aws:iam::123456789:role/infra --primary-container image=nginx'
        self.run_cmd(cmdline, expected_rc=0)

        # Verify only create operation was called (no monitoring)
        operation_names = [op[0].name for op in self.operations_called]
        assert 'CreateExpressGatewayService' in operation_names

    def test_update_gateway_service_with_monitoring(self):
        # Setup mock responses: only valid update response, no describe response
        self.parsed_responses = [
            # UpdateExpressGatewayService response
            {
                "service": {
                    "serviceArn": "arn:aws:ecs:us-east-1:123456789:service/test-cluster/test-service",
                    "serviceName": "test-service",
                    "status": "ACTIVE",
                }
            }
            # No DescribeExpressGatewayService response - will cause an error and monitoring to terminate
        ]

        # Execute command with monitoring enabled
        cmdline = 'ecs update-express-gateway-service --service-arn arn:aws:ecs:us-east-1:123456789:service/test-service --monitor-resources'

        self.run_cmd(cmdline, expected_rc=0)

        # Verify API calls were made (update + monitoring)
        operation_names = [op[0].name for op in self.operations_called]
        assert 'UpdateExpressGatewayService' in operation_names
        # Note: DescribeExpressGatewayService calls happen via after-call events
        # which are not supported by the functional test framework

    def test_delete_gateway_service_with_monitoring(self):
        # Setup mock responses: only valid delete response, no describe response
        self.parsed_responses = [
            # DeleteExpressGatewayService response
            {
                "service": {
                    "serviceArn": "arn:aws:ecs:us-east-1:123456789:service/test-cluster/test-service",
                    "serviceName": "test-service",
                    "status": "DRAINING",
                }
            }
            # No DescribeExpressGatewayService response - will cause an error and monitoring to terminate
        ]

        # Execute command with monitoring enabled
        cmdline = 'ecs delete-express-gateway-service --service-arn arn:aws:ecs:us-east-1:123456789:service/test-service --monitor-resources'

        self.run_cmd(cmdline, expected_rc=0)

        # Verify API calls were made (delete + monitoring)
        operation_names = [op[0].name for op in self.operations_called]
        assert 'DeleteExpressGatewayService' in operation_names
        # Note: DescribeExpressGatewayService calls happen via after-call events
        # which are not supported by the functional test framework

    def test_api_parameters_not_modified(self):
        # Setup mock response
        self.parsed_responses = [
            {
                "service": {
                    "serviceArn": "arn:aws:ecs:us-east-1:123456789:service/test-cluster/test-service",
                    "serviceName": "test-service",
                }
            }
        ]

        # Execute command with skip monitoring
        cmdline = 'ecs create-express-gateway-service --service-name test-service --cluster test-cluster --execution-role-arn arn:aws:iam::123456789:role/exec --infrastructure-role-arn arn:aws:iam::123456789:role/infra --primary-container image=nginx'
        self.run_cmd(cmdline, expected_rc=0)

        # Verify that monitor-resources parameter is not sent to the API
        request_body = json.loads(self.last_params)
        assert 'monitorResources' not in request_body
        assert 'monitor-resources' not in request_body

        # Verify normal parameters are present
        assert 'serviceName' in request_body
        assert 'cluster' in request_body

    def test_update_gateway_service_without_monitoring(self):
        # Setup mock response
        self.parsed_responses = [
            {
                "service": {
                    "serviceArn": "arn:aws:ecs:us-east-1:123456789:service/test-cluster/test-service",
                    "serviceName": "test-service",
                    "status": "ACTIVE",
                }
            }
        ]

        # Execute command without monitoring flag (default behavior)
        cmdline = 'ecs update-express-gateway-service --service-arn arn:aws:ecs:us-east-1:123456789:service/test-service'
        self.run_cmd(cmdline, expected_rc=0)

        # Verify only update operation was called (no monitoring)
        operation_names = [op[0].name for op in self.operations_called]
        assert 'UpdateExpressGatewayService' in operation_names

    def test_delete_gateway_service_without_monitoring(self):
        # Setup mock response
        self.parsed_responses = [
            {
                "service": {
                    "serviceArn": "arn:aws:ecs:us-east-1:123456789:service/test-cluster/test-service",
                    "serviceName": "test-service",
                    "status": "DRAINING",
                }
            }
        ]

        # Execute command without monitoring flag (default behavior)
        cmdline = 'ecs delete-express-gateway-service --service-arn arn:aws:ecs:us-east-1:123456789:service/test-service'
        self.run_cmd(cmdline, expected_rc=0)

        # Verify only delete operation was called (no monitoring)
        operation_names = [op[0].name for op in self.operations_called]
        assert 'DeleteExpressGatewayService' in operation_names
