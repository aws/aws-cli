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

from unittest.mock import Mock

from awscli.agentmode import AgentModeDriver


class TestAgentModeDriver:
    def setup_method(self):
        self.session = Mock()
        self.driver = AgentModeDriver(self.session)

    def test_should_enter_agent_mode_true(self):
        """Test should_enter_agent_mode when agent mode is requested"""
        args = ['--agent-mode']
        result = self.driver.should_enter_agent_mode(args)
        assert result

    def test_should_enter_agent_mode_false(self):
        """Test should_enter_agent_mode when agent mode is not requested"""
        args = ['--region', 'us-west-2']
        result = self.driver.should_enter_agent_mode(args)
        assert not result
