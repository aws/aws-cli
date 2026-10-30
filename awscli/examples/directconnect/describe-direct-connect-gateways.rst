**To describe your Direct Connect gateways**

The following ``describe-direct-connect-gateways`` example describes all of your Direct Connect gateways. ::

    aws directconnect describe-direct-connect-gateways

Output::

    {
        "directConnectGateways": [
            {
                "amazonSideAsn": 64512,
                "directConnectGatewayId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "ownerAccount": "123456789012",
                "directConnectGatewayName": "DxGateway2",
                "directConnectGatewayState": "available"
            },
            {
                "amazonSideAsn": 64512,
                "directConnectGatewayId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "ownerAccount": "123456789012",
                "directConnectGatewayName": "DxGateway1",
                "directConnectGatewayState": "available"
            }
        ]
    }

For more information, see `Direct Connect gateways <https://docs.aws.amazon.com/directconnect/latest/UserGuide/direct-connect-gateways.html>`__ in the *AWS Direct Connect User Guide*.
