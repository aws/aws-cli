**To describe your egress-only Internet gateways**

The following ``describe-egress-only-internet-gateways`` example describes your egress-only Internet gateways. ::

    aws ec2 describe-egress-only-internet-gateways

Output::

    {
        "EgressOnlyInternetGateways": [
            {
                "EgressOnlyInternetGatewayId": "eigw-015e0e244e24dfe8a",
                "Attachments": [
                    {
                        "State": "attached",
                        "VpcId": "vpc-0c62a468"
                    }
                ]
            }
        ]
    }