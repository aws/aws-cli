**To create a VPC**

The following ``create-vpc`` example creates a VPC with the specified IPv4 CIDR block. ::

    aws ec2 create-vpc \
        --cidr-block 10.0.0.0/16

Output::

    {
        "Vpc": {
            "CidrBlock": "10.0.0.0/16",
            "DhcpOptionsId": "dopt-5EXAMPLE",
            "State": "pending",
            "VpcId": "vpc-0a60eb65b4EXAMPLE",
            "OwnerId": "123456789012",
            "InstanceTenancy": "default",
            "Ipv6CidrBlockAssociationSet": [],
            "CidrBlockAssociationSet": [
                {
                    "AssociationId": "vpc-cidr-assoc-07501b79ecEXAMPLE",
                    "CidrBlock": "10.0.0.0/16",
                    "CidrBlockState": {
                        "State": "associated"
                    }
                }
            ],
            "IsDefault": false,
            "Tags": []
        }
    }             

**To create a VPC with dedicated tenancy**

The following ``create-vpc`` example creates a VPC with the specified IPv4 CIDR block and dedicated tenancy.

    aws ec2 create-vpc \
        --cidr-block 10.0.0.0/16 \
        --instance-tenancy dedicated

Output::

    {
        "Vpc": {
            "CidrBlock": "10.0.0.0/16",
            "DhcpOptionsId": "dopt-19edf471",
            "State": "pending",
            "VpcId": "vpc-0a53287fa4EXAMPLE",
            "OwnerId": "111122223333",
            "InstanceTenancy": "dedicated",
            "Ipv6CidrBlockAssociationSet": [],
            "CidrBlockAssociationSet": [
                {
                    "AssociationId": "vpc-cidr-assoc-00b24cc1c2EXAMPLE",
                    "CidrBlock": "10.0.0.0/16",
                    "CidrBlockState": {
                        "State": "associated"
                    }
                }
            ],
            "IsDefault": false,
            "Tags": []
        }
    }
                  
**To create a VPC with an IPv6 CIDR block**

The following ``create-vpc`` example creates a VPC with an Amazon-provided IPv6 CIDR block.

    aws ec2 create-vpc \
        --cidr-block 10.0.0.0/16 \
        --amazon-provided-ipv6-cidr-block

Output::

    {
        "Vpc": {
            "CidrBlock": "10.0.0.0/16",
            "DhcpOptionsId": "dopt-19edf471",
            "State": "pending",
            "VpcId": "vpc-07e8ffd50fEXAMPLE",
            "OwnerId": "111122223333",
            "InstanceTenancy": "default",
            "Ipv6CidrBlockAssociationSet": [
                {
                    "AssociationId": "vpc-cidr-assoc-0aed4e604eEXAMPLE",
                    "Ipv6CidrBlock": "",
                    "Ipv6CidrBlockState": {
                        "State": "associating"
                    }
                }
            ],
            "CidrBlockAssociationSet": [
                {
                    "AssociationId": "vpc-cidr-assoc-06472385d8EXAMPLE",
                    "CidrBlock": "10.0.0.0/16",
                    "CidrBlockState": {
                        "State": "associated"
                    }
                }
            ],
            "IsDefault": false,
            "Tags": []
        }
    }

For more information, see `Creating a VPC <https://docs.aws.amazon.com/vpc/latest/userguide/working-with-vpcs.html#Create-VPC>`__ in the *AWS VPC User Guide*.
