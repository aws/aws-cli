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

DEFAULT_INSTANCE_FLEET_NAME = "if-XYZ123"
DEFAULT_CLUSTER_NAME = "j-ABC123456"

INSTANCE_FLEETS_WITH_ON_DEMAND_MASTER_ONLY = (
    'InstanceFleetType=MASTER,TargetOnDemandCapacity=1,InstanceTypeConfigs=[{InstanceType=d2.xlarge}],'
    'LaunchSpecifications={OnDemandSpecification={AllocationStrategy=lowest-price,'
    'CapacityReservationOptions={UsageStrategy=use-capacity-reservations-first,CapacityReservationPreference=open}}},'
    'ResizeSpecifications={OnDemandResizeSpecification={TimeoutDurationMinutes=10}}')

INSTANCE_FLEETS_WITH_ON_DEMAND_MASTER_ONLY_WITH_TARGETED_ODCR = (
    'InstanceFleetType=MASTER,TargetOnDemandCapacity=1,InstanceTypeConfigs=[{InstanceType=d2.xlarge}],'
    'LaunchSpecifications={OnDemandSpecification={AllocationStrategy=lowest-price,'
    'CapacityReservationOptions={UsageStrategy=use-capacity-reservations-first,CapacityReservationResourceGroupArn=arn:aws:resource-groups:us-east-1:123456789012:group/Test}}}')

INSTANCE_FLEETS_WITH_SPOT_MASTER_ONLY = (
    'InstanceFleetType=MASTER,TargetSpotCapacity=1,InstanceTypeConfigs=[{InstanceType=d2.xlarge,BidPrice=0.1}],'
    'LaunchSpecifications={SpotSpecification={TimeoutDurationMinutes=20,TimeoutAction=TERMINATE_CLUSTER,AllocationStrategy=capacity-optimized}},'
    'ResizeSpecifications={SpotResizeSpecification={TimeoutDurationMinutes=10}}')

INSTANCE_FLEETS_WITH_SPOT_MASTER_ONLY_WITH_EBS_CONF = (
    'InstanceFleetType=MASTER,TargetSpotCapacity=1,InstanceTypeConfigs=[{InstanceType=d2.xlarge,BidPrice=0.1,'
    'EbsConfiguration={EbsOptimized=true,EbsBlockDeviceConfigs=[{VolumeSpecification={VolumeType=gp2,SizeInGB=100,'
    'Iops=100},VolumesPerInstance=4},{VolumeSpecification={VolumeType=gp2,SizeInGB=100,Iops=100}}]}}],'
    'LaunchSpecifications={SpotSpecification={TimeoutDurationMinutes=20,TimeoutAction=TERMINATE_CLUSTER,AllocationStrategy=capacity-optimized}}')

INSTANCE_FLEETS_WITH_SPOT_MASTER_CORE_CLUSTER = (
    'InstanceFleetType=MASTER,TargetSpotCapacity=1,InstanceTypeConfigs=[{InstanceType=d2.xlarge,BidPrice=0.1}],'
    'LaunchSpecifications={SpotSpecification={TimeoutDurationMinutes=20,TimeoutAction=TERMINATE_CLUSTER}},'
    'ResizeSpecifications={SpotResizeSpecification={TimeoutDurationMinutes=10}} '
    'InstanceFleetType=CORE,TargetSpotCapacity=100,InstanceTypeConfigs=[{InstanceType=d2.xlarge,BidPrice=0.5,'
    'WeightedCapacity=1},{InstanceType=m3.2xlarge,BidPrice=0.2,WeightedCapacity=2},{InstanceType=m3.4xlarge,BidPrice=0.4,'
    'WeightedCapacity=4}],LaunchSpecifications={SpotSpecification={TimeoutDurationMinutes=20,'
    'TimeoutAction=SWITCH_TO_ON_DEMAND,'
    'BlockDurationMinutes=120}},'
    'ResizeSpecifications={OnDemandResizeSpecification={TimeoutDurationMinutes=20},SpotResizeSpecification={TimeoutDurationMinutes=30}}')

INSTANCE_FLEETS_WITH_SPOT_MASTER_CORE_CLUSTER_WITH_CUSTOM_AMI = (
    'InstanceFleetType=MASTER,TargetSpotCapacity=1,InstanceTypeConfigs=[{InstanceType=d2.xlarge,BidPrice=0.1,CustomAmiId=ami-deadbeef}],'
    'LaunchSpecifications={SpotSpecification={TimeoutDurationMinutes=20,TimeoutAction=TERMINATE_CLUSTER}} '
    'InstanceFleetType=CORE,TargetSpotCapacity=100,InstanceTypeConfigs=[{InstanceType=d2.xlarge,BidPrice=0.5,'
    'WeightedCapacity=1,CustomAmiId=ami-deadbeef},{InstanceType=m3.2xlarge,BidPrice=0.2,WeightedCapacity=2,CustomAmiId=ami-deadpork},{InstanceType=m3.4xlarge,BidPrice=0.4,'
    'WeightedCapacity=4,CustomAmiId=ami-deadpork}],LaunchSpecifications={SpotSpecification={TimeoutDurationMinutes=20,'
    'TimeoutAction=SWITCH_TO_ON_DEMAND,'
    'BlockDurationMinutes=120}}')

INSTANCE_FLEETS_WITH_MISSING_BID_PRICE_CONFIGS = (
    'InstanceFleetType=MASTER,TargetSpotCapacity=1,InstanceTypeConfigs=[{InstanceType=d2.xlarge}],'
    'LaunchSpecifications={SpotSpecification={TimeoutDurationMinutes=20,TimeoutAction=TERMINATE_CLUSTER}}')

INSTANCE_FLEETS_WITH_SPOT_ALLOCATION_STRATEGY = (
    'InstanceFleetType=MASTER,TargetSpotCapacity=1,InstanceTypeConfigs=[{InstanceType=d2.xlarge,BidPrice=0.1}],'
    'LaunchSpecifications={SpotSpecification={TimeoutDurationMinutes=20,TimeoutAction=TERMINATE_CLUSTER,AllocationStrategy=price-capacity-optimized}} '
    'InstanceFleetType=CORE,TargetSpotCapacity=100,InstanceTypeConfigs=[{InstanceType=d2.xlarge,BidPrice=0.5,'
    'WeightedCapacity=1},{InstanceType=m3.2xlarge,BidPrice=0.2,WeightedCapacity=2},{InstanceType=m3.4xlarge,BidPrice=0.4,'
    'WeightedCapacity=4}],LaunchSpecifications={SpotSpecification={TimeoutDurationMinutes=20,'
    'TimeoutAction=TERMINATE_CLUSTER,AllocationStrategy=lowest-price}} '
    'InstanceFleetType=TASK,TargetSpotCapacity=100,InstanceTypeConfigs=[{InstanceType=d2.xlarge,BidPrice=0.5,'
    'WeightedCapacity=1},{InstanceType=m3.2xlarge,BidPrice=0.2,WeightedCapacity=2},{InstanceType=m3.4xlarge,BidPrice=0.4,'
    'WeightedCapacity=4}],LaunchSpecifications={SpotSpecification={TimeoutDurationMinutes=20,'
    'TimeoutAction=TERMINATE_CLUSTER,AllocationStrategy=diversified}}')

INSTANCE_FLEETS_WITH_PRIORITIZED_ALLOCATION_STRATEGY_SPOT_AND_OD = (
    'InstanceFleetType=MASTER,TargetSpotCapacity=1,InstanceTypeConfigs=[{InstanceType=d2.xlarge,'
    'BidPrice=0.1,Priority=0.0}],LaunchSpecifications={SpotSpecification={TimeoutDurationMinutes=30,'
    'TimeoutAction=TERMINATE_CLUSTER,AllocationStrategy=capacity-optimized-prioritized},'
    'OnDemandSpecification={AllocationStrategy=prioritized}} '
    'InstanceFleetType=CORE,TargetSpotCapacity=100,InstanceTypeConfigs=[{InstanceType=d2.xlarge,'
    'BidPrice=0.5,WeightedCapacity=1,Priority=0.0},{InstanceType=m3.2xlarge,BidPrice=0.2,'
    'WeightedCapacity=2,Priority=1.0},{InstanceType=m3.4xlarge,BidPrice=0.4,WeightedCapacity=4,'
    'Priority=99.0}],LaunchSpecifications={SpotSpecification={TimeoutDurationMinutes=32,'
    'TimeoutAction=TERMINATE_CLUSTER,AllocationStrategy=capacity-optimized-prioritized},'
    'OnDemandSpecification={AllocationStrategy=prioritized}} '
    'InstanceFleetType=TASK,TargetSpotCapacity=100,InstanceTypeConfigs=[{InstanceType=d2.xlarge,'
    'BidPrice=0.5,WeightedCapacity=1,Priority=10.0},{InstanceType=m3.2xlarge,BidPrice=0.2,'
    'WeightedCapacity=2,Priority=0.0},{InstanceType=m3.4xlarge,BidPrice=0.4,WeightedCapacity=4,'
    'Priority=100.0}],LaunchSpecifications={SpotSpecification={TimeoutDurationMinutes=77,'
    'TimeoutAction=TERMINATE_CLUSTER,AllocationStrategy='
    'capacity-optimized-prioritized},OnDemandSpecification={AllocationStrategy=prioritized}}')

TASK_INSTANCE_FLEET_WITH_RESIZE_ALLOCATION_STRATEGY_SPOT_AND_OD = (
    'InstanceFleetType=TASK,TargetSpotCapacity=100,Context=testContext,InstanceTypeConfigs=[{InstanceType=d2.xlarge,'
    'BidPrice=0.5,WeightedCapacity=1},{InstanceType=m3.2xlarge,BidPrice=0.2,WeightedCapacity=2},'
    '{InstanceType=m3.4xlarge,BidPrice=0.4,WeightedCapacity=4}],LaunchSpecifications={'
    'SpotSpecification={TimeoutDurationMinutes=77,TimeoutAction=TERMINATE_CLUSTER,'
    'AllocationStrategy=capacity-optimized-prioritized},OnDemandSpecification={'
    'AllocationStrategy=lowest-price}},ResizeSpecifications={SpotResizeSpecification={'
    'AllocationStrategy=capacity-optimized},OnDemandResizeSpecification={'
    'AllocationStrategy=lowest-price,CapacityReservationOptions={'
    'UsageStrategy=use-capacity-reservations-first,CapacityReservationPreference=open}}}')

INSTANCE_FLEETS_WITH_RESIZE_ALLOCATION_STRATEGY_SPOT_AND_OD = (
    'InstanceFleetType=MASTER,TargetSpotCapacity=1,InstanceTypeConfigs=[{InstanceType=d2.xlarge,'
    'BidPrice=0.1}],LaunchSpecifications={SpotSpecification={TimeoutDurationMinutes=30,'
    'TimeoutAction=TERMINATE_CLUSTER,AllocationStrategy=capacity-optimized-prioritized},'
    'OnDemandSpecification={AllocationStrategy=lowest-price}} '
    'InstanceFleetType=CORE,TargetSpotCapacity=100,InstanceTypeConfigs=[{InstanceType=d2.xlarge,'
    'BidPrice=0.5,WeightedCapacity=1},{InstanceType=m3.2xlarge,BidPrice=0.2,WeightedCapacity=2},'
    '{InstanceType=m3.4xlarge,BidPrice=0.4,WeightedCapacity=4}],LaunchSpecifications={'
    'SpotSpecification={TimeoutDurationMinutes=32,TimeoutAction=TERMINATE_CLUSTER,'
    'AllocationStrategy=capacity-optimized-prioritized},OnDemandSpecification={'
    'AllocationStrategy=lowest-price}},ResizeSpecifications={SpotResizeSpecification='
    '{AllocationStrategy=capacity-optimized},OnDemandResizeSpecification={'
    'AllocationStrategy=lowest-price,CapacityReservationOptions={'
    'UsageStrategy=use-capacity-reservations-first,CapacityReservationPreference=open}}} '
    f'{TASK_INSTANCE_FLEET_WITH_RESIZE_ALLOCATION_STRATEGY_SPOT_AND_OD}')

MODIFY_INSTANCE_FLEET_WITH_INSTANCE_TYPE_CONFIGS = (
    f'InstanceFleetId={DEFAULT_INSTANCE_FLEET_NAME},'
    f'InstanceTypeConfigs=[{{InstanceType=d2.xlarge}}],Context=testContext')

MODIFY_INSTANCE_FLEET_WITH_SPOT_AND_OD_RESIZE_SPECIFICATIONS = (
    f'InstanceFleetId={DEFAULT_INSTANCE_FLEET_NAME},ResizeSpecifications={{SpotResizeSpecification='
    f'{{AllocationStrategy=capacity-optimized}},OnDemandResizeSpecification={{'
    f'AllocationStrategy=lowest-price,CapacityReservationOptions={{'
    f'UsageStrategy=use-capacity-reservations-first,CapacityReservationPreference=open}}}}}}')

MODIFY_INSTANCE_FLEET_WITH_INSTANCE_TYPE_CONFIGS_AND_SPOT_AND_OD_RESIZE_SPECIFICATIONS = (
    f'InstanceFleetId={DEFAULT_INSTANCE_FLEET_NAME},ResizeSpecifications={{SpotResizeSpecification='
    f'{{AllocationStrategy=capacity-optimized}},OnDemandResizeSpecification={{'
    f'AllocationStrategy=lowest-price,CapacityReservationOptions={{'
    f'UsageStrategy=use-capacity-reservations-first,CapacityReservationPreference=open}}}}}}'
    f',InstanceTypeConfigs=[{{InstanceType=d2.xlarge}}]')

RES_INSTANCE_FLEETS_WITH_ON_DEMAND_MASTER_ONLY = \
    [{"InstanceTypeConfigs": [{"InstanceType": "d2.xlarge"}],
      "LaunchSpecifications": {
        "OnDemandSpecification": {
            "AllocationStrategy": "lowest-price",
            "CapacityReservationOptions": {
                "UsageStrategy": "use-capacity-reservations-first",
                "CapacityReservationPreference": "open"
            }
        }
      },
      "ResizeSpecifications": {
        "OnDemandResizeSpecification": {
          "TimeoutDurationMinutes": 10
        }
      },
      "TargetOnDemandCapacity": 1,
      "InstanceFleetType": "MASTER",
      "Name": "MASTER"
    }]

RES_INSTANCE_FLEETS_WITH_ON_DEMAND_MASTER_ONLY_WITH_TARGETED_ODCR = \
    [{"InstanceTypeConfigs": [{"InstanceType": "d2.xlarge"}],
      "LaunchSpecifications": {
          "OnDemandSpecification": {
              "AllocationStrategy": "lowest-price",
              "CapacityReservationOptions": {
                  "UsageStrategy": "use-capacity-reservations-first",
                  "CapacityReservationResourceGroupArn": "arn:aws:resource-groups:us-east-1:123456789012:group/Test"
              }
          }
      },
      "TargetOnDemandCapacity": 1,
      "InstanceFleetType": "MASTER",
      "Name": "MASTER"
      }]

RES_INSTANCE_FLEETS_WITH_SPOT_MASTER_ONLY = \
    [{"InstanceTypeConfigs": [{"InstanceType": "d2.xlarge","BidPrice": "0.1"}],
      "LaunchSpecifications": {
         "SpotSpecification": {"TimeoutDurationMinutes": 20, "TimeoutAction": "TERMINATE_CLUSTER", "AllocationStrategy": "capacity-optimized"}
      },
      "ResizeSpecifications": {
        "SpotResizeSpecification": {
          "TimeoutDurationMinutes": 10
        }
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
          "SpotSpecification": {"TimeoutDurationMinutes": 20, "TimeoutAction": "TERMINATE_CLUSTER", "AllocationStrategy": "capacity-optimized"}
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
      "ResizeSpecifications": {
        "SpotResizeSpecification": {
          "TimeoutDurationMinutes": 10
        }
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
      "ResizeSpecifications": {
        "OnDemandResizeSpecification": {
          "TimeoutDurationMinutes": 20
        },
        "SpotResizeSpecification": {
          "TimeoutDurationMinutes": 30
        }
      },
      "TargetSpotCapacity": 100,
      "InstanceFleetType": "CORE",
      "Name": "CORE"
    }]

RES_INSTANCE_FLEETS_WITH_SPOT_MASTER_CORE_CLUSTER_WITH_CUSTOM_AMI = \
    [{"InstanceTypeConfigs": [{"InstanceType": "d2.xlarge","BidPrice": "0.1", "CustomAmiId": "ami-deadbeef"}],
      "LaunchSpecifications": {
          "SpotSpecification": {"TimeoutDurationMinutes": 20, "TimeoutAction": "TERMINATE_CLUSTER"}
      },
      "TargetSpotCapacity": 1,
      "InstanceFleetType": "MASTER",
      "Name": "MASTER"
    },
    {"InstanceTypeConfigs": [{"InstanceType": "d2.xlarge","BidPrice": "0.5","WeightedCapacity": 1, "CustomAmiId": "ami-deadbeef"},
      {"InstanceType": "m3.2xlarge","BidPrice": "0.2","WeightedCapacity": 2, "CustomAmiId": "ami-deadpork"},{"InstanceType": "m3.4xlarge","BidPrice": "0.4",
      "WeightedCapacity": 4, "CustomAmiId": "ami-deadpork"}],
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

RES_INSTANCE_FLEETS_WITH_SPOT_ALLOCATION_STRATEGY = \
    [{"InstanceTypeConfigs": [{"InstanceType": "d2.xlarge","BidPrice": "0.1"}],
      "LaunchSpecifications": {
          "SpotSpecification": {"TimeoutDurationMinutes": 20, "TimeoutAction": "TERMINATE_CLUSTER", "AllocationStrategy": "price-capacity-optimized"}
      },
      "TargetSpotCapacity": 1,
      "InstanceFleetType": "MASTER",
      "Name": "MASTER"
    },
    {"InstanceTypeConfigs": [{"InstanceType": "d2.xlarge","BidPrice": "0.5","WeightedCapacity": 1},
      {"InstanceType": "m3.2xlarge","BidPrice": "0.2","WeightedCapacity": 2},{"InstanceType": "m3.4xlarge","BidPrice": "0.4",
      "WeightedCapacity": 4}],
      "LaunchSpecifications" : {
          "SpotSpecification": {"TimeoutDurationMinutes": 20, "TimeoutAction": "TERMINATE_CLUSTER", "AllocationStrategy": "lowest-price"}
      },
      "TargetSpotCapacity": 100,
      "InstanceFleetType": "CORE",
      "Name": "CORE"
    },
    {"InstanceTypeConfigs": [{"InstanceType": "d2.xlarge","BidPrice": "0.5","WeightedCapacity": 1},
      {"InstanceType": "m3.2xlarge","BidPrice": "0.2","WeightedCapacity": 2},{"InstanceType": "m3.4xlarge","BidPrice": "0.4",
      "WeightedCapacity": 4}],
      "LaunchSpecifications" : {
          "SpotSpecification": {"TimeoutDurationMinutes": 20, "TimeoutAction": "TERMINATE_CLUSTER", "AllocationStrategy": "diversified"}
      },
      "TargetSpotCapacity": 100,
      "InstanceFleetType": "TASK",
      "Name": "TASK"
    }]

RES_INSTANCE_FLEETS_WITH_PRIORITIZED_ALLOCATION_STRATEGY_SPOT_AND_OD = \
  [
    {
      "InstanceTypeConfigs": [
        {
          "InstanceType": "d2.xlarge",
          "BidPrice": "0.1",
          "Priority": 0
        }
      ],
      "LaunchSpecifications": {
        "SpotSpecification": {
          "TimeoutDurationMinutes": 30,
          "TimeoutAction": "TERMINATE_CLUSTER",
          "AllocationStrategy": "capacity-optimized-prioritized"
        },
        "OnDemandSpecification": {
          "AllocationStrategy": "prioritized"
        }
      },
      "TargetSpotCapacity": 1,
      "InstanceFleetType": "MASTER",
      "Name": "MASTER"
    },
    {
      "InstanceTypeConfigs": [
        {
          "InstanceType": "d2.xlarge",
          "BidPrice": "0.5",
          "WeightedCapacity": 1,
          "Priority": 0
        },
        {
          "InstanceType": "m3.2xlarge",
          "BidPrice": "0.2",
          "WeightedCapacity": 2,
          "Priority": 1
        },
        {
          "InstanceType": "m3.4xlarge",
          "BidPrice": "0.4",
          "WeightedCapacity": 4,
          "Priority": 99
        }
      ],
      "LaunchSpecifications": {
        "SpotSpecification": {
          "TimeoutDurationMinutes": 32,
          "TimeoutAction": "TERMINATE_CLUSTER",
          "AllocationStrategy": "capacity-optimized-prioritized"
        },
        "OnDemandSpecification": {
          "AllocationStrategy": "prioritized"
        }
      },
      "TargetSpotCapacity": 100,
      "InstanceFleetType": "CORE",
      "Name": "CORE"
    },
    {
      "InstanceTypeConfigs": [
        {
          "InstanceType": "d2.xlarge",
          "BidPrice": "0.5",
          "WeightedCapacity": 1,
          "Priority": 10
        },
        {
          "InstanceType": "m3.2xlarge",
          "BidPrice": "0.2",
          "WeightedCapacity": 2,
          "Priority": 0
        },
        {
          "InstanceType": "m3.4xlarge",
          "BidPrice": "0.4",
          "WeightedCapacity": 4,
          "Priority": 100
        }
      ],
      "LaunchSpecifications": {
        "SpotSpecification": {
          "TimeoutDurationMinutes": 77,
          "TimeoutAction": "TERMINATE_CLUSTER",
          "AllocationStrategy": "capacity-optimized-prioritized"
        },
        "OnDemandSpecification": {
          "AllocationStrategy": "prioritized"
        }
      },
      "TargetSpotCapacity": 100,
      "InstanceFleetType": "TASK",
      "Name": "TASK"
    }]

RES_INSTANCE_FLEETS_WITH_RESIZE_ALLOCATION_STRATEGY_SPOT_AND_OD = \
  [
    {
      "InstanceTypeConfigs": [
        {
          "InstanceType": "d2.xlarge",
          "BidPrice": "0.1"
        }
      ],
      "LaunchSpecifications": {
        "SpotSpecification": {
          "TimeoutDurationMinutes": 30,
          "TimeoutAction": "TERMINATE_CLUSTER",
          "AllocationStrategy": "capacity-optimized-prioritized"
        },
        "OnDemandSpecification": {
          "AllocationStrategy": "lowest-price"
        }
      },
      "TargetSpotCapacity": 1,
      "InstanceFleetType": "MASTER",
      "Name": "MASTER"
    },
    {
      "InstanceTypeConfigs": [
        {
          "InstanceType": "d2.xlarge",
          "BidPrice": "0.5",
          "WeightedCapacity": 1
        },
        {
          "InstanceType": "m3.2xlarge",
          "BidPrice": "0.2",
          "WeightedCapacity": 2
        },
        {
          "InstanceType": "m3.4xlarge",
          "BidPrice": "0.4",
          "WeightedCapacity": 4
        }
      ],
      "LaunchSpecifications": {
        "SpotSpecification": {
          "TimeoutDurationMinutes": 32,
          "TimeoutAction": "TERMINATE_CLUSTER",
          "AllocationStrategy": "capacity-optimized-prioritized"
        },
        "OnDemandSpecification": {
          "AllocationStrategy": "lowest-price"
        }
      },
      "ResizeSpecifications": {
        "OnDemandResizeSpecification": {
          "AllocationStrategy": "lowest-price",
          "CapacityReservationOptions": {
            "CapacityReservationPreference": "open",
            "UsageStrategy": "use-capacity-reservations-first"
          }
        },
        "SpotResizeSpecification": {
          "AllocationStrategy": "capacity-optimized"
        }
      },
      "TargetSpotCapacity": 100,
      "InstanceFleetType": "CORE",
      "Name": "CORE"
    },
    {
      "InstanceTypeConfigs": [
        {
          "InstanceType": "d2.xlarge",
          "BidPrice": "0.5",
          "WeightedCapacity": 1
        },
        {
          "InstanceType": "m3.2xlarge",
          "BidPrice": "0.2",
          "WeightedCapacity": 2
        },
        {
          "InstanceType": "m3.4xlarge",
          "BidPrice": "0.4",
          "WeightedCapacity": 4
        }
      ],
      "LaunchSpecifications": {
        "SpotSpecification": {
          "TimeoutDurationMinutes": 77,
          "TimeoutAction": "TERMINATE_CLUSTER",
          "AllocationStrategy": "capacity-optimized-prioritized"
        },
        "OnDemandSpecification": {
          "AllocationStrategy": "lowest-price"
        }
      },
      "ResizeSpecifications": {
        "OnDemandResizeSpecification": {
          "AllocationStrategy": "lowest-price",
          "CapacityReservationOptions": {
            "CapacityReservationPreference": "open",
            "UsageStrategy": "use-capacity-reservations-first"
          }
        },
        "SpotResizeSpecification": {
          "AllocationStrategy": "capacity-optimized"
        }
      },
      "TargetSpotCapacity": 100,
      "InstanceFleetType": "TASK",
      "Context": "testContext",
      "Name": "TASK"
    }
  ]

RES_TASK_INSTANCE_FLEET_WITH_RESIZE_ALLOCATION_STRATEGY_SPOT_AND_OD = \
  {
    "InstanceTypeConfigs": [
      {
        "InstanceType": "d2.xlarge",
        "BidPrice": "0.5",
        "WeightedCapacity": 1
      },
      {
        "InstanceType": "m3.2xlarge",
        "BidPrice": "0.2",
        "WeightedCapacity": 2
      },
      {
        "InstanceType": "m3.4xlarge",
        "BidPrice": "0.4",
        "WeightedCapacity": 4
      }
    ],
    "LaunchSpecifications": {
      "SpotSpecification": {
        "TimeoutDurationMinutes": 77,
        "TimeoutAction": "TERMINATE_CLUSTER",
        "AllocationStrategy": "capacity-optimized-prioritized"
      },
      "OnDemandSpecification": {
        "AllocationStrategy": "lowest-price"
      }
    },
    "ResizeSpecifications": {
      "OnDemandResizeSpecification": {
        "AllocationStrategy": "lowest-price",
        "CapacityReservationOptions": {
          "CapacityReservationPreference": "open",
          "UsageStrategy": "use-capacity-reservations-first"
        }
      },
      "SpotResizeSpecification": {
        "AllocationStrategy": "capacity-optimized"
      }
    },
    "TargetSpotCapacity": 100,
    "InstanceFleetType": "TASK",
    "Context": "testContext"
  }

RES_MODIFY_INSTANCE_FLEET_WITH_INSTANCE_TYPE_CONFIGS = \
    {
      "ClusterId": DEFAULT_CLUSTER_NAME,
      "InstanceFleet": {
        "InstanceFleetId": DEFAULT_INSTANCE_FLEET_NAME,
        "InstanceTypeConfigs": [
          {"InstanceType": "d2.xlarge"}
        ],
        "Context": "testContext"
      }
    }

RES_MODIFY_INSTANCE_FLEET_WITH_SPOT_AND_OD_RESIZE_SPECIFICATIONS = \
    {
      "ClusterId": DEFAULT_CLUSTER_NAME,
      "InstanceFleet": {
        "InstanceFleetId": DEFAULT_INSTANCE_FLEET_NAME,
          "ResizeSpecifications": {
            "OnDemandResizeSpecification": {
              "AllocationStrategy": "lowest-price",
              "CapacityReservationOptions": {
                "CapacityReservationPreference": "open",
                "UsageStrategy": "use-capacity-reservations-first"
              }
            },
          "SpotResizeSpecification": {"AllocationStrategy": "capacity-optimized"}
        }
      }
  }

RES_MODIFY_INSTANCE_FLEET_WITH_INSTANCE_TYPE_CONFIGS_AND_SPOT_AND_OD_RESIZE_SPECIFICATIONS = \
    {
      "ClusterId": DEFAULT_CLUSTER_NAME,
      "InstanceFleet": {
        "InstanceFleetId": DEFAULT_INSTANCE_FLEET_NAME,
          "ResizeSpecifications": {
            "OnDemandResizeSpecification": {
              "AllocationStrategy": "lowest-price",
              "CapacityReservationOptions": {
                "CapacityReservationPreference": "open",
                "UsageStrategy": "use-capacity-reservations-first"
              }
            },
          "SpotResizeSpecification": {"AllocationStrategy": "capacity-optimized"}
        },
        "InstanceTypeConfigs": [
            {"InstanceType": "d2.xlarge"}
        ]
      }
    }