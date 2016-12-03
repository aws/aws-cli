**To disassociate an IPv6 CIDR block from a VPC**

This example disassociates an IPv6 CIDR block from a VPC using the association ID for the CIDR block.

Command::

  aws ec2 disassociate-vpc-cidr-block --association-id vpc-cidr-assoc-eca54085

Output::

  {
    "Ipv6CidrBlockAssociation": {
        "Ipv6CidrBlock": "2001:db8:1234:1a00::/56", 
        "AssociationId": "vpc-cidr-assoc-eca54085", 
        "Ipv6CidrBlockState": {
            "State": "disassociating"
        }
    }, 
    "VpcId": "vpc-a034d6c4"
  }