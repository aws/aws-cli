**To disassociate a transit gateway route table from a  resource attachment**

The following ``disassociate-transit-gateway-route-table`` example disassociates the specified attachment from the transit gateway route table. ::

    aws ec2 disassociate-transit-gateway-route-table \
        --transit-gateway-route-table-id tgw-rtb-002573ed1eEXAMPLE \
        --transit-gateway-attachment-id tgw-attach-08e0bc912cEXAMPLE

Output::

    {
        "Association": {
            "TransitGatewayRouteTableId": "tgw-rtb-002573ed1eEXAMPLE",
            "TransitGatewayAttachmentId": "tgw-attach-08e0bc912cEXAMPLE",
            "ResourceId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "ResourceType": "direct-connect-gateway",
            "State": "disassociating"
        }
    }

For more information, see `Transit gateway route tables <https://docs.aws.amazon.com/vpc/latest/tgw/tgw-route-tables.html>`__ in the *Transit Gateways Guide*.