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

INSTANCE_FLEETS_WITH_ON_DEMAND_MASTER_ONLY = (
    'InstanceFleetType=MASTER,TargetOnDemandCapacity=1,InstanceTypeConfigs=[{InstanceType=d2.xlarge}] ')

INSTANCE_FLEETS_WITH_SPOT_MASTER_ONLY = (
    'InstanceFleetType=MASTER,TargetSpotCapacity=1,InstanceTypeConfigs=[{InstanceType=d2.xlarge,BidPrice=0.1}],'
    'LaunchSpecifications={SpotSpecification={TimeoutDurationMinutes=20,TimeoutAction=TERMINATE_CLUSTER}}')

INSTANCE_FLEETS_WITH_SPOT_MASTER_ONLY_WITH_EBS_CONF = (
    'InstanceFleetType=MASTER,TargetSpotCapacity=1,InstanceTypeConfigs=[{InstanceType=d2.xlarge,BidPrice=0.1,'
    'EbsConfiguration={EbsOptimized=true,EbsBlockDeviceConfigs=[{VolumeSpecification={VolumeType=gp2,SizeInGB=100,'
    'Iops=100},VolumesPerInstance=4},{VolumeSpecification={VolumeType=gp2,SizeInGB=100,Iops=100}}]}}],'
    'LaunchSpecifications={SpotSpecification={TimeoutDurationMinutes=20,TimeoutAction=TERMINATE_CLUSTER}}')

INSTANCE_FLEETS_WITH_SPOT_MASTER_CORE_CLUSTER = (
    'InstanceFleetType=MASTER,TargetSpotCapacity=1,InstanceTypeConfigs=[{InstanceType=d2.xlarge,BidPrice=0.1}],'
    'LaunchSpecifications={SpotSpecification={TimeoutDurationMinutes=20,TimeoutAction=TERMINATE_CLUSTER}} '
    'InstanceFleetType=CORE,TargetSpotCapacity=100,InstanceTypeConfigs=[{InstanceType=d2.xlarge,BidPrice=0.5,'
    'WeightedCapacity=1},{InstanceType=m3.2xlarge,BidPrice=0.2,WeightedCapacity=2},{InstanceType=m3.4xlarge,BidPrice=0.4,'
    'WeightedCapacity=4}],LaunchSpecifications={SpotSpecification={TimeoutDurationMinutes=20,'
    'TimeoutAction=SWITCH_TO_ON_DEMAND,'
    'BlockDurationMinutes=120}}')

INSTANCE_FLEETS_WITH_MISSING_BID_PRICE_CONFIGS = (
    'InstanceFleetType=MASTER,TargetSpotCapacity=1,InstanceTypeConfigs=[{InstanceType=d2.xlarge}],'
    'LaunchSpecifications={SpotSpecification={TimeoutDurationMinutes=20,TimeoutAction=TERMINATE_CLUSTER}}')

RES_INSTANCE_FLEETS_WITH_ON_DEMAND_MASTER_ONLY = \
    [{"InstanceTypeConfigs": [{"InstanceType": "d2.xlarge"}],
      "TargetOnDemandCapacity": 1,
      "InstanceFleetType": "MASTER",
      "Name": "MASTER"
    }]

RES_INSTANCE_FLEETS_WITH_SPOT_MASTER_ONLY = \
    [{"InstanceTypeConfigs": [{"InstanceType": "d2.xlarge","BidPrice": "0.1"}],
      "LaunchSpecifications": {
         "SpotSpecification": {"TimeoutDurationMinutes": 20, "TimeoutAction": "TERMINATE_CLUSTER"}
      },
      "TargetSpotCapacity": 1,
      "InstanceFleetType": "MASTER",
      "Name": "MASTER"
    }]

RES_INSTANCE_FLEETS_WITH_SPOT_MASTER_ONLY_WITH_EBS_CONF = \
    [{"InstanceTypeConfigs": [{"InstanceType": "d2.xlarge","BidPrice": "0.1",
      "EbsConfiguration": {"EbsOptimized": True, "EbsBlockDeviceConfigs": [{"VolumeSpecification": {"Iops": 100,
      "SizeInGB": 100, "VolumeType": "gp2"},"VolumesPerInstance": 4}, {"VolumeSpecification": {"Iops": 100,
      "SizeInGB": 100, "VolumeType": "gp2"}}]}}],
      "LaunchSpecifications": {
          "SpotSpecification": {"TimeoutDurationMinutes": 20, "TimeoutAction": "TERMINATE_CLUSTER"}
      },
      "TargetSpotCapacity": 1,
      "InstanceFleetType": "MASTER",
      "Name": "MASTER"
    }]

RES_INSTANCE_FLEETS_WITH_SPOT_MASTER_CORE_CLUSTER = \
    [{"InstanceTypeConfigs": [{"InstanceType": "d2.xlarge","BidPrice": "0.1"}],
      "LaunchSpecifications": {
          "SpotSpecification": {"TimeoutDurationMinutes": 20, "TimeoutAction": "TERMINATE_CLUSTER"}
      },
      "TargetSpotCapacity": 1,
      "InstanceFleetType": "MASTER",
      "Name": "MASTER"
    },
    {"InstanceTypeConfigs": [{"InstanceType": "d2.xlarge","BidPrice": "0.5","WeightedCapacity": 1},
      {"InstanceType": "m3.2xlarge","BidPrice": "0.2","WeightedCapacity": 2},{"InstanceType": "m3.4xlarge","BidPrice": "0.4",
      "WeightedCapacity": 4}],
      "LaunchSpecifications" : {
          "SpotSpecification": {"TimeoutDurationMinutes": 20, "TimeoutAction": "SWITCH_TO_ON_DEMAND",
      "BlockDurationMinutes": 120}
      },
      "TargetSpotCapacity": 100,
      "InstanceFleetType": "CORE",
      "Name": "CORE"
    }]

RES_INSTANCE_FLEETS_WITH_COMPLEX_CONFIG_FROM_JSON= \
    [{"InstanceTypeConfigs": [{"EbsConfiguration": {"EbsOptimized": True,"EbsBlockDeviceConfigs": [{
      "VolumeSpecification": {"VolumeType": "gp2","SizeInGB": 100},"VolumesPerInstance": 2}]},"BidPrice": "1",
      "InstanceType": "m3.xlarge"}],
      "LaunchSpecifications": {
          "SpotSpecification": {"TimeoutDurationMinutes": 20,"TimeoutAction": "TERMINATE_CLUSTER"}
      },
      "Name": "master-fleet",
      "InstanceFleetType": "MASTER",
      "TargetSpotCapacity": 1},
      {"InstanceTypeConfigs": [{"WeightedCapacity": 1,"EbsConfiguration": {"EbsOptimized": True,"EbsBlockDeviceConfigs":
        [{"VolumeSpecification": {"VolumeType": "gp2","SizeInGB": 100},"VolumesPerInstance": 2}]},
        "BidPrice": "1","InstanceType": "m3.xlarge"},{"WeightedCapacity": 2,"EbsConfiguration": {"EbsOptimized": False,
        "EbsBlockDeviceConfigs": [{"VolumeSpecification": {"VolumeType": "gp2","SizeInGB": 100},"VolumesPerInstance": 2},
        {"VolumeSpecification": {"VolumeType": "gp2","SizeInGB": 500},"VolumesPerInstance": 1}]},"BidPrice": "1",
        "InstanceType": "m3.large"}],
      "LaunchSpecifications" :{
          "SpotSpecification": {"TimeoutDurationMinutes": 20,"TimeoutAction": "TERMINATE_CLUSTER"}
      },
      "Name": "core-fleet",
      "InstanceFleetType": "CORE",
      "TargetSpotCapacity": 10
    }]
