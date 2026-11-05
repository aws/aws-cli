**To create a site**

The following ``create-site`` example creates a site in the specified global network. The site details include a description and the location information. ::

    aws networkmanager create-site \
        --global-network-id global-network-01231231231231231 \
        --description "New York head office" \
        --location Latitude=40.7128,Longitude=-74.0060

Output::

    {
        "Site": {
            "SiteId": "site-444555aaabbb11223",
            "SiteArn": "arn:aws:networkmanager::123456789012:site/global-network-01231231231231231/site-444555aaabbb11223",
            "GlobalNetworkId": "global-network-01231231231231231",
            "Description": "New York head office",
            "Location": {
                "Latitude": "40.7128",
                "Longitude": "-74.0060"
            },
            "CreatedAt": 1575554300.0,
            "State": "PENDING"
        }
    }

For more information, see `Sites and links in AWS Global Networks for Transit Gateways <https://docs.aws.amazon.com/network-manager/latest/tgwnm/nm-sites.html>`__ in the *Transit Gateway Network Manager Guide*.
