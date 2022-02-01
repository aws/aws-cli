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


def validate_and_build_instance_fleets(parsed_instance_fleets):
    """
    Helper method that converts --instance-fleets option value in
    create-cluster to Amazon Elastic MapReduce InstanceFleetConfig
    data type.
    """
    instance_fleets = []
    for instance_fleet in parsed_instance_fleets:
        instance_fleet_config = {}

        keys = instance_fleet.keys()

        if 'Name' in keys:
            instance_fleet_config['Name'] = instance_fleet['Name']
        else:
            instance_fleet_config['Name'] = instance_fleet['InstanceFleetType']
        instance_fleet_config['InstanceFleetType'] = instance_fleet['InstanceFleetType']

        if 'TargetOnDemandCapacity' in keys:
            instance_fleet_config['TargetOnDemandCapacity'] = instance_fleet['TargetOnDemandCapacity']

        if 'TargetSpotCapacity' in keys:
            instance_fleet_config['TargetSpotCapacity'] = instance_fleet['TargetSpotCapacity']

        if 'InstanceTypeConfigs' in keys:
            if 'TargetSpotCapacity' in keys:
                for instance_type_config in instance_fleet['InstanceTypeConfigs']:
                    instance_type_config_keys = instance_type_config.keys()
            instance_fleet_config['InstanceTypeConfigs'] = instance_fleet['InstanceTypeConfigs']

        if 'LaunchSpecifications' in keys:
            instanceFleetProvisioningSpecifications = instance_fleet['LaunchSpecifications']
            instance_fleet_config['LaunchSpecifications'] = {}

            if 'SpotSpecification' in instanceFleetProvisioningSpecifications:
                instance_fleet_config['LaunchSpecifications']['SpotSpecification'] = \
                    instanceFleetProvisioningSpecifications['SpotSpecification']

            if 'OnDemandSpecification' in instanceFleetProvisioningSpecifications:
                instance_fleet_config['LaunchSpecifications']['OnDemandSpecification'] = \
                    instanceFleetProvisioningSpecifications['OnDemandSpecification']

        instance_fleets.append(instance_fleet_config)
    return instance_fleets
