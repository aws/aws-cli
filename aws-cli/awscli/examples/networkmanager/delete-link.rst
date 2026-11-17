**To delete a link**

The following ``delete-link`` example deletes the specified link from the specified global network. ::

    aws networkmanager delete-link \
        --global-network-id global-network-01231231231231231 \
        --link-id link-11112222aaaabbbb1

Output::

    {
        "Link": {
            "LinkId": "link-11112222aaaabbbb1",
            "LinkArn": "arn:aws:networkmanager::123456789012:link/global-network-01231231231231231/link-11112222aaaabbbb1",
            "GlobalNetworkId": "global-network-01231231231231231",
            "SiteId": "site-444555aaabbb11223",
            "Description": "VPN Link",
            "Type": "broadband",
            "Bandwidth": {
                "UploadSpeed": 20,
                "DownloadSpeed": 20
            },
            "Provider": "AnyCompany",
            "CreatedAt": 1575555811.0,
            "State": "DELETING"
        }
    }

For more information, see `Sites and links in AWS Global Networks for Transit Gateways <https://docs.aws.amazon.com/network-manager/latest/tgwnm/nm-sites.html>`__ in the *Transit Gateway Network Manager Guide*.
