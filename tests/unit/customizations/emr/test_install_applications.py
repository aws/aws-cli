#!/usr/bin/env python
# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from tests.unit import BaseAWSCommandParamsTest
from nose.tools import raises


class TestInstallApplications(BaseAWSCommandParamsTest):
    prefix = 'emr install-applications'
    SCRIPT_RUNNER_JAR = 's3://elasticmapreduce/libs/script-runner/'\
                        'script-runner.jar'

    HIVE_BASE = 's3://elasticmapreduce/libs/hive'
    HIVE_SCRIPT = 's3://elasticmapreduce/libs/hive/hive-script'
    HIVE_STEP = {'ActionOnFailure': 'CANCEL_AND_WAIT', 'Name': 'Install Hive',
                 'HadoopJarStep': {'Jar': SCRIPT_RUNNER_JAR, 'Args': [
                     HIVE_SCRIPT, '--install-hive', '--base-path', HIVE_BASE,
                     '--hive-versions', '999']}}

    PIG_BASE = 's3://elasticmapreduce/libs/pig'
    PIG_SCRIPT = 's3://elasticmapreduce/libs/pig/pig-script'
    PIG_STEP = {'ActionOnFailure': 'CANCEL_AND_WAIT', 'Name': 'Install Pig',
                'HadoopJarStep': {'Jar': SCRIPT_RUNNER_JAR, 'Args': [
                    PIG_SCRIPT, '--install-pig', '--base-path', PIG_BASE,
                    '--pig-versions', '111']}}

    @raises(Exception)
    def test_no_step(self):
        args = ' --cluster-id j-ABC123456'
        cmdline = self.prefix + args
        result = {'JobFlowId': 'j-ABC123456', 'Steps': []}
        self.assert_params_for_cmd(cmdline, result)

    def test_intall_hive(self):
        args = ' --cluster-id j-ABC123456 --hive Version=999'
        cmdline = self.prefix + args
        result = {'JobFlowId': 'j-ABC123456', 'Steps': [self.HIVE_STEP]}
        self.assert_params_for_cmd(cmdline, result)

    def test_intall_pig(self):
        args = ' --cluster-id j-ABC123456 --pig Version=111'
        cmdline = self.prefix + args
        result = {'JobFlowId': 'j-ABC123456', 'Steps': [self.PIG_STEP]}
        self.assert_params_for_cmd(cmdline, result)

    def test_intall_hive_and_pig(self):
        args = ' --cluster-id j-ABC123456 --hive Version=999'\
               ' --pig Version=111'
        cmdline = self.prefix + args
        result = {'JobFlowId': 'j-ABC123456', 'Steps': [self.HIVE_STEP,
                                                        self.PIG_STEP]}
        self.assert_params_for_cmd(cmdline, result)

    @raises(Exception)
    def test_hive_version_missing(self):
        args = ' --cluster-id j-ABC123456 --hive v=1'
        cmdline = self.prefix + args
        self.run_cmd(cmdline)

    @raises(Exception)
    def test_pig_version_missing(self):
        args = ' --cluster-id j-ABC123456 --hive version=1 --pig v=1'
        cmdline = self.prefix + args
        self.run_cmd(cmdline)

    @raises(Exception)
    def test_invalid_format(self):
        args = ' --cluster-id j-ABC123456 --hive version1'
        cmdline = self.prefix + args
        self.run_cmd(cmdline)


if __name__ == "__main__":
    unittest.main()
