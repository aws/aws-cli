**To create a Direct Connect gateway**

The following ``create-direct-connect-gateway`` example creates a Direct Connect gateway with the name ``DxGateway1``. ::

    aws directconnect create-direct-connect-gateway \
        --direct-connect-gateway-name "DxGateway1"

Output::

    {
        "directConnectGateway": {
            "amazonSideAsn": 64512,
            "directConnectGatewayId": "5f294f92-bafb-4011-916d-9b0bdexample",
            "ownerAccount": "123456789012",
            "directConnectGatewayName": "DxGateway1",
            "directConnectGatewayState": "available"
        }
    }

For more information, see `Create a Direct Connect gateway <https://docs.aws.amazon.com/directconnect/latest/UserGuide/create-direct-connect-gateway.html>`__ in the *AWS Direct Connect User Guide*.
