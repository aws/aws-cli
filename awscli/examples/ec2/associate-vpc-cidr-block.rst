**To associate an IPv6 CIDR block with a VPC**

This example associates an IPv6 CIDR block with a VPC.

Command::

  aws ec2 associate-vpc-cidr-block --amazon-provided-ipv6-cidr-block --vpc-id vpc-a034d6c4

Output::

  {
    "Ipv6CidrBlockAssociation": {
        "Ipv6CidrBlockState": {
            "State": "associating"
        }, 
        "AssociationId": "vpc-cidr-assoc-eca54085"
    }, 
    "VpcId": "vpc-a034d6c4"
  }

**To associate an additional IPv4 CIDR block with a VPC**

This example associates the IPv4 CIDR block ``10.2.0.0/16`` with VPC ``vpc-1a2b3c4d``.

Command::

  aws ec2 associate-vpc-cidr-block --vpc-id vpc-1a2b3c4d --cidr-block 10.2.0.0/16

Output::

  {
    "CidrBlockAssociation": {
        "AssociationId": "vpc-cidr-assoc-2447724d", 
        "CidrBlock": "10.2.0.0/16", 
        "CidrBlockState": {
            "State": "associating"
        }
    }, 
    "VpcId": "vpc-1a2b3c4d"
  }