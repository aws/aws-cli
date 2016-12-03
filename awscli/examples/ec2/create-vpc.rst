**To create a VPC**

This example creates a VPC with the specified IPv4 CIDR block.

Command::

  aws ec2 create-vpc --cidr-block 10.0.0.0/16

Output::

  {
      "Vpc": {
        "VpcId": "vpc-145db170", 
        "InstanceTenancy": "default", 
        "CidrBlockAssociationSet": [], 
        "Ipv6CidrBlockAssociationSet": [], 
        "State": "pending", 
        "DhcpOptionsId": "dopt-dbedadb2", 
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
        "VpcId": "vpc-145db170", 
        "InstanceTenancy": "dedicated", 
        "CidrBlockAssociationSet": [], 
        "Ipv6CidrBlockAssociationSet": [], 
        "State": "pending", 
        "DhcpOptionsId": "dopt-dbedadb2", 
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
        "VpcId": "vpc-31896b55", 
        "InstanceTenancy": "default", 
        "CidrBlockAssociationSet": [], 
        "Ipv6CidrBlockAssociationSet": [
            {
                "Ipv6CidrBlock": "", 
                "AssociationId": "vpc-cidr-assoc-17a5407e", 
                "Ipv6CidrBlockState": {
                    "State": "associating"
                }
            }
        ], 
        "State": "pending", 
        "DhcpOptionsId": "dopt-dbedadb2", 
        "CidrBlock": "10.0.0.0/16", 
        "IsDefault": false
    }
  }
