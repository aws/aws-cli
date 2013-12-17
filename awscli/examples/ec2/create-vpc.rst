**To create a VPC**

This example creates a VPC with the specified CIDR block.

Command::

  aws ec2 create-vpc --cidr-block 10.0.0.0/16

Output::

  {
      "Vpc": {
          "InstanceTenancy": "default",
          "State": "pending",
          "VpcId": "vpc-a01106c2",
          "CidrBlock": "10.0.0.0/16",
          "DhcpOptionsId": "dopt-7a8b9c2d"
      }
  }
  
**To create a VPC with dedicated tenancy**

This example creates a VPC with the specified CIDR block and ``dedicated`` tenancy.

Command::

  aws ec2 create-vpc --cidr-block 10.0.0.0/16 --instance-tenancy dedicated

Output::

  {
      "Vpc": {
          "InstanceTenancy": "dedicated",
          "State": "pending",
          "VpcId": "vpc-a01106c2",
          "CidrBlock": "10.0.0.0/16",
          "DhcpOptionsId": "dopt-7a8b9c2d"
      }
  }  