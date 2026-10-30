**To describe your Direct Connect gateway association proposals**

The following ``describe-direct-connect-gateway-association-proposals`` example displays details about your Direct Connect gateway association proposals. ::

    aws directconnect describe-direct-connect-gateway-association-proposals

Output::

    {
        "directConnectGatewayAssociationProposals": [
            {
                "proposalId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "directConnectGatewayId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "directConnectGatewayOwnerAccount": "123456789012",
                "proposalState": "requested",
                "associatedGateway": {
                    "id": "tgw-02f776b1a7EXAMPLE",
                    "type": "transitGateway",
                    "ownerAccount": "123456789012",
                    "region": "us-west-2"
                },
                "existingAllowedPrefixesToDirectConnectGateway": [
                    {
                        "cidr": "192.168.2.0/30"
                    },
                    {
                        "cidr": "192.168.1.0/30"
                    }
                ],
                "requestedAllowedPrefixesToDirectConnectGateway": [
                    {
                        "cidr": "192.168.1.0/30"
                    }
                ]
            },
            {
                "proposalId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "directConnectGatewayId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "directConnectGatewayOwnerAccount": "123456789012",
                "proposalState": "accepted",
                "associatedGateway": {
                    "id": "tgw-045776b1a7EXAMPLE",
                    "type": "transitGateway",
                    "ownerAccount": "123456789012",
                    "region": "us-west-2"
                },
                "existingAllowedPrefixesToDirectConnectGateway": [
                    {
                        "cidr": "192.168.4.0/30"
                    },
                    {
                        "cidr": "192.168.5.0/30"
                    }
                ],
                "requestedAllowedPrefixesToDirectConnectGateway": [
                    {
                        "cidr": "192.168.5.0/30"
                    }
                ]
            }
        ]
    }

For more information, see `Associating and Disassociating Transit Gateways <https://docs.aws.amazon.com/directconnect/latest/UserGuide/associate-tgw-with-direct-connect-gateway.html>`__ in the *AWS Direct Connect User Guide*.
