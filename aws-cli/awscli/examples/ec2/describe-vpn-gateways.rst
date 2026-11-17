**To describe your virtual private gateways**

The following ``describe-vpn-gateways`` example describes your virtual private gateways. ::

    aws ec2 describe-vpn-gateways

Output::

    {
        "VpnGateways": [
            {
                "State": "available",
                "Type": "ipsec.1",
                "VpnGatewayId": "vgw-f211f09b",
                "VpcAttachments": [
                    {
                        "State": "attached",
                        "VpcId": "vpc-98eb5ef5"
                    }
                ]
            },
            {
                "State": "available",
                "Type": "ipsec.1",
                "VpnGatewayId": "vgw-9a4cacf3",
                "VpcAttachments": [
                    {
                        "State": "attaching",
                        "VpcId": "vpc-a01106c2"
                    }
                ]
            }
        ]
    }

For more information, see `How AWS Site-to-Site VPN works <https://docs.aws.amazon.com/vpn/latest/s2svpn/how_it_works.html>`__ in the *AWS Site-to-Site VPN User Guide*.
