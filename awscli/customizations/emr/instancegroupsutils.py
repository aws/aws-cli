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

from awscli.customizations.emr import constants


def build_instance_groups(parsed_instance_groups):
    """
    Helper method that converts --instance-groups option value in
    create-cluster and add-instance-groups to
    Amazon Elastic MapReduce InstanceGroupConfig data type.
    """
    instance_groups = []
    for instance_group in parsed_instance_groups:
        ig_config = {}
        keys = instance_group.keys()
        if 'Name' in keys:
            ig_config['Name'] = instance_group['Name']
        else:
            ig_config['Name'] = instance_group['InstanceGroupType']
        ig_config['InstanceType'] = instance_group['InstanceType']
        ig_config['InstanceCount'] = instance_group['InstanceCount']
        ig_config['InstanceRole'] = instance_group['InstanceGroupType'].upper()

        if 'BidPrice' in keys:
            ig_config['BidPrice'] = instance_group['BidPrice']
            ig_config['Market'] = constants.SPOT
        else:
            ig_config['Market'] = constants.ON_DEMAND
        instance_groups.append(ig_config)

    return instance_groups