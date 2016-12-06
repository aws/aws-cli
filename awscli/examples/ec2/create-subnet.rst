**To create a subnet**

This example creates a subnet in the specified VPC with the specified IPv4 CIDR block. We recommend that you let us select an Availability Zone for you. Alternatively, you can use the ``--availability-zone`` option to specify the Availability Zone.

Command::

  aws ec2 create-subnet --vpc-id vpc-a01106c2 --cidr-block 10.0.1.0/24 

Output::

  {
      "Subnet": {
        "VpcId": "vpc-a01106c2",
        "AvailableIpAddressCount": 251, 
        "MapPublicIpOnLaunch": false, 
        "DefaultForAz": false, 
        "Ipv6CidrBlockAssociationSet": [], 
        "State": "pending", 
        "AvailabilityZone": "us-east-1a", 
        "SubnetId": "subnet-2c2de375", 
        "CidrBlock": "10.0.1.0/24", 
        "AssignIpv6AddressOnCreation": false
      }  
  }

**To create a subnet with an IPv6 CIDR block**

This example creates a subnet in the specified VPC with the specified IPv4 and IPv6 CIDR blocks (from the ranges of the VPC).

Command::

  aws ec2 create-subnet --vpc-id vpc-31896b55 --cidr-block 10.0.0.0/24 --ipv6-cidr-block 2001:db8:1234:a100::/64
  
Output::

  {
    "Subnet": {
        "VpcId": "vpc-31896b55", 
        "AvailableIpAddressCount": 251, 
        "MapPublicIpOnLaunch": false, 
        "DefaultForAz": false, 
        "Ipv6CidrBlockAssociationSet": [
            {
                "Ipv6CidrBlock": "2001:db8:1234:a100::/64", 
                "AssociationId": "subnet-cidr-assoc-3fe7e347", 
                "Ipv6CidrBlockState": {
                    "State": "ASSOCIATING"
                }
            }
        ], 
        "State": "pending", 
        "AvailabilityZone": "ap-southeast-2a", 
        "SubnetId": "subnet-5504d223", 
        "CidrBlock": "10.0.0.0/24", 
        "AssignIpv6AddressOnCreation": false
    }
  }