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