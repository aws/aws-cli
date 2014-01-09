**To describe your route tables**

This example describes your route tables.

Command::

  aws ec2 describe-route-tables

Output::

  {
      "RouteTables": [
          {
              "Associations": [
                  {
                      "RouteTableAssociationId": "rtbassoc-d8ccddba",
                      "Main": true,
                      "RouteTableId": "rtb-1f382e7d"
                  }
              ],
              "RouteTableId": "rtb-1f382e7d",
              "VpcId": "vpc-a01106c2",
              "PropagatingVgws": [],
              "Tags": [],
              "Routes": [
                  {
                      "GatewayId": "local",
                      "DestinationCidrBlock": "10.0.0.0/16",
                      "State": "active"
                  }
              ]
          },
          {
              "Associations": [
                  {
                      "SubnetId": "subnet-b61f49f0",
                      "RouteTableAssociationId": "rtbassoc-781d0d1a",
                      "RouteTableId": "rtb-22574640"
                  }
              ],
              "RouteTableId": "rtb-22574640",
              "VpcId": "vpc-a01106c2",
              "PropagatingVgws": [
                  {
                      "GatewayId": "vgw-f211f09b"
                  }
              ],
              "Tags": [],
              "Routes": [
                  {
                      "GatewayId": "local",
                      "DestinationCidrBlock": "10.0.0.0/16",
                      "State": "active"
                  },
                  {
                      "GatewayId": "igw-046d7966",
                      "DestinationCidrBlock": "0.0.0.0/0",
                      "State": "active"
                  }
              ]
          }          
      ]
  }