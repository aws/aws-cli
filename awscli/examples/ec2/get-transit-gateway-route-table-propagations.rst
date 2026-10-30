**To display information about the route table propagations for the specified transit gateway route table**

The following ``get-transit-gateway-route-table-propagations`` example returns the route table propagations for the specified route table. ::

    aws ec2 get-transit-gateway-route-table-propagations \
        --transit-gateway-route-table-id tgw-rtb-002573ed1eEXAMPLE

Output::

    {
        "TransitGatewayRouteTablePropagations": [
            {
                "TransitGatewayAttachmentId": "tgw-attach-01f8100bc7EXAMPLE",
                "ResourceId": "vpc-3EXAMPLE",
                "ResourceType": "vpc",
                "State": "enabled"
            },
            {
                "TransitGatewayAttachmentId": "tgw-attach-08e0bc912cEXAMPLE",
                "ResourceId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "ResourceType": "direct-connect-gateway",
                "State": "enabled"
            },
            {
                "TransitGatewayAttachmentId": "tgw-attach-0a89069f57EXAMPLE",
                "ResourceId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "ResourceType": "direct-connect-gateway",
                "State": "enabled"
            }
        ]
    }

For more information, see `Transit gateway route tables <https://docs.aws.amazon.com/vpc/latest/tgw/tgw-route-tables.html>`__ in the *Transit Gateways Guide*.