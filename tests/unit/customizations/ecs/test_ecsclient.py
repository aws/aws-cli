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

import mock

from argparse import Namespace
from botocore import config
from awscli.testutils import capture_output, unittest
from awscli.customizations.ecs.deploy import ECSClient, ECSDeploy


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
            self.session, None, self.global_args, ECSDeploy.USER_AGENT_EXTRA)

        expected_user_agent_extra = 'customization/ecs-deploy'

        create_args = self.session.create_client.call_args
        self.assertEquals(create_args[0][0], 'ecs')
        self.assertEquals(
            create_args[1]['region_name'], self.global_args.region)
        self.assertEquals(create_args[1]['config'].user_agent_extra,
                          expected_user_agent_extra)
