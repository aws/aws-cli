**Example 1: To create a virtual private gateway**

The following ``create-vpn-gateway`` example creates a virtual private gateway. ::

    aws ec2 create-vpn-gateway \
        --type ipsec.1

Output::

    {
        "VpnGateway": {
            "AmazonSideAsn": 64512,
            "State": "available",
            "Type": "ipsec.1",
            "VpnGatewayId": "vgw-9a4cacf3",
            "VpcAttachments": []
        }
    }

For more information, see `How AWS Site-to-Site VPN works <https://docs.aws.amazon.com/vpn/latest/s2svpn/how_it_works.html>`__ in the *AWS Site-to-Site VPN User Guide*.

**Example 2: To create a virtual private gateway with a specific Amazon-side ASN**

The following ``create-vpn-gateway`` example creates a virtual private gateway and specifies the Autonomous System Number (ASN) for the Amazon side of the BGP session. ::

    aws ec2 create-vpn-gateway \
        --type ipsec.1 \
        --amazon-side-asn 65001

Output::

    {
        "VpnGateway": {
            "AmazonSideAsn": 65001,
            "State": "available",
            "Type": "ipsec.1",
            "VpnGatewayId": "vgw-9a4cacf3",
            "VpcAttachments": []
        }
    }

For more information, see `How AWS Site-to-Site VPN works <https://docs.aws.amazon.com/vpn/latest/s2svpn/how_it_works.html>`__ in the *AWS Site-to-Site VPN User Guide*.
