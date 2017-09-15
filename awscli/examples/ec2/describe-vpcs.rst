**To describe your VPCs**

This example describes your VPCs.

Command::

  aws ec2 describe-vpcs

Output::

  {
      "Vpcs": [
          {
              "VpcId": "vpc-a01106c2",
              "InstanceTenancy": "default",
              "Tags": [
                  {
                      "Value": "MyVPC",
                      "Key": "Name"
                  }
              ],
              "CidrBlockAssociations": [
                {
                    "AssociationId": "vpc-cidr-assoc-dbd28eb3", 
                    "CidrBlock": "10.0.0.0/16", 
                    "CidrBlockState": {
                        "State": "associated"
                    }
                }
              ],
              "State": "available",
              "DhcpOptionsId": "dopt-7a8b9c2d",
              "CidrBlock": "10.0.0.0/16",
              "IsDefault": false
          },
          {
              "VpcId": "vpc-b61106d4",
              "InstanceTenancy": "dedicated",
              "CidrBlockAssociations": [
                {
                    "AssociationId": "vpc-cidr-assoc-6e42b505", 
                    "CidrBlock": "10.50.0.0/16", 
                    "CidrBlockState": {
                        "State": "associated"
                    }
                }
              ],
              "State": "available",
              "DhcpOptionsId": "dopt-97eb5efa",
              "CidrBlock": "10.50.0.0/16",
              "IsDefault": false
          },
          {
            "VpcId": "vpc-a45db1c0", 
            "InstanceTenancy": "default",
            "CidrBlockAssociations": [
                {
                    "AssociationId": "vpc-cidr-assoc-42d6132b", 
                    "CidrBlock": "198.168.0.0/24", 
                    "CidrBlockState": {
                        "State": "associated"
                    }
                }
            ], 
            "Ipv6CidrBlockAssociationSet": [
                {
                    "Ipv6CidrBlock": "2001:db8:1234:8800::/56", 
                    "AssociationId": "vpc-cidr-assoc-e5a5408c", 
                    "Ipv6CidrBlockState": {
                        "State": "associated"
                    }
                }
            ], 
            "State": "available", 
            "DhcpOptionsId": "dopt-dbedadb2", 
            "CidrBlock": "198.168.0.0/24", 
            "IsDefault": false
        }
      ]  
  }
  
**To describe a specific VPC**

This example describes the specified VPC.

Command::

  aws ec2 describe-vpcs --vpc-ids vpc-a01106c2

Output::

  {
      "Vpcs": [
          {
              "VpcId": "vpc-a01106c2",
              "InstanceTenancy": "default",
              "Tags": [
                  {
                      "Value": "MyVPC",
                      "Key": "Name"
                  }
              ],
              "CidrBlockAssociations": [
                {
                    "AssociationId": "vpc-cidr-assoc-a26a41ca", 
                    "CidrBlock": "10.0.0.0/16", 
                    "CidrBlockState": {
                        "State": "associated"
                    }
                }
              ], 
              "State": "available",
              "DhcpOptionsId": "dopt-7a8b9c2d",
              "CidrBlock": "10.0.0.0/16",
              "IsDefault": false
          }
      ]  
  }