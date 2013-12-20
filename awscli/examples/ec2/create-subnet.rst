**To create a subnet**

This example creates a subnet in the specified VPC with the specified CIDR block. We recommend that you let us select an Availability Zone for you. Alternatively, you can use the ``--availability-zone`` option to specify the Availability Zone.

Command::

  aws ec2 create-subnet --vpc-id vpc-a01106c2 --cidr-block 10.0.1.0/24 

Output::

  {
      "Subnet": {
          "VpcId": "vpc-a01106c2",
          "CidrBlock": "10.0.1.0/24",
          "State": "pending",
          "AvailabilityZone": "us-east-1c",
          "SubnetId": "subnet-9d4a7b6c",
          "AvailableIpAddressCount": 251
      }  
  }