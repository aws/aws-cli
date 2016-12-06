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
                      "State": "active",
                      "Origin": "CreateRouteTable"
                  }
              ]
          },
          {
              "Associations": [
                  {
                      "SubnetId": "subnet-b61f49f0",
                      "RouteTableAssociationId": "rtbassoc-781d0d1a",
                      "Main": false,
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
                      "State": "active",
                      "Origin": "CreateRouteTable"
                  },
                  {
                      "GatewayId": "igw-046d7966",
                      "DestinationCidrBlock": "0.0.0.0/0",
                      "State": "active",
                      "Origin": "CreateRoute"
                  }
              ]
          },
          {
            "Associations": [
                {
                    "RouteTableAssociationId": "rtbassoc-91fbacf5", 
                    "Main": true, 
                    "RouteTableId": "rtb-1a459c7e"
                }
            ], 
            "RouteTableId": "rtb-1a459c7e", 
            "VpcId": "vpc-31896b55", 
            "PropagatingVgws": [], 
            "Tags": [], 
            "Routes": [
                {
                    "GatewayId": "local", 
                    "DestinationCidrBlock": "10.0.0.0/16", 
                    "State": "active", 
                    "Origin": "CreateRouteTable"
                }, 
                {
                    "GatewayId": "igw-2fa4e34a", 
                    "DestinationCidrBlock": "0.0.0.0/0", 
                    "State": "active", 
                    "Origin": "CreateRoute"
                }, 
                {
                    "GatewayId": "local", 
                    "Origin": "CreateRouteTable", 
                    "State": "active", 
                    "DestinationIpv6CidrBlock": "2001:db8:1234:a100::/56"
                }, 
                {
                    "GatewayId": "igw-2fa4e34a", 
                    "Origin": "CreateRoute", 
                    "State": "active", 
                    "DestinationIpv6CidrBlock": "::/0"
                }
            ]
        }
    ]
  }          