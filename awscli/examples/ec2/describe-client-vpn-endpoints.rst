**To describe your Client VPN endpoints**

The following example displays details about all of your Client VPN endpoints. ::

    aws ec2 describe-client-vpn-endpoints

Output::

    {
        "ClientVpnEndpoints": [
            {
                "ClientVpnEndpointId": "cvpn-endpoint-123456789123abcde",
                "Description": "",
                "Status": {
                    "Code": "available"
                },
                "CreationTime": "2019-07-08T11:37:27",
                "DnsName": "*.cvpn-endpoint-123456789123abcde.prod.clientvpn.ap-south-1.amazonaws.com",
                "ClientCidrBlock": "172.31.0.0/16",
                "DnsServers": [
                    "8.8.8.8"
                ],
                "SplitTunnel": false,
                "VpnProtocol": "openvpn",
                "TransportProtocol": "udp",
                "ServerCertificateArn": "arn:aws:acm:ap-south-1:123456789012:certificate/a1b2c3d4-5678-90ab-cdef-11111EXAMPLE",
                "AuthenticationOptions": [
                    {
                        "Type": "certificate-authentication",
                        "MutualAuthentication": {
                            "ClientRootCertificateChain": "arn:aws:acm:ap-south-1:123456789012:certificate/a1b2c3d4-5678-90ab-cdef-22222EXAMPLE"
                        }
                    }
                ],
                "ConnectionLogOptions": {
                    "Enabled": false
                },
                "Tags": [
                    {
                        "Key": "Name",
                        "Value": "Client VPN"
                    }
                ]
            }
        ]
    }
