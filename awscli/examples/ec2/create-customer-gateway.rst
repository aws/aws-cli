**To create a customer gateway**

The following ``create-customer-gateway`` example creates a customer gateway with the specified IP address for its outside interface. ::

    aws ec2 create-customer-gateway \
        --type ipsec.1 \
        --public-ip 12.1.2.3 \
        --bgp-asn 65534

Output::

    {
        "CustomerGateway": {
            "CustomerGatewayId": "cgw-0e11f167",
            "IpAddress": "12.1.2.3",
            "State": "available",
            "Type": "ipsec.1",
            "BgpAsn": "65534"
        }
    }

For more information, see `AWS Site-to-Site VPN customer gateway devices <https://docs.aws.amazon.com/vpn/latest/s2svpn/your-cgw.html>`__ in the *AWS Site-to-Site VPN User Guide*.
