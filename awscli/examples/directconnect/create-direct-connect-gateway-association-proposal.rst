**To create a proposal to associate the specified transit gateway with the specified Direct Connect gateway**

The following ``create-direct-connect-gateway-association-proposal`` example creates a proposal that associates the specified transit gateway with the specified Direct Connect gateway. ::

    aws directconnect create-direct-connect-gateway-association-proposal \
        --direct-connect-gateway-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --direct-connect-gateway-owner-account 123456789012 \
        --gateway-id tgw-02f776b1a7EXAMPLE \
        --add-allowed-prefixes-to-direct-connect-gateway cidr=192.168.1.0/30

Output::

    {
        "directConnectGatewayAssociationProposal": {
            "proposalId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "directConnectGatewayId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "directConnectGatewayOwnerAccount": "123456789012",
            "proposalState": "requested",
            "associatedGateway": {
                "id": "tgw-02f776b1a7EXAMPLE",
                "type": "transitGateway",
                "ownerAccount": "123456789012",
                "region": "us-west-2"
            },
            "requestedAllowedPrefixesToDirectConnectGateway": [
                {
                    "cidr": "192.168.1.0/30"
                }
            ]
        }
    }

For more information, see `Create a Transit Gateway and Direct Connect association proposal <https://docs.aws.amazon.com/directconnect/latest/UserGuide/multi-account-tgw-create-proposal.html>`__ in the *AWS Direct Connect User Guide*.
