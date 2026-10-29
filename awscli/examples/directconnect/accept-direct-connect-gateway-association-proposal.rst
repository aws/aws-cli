**To accept a gateway association proposal**

The following ``accept-direct-connect-gateway-association-proposal`` example accepts the specified proposal. ::

    aws directconnect accept-direct-connect-gateway-association-proposal \
        --direct-connect-gateway-id 11460968-4ac1-4fd3-bdb2-00599EXAMPLE \
        --proposal-id cb7f41cb-8128-43a5-93b1-dcaedEXAMPLE \
        --associated-gateway-owner-account 111122223333

Output::

    {
        "directConnectGatewayAssociation": {
            "directConnectGatewayId": "11460968-4ac1-4fd3-bdb2-00599EXAMPLE",
            "directConnectGatewayOwnerAccount": "111122223333",
            "associationState": "associating",
            "associatedGateway": {
                "id": "tgw-02f776b1a7EXAMPLE",
                "type": "transitGateway",
                "ownerAccount": "111122223333",
                "region": "us-east-1"
            },
            "associationId": "6441f8bf-5917-4279-ade1-9708bEXAMPLE",
            "allowedPrefixesToDirectConnectGateway": [
                {
                    "cidr": "192.168.1.0/30"
                }
            ]
        }
    }

For more information, see `Accept or reject a Transit Gateway and Direct Connect association proposal <https://docs.aws.amazon.com/directconnect/latest/UserGuide/multi-account-tgw-accept-reject-proposal.html>`__ in the *AWS Direct Connect User Guide*.
