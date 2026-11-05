**To create a link**

The following ``create-link`` example creates a link in the specified global network. The link includes a description and details about the link type, bandwidth, and provider. The site ID indicates the site to which the link is associated. ::

    aws networkmanager create-link \
        --global-network-id global-network-01231231231231231 \
        --description "VPN Link" \
        --type "broadband" \
        --bandwidth UploadSpeed=10,DownloadSpeed=20 \
        --provider "AnyCompany" \
        --site-id site-444555aaabbb11223

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
                "UploadSpeed": 10,
                "DownloadSpeed": 20
            },
            "Provider": "AnyCompany",
            "CreatedAt": 1575555811.0,
            "State": "PENDING"
        }
    }

For more information, see `Sites and links in AWS Global Networks for Transit Gateways <https://docs.aws.amazon.com/network-manager/latest/tgwnm/nm-sites.html>`__ in the *Transit Gateway Network Manager Guide*.
