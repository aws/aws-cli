**To delete a global network**

The following ``delete-global-network`` example deletes the specified global network. ::

    aws networkmanager delete-global-network \
        --global-network-id global-network-01231231231231231 \
        --region us-west-2

Output::

    {
        "GlobalNetwork": {
            "GlobalNetworkId": "global-network-01231231231231231",
            "GlobalNetworkArn": "arn:aws:networkmanager::123456789012:global-network/global-network-01231231231231231",
            "Description": "Head offices global network",
            "CreatedAt": 1575553525.0,
            "State": "DELETING"
        }
    }

For more information, see `Global Networks <https://docs.aws.amazon.com/vpc/latest/tgw/global-networks.html>`__ in the *Transit Gateway Network Manager Guide*.
