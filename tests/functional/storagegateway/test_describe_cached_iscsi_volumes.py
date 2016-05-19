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
from awscli.testutils import BaseAWSCommandParamsTest


class TestDescribeCachedISCSIVolumes(BaseAWSCommandParamsTest):

    PREFIX = 'storagegateway describe-cached-iscsi-volumes'
    VOLUME_ARN = 'a' * 50

    def test_accepts_old_argname(self):
        cmdline = (self.PREFIX + '  --volume-ar-ns %s') % (self.VOLUME_ARN,)
        params = {
            'VolumeARNs': [self.VOLUME_ARN],
        }
        self.assert_params_for_cmd(cmdline, params)

    def test_accepts_fixed_param_name(self):
        cmdline = (self.PREFIX + '  --volume-arns %s') % (self.VOLUME_ARN,)
        params = {
            'VolumeARNs': [self.VOLUME_ARN],
        }
        self.assert_params_for_cmd(cmdline, params)
