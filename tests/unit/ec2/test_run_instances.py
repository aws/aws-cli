#!/usr/bin/env python
# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from tests import BaseCLIDriverTest
import awscli.clidriver


class TestDescribeInstances(BaseCLIDriverTest):

    prefix = 'aws ec2 run-instances'

    def test_block_device_mapping(self):
        args = ' --image-id ami-foobar --min-count 1 --max-count 1'
        args_list = (self.prefix + args).split()
        # We're switching to list form because we need to test
        # when there's leading spaces.  This is the CLI equivalent
        # of --block-dev-mapping ' [{"device_name" ...'
        # (note the space between ``'`` and ``[``)
        args_list.append('--block-device-mapping')
        args_list.append(
            ' [{"device_name":"/dev/sda1","ebs":{"volume_size":20}}]')
        result = {
            'BlockDeviceMapping.1.DeviceName': '/dev/sda1',
            'BlockDeviceMapping.1.Ebs.VolumeSize': '20',
            'ImageId': 'ami-foobar',
            'MaxCount': '1',
            'MinCount': '1'
        }
        params = self.driver.test(args_list)
        self.assertEqual(params, result)


if __name__ == "__main__":
    unittest.main()
