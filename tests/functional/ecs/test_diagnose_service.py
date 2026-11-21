# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
"""Functional tests for ``aws ecs diagnose-service``.

These drive the command through the real CLI command table (so they also assert
the verb is registered alongside the existing ``ecs deploy`` et al.) with
scripted botocore responses, and verify that only read operations are ever
issued and that exit codes follow the shared convention.
"""

import json

from awscli.testutils import BaseAWSCommandParamsTest

# Operations that would create, modify or delete state across the four services
# this command touches. It must never issue any of these.
_MUTATING = {
    'UpdateService',
    'CreateService',
    'DeleteService',
    'RegisterTaskDefinition',
    'RunTask',
    'StopTask',
    'AttachRolePolicy',
    'PutRetentionPolicy',
    'RegisterTargets',
}

_TASK_DEF_ARN = 'arn:aws:ecs:us-east-1:111122223333:task-definition/web:5'


class TestDiagnoseServiceCommand(BaseAWSCommandParamsTest):
    def _healthy_responses(self):
        return [
            # 1. DescribeServices (gating) -> one ACTIVE service, no LB.
            {
                'services': [
                    {
                        'serviceName': 'web',
                        'status': 'ACTIVE',
                        'desiredCount': 1,
                        'runningCount': 1,
                        'pendingCount': 0,
                        'launchType': 'FARGATE',
                        'taskDefinition': _TASK_DEF_ARN,
                        'deployments': [
                            {
                                'id': 'ecs-svc/1',
                                'status': 'PRIMARY',
                                'rolloutState': 'COMPLETED',
                            }
                        ],
                        'events': [{'message': 'steady state'}],
                        'loadBalancers': [],
                    }
                ],
                'failures': [],
            },
            # 2. DescribeTaskDefinition (execution role present).
            {
                'taskDefinition': {
                    'family': 'web',
                    'revision': 5,
                    'taskDefinitionArn': _TASK_DEF_ARN,
                    'executionRoleArn': (
                        'arn:aws:iam::111122223333:role/ecsTaskExecutionRole'
                    ),
                    'containerDefinitions': [
                        {'name': 'web', 'image': 'web:1'}
                    ],
                }
            },
            # 3. IAM: execution role has an attached policy.
            {'AttachedPolicies': [{'PolicyName': 'exec'}]},
            {'PolicyNames': []},
            # 4. ListTasks STOPPED (none).
            {'taskArns': []},
            # 5. ListTasks RUNNING (none).
            {'taskArns': []},
        ]

    def test_runs_read_only_and_reports_healthy(self):
        self.parsed_responses = self._healthy_responses()
        stdout, _, rc = self.run_cmd(
            [
                'ecs',
                'diagnose-service',
                '--service',
                'web',
                '--cluster',
                'prod',
                '--no-logs',
                '--region',
                'us-east-1',
            ],
            expected_rc=0,
        )
        names = [c[0].name for c in self.operations_called]
        # The gating read runs first; no mutating operation is ever issued.
        self.assertEqual(names[0], 'DescribeServices')
        self.assertFalse(_MUTATING.intersection(names))
        parsed = json.loads(stdout)
        self.assertTrue(parsed['healthy'])
        self.assertEqual(parsed['blockers'], [])
        self.assertEqual(parsed['service_summary']['running_count'], 1)

    def test_missing_service_is_operational_error(self):
        # No --cluster, so the command first scans ListClusters to find the
        # owning cluster; none found -> falls back to "default", where
        # DescribeServices returns no services -> NOT_FOUND -> rc 255.
        self.parsed_responses = [
            {'clusterArns': []},
            {'services': [], 'failures': [{'reason': 'MISSING'}]},
        ]
        _, stderr, rc = self.run_cmd(
            [
                'ecs',
                'diagnose-service',
                '--service',
                'ghost',
                '--region',
                'us-east-1',
            ],
            expected_rc=255,
        )
        self.assertIn('NOT_FOUND', stderr)
        names = [c[0].name for c in self.operations_called]
        # Only cluster discovery and the gating read were attempted.
        self.assertEqual(names, ['ListClusters', 'DescribeServices'])

    def test_no_service_arg_runs_triage_mode(self):
        # --service is optional: without it the command triages every
        # cluster. With no clusters it reports an empty, exhaustive triage.
        self.parsed_responses = [{'clusterArns': []}]
        stdout, _, rc = self.run_cmd(
            ['ecs', 'diagnose-service', '--region', 'us-east-1'],
            expected_rc=0,
        )
        names = [c[0].name for c in self.operations_called]
        self.assertEqual(names, ['ListClusters'])
        parsed = json.loads(stdout)
        self.assertEqual(parsed['mode'], 'triage')
        self.assertEqual(parsed['clusters_scanned'], 0)
        self.assertEqual(parsed['unhealthy'], [])
