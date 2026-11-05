**To update the specified attributes of the Direct Connect gateway association**

The following ``update-direct-connect-gateway-association`` example adds the specified CIDR block to a Direct Connect gateway association. ::

    aws directconnect update-direct-connect-gateway-association \
        --association-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --add-allowed-prefixes-to-direct-connect-gateway cidr=192.168.2.0/30

Output::

    {
        "directConnectGatewayAssociation": {
            "directConnectGatewayId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "directConnectGatewayOwnerAccount": "123456789012",
            "associationState": "updating",
            "associatedGateway": {
                "id": "tgw-02f776b1a7EXAMPLE",
                "type": "transitGateway",
                "ownerAccount": "123456789012",
                "region": "us-west-2"
            },
            "associationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "allowedPrefixesToDirectConnectGateway": [
                {
                    "cidr": "192.168.2.0/30"
                },
                {
                    "cidr": "192.168.1.0/30"
                }
            ]
        }
    }

For more information, see `Working with Direct Connect Gateways <https://docs.aws.amazon.com/directconnect/latest/UserGuide/direct-connect-gateways.html>`__ in the *AWS Direct Connect User Guide*.
