**To get your link associations**

The following ``get-link-associations`` example gets the link associations in the specified global network. ::

    aws networkmanager get-link-associations \
        --global-network-id global-network-01231231231231231

Output::

    {
        "LinkAssociations": [
            {
                "GlobalNetworkId": "global-network-01231231231231231",
                "DeviceId": "device-07f6fd08867abc123",
                "LinkId": "link-11112222aaaabbbb1",
                "LinkAssociationState": "AVAILABLE"
            }
        ]
    }

For more information, see `Associate or disassociate a device link using AWS Network Manager <https://docs.aws.amazon.com/network-manager/latest/tgwnm/nm-device-link-associate.html>`__ in the *AWS Global Networks for Transit Gateways User Guide*.
