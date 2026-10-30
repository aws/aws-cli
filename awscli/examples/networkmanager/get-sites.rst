**To get your sites**

The following ``get-sites`` example gets the sites in the specified global network. ::

    aws networkmanager get-sites \
        --global-network-id global-network-01231231231231231

Output::

    {
        "Sites": [
            {
                "SiteId": "site-444555aaabbb11223",
                "SiteArn": "arn:aws:networkmanager::123456789012:site/global-network-01231231231231231/site-444555aaabbb11223",
                "GlobalNetworkId": "global-network-01231231231231231",
                "Description": "NY head office",
                "Location": {
                    "Latitude": "40.7128",
                    "Longitude": "-74.0060"
                },
                "CreatedAt": 1575554528.0,
                "State": "AVAILABLE"
            }
        ]
    }

For more information, see `Sites and links in AWS Global Networks for Transit Gateways <https://docs.aws.amazon.com/network-manager/latest/tgwnm/nm-sites.html>`__ in the *AWS Global Networks for Transit Gateways User Guide*.
