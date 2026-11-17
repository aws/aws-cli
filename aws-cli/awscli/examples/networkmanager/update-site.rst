**To update a site**

The following ``update-site`` example updates the description for site ``site-444555aaabbb11223`` in the specified global network. ::

    aws networkmanager update-site \
        --global-network-id global-network-01231231231231231 \
        --site-id site-444555aaabbb11223 \
        --description "New York Office site"

Output::

    {
        "Site": {
            "SiteId": "site-444555aaabbb11223",
            "SiteArn": "arn:aws:networkmanager::123456789012:site/global-network-01231231231231231/site-444555aaabbb11223",
            "GlobalNetworkId": "global-network-01231231231231231",
            "Description": "New York Office site",
            "Location": {
                "Latitude": "40.7128",
                "Longitude": "-74.0060"
            },
            "CreatedAt": 1575554528.0,
            "State": "UPDATING"
        }
    }

For more information, see `Sites and links in AWS Global Networks for Transit Gateways <https://docs.aws.amazon.com/network-manager/latest/tgwnm/nm-sites.html>`__ in the *Transit Gateway Network Manager Guide*.
