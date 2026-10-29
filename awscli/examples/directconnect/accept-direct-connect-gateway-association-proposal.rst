**To accept a gateway association proposal**

The following ``accept-direct-connect-gateway-association-proposal`` example accepts the specified proposal. ::

    aws directconnect accept-direct-connect-gateway-association-proposal \
        --direct-connect-gateway-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --proposal-id a1b2c3d4-5678-90ab-cdef-EXAMPLE22222 \
        --associated-gateway-owner-account 123456789012

Output::

    {
        "directConnectGatewayAssociation": {
            "directConnectGatewayId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "directConnectGatewayOwnerAccount": "123456789012",
            "associationState": "associating",
            "associatedGateway": {
                "id": "tgw-02f776b1a7EXAMPLE",
                "type": "transitGateway",
                "ownerAccount": "123456789012",
                "region": "us-west-2"
            },
            "associationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
            "allowedPrefixesToDirectConnectGateway": [
                {
                    "cidr": "192.168.1.0/30"
                }
            ]
        }
    }

For more information, see `Accept or reject a Transit Gateway and Direct Connect association proposal <https://docs.aws.amazon.com/directconnect/latest/UserGuide/multi-account-tgw-accept-reject-proposal.html>`__ in the *AWS Direct Connect User Guide*.
