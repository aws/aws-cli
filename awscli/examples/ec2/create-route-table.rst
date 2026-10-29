**To create a route table**

The following ``create-route-table`` example creates a route table for the specified VPC. ::

    aws ec2 create-route-table \
        --vpc-id vpc-a01106c2

Output::

    {
        "RouteTable": {
            "Associations": [],
            "RouteTableId": "rtb-22574640",
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
        }
    }

For more information, see `Create a route table for your VPC <https://docs.aws.amazon.com/vpc/latest/userguide/create-vpc-route-table.html>`__ in the *Amazon VPC User Guide*.
