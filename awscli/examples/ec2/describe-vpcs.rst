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
              "State": "available",
              "DhcpOptionsId": "dopt-7a8b9c2d",
              "CidrBlock": "10.0.0.0/16",
              "IsDefault": false
          },
          {
              "VpcId": "vpc-b61106d4",
              "InstanceTenancy": "dedicated",
              "State": "available",
              "DhcpOptionsId": "dopt-97eb5efa",
              "CidrBlock": "10.50.0.0/16",
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
              "State": "available",
              "DhcpOptionsId": "dopt-7a8b9c2d",
              "CidrBlock": "10.0.0.0/16",
              "IsDefault": false
          }
      ]  
  }