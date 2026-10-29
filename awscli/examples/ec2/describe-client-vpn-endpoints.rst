**To describe your Client VPN endpoints**

The following ``describe-client-vpn-endpoints`` example displays details about all of your Client VPN endpoints. ::

    aws ec2 describe-client-vpn-endpoints

Output::

    {
        "ClientVpnEndpoints": [
            {
                "ClientVpnEndpointId": "cvpn-endpoint-123456789abcabcde",
                "Description": "Endpoint for Admin access",
                "Status": {
                    "Code": "available"
                },
                "CreationTime": "2020-11-13T11:37:27",
                "DnsName": "*.cvpn-endpoint-123456789abcabcde.prod.clientvpn.us-west-2.amazonaws.com",
                "ClientCidrBlock": "172.31.0.0/16",
                "DnsServers": [
                    "8.8.8.8"
                ],
                "SplitTunnel": false,
                "VpnProtocol": "openvpn",
                "TransportProtocol": "udp",
                "VpnPort": 443,
                "ServerCertificateArn": "arn:aws:acm:us-west-2:123456789012:certificate/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "AuthenticationOptions": [
                    {
                        "Type": "certificate-authentication",
                        "MutualAuthentication": {
                            "ClientRootCertificateChain": "arn:aws:acm:us-west-2:123456789012:certificate/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
                        }
                    }
                ],
                "ConnectionLogOptions": {
                    "Enabled": true,
                    "CloudwatchLogGroup": "Client-vpn-connection-logs",
                    "CloudwatchLogStream": "cvpn-endpoint-123456789abcabcde-us-west-2-2020/11/13-FCD8HEMVaCcw"
                },
                "Tags": [
                    {
                        "Key": "Name",
                        "Value": "Client VPN"
                    }
                ],
                "SecurityGroupIds": [
                    "sg-aabbcc11223344567"
                ],
                "VpcId": "vpc-a87f92c1",
                "SelfServicePortalUrl": "https://self-service.clientvpn.amazonaws.com/endpoints/cvpn-endpoint-123456789abcabcde",
                "ClientConnectOptions": {
                    "Enabled": false
                }
            }
        ]
    }

For more information, see `Client VPN Endpoints <https://docs.aws.amazon.com/vpn/latest/clientvpn-admin/cvpn-working-endpoints.html>`__ in the *AWS Client VPN Administrator Guide*.
