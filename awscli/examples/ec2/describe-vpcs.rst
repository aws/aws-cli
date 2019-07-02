**To describe your VPCs**

This example describes your VPCs.

Command::

  aws ec2 describe-vpcs

Output::

 {
      "Vpcs": [
          {
              "CidrBlock": "30.1.0.0/16",
              "DhcpOptionsId": "dopt-19edf471",
              "State": "available",
              "VpcId": "vpc-0e9801d1295ce6ff8",
              "OwnerId": "111111111111",
              "InstanceTenancy": "default",
              "CidrBlockAssociationSet": [
                  {
                      "AssociationId": "vpc-cidr-assoc-062c64cfaf5506c01",
                      "CidrBlock": "30.1.0.0/16",
                      "CidrBlockState": {
                          "State": "associated"
                      }
                  }
              ],
              "IsDefault": false,
              "Tags": [
                  {
                      "Key": "Name",
                      "Value": "Not Shared"
                  }
              ]
          },
          {
              "CidrBlock": "10.0.0.0/16",
              "DhcpOptionsId": "dopt-19edf471",
              "State": "available",
              "VpcId": "vpc-06e4ab6c6c3b23ae3",
              "OwnerId": "123456789210",
              "InstanceTenancy": "default",
              "CidrBlockAssociationSet": [
                  {
                      "AssociationId": "vpc-cidr-assoc-00b17b4eddabea54b",
                      "CidrBlock": "10.0.0.0/16",
                      "CidrBlockState": {
                          "State": "associated"
                      }
                  }
              ],
              "IsDefault": false,
              "Tags": [
                  {
                      "Key": "Name",
                      "Value": "Shared VPC"
                  }
              ]
          }
      ]
  }
  
**To describe a specific VPC**

This example describes the specified VPC.

Command::

  aws ec2 describe-vpcs --vpc-id vpc-0f501f7ee88fd121c

Output::

 {
    "Vpcs": [
        {
            "CidrBlock": "192.168.1.0/24",
            "DhcpOptionsId": "dopt-6fe3f60d",
            "State": "available",
            "VpcId": "vpc-0f501f7ee88fd121c",
            "OwnerId": "111111111111",
            "InstanceTenancy": "default",
            "CidrBlockAssociationSet": [
                {
                    "AssociationId": "vpc-cidr-assoc-01d91c3ba1ee7c2be",
                    "CidrBlock": "192.168.1.0/24",
                    "CidrBlockState": {
                        "State": "associated"
                    }
                }
            ],
            "IsDefault": false,
            "Tags": [
                {
                    "Key": "Name",
                    "Value": "Example"
                }
            ]
        }
    ]
}
