**To create a core network**

The following ``create-core-network`` example creates a core network using an optional description and tags within an AWS Cloud WAN global network. ::

    aws networkmanager create-core-network \
        --global-network-id global-network-cdef-EXAMPLE22222 \
        --description "Main headquarters location" \
        --tags Key=Name,Value="New York City office"

Output::

    {
        "CoreNetwork": {
            "GlobalNetworkId": "global-network-cdef-EXAMPLE22222",
            "CoreNetworkId": "core-network-cdef-EXAMPLE33333",
            "CoreNetworkArn": "arn:aws:networkmanager::987654321012:core-network/core-network-cdef-EXAMPLE33333",
            "Description": "Main headquarters location",
            "CreatedAt": "2022-01-10T19:53:59+00:00",
            "State": "AVAILABLE",
            "Tags": [
                {
                    "Key": "Name",
                    "Value": "New York City office"
                }
            ]
        }
    }

For more information, see `Global and core networks <https://docs.aws.amazon.com/network-manager/latest/cloudwan/cloudwan-core-network-policy.html>`__ in the *AWS Cloud WAN User Guide*.