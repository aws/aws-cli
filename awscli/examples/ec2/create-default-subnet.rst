**To create a default subnet**

The following ``create-default-subnet`` example creates a default subnet in Availability Zone ``us-west-2a``. ::

    aws ec2 create-default-subnet \
        --availability-zone us-west-2a

Output::

    {
        "Subnet": {
            "AvailabilityZone": "us-west-2a",
            "Tags": [],
            "AvailableIpAddressCount": 4091,
            "DefaultForAz": true,
            "Ipv6CidrBlockAssociationSet": [],
            "VpcId": "vpc-1a2b3c4d",
            "State": "available",
            "MapPublicIpOnLaunch": true,
            "SubnetId": "subnet-1122aabb",
            "CidrBlock": "172.31.32.0/20",
            "AssignIpv6AddressOnCreation": false
        }
    }

For more information, see `Work with your default VPC and default subnets <https://docs.aws.amazon.com/vpc/latest/userguide/work-with-default-vpc.html>`__ in the *Amazon VPC User Guide*.
