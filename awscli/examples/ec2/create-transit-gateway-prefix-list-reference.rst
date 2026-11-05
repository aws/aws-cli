**To create a reference to a prefix list**

The following ``create-transit-gateway-prefix-list-reference`` example creates a reference to the specified prefix list in the specified transit gateway route table. ::

    aws ec2 create-transit-gateway-prefix-list-reference \
        --transit-gateway-route-table-id tgw-rtb-0123456789abcd123 \
        --prefix-list-id pl-11111122222222333 \
        --transit-gateway-attachment-id tgw-attach-aaaaaabbbbbb11111

Output::

    {
        "TransitGatewayPrefixListReference": {
            "TransitGatewayRouteTableId": "tgw-rtb-0123456789abcd123",
            "PrefixListId": "pl-11111122222222333",
            "PrefixListOwnerId": "123456789012",
            "State": "pending",
            "Blackhole": false,
            "TransitGatewayAttachment": {
                "TransitGatewayAttachmentId": "tgw-attach-aaaaaabbbbbb11111",
                "ResourceType": "vpc",
                "ResourceId": "vpc-0a1b2c3d4e5f6a7b8"
            }
        }
    }

For more information, see `Create a prefix list reference <https://docs.aws.amazon.com/vpc/latest/tgw/create-prefix-list-reference.html>`__ in the *Transit Gateways Guide*.