**To create a global network**

The following ``create-global-network`` example creates a new global network in your account with the description 'My global network'. ::

    aws networkmanager create-global-network \
        --description "Head offices global network" \
        --region us-west-2

Output::

    {
        "GlobalNetwork": {
            "GlobalNetworkId": "global-network-01231231231231231",
            "GlobalNetworkArn": "arn:aws:networkmanager::123456789012:global-network/global-network-01231231231231231",
            "Description": "Head offices global network",
            "CreatedAt": 1575553525.0,
            "State": "PENDING"
        }
    }

For more information, see `Global Networks <https://docs.aws.amazon.com/vpc/latest/tgw/global-networks.html>`__ in the *Transit Gateway Network Manager Guide*.
