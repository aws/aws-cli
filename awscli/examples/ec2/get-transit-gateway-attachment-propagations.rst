**To list the route tables to which the specified resource attachment propagates routes**

The following ``get-transit-gateway-attachment-propagations`` example lists the route table to which the specified resource attachment propagates routes. ::

    aws ec2 get-transit-gateway-attachment-propagations \
        --transit-gateway-attachment-id tgw-attach-09fbd47ddfEXAMPLE

Output::

    {
        "TransitGatewayAttachmentPropagations": [
            {
                "TransitGatewayRouteTableId": "tgw-rtb-0882c61b97EXAMPLE",
                "State": "enabled"
            }
        ]
    }

For more information, see `View Transit Gateway Route Tables <https://docs.aws.amazon.com/vpc/latest/tgw/tgw-route-tables.html#view-tgw-route-tables>`__ in the *AWS Transit Gateways Guide*.
