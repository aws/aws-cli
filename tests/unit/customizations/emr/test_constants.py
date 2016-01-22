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

INSTANCE_GROUPS_WITH_EBS_VOLUME_ARG = (
    ' InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge '
    'InstanceGroupType=CORE,InstanceType=m3.xlarge,InstanceCount=2,EbsConfiguration={EbsOptimized=true,VolumeSpecifications=[{VolumeType=gp2,SizeInGB=100,Iops=100},{VolumeType=gp2,SizeInGB=100,Iops=100}]}')

INSTANCE_GROUPS_WITH_EBS_VOLUME_MISSING_VOLTYPE_ARG = (
    ' InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge '
    'InstanceGroupType=CORE,InstanceType=m3.xlarge,InstanceCount=2,EbsConfiguration={EbsOptimized=true,VolumeSpecifications=[{SizeInGB=100,Iops=100},{VolumeType=gp2,SizeInGB=100,Iops=100}]}')

INSTANCE_GROUPS_WITH_EBS_VOLUME_MISSING_SIZE_ARG = (
    ' InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge '
    'InstanceGroupType=CORE,InstanceType=m3.xlarge,InstanceCount=2,EbsConfiguration={EbsOptimized=true,VolumeSpecifications=[{VolumeType=gp2,Iops=100},{VolumeType=gp2,SizeInGB=100,Iops=100}]}')

INSTANCE_GROUPS_WITH_EBS_VOLUME_MISSING_VOLSPEC_ARG = (
    ' InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge '
    'InstanceGroupType=CORE,InstanceType=m3.xlarge,InstanceCount=2,EbsConfiguration={EbsOptimized=true}')

INSTANCE_GROUPS_WITH_EBS_VOLUME_MISSING_IOPS_ARG = (
    ' InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge '
    'InstanceGroupType=CORE,InstanceType=m3.xlarge,InstanceCount=2,EbsConfiguration={EbsOptimized=true,VolumeSpecifications=[{VolumeType=gp2,SizeInGB=100}]}')

MULTIPLE_INSTANCE_GROUPS_WITH_EBS_VOLUMES_VOLUME_ARG = (
    ' InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m3.xlarge,EbsConfiguration={EbsOptimized=true,VolumeSpecifications=[{Iops=100,VolumeType=gp2,SizeInGB=20}]} '
    'InstanceGroupType=CORE,InstanceType=m3.xlarge,InstanceCount=2,EbsConfiguration={EbsOptimized=true,VolumeSpecifications=[{VolumeType=gp2,SizeInGB=100}]}')

INSTANCE_GROUPS_WITH_EBS = \
    [{'InstanceCount': 1,
      'InstanceRole': 'MASTER',
      'InstanceType': 'm3.xlarge',
      'Market': 'ON_DEMAND',
      'Name': 'MASTER'},
     {'EbsConfiguration': {'EbsOptimized': True,
                           'VolumeSpecifications': [{'Iops': 100,
                                                     'SizeInGB': 100,
                                                     'VolumeType': 'gp2'},
                                                    {'Iops': 100,
                                                     'SizeInGB': 100,
                                                     'VolumeType': 'gp2'}]},
      'InstanceCount': 2,
      'InstanceRole': 'CORE',
      'InstanceType': 'm3.xlarge',
      'Market': 'ON_DEMAND',
      'Name': 'CORE'}]

INSTANCE_GROUPS_WITH_EBS_VOLUME_MISSING_IOPS = \
    [{'InstanceCount': 1,
      'InstanceRole': 'MASTER',
      'InstanceType': 'm3.xlarge',
      'Market': 'ON_DEMAND',
      'Name': 'MASTER'},
     {'EbsConfiguration': {'EbsOptimized': True,
                           'VolumeSpecifications': [{'SizeInGB': 100,
                                                     'VolumeType': 'gp2'}]},
      'InstanceCount': 2,
      'InstanceRole': 'CORE',
      'InstanceType': 'm3.xlarge',
      'Market': 'ON_DEMAND',
      'Name': 'CORE'}]

INSTANCE_GROUPS_WITH_EBS_VOLUME_MISSING_VOLSPEC = \
    [{'InstanceCount': 1,
      'InstanceRole': 'MASTER',
      'InstanceType': 'm3.xlarge',
      'Market': 'ON_DEMAND',
      'Name': 'MASTER'},
     {'EbsConfiguration': {'EbsOptimized': True},
      'InstanceCount': 2,
      'InstanceRole': 'CORE',
      'InstanceType': 'm3.xlarge',
      'Market': 'ON_DEMAND',
      'Name': 'CORE'}]

MULTIPLE_INSTANCE_GROUPS_WITH_EBS_VOLUMES = \
    [{'EbsConfiguration': {'EbsOptimized': True,
                           'VolumeSpecifications': [{'Iops': 100,
                                                     'SizeInGB': 20,
                                                     'VolumeType': 'gp2'}]},
      'InstanceCount': 1,
      'InstanceRole': 'MASTER',
      'InstanceType': 'm3.xlarge',
      'Market': 'ON_DEMAND',
      'Name': 'MASTER'},
     {'EbsConfiguration': {'EbsOptimized': True,
                           'VolumeSpecifications': [{'SizeInGB': 100,
                                                     'VolumeType': 'gp2'}]},
      'InstanceCount': 2,
      'InstanceRole': 'CORE',
      'InstanceType': 'm3.xlarge',
      'Market': 'ON_DEMAND',
      'Name': 'CORE'}]
