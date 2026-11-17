**To describe the target networks for a Client VPN endpoint**

The following ``describe-client-vpn-target-networks`` example displays details about the target networks for the specified Client VPN endpoint. ::

    aws ec2 describe-client-vpn-target-networks \
        --client-vpn-endpoint-id cvpn-endpoint-123456789abcabcde

Output::

    {
        "ClientVpnTargetNetworks": [
            {
                "AssociationId": "cvpn-assoc-012e837060753dc3d",
                "VpcId": "vpc-11111222222333333",
                "TargetNetworkId": "subnet-0123456789abcabca",
                "ClientVpnEndpointId": "cvpn-endpoint-123456789abcabcde",
                "Status": {
                    "Code": "associating"
                },
                "SecurityGroups": [
                    "sg-0123456789aabcabc"
                ]
            }
        ]
    }

For more information, see `Target Networks <https://docs.aws.amazon.com/vpn/latest/clientvpn-admin/cvpn-working-target.html>`__ in the *AWS Client VPN Administrator Guide*.
