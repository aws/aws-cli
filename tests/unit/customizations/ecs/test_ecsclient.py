# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from argparse import Namespace

from botocore import config

from awscli.customizations.ecs.deploy import ECSClient, ECSDeploy
from awscli.testutils import capture_output, mock, unittest


class TestECSClient(unittest.TestCase):
    def setUp(self):
        ecs_client = mock.Mock()
        self.session = mock.Mock()
        self.session.create_client.side_effect = ecs_client

        # set global args
        self.global_args = Namespace()
        self.global_args.region = 'us-east-1'
        self.global_args.endpoint_url = None
        self.global_args.verify_ssl = None

    def test_client_config(self):
        self.test_client = ECSClient(
            self.session, None, self.global_args, ECSDeploy.USER_AGENT_EXTRA
        )

        expected_user_agent_extra = 'md/customization#ecs-deploy'

        create_args = self.session.create_client.call_args
        self.assertEqual(create_args[0][0], 'ecs')
        self.assertEqual(
            create_args[1]['region_name'], self.global_args.region
        )
        self.assertEqual(
            create_args[1]['config'].user_agent_extra,
            expected_user_agent_extra,
        )

    def _get_service_details_with_cluster(self, cluster):
        args = Namespace(cluster=cluster, service='my-service')
        test_client = ECSClient(
            self.session, args, self.global_args, ECSDeploy.USER_AGENT_EXTRA
        )
        test_client._client = mock.Mock()
        test_client._client.describe_services.return_value = {
            'services': [
                {
                    'serviceArn': (
                        'arn:aws:ecs:us-east-1:123456789012:service/my-service'
                    ),
                    'serviceName': 'my-service',
                    'clusterArn': (
                        'arn:aws:ecs:us-east-1:123456789012:cluster/default'
                    ),
                }
            ]
        }
        test_client.get_service_details()
        return test_client._client.describe_services.call_args[1]['cluster']

    def test_get_service_details_defaults_cluster_when_not_specified(self):
        used_cluster = self._get_service_details_with_cluster(None)
        self.assertEqual(used_cluster, 'default')

    def test_get_service_details_defaults_cluster_when_empty_string(self):
        # A caller may pass an empty string for --cluster (e.g. by
        # interpolating an unset shell variable), which should be treated
        # the same as not specifying a cluster at all.
        used_cluster = self._get_service_details_with_cluster('')
        self.assertEqual(used_cluster, 'default')

    def test_get_service_details_uses_specified_cluster(self):
        used_cluster = self._get_service_details_with_cluster('my-cluster')
        self.assertEqual(used_cluster, 'my-cluster')
