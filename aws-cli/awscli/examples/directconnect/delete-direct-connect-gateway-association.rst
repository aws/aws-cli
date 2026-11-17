**To delete a Direct Connect gateway association**

The following ``delete-direct-connect-gateway-association`` example deletes the Direct Connect gateway association with a transit gateway that has the specified association ID. ::

    aws directconnect delete-direct-connect-gateway-association \
        --association-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "directConnectGatewayAssociation": {
            "directConnectGatewayId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "directConnectGatewayOwnerAccount": "123456789012",
            "associationState": "disassociating",
            "associatedGateway": {
                "id": "tgw-095b3b0b54EXAMPLE",
                "type": "transitGateway",
                "ownerAccount": "123456789012",
                "region": "us-west-2"
            },
            "associationId": " be85116d-46eb-4b43-a27a-da0c2ad648deEXAMPLE ",
            "allowedPrefixesToDirectConnectGateway": [
                {
                    "cidr": "192.0.1.0/28"
                }
            ]
        }
    }

For more information, see `Associate or disassociate Direct Connect with a Transit Gateway <https://docs.aws.amazon.com/directconnect/latest/UserGuide/associate-tgw-with-direct-connect-gateway.html>`__ in the *AWS Direct Connect User Guide*.
