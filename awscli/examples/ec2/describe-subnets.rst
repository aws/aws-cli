**Example 1: To describe your subnets**

The following ``describe-subnets`` example displays the details of your subnets. ::

    aws ec2 describe-subnets

Output::

    {
        "Subnets": [
            {
                "AvailabilityZone": "us-east-2c",
                "AvailabilityZoneId": "use2-az3",
                "AvailableIpAddressCount": 251,
                "CidrBlock": "10.0.2.0/24",
                "DefaultForAz": false,
                "MapPublicIpOnLaunch": false,
                "State": "available",
                "SubnetId": "subnet-0bb1c79de3EXAMPLE",
                "VpcId": "vpc-0ee975135dEXAMPLE",
                "OwnerId": "111122223333",
                "AssignIpv6AddressOnCreation": false,
                "Ipv6CidrBlockAssociationSet": [],
                "SubnetArn": "arn:aws:ec2:us-east-2:111122223333:subnet/subnet-0bb1c79de3EXAMPLE"
            },
            {
                "AvailabilityZone": "us-east-2c",
                "AvailabilityZoneId": "use2-az3",
                "AvailableIpAddressCount": 248,
                "CidrBlock": "10.0.1.0/24",
                "DefaultForAz": false,
                "MapPublicIpOnLaunch": false,
                "State": "available",
                "SubnetId": "subnet-0931fc2fa5EXAMPLE",
                "VpcId": "vpc-06e4ab6c6cEXAMPLE",
                "OwnerId": "111122223333",
                "AssignIpv6AddressOnCreation": false,
                "Ipv6CidrBlockAssociationSet": [],
                "Tags": [
                    {
                       "Key": "Name",
                       "Value": "MySubnet"
                    }
                ],
                "SubnetArn": "arn:aws:ec2:us-east-2:111122223333:subnet/subnet-0931fc2fa5EXAMPLE"
            }
        ]
    }

**Example 2: To descripe a specific subnets**

The following ``describe-subnets`` example uses a filter to retrieve details for the subnets of the specified VPC. ::

    aws ec2 describe-subnets \
        --filters "Name=vpc-id,Values=vpc-06e4ab6c6cEXAMPLE"

Output::

    {
        "Subnets": [
            {
                "AvailabilityZone": "us-east-2c",
                "AvailabilityZoneId": "use2-az3",
                "AvailableIpAddressCount": 248,
                "CidrBlock": "10.0.1.0/24",
                "DefaultForAz": false,
                "MapPublicIpOnLaunch": false,
                "State": "available",
                "SubnetId": "subnet-0931fc2fa5EXAMPLE",
                "VpcId": "vpc-06e4ab6c6cEXAMPLE",
                "OwnerId": "111122223333",
                "AssignIpv6AddressOnCreation": false,
                "Ipv6CidrBlockAssociationSet": [],
                "Tags": [
                    {
                        "Key": "Name",
                        "Value": "MySubnet"
                    }
                ],
                "SubnetArn": "arn:aws:ec2:us-east-2:111122223333:subnet/subnet-0931fc2fa5EXAMPLE"
            }
        ]
    }

**Example 3: To describe subnets with a specific tag**

The following ``describe-subnets`` example uses a filter to retrieve the details of those subnets with the tag ``Name=MySubnet``. The command specifies that the output is a simple text string. ::

    aws ec2 describe-subnets \
        --filters Name=tag:Name,Values=MySubnet \
        --output text

Output::

    SUBNETS False   us-east-2c      use2-az3        248     10.0.1.0/24     False   False   111122223333    available               arn:aws:ec2:us-east-2:111122223333:subnet/subnet-0931fc2fa5EXAMPLE      subnet-0931fc2fa5f1cbe44        vpc-06e4ab6c6c3b23ae3
    TAGS    Name    MySubnet

For more information, see `Working with VPCs and Subnets <https://docs.aws.amazon.com/vpc/latest/userguide/working-with-vpcs.html>`__ in the *AWS VPC User Guide*.
