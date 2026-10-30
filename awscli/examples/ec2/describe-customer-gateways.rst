**Example 1: To describe your customer gateways**

The following ``describe-customer-gateways`` example describes your customer gateways. ::

    aws ec2 describe-customer-gateways

Output::

    {
        "CustomerGateways": [
            {
                "CustomerGatewayId": "cgw-b4dc3961",
                "IpAddress": "203.0.113.12",
                "State": "available",
                "Type": "ipsec.1",
                "BgpAsn": "65000"
            },
            {
                "CustomerGatewayId": "cgw-0e11f167",
                "IpAddress": "12.1.2.3",
                "State": "available",
                "Type": "ipsec.1",
                "BgpAsn": "65534"
            }
        ]
    }

For more information, see `AWS Site-to-Site VPN customer gateway devices <https://docs.aws.amazon.com/vpn/latest/s2svpn/your-cgw.html>`__ in the *AWS Site-to-Site VPN User Guide*.

**Example 2: To describe a specific customer gateway**

The following ``describe-customer-gateways`` example describes the specified customer gateway. ::

    aws ec2 describe-customer-gateways \
        --customer-gateway-ids cgw-0e11f167

Output::

    {
        "CustomerGateways": [
            {
                "CustomerGatewayId": "cgw-0e11f167",
                "IpAddress": "12.1.2.3",
                "State": "available",
                "Type": "ipsec.1",
                "BgpAsn": "65534"
            }
        ]
    }

For more information, see `AWS Site-to-Site VPN customer gateway devices <https://docs.aws.amazon.com/vpn/latest/s2svpn/your-cgw.html>`__ in the *AWS Site-to-Site VPN User Guide*.
