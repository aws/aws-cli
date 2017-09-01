**To create a VPC**

This example creates a VPC with the specified IPv4 CIDR block.

Command::

  aws ec2 create-vpc --cidr-block 10.0.0.0/16

Output::

  {
    "Vpc": {
        "VpcId": "vpc-ff7bbf86", 
        "InstanceTenancy": "default", 
        "Tags": [], 
        "CidrBlockAssociations": [
            {
                "AssociationId": "vpc-cidr-assoc-6e42b505", 
                "CidrBlock": "10.0.0.0/16", 
                "CidrBlockState": {
                    "State": "associated"
                }
            }
        ], 
        "Ipv6CidrBlockAssociationSet": [], 
        "State": "pending", 
        "DhcpOptionsId": "dopt-38f7a057", 
        "CidrBlock": "10.0.0.0/16", 
        "IsDefault": false
    }
  }
  
**To create a VPC with dedicated tenancy**

This example creates a VPC with the specified IPv4 CIDR block and ``dedicated`` tenancy.

Command::

  aws ec2 create-vpc --cidr-block 10.0.0.0/16 --instance-tenancy dedicated

Output::

  {
    "Vpc": {
        "VpcId": "vpc-848344fd", 
        "InstanceTenancy": "dedicated", 
        "Tags": [], 
        "CidrBlockAssociations": [
            {
                "AssociationId": "vpc-cidr-assoc-8c4fb8e7", 
                "CidrBlock": "10.0.0.0/16", 
                "CidrBlockState": {
                    "State": "associated"
                }
            }
        ], 
        "Ipv6CidrBlockAssociationSet": [], 
        "State": "pending", 
        "DhcpOptionsId": "dopt-38f7a057", 
        "CidrBlock": "10.0.0.0/16", 
        "IsDefault": false
    }
  } 
  
**To create a VPC with an IPv6 CIDR block**

This example creates a VPC with an Amazon-provided IPv6 CIDR block.

Command::

  aws ec2 create-vpc --cidr-block 10.0.0.0/16 --amazon-provided-ipv6-cidr-block
  
Output::

  {
    "Vpc": {
        "VpcId": "vpc-4b804732", 
        "InstanceTenancy": "default", 
        "Tags": [], 
        "CidrBlockAssociations": [
            {
                "AssociationId": "vpc-cidr-assoc-6c4dba07", 
                "CidrBlock": "10.0.0.0/16", 
                "CidrBlockState": {
                    "State": "associated"
                }
            }
        ], 
        "Ipv6CidrBlockAssociationSet": [
            {
                "Ipv6CidrBlock": "", 
                "AssociationId": "vpc-cidr-assoc-634dba08", 
                "Ipv6CidrBlockState": {
                    "State": "associating"
                }
            }
        ], 
        "State": "pending", 
        "DhcpOptionsId": "dopt-38f7a057", 
        "CidrBlock": "10.0.0.0/16", 
        "IsDefault": false
    }
  }
