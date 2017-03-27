# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import json
import shutil

from awscli.testutils import BaseAWSCommandParamsTest
from awscli.testutils import FileCreator


class TestDescribeVolumes(BaseAWSCommandParamsTest):

    prefix = 'ec2 describe-volumes'

    def setUp(self):
        super(TestDescribeVolumes, self).setUp()
        self.file_creator = FileCreator()

    def tearDown(self):
        super(TestDescribeVolumes, self).tearDown()
        shutil.rmtree(self.file_creator.rootdir)

    def test_max_results_set_by_default(self):
        command = self.prefix
        params = {'MaxResults': 1000}
        self.assert_params_for_cmd(command, params)

    def test_max_results_not_set_with_volume_ids(self):
        command = self.prefix + ' --volume-ids id-volume'
        params = {'VolumeIds': ['id-volume']}
        self.assert_params_for_cmd(command, params)

    def test_max_results_not_set_with_filter(self):
        command = self.prefix + ' --filters Name=volume-id,Values=id-volume'
        params = {'Filters': [{'Name': 'volume-id', 'Values': ['id-volume']}]}
        self.assert_params_for_cmd(command, params)

    def test_max_results_not_overwritten(self):
        command = self.prefix + ' --max-results 5'
        params = {'MaxResults': 5}
        self.assert_params_for_cmd(command, params)

        command = self.prefix + ' --page-size 5'
        self.assert_params_for_cmd(command, params)

    def test_max_results_with_cli_input_json(self):
        params = {'VolumeIds': ['vol-12345']}
        file_path = self.file_creator.create_file(
            'params.json', json.dumps(params))

        command = self.prefix + ' --cli-input-json file://%s' % file_path
        self.assert_params_for_cmd(command, params)
