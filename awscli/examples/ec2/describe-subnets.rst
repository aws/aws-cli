**To describe your subnets**

This example describes your subnets.

Command::

  aws ec2 describe-subnets 

Output::

  {
      "Subnets": [
          {
              "VpcId": "vpc-a01106c2",
              "CidrBlock": "10.0.1.0/24",
              "MapPublicIpOnLaunch": false,
              "DefaultForAz": false,
              "State": "available",
              "AvailabilityZone": "us-east-1c",
              "SubnetId": "subnet-9d4a7b6c",
              "AvailableIpAddressCount": 251
          },
          {
              "VpcId": "vpc-b61106d4",
              "CidrBlock": "10.0.0.0/24",
              "MapPublicIpOnLaunch": false,
              "DefaultForAz": false,
              "State": "available",
              "AvailabilityZone": "us-east-1d",
              "SubnetId": "subnet-65ea5f08",
              "AvailableIpAddressCount": 251
          }
      ]  
  }
  
**To describe the subnets for a specific VPC**

This example describes the subnets for the specified VPC.

Command::

  aws ec2 describe-subnets --filter "Name=vpc-id,Values=vpc-a01106c2"

Output::

  {
      "Subnets": [
          {
              "VpcId": "vpc-a01106c2",
              "CidrBlock": "10.0.1.0/24",
              "MapPublicIpOnLaunch": false,
              "DefaultForAz": false,
              "State": "available",
              "AvailabilityZone": "us-east-1c",
              "SubnetId": "subnet-9d4a7b6c",
              "AvailableIpAddressCount": 251
          }
      ]  
  }
