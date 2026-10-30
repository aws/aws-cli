**To create an egress-only Internet gateway**

The following ``create-egress-only-internet-gateway`` example creates an egress-only Internet gateway for the specified VPC. ::

    aws ec2 create-egress-only-internet-gateway \
        --vpc-id vpc-0c62a468

Output::

    {
        "EgressOnlyInternetGateway": {
            "EgressOnlyInternetGatewayId": "eigw-015e0e244e24dfe8a",
            "Attachments": [
                {
                    "State": "attached",
                    "VpcId": "vpc-0c62a468"
                }
            ]
        }
    }

For more information, see `Enable outbound IPv6 traffic using an egress-only internet gateway <https://docs.aws.amazon.com/vpc/latest/userguide/egress-only-internet-gateway.html>`__ in the *Amazon VPC User Guide*.
