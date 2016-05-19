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

  aws ec2 describe-subnets --filters "Name=vpc-id,Values=vpc-a01106c2"

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
  
**To describe subnets with a specific tag**

This example lists subnets with the tag ``Name=MySubnet`` and returns the output in text format.

Command::

  aws ec2 describe-subnets --filters Name=tag:Name,Values=MySubnet --output text

Output::

  SUBNETS	us-east-1a	251	10.0.1.0/24	False	False	available	subnet-1a2b3c4d	vpc-11223344
  TAGS	Name	MySubnet