**Example 1: To describe your subnets**

The following ``describe-subnets`` example displays the details of your subnets. ::

    aws ec2 describe-subnets

Output::

    {
        "Subnets": [
            {
                 "AvailabilityZone": "us-east-1d",
                "AvailabilityZoneId": "use1-az2",
                "AvailableIpAddressCount": 4089,
                "CidrBlock": "172.31.80.0/20",
                "DefaultForAz": true,
                "MapPublicIpOnLaunch": false,
                "MapCustomerOwnedIpOnLaunch": true,
                "State": "available",
                "SubnetId": "subnet-0bb1c79de3EXAMPLE",
                "VpcId": "vpc-0ee975135dEXAMPLE",
                "OwnerId": "111122223333",
                "AssignIpv6AddressOnCreation": false,
                "Ipv6CidrBlockAssociationSet": [],
                "CustomerOwnedIpv4Pool:": 'pool-2EXAMPLE',    
                "SubnetArn": "arn:aws:ec2:us-east-2:111122223333:subnet/subnet-0bb1c79de3EXAMPLE"
            },
            {
                "AvailabilityZone": "us-east-1d",
                "AvailabilityZoneId": "use1-az2",
                "AvailableIpAddressCount": 4089,
                "CidrBlock": "172.31.80.0/20",
                "DefaultForAz": true,
                "MapPublicIpOnLaunch": true,
                "MapCustomerOwnedIpOnLaunch": false,
                "State": "available",
                "SubnetId": "subnet-8EXAMPLE",
                "VpcId": "vpc-3EXAMPLE",
                "OwnerId": "1111222233333",
                "AssignIpv6AddressOnCreation": false,
                "Ipv6CidrBlockAssociationSet": [],        
                "Tags": [
                    {
                        "Key": "Name",
                        "Value": "MySubnet"
                    }
                ],
                "SubnetArn": "arn:aws:ec2:us-east-1:111122223333:subnet/subnet-8EXAMPLE"
            }
        ]
    }

For more information, see `Working with VPCs and Subnets <https://docs.aws.amazon.com/vpc/latest/userguide/working-with-vpcs.html>`__ in the *AWS VPC User Guide*.

**Example 2: To describe a specificied VPCs subnets**

The following ``describe-subnets`` example uses a filter to retrieve details for the subnets of the specified VPC. ::

    aws ec2 describe-subnets \
        --filters "Name=vpc-id,Values=vpc-3EXAMPLE"

Output::

    {
        "Subnets": [
            {
                "AvailabilityZone": "us-east-1d",
                "AvailabilityZoneId": "use1-az2",
                "AvailableIpAddressCount": 4089,
                "CidrBlock": "172.31.80.0/20",
                "DefaultForAz": true,
                "MapPublicIpOnLaunch": true,
                "MapCustomerOwnedIpOnLaunch": false,
                "State": "available",
                "SubnetId": "subnet-8EXAMPLE",
                "VpcId": "vpc-3EXAMPLE",
                "OwnerId": "1111222233333",
                "AssignIpv6AddressOnCreation": false,
                "Ipv6CidrBlockAssociationSet": [],
                "Tags": [
                    {
                        "Key": "Name",
                        "Value": "MySubnet"
                    }
                ],
                "SubnetArn": "arn:aws:ec2:us-east-1:111122223333:subnet/subnet-8EXAMPLE"
            }
        ]
    }

For more information, see `Working with VPCs and Subnets <https://docs.aws.amazon.com/vpc/latest/userguide/working-with-vpcs.html>`__ in the *AWS VPC User Guide*.

**Example 3: To describe subnets with a specific tag**

The following ``describe-subnets`` example uses a filter to retrieve the details of those subnets with the tag ``Name=MySubnet``. The command specifies that the output is a simple text string. ::

    aws ec2 describe-subnets \
        --filters Name=tag:Name,Values=MySubnet \
        --output text

Output::

    SUBNETS False   us-east-1c      use1-az1        250     10.0.0.0/24     False   False   False   111122223333    available       arn:aws:ec2:us-east-1:111122223333:subnet/subnet-0d3d002af8EXAMPLE      subnet-0d3d002af8EXAMPLE        vpc-0065acced4EXAMPLE   TAGS    Name    MySubnet

For more information, see `Working with VPCs and Subnets <https://docs.aws.amazon.com/vpc/latest/userguide/working-with-vpcs.html>`__ in the *AWS VPC User Guide*.
