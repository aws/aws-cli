**Example 1: To create a subnet with an IPv4 CIDR block**

The following ``create-subnet`` example creates a subnet in the specified VPC with the specified IPv4 CIDR block. We recommend that you let us select an Availability Zone for you. Alternatively, you can use the ``--availability-zone`` option to specify the Availability Zone. ::

    aws ec2 create-subnet \
        --vpc-id vpc-081ec835f3EXAMPLE \
        --cidr-block 10.0.1.0/24

Output::

    {
        "Subnet": {
            "AvailabilityZone": "us-east-2c",
            "AvailabilityZoneId": "use2-az3",
            "AvailableIpAddressCount": 251,
            "CidrBlock": "10.0.1.0/24",
            "DefaultForAz": false,
            "MapPublicIpOnLaunch": false,
            "State": "pending",
            "SubnetId": "subnet-0e3f5cac72EXAMPLE",
            "VpcId": "vpc-081ec835f3EXAMPLE",
            "OwnerId": "111122223333",
            "AssignIpv6AddressOnCreation": false,
            "Ipv6CidrBlockAssociationSet": [],
            "SubnetArn": "arn:aws:ec2:us-east-2:111122223333:subnet/subnet-0e3f5cac72375030d"
        }
    }             

For more information, see `Creating a Subnet in Your VPC <https://docs.aws.amazon.com/vpc/latest/userguide/working-with-vpcs.html#AddaSubnet>`__ in the *AWS VPC User Guide*

**Example 2: To create a subnet with an IPv6 CIDR block**

The following ``create-subnet`` example creates a subnet in the specified VPC with the specified IPv4 and IPv6 CIDR blocks (from the ranges of the VPC). ::

   aws ec2 create-subnet \
    --vpc-id vpc-07e8ffd50fEXAMPLE \
    --cidr-block 10.0.0.0/24 \
    --ipv6-cidr-block 2600:1f16:115:200::/64
    
Output::

    {
        "Subnet": {
            "AvailabilityZone": "us-east-2b",
            "AvailabilityZoneId": "use2-az2",
            "AvailableIpAddressCount": 251,
            "CidrBlock": "10.0.0.0/24",
            "DefaultForAz": false,
            "MapPublicIpOnLaunch": false,
            "State": "pending",
            "SubnetId": "subnet-02bf4c428bEXAMPLE",
            "VpcId": "vpc-07e8ffd50EXAMPLE",
            "OwnerId": "1111222233333",
            "AssignIpv6AddressOnCreation": false,
            "Ipv6CidrBlockAssociationSet": [
                {
                    "AssociationId": "subnet-cidr-assoc-002afb9f3cEXAMPLE",
                    "Ipv6CidrBlock": "2600:1f16:115:200::/64",
                    "Ipv6CidrBlockState": {
                        "State": "associating"
                    }
                }
            ],
            "SubnetArn": "arn:aws:ec2:us-east-2:111122223333:subnet/subnet-02bf4c428bEXAMPLE"
        }
    }

For more information, see `Creating a Subnet in Your VPC <https://docs.aws.amazon.com/vpc/latest/userguide/working-with-vpcs.html#AddaSubnet>`__ in the *AWS VPC User Guide*.
