# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from awscli.customizations.emr import exceptions
from awscli.customizations.emr.configutils import ConfigWriter
from awscli.testutils import BaseAWSCommandParamsTest
import mock


class EMRBaseAWSCommandParamsTest(BaseAWSCommandParamsTest):

    def setUp(self):
        super(EMRBaseAWSCommandParamsTest, self).setUp()

        # Do not use any emr-specific configs for the test cases
        self.get_scoped_config_mock = mock.Mock()
        self.set_configs({})

        # Do not write or update the config (~/.aws/config) file
        self.patcher_update_config = mock.patch(
            'awscli.customizations.emr.configutils.ConfigWriter.update_config')
        self.mock_update_config = self.patcher_update_config.start()

    def set_configs(self, configs):
        self.driver.session.get_scoped_config = self.get_scoped_config_mock
        self.get_scoped_config_mock.return_value = {'emr': configs}

    def tearDown(self):
        super(EMRBaseAWSCommandParamsTest, self).tearDown()
        self.patcher_update_config.stop()

    def assert_error_msg(self, cmd,
                         exception_class_name, error_msg_kwargs={}, rc=255):
        exception_class = getattr(exceptions, exception_class_name)
        error_msg = "\n%s\n" % exception_class.fmt.format(**error_msg_kwargs)
        result = self.run_cmd(cmd, rc)
        self.assertEquals(error_msg, result[1])
