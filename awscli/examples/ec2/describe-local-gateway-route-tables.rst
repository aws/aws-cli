**To describe your Local Gateway Route Tables**

The following ``describe-local-gateway-route-tables`` example displays details about the local gateway route tables. ::

    aws ec2 describe-local-gateway-route-tables

Output::

    {
        "LocalGatewayRouteTables": [
            {
                "LocalGatewayRouteTableId": "lgw-rtb-059615ef7deEXAMPLE",
                "LocalGatewayId": "lgw-09b493aa7cEXAMPLE",
                "OutpostArn": "arn:aws:outposts:us-west-2:123456789012:outpost/op-0dc11b66edEXAMPLE",
                "State": "available"
            }
        ]
    }

For more information, see `Local gateway route tables <https://docs.aws.amazon.com/outposts/latest/userguide/routing.html>`__ in the *AWS Outposts User Guide*.
