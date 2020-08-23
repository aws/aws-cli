**To display information about the route table propagations for the specified transit gateway route table**

 The following ``get-transit-gateway-route-table-propagations`` example returns the route table propagations for the specified route table. ::
 
     ec2 get-transit-gateway-route-table-propagations \
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
                "ResourceId": "11460968-4ac1-4fd3-bdb2-00599EXAMPLE",
                "ResourceType": "direct-connect-gateway",
                "State": "enabled"
            },
            {
                "TransitGatewayAttachmentId": "tgw-attach-0a89069f57EXAMPLE",
                "ResourceId": "8384da05-13ce-4a91-aada-5a1baEXAMPLE",
                "ResourceType": "direct-connect-gateway",
                "State": "enabled"
            }
        ]
    }

For more information, see `View Transit Gateway Route Table Propagations<https://docs.aws.amazon.com/vpc/latest/tgw/tgw-route-tables.html#view-tgw-route-propagations>`__ in the *AWS Transit Gateways Guide*.
