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
from awscli.customizations.emr import exceptions


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
            if instance_group['BidPrice'] != 'OnDemandPrice':
                ig_config['BidPrice'] = instance_group['BidPrice']
            ig_config['Market'] = constants.SPOT
        else:
            ig_config['Market'] = constants.ON_DEMAND
        if 'EbsConfiguration' in keys:
            ig_config['EbsConfiguration'] = instance_group['EbsConfiguration']

        if 'AutoScalingPolicy' in keys:
            ig_config['AutoScalingPolicy'] = instance_group['AutoScalingPolicy']

        if 'Configurations' in keys:
            ig_config['Configurations'] = instance_group['Configurations']

        if 'CustomAmiId' in keys:
            ig_config['CustomAmiId'] = instance_group['CustomAmiId']

        instance_groups.append(ig_config)
    return instance_groups


def _build_instance_group(
        instance_type, instance_count, instance_group_type):
    ig_config = {}
    ig_config['InstanceType'] = instance_type
    ig_config['InstanceCount'] = instance_count
    ig_config['InstanceRole'] = instance_group_type.upper()
    ig_config['Name'] = ig_config['InstanceRole']
    ig_config['Market'] = constants.ON_DEMAND
    return ig_config


def validate_and_build_instance_groups(
        instance_groups, instance_type, instance_count):
    if (instance_groups is None and instance_type is None):
        raise exceptions.MissingRequiredInstanceGroupsError

    if (instance_groups is not None and
        (instance_type is not None or
            instance_count is not None)):
        raise exceptions.InstanceGroupsValidationError

    if instance_groups is not None:
        return build_instance_groups(instance_groups)
    else:
        instance_groups = []
        master_ig = _build_instance_group(
            instance_type=instance_type,
            instance_count=1,
            instance_group_type="MASTER")
        instance_groups.append(master_ig)
        if instance_count is not None and int(instance_count) > 1:
            core_ig = _build_instance_group(
                instance_type=instance_type,
                instance_count=int(instance_count) - 1,
                instance_group_type="CORE")
            instance_groups.append(core_ig)

        return instance_groups
