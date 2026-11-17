**To delete a prefix list reference**

The following ``delete-transit-gateway-prefix-list-reference`` example deletes the specified prefix list reference. ::

    aws ec2 delete-transit-gateway-prefix-list-reference \
        --transit-gateway-route-table-id tgw-rtb-0123456789abcd123 \
        --prefix-list-id pl-11111122222222333

Output::

    {
        "TransitGatewayPrefixListReference": {
            "TransitGatewayRouteTableId": "tgw-rtb-0123456789abcd123",
            "PrefixListId": "pl-11111122222222333",
            "PrefixListOwnerId": "123456789012",
            "State": "deleting",
            "Blackhole": false,
            "TransitGatewayAttachment": {
                "TransitGatewayAttachmentId": "tgw-attach-aabbccddaabbccaab",
                "ResourceType": "vpc",
                "ResourceId": "vpc-1122334455aabbccd"
            }
        }
    }

For more information, see `Delete a prefix list reference in AWS Transit Gateway <https://docs.aws.amazon.com/vpc/latest/tgw/delete-prefix-list-reference.html>`__ in the *Transit Gateways Guide*.
