**To describe Direct Connect gateway associations**

The following ``describe-direct-connect-gateway-associations`` example describes all the associations with Direct Connect gateway ``5f294f92-bafb-4011-916d-9b0bexample``. ::

    aws directconnect describe-direct-connect-gateway-associations \
        --direct-connect-gateway-id 5f294f92-bafb-4011-916d-9b0bexample

Output::

    {
        "nextToken": "eyJ2IjoxLCJzIjoxLCJpIjoiOU83OTFodzdycnZCbkN4MExHeHVwQT09IiwiYyI6InIxTEN0UEVHV0I1UFlkaWFnNlUxanJkRWF6eW1iOElHM0FRVW1MdHRJK0dxcnN1RWtvcFBKWFE2ZjRNRGdGTkhCa0tDZmVINEtZOEYwZ0dEYWZpbmU0ZnZMYVhKRjdXRVdENmdQZ1Y4d2w0PSJ9",
        "directConnectGatewayAssociations": [
            {
                "associationState": "associating",
                "virtualGatewayOwnerAccount": "123456789012",
                "directConnectGatewayId": "5f294f92-bafb-4011-916d-9b0bexample",
                "virtualGatewayId": "vgw-6efe725e",
                "virtualGatewayRegion": "us-west-2"
            },
            {
                "associationState": "disassociating",
                "virtualGatewayOwnerAccount": "123456789012",
                "directConnectGatewayId": "5f294f92-bafb-4011-916d-9b0bexample",
                "virtualGatewayId": "vgw-ebaa27db",
                "virtualGatewayRegion": "us-west-2"
            }
        ]
    }

For more information, see `Associate or disassociate Direct Connect virtual private gateways <https://docs.aws.amazon.com/directconnect/latest/UserGuide/associate-vgw-with-direct-connect-gateway.html>`__ in the *AWS Direct Connect User Guide*.
