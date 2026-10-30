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

For more information, see `Enable outbound IPv6 traffic using an egress-only internet gateway <https://docs.aws.amazon.com/vpc/latest/userguide/egress-only-internet-gateway.html>`__ in the *Amazon VPC User Guide*.
